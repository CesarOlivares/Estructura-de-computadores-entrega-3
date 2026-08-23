"""
Demostración en vivo de la condición de carrera, ejecutada desde el tablero.

Qué hace
--------
Corre DOS veces el mismo experimento sobre el Redis real —una con el reclamo
ingenuo y otra con el atómico— y cuenta cuántas veces se procesó cada lote.
Con el reclamo en dos pasos, varias réplicas toman el mismo lote y el total de
procesamientos supera al de lotes pedidos. Con el reclamo atómico, cada lote se
procesa exactamente una vez.

Por qué se puede confiar en lo que muestra
------------------------------------------
1. **Es el mismo código.** Las dos funciones que se comparan se importan de
   `comun/reclamo.py`, el mismo módulo que importa `estacion/worker.py` para
   trabajar de verdad. No hay una copia para la demo.

2. **Es el Redis real.** Las colas son listas de Redis de verdad y las réplicas
   son hilos concurrentes compitiendo por ellas. Nada está simulado: si el
   reclamo atómico fallara, aquí se vería.

3. **No toca la línea de producción.** El experimento usa sus propias claves
   `demo:carrera:<id>`, generadas por corrida y borradas al terminar. Las colas
   `cola:*` y los contadores de la planta quedan intactos, así que se puede
   ejecutar con lotes circulando sin ensuciar las métricas.

Por qué hilos y no contenedores
-------------------------------
Levantar tres contenedores por modo tomaría minutos y exigiría que el tablero
tuviera acceso al socket de Docker. Lo que la carrera necesita no es que los
competidores sean procesos separados, sino que sean **concurrentes sobre la
misma cola**: durante el `LRANGE`, el `sleep` y el `LREM` cada hilo está
esperando a la red, no ocupando el intérprete, así que compiten igual que tres
contenedores. La versión con contenedores reales existe y da el mismo
resultado: `experimentos/fase6_carrera.sh`.

Los conteos se llevan en memoria del proceso (no en hashes de Redis como en el
script de la Fase 6) porque son instrumentación, no la mecánica bajo prueba:
lo que se está evaluando es quién logra sacar el lote de la cola.
"""

import os
import threading
import time
import uuid
from collections import Counter

import redis

from comun import reclamo

# --- Parámetros por defecto de la demostración ------------------------------
# Pensados para que la corrida completa dure unos segundos en vivo, no para
# parecerse a los tiempos de la planta (que son de 3 a 12 s por lote).
LOTES = 100          # cuántos lotes se encolan en cada modo
REPLICAS = 3         # cuántas máquinas compiten por esa cola
CICLO_S = 0.01       # lo que "tarda" una máquina en envasar un lote
DEMORA_S = 0.03      # ancho de la ventana del reclamo ingenuo
TIMEOUT_BRPOP_S = 0.5  # más corto que en producción: la demo debe terminar ya

# Cuántas veces seguidas puede una réplica encontrar la cola vacía antes de
# darse por terminada. Con una sola sería frágil: una réplica podría mirar
# justo en el hueco entre que otra saca un lote y lo procesa.
VACIAS_PARA_TERMINAR = 3

_redis = redis.Redis(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    decode_responses=True,
    socket_timeout=10,        # mayor que el BRPOP, o cortaría esperas sanas
    socket_connect_timeout=2,
    max_connections=16,       # una conexión por réplica, con holgura
)


class ErrorDeDemo(Exception):
    """Redis no respondió. app.py lo traduce a un mensaje entendible."""


def _replica(indice, cola, reclamar, conteo, reparto, candado, ciclo):
    """Una máquina: reclama lotes de `cola` hasta que deja de haber trabajo.

    Corre en su propio hilo. Es deliberadamente igual al bucle de
    `worker.py`: reclamar, tardar el tiempo de ciclo, anotar lo hecho.
    """
    nombre = f"Réplica {indice}"
    vacias = 0
    while vacias < VACIAS_PARA_TERMINAR:
        lote = reclamar(_redis, cola)
        if lote is None:
            vacias += 1
            continue
        vacias = 0
        time.sleep(ciclo)  # simula el ciclo de la máquina
        with candado:
            conteo[lote] += 1
            reparto[nombre] += 1


def ejecutar(modo, lotes=LOTES, replicas=REPLICAS, ciclo=CICLO_S, demora=DEMORA_S):
    """Corre el experimento en un modo y devuelve qué pasó.

    `modo` es "ingenuo" o "atomico" — los mismos valores que acepta la variable
    de entorno MODO_RECLAMO de las estaciones.
    """
    cola = f"demo:carrera:{modo}:{uuid.uuid4().hex[:8]}"
    reclamar = reclamo.reclamador(modo, demora_ingenua=demora,
                                  timeout_brpop=TIMEOUT_BRPOP_S)
    conteo, reparto, candado = Counter(), Counter(), threading.Lock()

    try:
        # Encolar los lotes de una sola vez: el experimento mide el reparto,
        # no la llegada, así que todos deben estar disponibles desde el inicio.
        _redis.delete(cola)
        _redis.lpush(cola, *[str(i) for i in range(1, lotes + 1)])

        partida = time.monotonic()
        hilos = [
            threading.Thread(
                target=_replica,
                args=(i, cola, reclamar, conteo, reparto, candado, ciclo),
                daemon=True)
            for i in range(1, replicas + 1)
        ]
        for hilo in hilos:
            hilo.start()
        for hilo in hilos:
            hilo.join()
        duracion = time.monotonic() - partida
    except redis.RedisError as error:
        raise ErrorDeDemo(f"Redis no respondió durante la demostración: {error}")
    finally:
        try:
            _redis.delete(cola)  # no dejar basura aunque algo haya fallado
        except redis.RedisError:
            pass

    procesamientos = sum(conteo.values())
    distintos = len(conteo)
    # Cuántos lotes se procesaron 1 vez, 2 veces, 3 veces... Es la distribución
    # que se grafica: con el reclamo correcto, todo cae en la columna "1 vez".
    distribucion = Counter(conteo.values())

    return {
        "modo": modo,
        "lotes": lotes,
        "replicas": replicas,
        "procesamientos": procesamientos,
        "distintos": distintos,
        "duplicados": sum(1 for veces in conteo.values() if veces > 1),
        # Trabajo de más: latas envasadas que nadie pidió. Es el número que
        # tiene consecuencia física en la planta.
        "de_mas": procesamientos - lotes,
        "perdidos": lotes - distintos,
        "max_veces": max(conteo.values(), default=0),
        "distribucion": dict(distribucion),
        "reparto": dict(sorted(reparto.items())),
        "segundos": duracion,
    }


def comparar(lotes=LOTES, replicas=REPLICAS, ciclo=CICLO_S, demora=DEMORA_S,
             al_terminar_modo=None):
    """Corre los dos modos y devuelve {"ingenuo": ..., "atomico": ...}.

    `al_terminar_modo(modo, resultado)` se llama después de cada uno, para que
    la pantalla pueda ir contando lo que ya está listo. Se invoca desde el hilo
    principal: Streamlit no admite que lo llamen desde los hilos de trabajo.

    Se corre primero el ingenuo a propósito: la demostración se cuenta en ese
    orden —primero el problema, después la solución— y así el último resultado
    que queda en pantalla es el correcto.
    """
    resultados = {}
    for modo in ("ingenuo", "atomico"):
        resultados[modo] = ejecutar(modo, lotes, replicas, ciclo, demora)
        if al_terminar_modo:
            al_terminar_modo(modo, resultados[modo])
    return resultados
