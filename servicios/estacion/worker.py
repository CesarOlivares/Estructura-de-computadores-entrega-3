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


def main() -> None:
    log(f"lista: {COLA_ENTRADA} -> {COLA_SALIDA}, ciclo {TIEMPO_CICLO}s")
    procesadas = 0
    while True:
        # timeout=2: si no llega nada volvemos al loop (permite refrescar
        # estado más adelante); seguimos bloqueados sin gastar CPU.
        resultado = r.brpop(COLA_ENTRADA, timeout=2)
        if resultado is None:
            continue
        _, orden_id = resultado
        log(f"procesando orden {orden_id}")
        time.sleep(TIEMPO_CICLO)  # simula el ciclo de la máquina
        r.lpush(COLA_SALIDA, orden_id)
        procesadas += 1
        log(f"orden {orden_id} terminada ({procesadas} en total)")


if __name__ == "__main__":
    main()
