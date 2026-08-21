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
from datetime import datetime, timezone

import redis
import uvicorn
from fastapi import FastAPI

import bd

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
# con una ventana entre medio). El ingenuo se conserva solo para reproducir
# la condición de carrera en demos; ver experimentos/fase6_carrera.sh.
MODO_RECLAMO = os.environ.get("MODO_RECLAMO", "atomico")
# Pausa artificial dentro de la ventana del modo ingenuo, para hacer visible
# en segundos un problema que en la realidad ocurre en microsegundos.
DEMORA_INGENUA = float(os.environ.get("DEMORA_INGENUA", "0.1"))

# Identidad de la réplica: etapa + hostname del contenedor (único por réplica).
# PREFIJO_REPLICA permite distinguir variantes (p. ej. una réplica lenta).
REPLICA_ID = f"{os.environ.get('PREFIJO_REPLICA', NOMBRE_ETAPA)}-{socket.gethostname()}"

r = redis.Redis(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    decode_responses=True,
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


# --- Reclamo de órdenes -----------------------------------------------------


def reclamar_atomico():
    """Reclamo correcto: BRPOP saca el elemento en UNA operación indivisible.

    Redis garantiza que cada elemento se entrega a exactamente una réplica,
    aunque haya varias esperando sobre la misma cola.
    """
    resultado = r.brpop(COLA_ENTRADA, timeout=2)
    return None if resultado is None else resultado[1]


def reclamar_ingenuo():
    """Reclamo INTENCIONALMENTE ROTO, para demostrar la condición de carrera.

    Separa el reclamo en dos operaciones: (1) mirar el último elemento con
    LRANGE, (2) sacarlo con LREM. Entre ambas hay una ventana en la que otra
    réplica puede mirar la cola y ver LA MISMA orden. Las dos la "reclaman",
    las dos la procesan: orden duplicada. Ignorar el resultado de LREM (que
    avisaría que otro la sacó primero) es exactamente el error que se comete
    al programar esto sin pensar en concurrencia.
    """
    vistos = r.lrange(COLA_ENTRADA, -1, -1)  # 1) mirar sin sacar
    if not vistos:
        time.sleep(0.2)  # cola vacía: pequeña pausa para no martillar Redis
        return None
    orden_id = vistos[0]
    time.sleep(DEMORA_INGENUA)  # <- la ventana fatal, ensanchada para la demo
    r.lrem(COLA_ENTRADA, 1, orden_id)  # 2) sacar por valor, ignorando si ya no estaba
    return orden_id


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
    reclamar = reclamar_ingenuo if MODO_RECLAMO == "ingenuo" else reclamar_atomico
    while True:
        try:
            orden_id = reclamar()
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
            r.hincrby("conteo:procesadas", orden_id, 1)
            r.hincrby("conteo:replica", REPLICA_ID, 1)
            publicar_estado()
            log(f"orden {orden_id} terminada ({estado_local['procesadas']} en total)")
        except redis.exceptions.RedisError as error:
            estado_local["ocupada"] = False
            log(f"sin conexión con Redis ({error}); reintento en 2 s")
            time.sleep(2)


# --- API HTTP de la réplica (docs/diseno.md §1.2) ---------------------------

app = FastAPI(title=f"estacion-{NOMBRE_ETAPA}")


@app.get("/estado")
def get_estado() -> dict:
    """Estado de ESTA réplica; en_cola es el largo actual de su cola de entrada."""
    try:
        en_cola = r.llen(COLA_ENTRADA)
    except redis.exceptions.RedisError:
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
