"""Worker de estación — un solo programa para las cuatro etapas de la línea.

Qué etapa es, de qué cola come y a cuál escupe, y cuánto tarda su ciclo, todo
viene por variables de entorno (nunca escrito en el código):

    NOMBRE_ETAPA=envasado
    COLA_ENTRADA=cola:envasado
    COLA_SALIDA=cola:sellado
    TIEMPO_CICLO=12

Estructura: el ciclo de trabajo corre en un hilo (BRPOP bloqueante → esperar
TIEMPO_CICLO → LPUSH a la salida) y el hilo principal atiende HTTP con
GET /estado y GET /salud. Además cada réplica publica su estado en el hash
`estado:replicas` de Redis, para que métricas y UI vean todas las réplicas
sin tener que descubrirlas una por una.
"""

import json
import os
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as PlazoAgotado
from datetime import datetime, timezone

import redis
import uvicorn
from fastapi import FastAPI

import bd
from comun import reclamo

NOMBRE_ETAPA = os.environ["NOMBRE_ETAPA"]
COLA_ENTRADA = os.environ["COLA_ENTRADA"]
COLA_SALIDA = os.environ["COLA_SALIDA"]
TIEMPO_CICLO = float(os.environ["TIEMPO_CICLO"])
PUERTO = int(os.environ.get("PUERTO", "8080"))

# La última etapa es la que desemboca en cola:listos: además de empujar la
# orden, la marca como terminada en la base.
ES_ULTIMA_ETAPA = COLA_SALIDA == "cola:listos"
ETAPA_SIGUIENTE = COLA_SALIDA.split(":", 1)[1]  # "cola:sellado" -> "sellado"

# Cómo reclama trabajo la réplica: "atomico" (BRPOP, UNA operación — el modo
# correcto y el default) o "ingenuo" (mirar y después sacar, DOS operaciones
# con una ventana entre medio). Las dos implementaciones viven en
# comun/reclamo.py, compartidas con la demostración del tablero. El ingenuo se
# conserva solo para reproducir la condición de carrera; ver
# experimentos/fase6_carrera.sh y la sección de demostración de la UI.
MODO_RECLAMO = os.environ.get("MODO_RECLAMO", "atomico")
# Pausa artificial dentro de la ventana del modo ingenuo, para hacer visible
# en segundos un problema que en la realidad ocurre en microsegundos.
DEMORA_INGENUA = float(os.environ.get("DEMORA_INGENUA", reclamo.DEMORA_INGENUA_S))

# Identidad de la réplica: etapa + hostname del contenedor (único por réplica).
# PREFIJO_REPLICA permite distinguir variantes (p. ej. una réplica lenta).
REPLICA_ID = f"{os.environ.get('PREFIJO_REPLICA', NOMBRE_ETAPA)}-{socket.gethostname()}"

r = redis.Redis(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    decode_responses=True,
    # Fase 12: si Redis se cae, sin timeout de conexión el BRPOP se quedaría
    # esperando el timeout de TCP del sistema operativo en vez de entrar al
    # reintento del bucle. El socket_timeout debe ser MAYOR que el timeout del
    # BRPOP (2 s): si no, cortaría conexiones sanas que solo están bloqueadas
    # esperando trabajo.
    socket_timeout=5,
    socket_connect_timeout=2,
)

# Estado local de la réplica (contrato de GET /estado en docs/diseno.md §1.2).
# Lo modifica solo el hilo del worker; HTTP únicamente lo lee.
estado_local = {
    "etapa": NOMBRE_ETAPA,
    "replica_id": REPLICA_ID,
    "procesadas": 0,
    "ocupada": False,
}


def log(mensaje: str) -> None:
    """Toda línea de log lleva el replica_id para poder seguir quién hizo qué."""
    print(f"[{REPLICA_ID}] {mensaje}", flush=True)


def publicar_estado() -> None:
    """Latido de la réplica: su estado + tiempo de ciclo, con marca de tiempo."""
    datos = {
        **estado_local,
        "tiempo_ciclo": TIEMPO_CICLO,
        "actualizado_en": datetime.now(timezone.utc).isoformat(),
    }
    try:
        r.hset("estado:replicas", REPLICA_ID, json.dumps(datos))
    except redis.exceptions.RedisError:
        pass  # sin Redis no hay dónde publicar; el ciclo del worker ya reintenta


# --- Ciclo del worker -------------------------------------------------------


def ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def registrar_inicio(orden_id: str) -> None:
    """Evento `inicia`: esta réplica tomó la orden de su cola."""
    with bd.transaccion() as con:
        con.execute(
            "INSERT INTO eventos (orden_id, etapa, replica_id, tipo, timestamp)"
            " VALUES (?, ?, ?, ?, ?)",
            (orden_id, NOMBRE_ETAPA, REPLICA_ID, "inicia", ahora_iso()),
        )


