"""Demo desechable (Fase 1): productor de órdenes.

Encola 15 órdenes en la lista 'cola:ordenes' de Redis con LPUSH.
Cada orden es solo un identificador ('orden-1' ... 'orden-15'): en esta demo
no hay datos reales; lo único que interesa es observar cómo se reparten
entre varios trabajadores compitiendo por la misma cola.
"""

import redis

# Redis corre en un contenedor con el puerto 6379 publicado en localhost.
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

for i in range(1, 16):
    orden = f"orden-{i}"
    # LPUSH agrega por la izquierda; los trabajadores extraen por la derecha
    # con BRPOP, de modo que la cola se comporta como FIFO.
    r.lpush("cola:ordenes", orden)
    print(f"encolada {orden}")

print("15 órdenes encoladas en cola:ordenes")
