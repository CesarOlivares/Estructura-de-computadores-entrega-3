"""Las dos maneras de reclamar trabajo de una cola compartida de Redis.

Este es el corazón del problema del Caso 2. Varias réplicas de envasado comen
de la MISMA cola; el modo en que cada una toma su próximo lote decide si el
sistema es correcto o produce el mismo lote dos veces.

Por qué vive aquí y no dentro de `estacion/`
--------------------------------------------
Dos servicios ejecutan estas funciones:

    servicios/estacion/worker.py   las usa para trabajar de verdad
    servicios/ui/carrera.py        las usa en la demostración del tablero

Si el tablero tuviera su propia copia, la demostración probaría el código de la
copia, no el que corre en la planta — y bastaría con que una de las dos se
editara para que la demo dejara de demostrar nada. Manteniéndolas en un solo
archivo importado por ambos, lo que se ve en pantalla es exactamente lo que
hacen las estaciones.
"""

import time

# Segundos que BRPOP se queda esperando trabajo antes de devolver None. Debe
# ser MENOR que el socket_timeout del cliente de Redis: si no, el cliente
# cortaría una conexión sana que solo está bloqueada esperando un lote.
TIMEOUT_BRPOP_S = 2

# Pausa artificial dentro de la ventana del modo ingenuo. La carrera existe sin
# ella, pero dura microsegundos y el experimento podría salir "limpio" por
# suerte. Ensancharla no cambia la naturaleza del error, solo su probabilidad:
# hace demostrable en vivo un fallo que de otro modo sería intermitente.
DEMORA_INGENUA_S = 0.1


def reclamar_atomico(r, cola, timeout=TIMEOUT_BRPOP_S):
    """Reclamo CORRECTO: BRPOP saca el lote en UNA operación indivisible.

    Redis procesa los comandos de a uno. Cuando varias réplicas están
    bloqueadas en BRPOP sobre la misma cola, el lote que llega se entrega a
    exactamente una de ellas: no hay ningún instante en que dos puedan verlo
    como disponible, porque "verlo" y "sacarlo" son el mismo acto.

    Devuelve el id del lote, o None si pasó `timeout` sin que llegara trabajo.
    """
    resultado = r.brpop(cola, timeout=timeout)
    return None if resultado is None else resultado[1]


def reclamar_ingenuo(r, cola, demora=DEMORA_INGENUA_S, pausa_vacia=0.2):
    """Reclamo INTENCIONALMENTE ROTO, conservado para demostrar la carrera.

    Parte el reclamo en dos operaciones separadas:

        1. LRANGE cola -1 -1   mirar cuál es el próximo lote, sin sacarlo
        2. LREM   cola 1 <id>  sacarlo de la cola

    Entre una y otra hay una ventana. Durante esa ventana la cola sigue
    conteniendo el lote, así que otra réplica que mire verá EL MISMO. Las dos
    creen haberlo reclamado y las dos lo procesan: el pedido se envasa dos
    veces.

    El error concreto es ignorar el valor de retorno de LREM, que dice cuántos
    elementos borró. Si borró 0, otra réplica se lo llevó primero. Chequearlo
    arreglaría este caso, pero seguiría siendo mirar-y-sacar en dos pasos: la
    solución correcta no es chequear mejor, es que no exista la ventana.
    """
    vistos = r.lrange(cola, -1, -1)          # 1) mirar sin sacar
    if not vistos:
        time.sleep(pausa_vacia)              # cola vacía: no martillar a Redis
        return None
    orden_id = vistos[0]
    time.sleep(demora)                       # <- la ventana fatal
    r.lrem(cola, 1, orden_id)                # 2) sacar, ignorando si ya no estaba
    return orden_id


def reclamador(modo, demora_ingenua=DEMORA_INGENUA_S, timeout_brpop=TIMEOUT_BRPOP_S):
    """Elige el modo y deja una función uniforme `reclamar(r, cola)`.

    Que ambos modos se usen a través de la misma firma es lo que permite que
    el bucle del worker no tenga un `if` de modo adentro: la decisión se toma
    una vez, al arrancar.
    """
    if modo == "ingenuo":
        return lambda r, cola: reclamar_ingenuo(r, cola, demora_ingenua)
    return lambda r, cola: reclamar_atomico(r, cola, timeout_brpop)