def registrar_termino(orden_id: str) -> None:
    """Evento `termina`; si esta es la última etapa, además cierra la orden;
    si no, registra el `entra_cola` de la etapa siguiente (lo escribe quien
    encola, según docs/diseno.md §2)."""
    ahora = ahora_iso()
    with bd.transaccion() as con:
        con.execute(
            "INSERT INTO eventos (orden_id, etapa, replica_id, tipo, timestamp)"
            " VALUES (?, ?, ?, ?, ?)",
            (orden_id, NOMBRE_ETAPA, REPLICA_ID, "termina", ahora),
        )
        if ES_ULTIMA_ETAPA:
            con.execute(
                "UPDATE ordenes SET estado = 'terminada', terminada_en = ? WHERE id = ?",
                (ahora, orden_id),
            )
        else:
            con.execute(
                "INSERT INTO eventos (orden_id, etapa, replica_id, tipo, timestamp)"
                " VALUES (?, ?, ?, ?, ?)",
                (orden_id, ETAPA_SIGUIENTE, REPLICA_ID, "entra_cola", ahora),
            )


def bucle_worker() -> None:
    log(f"lista: {COLA_ENTRADA} -> {COLA_SALIDA}, ciclo {TIEMPO_CICLO}s, reclamo {MODO_RECLAMO}")
    reclamar = reclamo.reclamador(MODO_RECLAMO, DEMORA_INGENUA)
    while True:
        try:
            orden_id = reclamar(r, COLA_ENTRADA)
            if orden_id is None:
                publicar_estado()  # latido periódico aunque no haya trabajo
                continue
            estado_local["ocupada"] = True
            publicar_estado()
            log(f"procesando orden {orden_id}")
            registrar_inicio(orden_id)
            time.sleep(TIEMPO_CICLO)  # simula el ciclo de la máquina
            registrar_termino(orden_id)
            r.lpush(COLA_SALIDA, orden_id)
            estado_local["procesadas"] += 1
            estado_local["ocupada"] = False
            # Conteos en Redis para los experimentos: cuántas veces se procesó
            # cada orden (detector de duplicados) y cuánto procesó cada réplica.
            #
            # El detector de duplicados va POR ETAPA. Con un hash único para
            # toda la línea, el mismo orden_id lo incrementarían las cuatro
            # estaciones a medida que el lote avanza, y el avance normal de un
            # lote se leería como si lo hubieran procesado cuatro veces. Lo que
            # se quiere detectar es que DOS RÉPLICAS DE LA MISMA ETAPA tomaron
            # el mismo lote; comparar entre etapas no significa nada.
            r.hincrby(f"conteo:procesadas:{NOMBRE_ETAPA}", orden_id, 1)
            # Este sí es global: la clave ya lleva la etapa dentro del
            # replica_id, así que no hay ambigüedad que resolver.
            r.hincrby("conteo:replica", REPLICA_ID, 1)
            publicar_estado()
            log(f"orden {orden_id} terminada ({estado_local['procesadas']} en total)")
        except redis.exceptions.RedisError as error:
            estado_local["ocupada"] = False
            log(f"sin conexión con Redis ({error}); reintento en 2 s")
            time.sleep(2)


# --- API HTTP de la réplica (docs/diseno.md §1.2) ---------------------------

app = FastAPI(title=f"estacion-{NOMBRE_ETAPA}")


# Plazo duro para el LLEN de /estado (Fase 12): socket_connect_timeout no
# cubre la resolución DNS, y con Redis detenido getaddrinfo tarda ~45 s en
# rendirse — /estado se colgaría. El hilo del worker no lo necesita: a él un
# reintento lento no le bloquea nada.
PLAZO_REDIS_S = float(os.environ.get("PLAZO_REDIS_S", "2"))
_hilos_estado = ThreadPoolExecutor(max_workers=2)


@app.get("/estado")
def get_estado() -> dict:
    """Estado de ESTA réplica; en_cola es el largo actual de su cola de entrada."""
    futuro = _hilos_estado.submit(r.llen, COLA_ENTRADA)
    try:
        en_cola = futuro.result(timeout=PLAZO_REDIS_S)
    except (PlazoAgotado, redis.exceptions.RedisError):
        futuro.cancel()
        en_cola = None  # sin Redis no se puede saber; el resto sigue siendo válido
    return {**estado_local, "en_cola": en_cola}


@app.get("/salud")
def salud() -> dict:
    """Healthcheck: si responde, el servicio está vivo."""
    return {"estado": "ok"}


if __name__ == "__main__":
    bd.inicializar()  # el primer servicio en llegar crea las tablas
    threading.Thread(target=bucle_worker, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=PUERTO, log_level="warning")
