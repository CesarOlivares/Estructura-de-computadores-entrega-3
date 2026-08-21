"""
Capa de datos del tablero.

Toda la comunicacion con el resto del sistema pasa por aqui: app.py solo dibuja.
No hay simulacion ni datos de ejemplo. Si un servicio no responde, se dice.

De donde sale cada cosa
-----------------------

    metrics-api  GET /metricas?ventana_s=N   espera, servicio, en_cola y
                                             procesadas por etapa + lead time
    metrics-api  GET /metricas/cuello        que etapa esta atascada y por que
    orders-api   POST /ordenes               ingresar un lote (interaccion real)
    Redis        HGETALL estado:replicas     carga de cada replica

La ultima merece explicacion. metrics-api entrega numeros por ETAPA, pero no por
REPLICA, y el enunciado pide un indicador de carga por replica. Cada estacion
publica su propio latido en el hash `estado:replicas` de Redis justamente para
que alguien lo observe (ver publicar_estado() en servicios/estacion/worker.py).
Leer ese hash es usarlo para lo que fue hecho, y evita tener que descubrir
cuantas replicas hay ni en que puerto vive cada una, que con `--scale` no es
fijo.

El historico no lo entrega ningun servicio: lo arma el tablero muestreando
/metricas en cada refresco. Vive en memoria de la sesion, asi que se reinicia
al recargar la pagina. Es suficiente para ver una tendencia en vivo, que es
para lo que sirve.
"""

import json
import os
from datetime import datetime, timezone

import redis
import requests

URL_ORDENES = os.environ.get("URL_ORDENES", "http://ordenes:8000")
URL_METRICAS = os.environ.get("URL_METRICAS", "http://metricas:8001")
TIMEOUT = float(os.environ.get("TIMEOUT_HTTP", "3"))

# Orden fisico de la linea. Es el orden en que se dibujan las etapas.
ETAPAS = os.environ.get(
    "ETAPAS", "fileteado,envasado,sellado,esterilizacion").split(",")

# Un latido mas viejo que esto significa que esa replica ya no esta corriendo:
# el hash de Redis conserva la entrada aunque el contenedor se haya detenido.
LATIDO_VENCIDO_S = float(os.environ.get("LATIDO_VENCIDO_S", "30"))

_redis = redis.Redis(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    decode_responses=True,
    # Sin estos timeouts, una consulta a un Redis caido se queda esperando el
    # timeout de TCP del sistema operativo, que son minutos. El tablero se
    # congelaria en vez de avisar.
    socket_timeout=2,
    socket_connect_timeout=2,
)


class ErrorDeServicio(Exception):
    """Un servicio no respondio.

    app.py lo traduce a un mensaje que se entienda. Existe para que la UI nunca
    muestre un traceback: el enunciado pide mensajes claros en la interfaz.
    """


def _get(url, **params):
    try:
        respuesta = requests.get(url, timeout=TIMEOUT, params=params or None)
    except requests.Timeout as error:
        raise ErrorDeServicio(f"{url} no respondió en {TIMEOUT:g} s") from error
    except requests.RequestException as error:
        raise ErrorDeServicio(f"no hay conexión con {url}") from error
    if respuesta.status_code >= 500:
        raise ErrorDeServicio(f"{url} respondió {respuesta.status_code}")
    return respuesta.json()


def diagnostico():
    """Explica en castellano cual es la causa mas probable de una falla.

    Hace falta porque el sintoma engaña. Si Redis se cae, orders-api y
    metrics-api SIGUEN vivos —su /salud responde al instante porque no consulta
    Redis— pero cualquier peticion que si lo consulte se queda esperando. Desde
    fuera parece que el servicio lento es el que falla, cuando el que falta es
    Redis.

    Decir "no responde órdenes" cuando el problema es Redis manda a buscar el
    error al lugar equivocado.
    """
    estado = salud()
    caidos = [nombre for nombre, valor in estado.items() if valor != "ok"]

    if estado.get("Redis") != "ok":
        return ("**Redis no está respondiendo.** Es el servicio que coordina las "
                "colas, así que los demás quedan esperándolo aunque sigan vivos. "
                "Revísalo con `docker compose ps` y levántalo con "
                "`docker compose start redis`.")
    if caidos:
        return (f'**Sin respuesta de: {", ".join(caidos)}.** '
                "Revisa `docker compose ps` y los registros con "
                "`docker compose logs <servicio>`.")
    return ("Los servicios responden pero la consulta tardó demasiado. Puede que "
            "aún estén arrancando: espera unos segundos.")


# --------------------------------------------------------------------------
# Consultas sueltas
# --------------------------------------------------------------------------

def salud():
    """Estado de cada servicio, para el panel lateral. Nunca lanza excepcion."""
    estado = {}
    for nombre, url in (("Órdenes", URL_ORDENES), ("Métricas", URL_METRICAS)):
        try:
            respuesta = requests.get(f"{url}/salud", timeout=TIMEOUT)
            estado[nombre] = ("ok" if respuesta.status_code == 200
                              else f"responde {respuesta.status_code}")
        except requests.RequestException:
            estado[nombre] = "sin conexión"
    try:
        _redis.ping()
        estado["Redis"] = "ok"
    except redis.RedisError:
        estado["Redis"] = "sin conexión"
    return estado


