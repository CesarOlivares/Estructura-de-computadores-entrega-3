"""Demo desechable (Fase 1): trabajador que consume órdenes.

Extrae órdenes de 'cola:ordenes' con BRPOP y simula procesarlas.

BRPOP es una operación atómica: aunque haya varios trabajadores esperando
sobre la misma cola, Redis entrega cada elemento a exactamente uno. Esa es
la propiedad que este prototipo quiere demostrar (cero duplicados, cero
pérdidas), y es la base del balanceo por demanda del proyecto.

Se lanza un trabajador por terminal (3 en la prueba de la fase). Termina
solo cuando pasan TIMEOUT segundos sin recibir trabajo, y reporta cuántas
órdenes procesó para poder sumar entre trabajadores.
"""

import os
import time

import redis

# Identidad simple para distinguir trabajadores en la salida.
NOMBRE = os.environ.get("NOMBRE", f"trabajador-{os.getpid()}")
TIEMPO_PROCESO = 1  # segundos que "cuesta" procesar una orden (simulado)
TIMEOUT = 5         # segundos sin trabajo tras los cuales el trabajador termina

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

procesadas = []
while True:
    # BRPOP bloquea hasta que haya un elemento o venza el timeout: el
    # trabajador ocioso NO consume CPU (a diferencia de consultar la cola
    # en un ciclo, que es el error que la Fase 5 prohíbe explícitamente).
    resultado = r.brpop("cola:ordenes", timeout=TIMEOUT)
    if resultado is None:
        # No llegó nada en TIMEOUT segundos: asumimos que ya no hay trabajo.
        break
    _, orden = resultado
    print(f"[{NOMBRE}] procesando {orden}")
    time.sleep(TIEMPO_PROCESO)  # simula el trabajo real
    procesadas.append(orden)

print(f"[{NOMBRE}] terminé: {len(procesadas)} órdenes -> {procesadas}")
