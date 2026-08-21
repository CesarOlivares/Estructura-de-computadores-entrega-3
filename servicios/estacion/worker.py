"""Worker de estación — un solo programa para las cuatro etapas de la línea.

Qué etapa es, de qué cola come y a cuál escupe, y cuánto tarda su ciclo, todo
viene por variables de entorno (nunca escrito en el código):

    NOMBRE_ETAPA=envasado
    COLA_ENTRADA=cola:envasado
    COLA_SALIDA=cola:sellado
    TIEMPO_CICLO=12

Ciclo de vida: BRPOP de la cola de entrada (bloqueante: el worker ocioso NO
consume CPU) → esperar TIEMPO_CICLO (simula el trabajo) → LPUSH a la cola de
salida. LPUSH por la izquierda + BRPOP por la derecha = cola FIFO.
"""

import os
import socket
import time

import redis

NOMBRE_ETAPA = os.environ["NOMBRE_ETAPA"]
COLA_ENTRADA = os.environ["COLA_ENTRADA"]
COLA_SALIDA = os.environ["COLA_SALIDA"]
TIEMPO_CICLO = float(os.environ["TIEMPO_CICLO"])

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


def log(mensaje: str) -> None:
    """Toda línea de log lleva el replica_id para poder seguir quién hizo qué."""
    print(f"[{REPLICA_ID}] {mensaje}", flush=True)


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


def main() -> None:
    log(f"lista: {COLA_ENTRADA} -> {COLA_SALIDA}, ciclo {TIEMPO_CICLO}s, reclamo {MODO_RECLAMO}")
    reclamar = reclamar_ingenuo if MODO_RECLAMO == "ingenuo" else reclamar_atomico
    procesadas = 0
    while True:
        orden_id = reclamar()
        if orden_id is None:
            continue
        log(f"procesando orden {orden_id}")
        time.sleep(TIEMPO_CICLO)  # simula el ciclo de la máquina
        r.lpush(COLA_SALIDA, orden_id)
        procesadas += 1
        # Conteos en Redis para los experimentos: cuántas veces se procesó
        # cada orden (detector de duplicados) y cuánto procesó cada réplica.
        r.hincrby("conteo:procesadas", orden_id, 1)
        r.hincrby("conteo:replica", REPLICA_ID, 1)
        log(f"orden {orden_id} terminada ({procesadas} en total)")


if __name__ == "__main__":
    main()