def crear_orden(producto, cantidad):
    """Ingresa un lote a la linea. Devuelve (ok, mensaje).

    Traduce cada codigo HTTP a algo que el operador pueda entender, en vez de
    mostrarle el numero pelado.
    """
    try:
        respuesta = requests.post(f"{URL_ORDENES}/ordenes",
                                  json={"producto": producto, "cantidad": cantidad},
                                  timeout=TIMEOUT)
    except requests.Timeout:
        # No decir "no hay conexión con órdenes": el servicio puede estar vivo y
        # atascado esperando a Redis. Ver diagnostico().
        return False, ("El servicio de órdenes no respondió a tiempo. "
                       "Revisa el estado de los servicios más abajo.")
    except requests.RequestException:
        return False, "No hay conexión con el servicio de órdenes."

    if respuesta.status_code == 201:
        return True, f'Lote #{respuesta.json()["id"]} ingresado a la línea.'
    if respuesta.status_code == 422:
        return False, "La cantidad de latas debe ser un número entero mayor que 0."
    if respuesta.status_code == 503:
        return False, ("El servicio de coordinación (Redis) no responde. "
                       "El lote no se creó; puedes reintentar.")
    return False, f"El servicio de órdenes respondió {respuesta.status_code}."


def replicas_por_etapa():
    """Lee el hash `estado:replicas` y agrupa las replicas vivas por etapa.

    Cada estacion publica ahi un JSON con etapa, replica_id, procesadas,
    ocupada, tiempo_ciclo y actualizado_en.

    Devuelve {} si Redis no responde: el resto del tablero sigue siendo valido
    sin el detalle por replica.
    """
    try:
        crudo = _redis.hgetall("estado:replicas")
    except redis.RedisError:
        return {}

    ahora = datetime.now(timezone.utc)
    por_etapa = {}
    for replica_id, texto in crudo.items():
        try:
            datos = json.loads(texto)
        except (ValueError, TypeError):
            continue  # entrada corrupta: se ignora, no se cae el tablero

        # Descartar replicas que dejaron de latir (contenedor detenido). Su
        # entrada queda en el hash para siempre si no se limpia.
        try:
            visto = datetime.fromisoformat(datos["actualizado_en"])
            if (ahora - visto).total_seconds() > LATIDO_VENCIDO_S:
                continue
        except (KeyError, ValueError):
            pass  # sin marca de tiempo legible, se muestra igual

        datos["replica_id"] = replica_id
        # Una replica configurada mas lenta lleva prefijo propio (PREFIJO_REPLICA
        # en el compose). Es el experimento de balanceo de la Fase 7.
        datos["lenta"] = replica_id.startswith(f'{datos.get("etapa", "")}-lento')
        por_etapa.setdefault(datos.get("etapa"), []).append(datos)

    for lista in por_etapa.values():
        lista.sort(key=lambda replica: replica["replica_id"])
    return por_etapa


# --------------------------------------------------------------------------
# El tablero completo
# --------------------------------------------------------------------------

def tablero(ventana_s):
    """Junta metricas, cuello de botella y replicas en una sola estructura.

    Es lo unico que app.py necesita para dibujar la pantalla entera.
    """
    metricas = _get(f"{URL_METRICAS}/metricas", ventana_s=ventana_s)
    cuello = _get(f"{URL_METRICAS}/metricas/cuello", ventana_s=ventana_s)
    replicas = replicas_por_etapa()

    estados = cuello.get("estados", {})
    etapas = []
    for nombre in ETAPAS:
        datos = metricas.get("etapas", {}).get(nombre, {})
        suyas = replicas.get(nombre, [])
        etapas.append({
            "etapa": nombre,
            "espera": datos.get("espera_promedio_s"),
            "servicio": datos.get("servicio_promedio_s"),
            "en_cola": datos.get("en_cola"),
            "procesadas": datos.get("procesadas", 0),
            "estado": estados.get(nombre, "normal"),
            "replicas": suyas,
            # El tiempo de ciclo configurado lo reporta cada replica en su
            # latido; no hace falta repetirlo en la UI.
            "tiempo_ciclo": suyas[0]["tiempo_ciclo"] if suyas else None,
        })

    # Lotes dentro de la linea = los que hacen cola + los que se estan
    # procesando ahora. Se deduce de datos que ya tenemos, sin pedir la lista
    # completa de ordenes en cada refresco.
    esperando = sum(e["en_cola"] or 0 for e in etapas)
    procesando = sum(1 for lista in replicas.values()
                     for replica in lista if replica.get("ocupada"))
    # Terminados = cuantas veces termino la ULTIMA etapa.
    terminados = etapas[-1]["procesadas"] if etapas else 0

    return {
        "ventana_s": metricas.get("ventana_s", ventana_s),
        "etapas": etapas,
        "cuello": cuello,
        "lead_time": metricas.get("lead_time_promedio_s"),
        "esperando": esperando,
        "procesando": procesando,
        "en_la_linea": esperando + procesando,
        "terminados": terminados,
        "hay_replicas": bool(replicas),
    }
