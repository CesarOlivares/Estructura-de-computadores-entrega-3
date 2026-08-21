# Fase 5 — Una estación consume

**Estado: CERRADA (21/08/2026)**

## Objetivo

El worker genérico de estación: **un solo programa** que sirve para las cuatro
etapas, configurado 100 % por variables de entorno. En el compose se despliega
solo fileteado; las demás etapas se agregan en las fases siguientes.

## Qué se logró

- [x] `servicios/estacion/worker.py`: ciclo `BRPOP` (bloqueante) → esperar
      `TIEMPO_CICLO` → `LPUSH` a la cola siguiente. `LPUSH` izquierda +
      `BRPOP` derecha = FIFO.
- [x] Configuración por entorno: `NOMBRE_ETAPA`, `COLA_ENTRADA`, `COLA_SALIDA`,
      `TIEMPO_CICLO`, `REDIS_HOST`. La misma imagen servirá para las 4 etapas.
- [x] `replica_id` (etapa + hostname del contenedor) en **cada línea de log**.
- [x] Tiempos de ciclo parametrizables desde el compose
      (`${CICLO_FILETEADO:-4}`): el default es el del diseño y los
      experimentos pueden acelerarlos sin tocar código.
- [x] **Prueba oficial**: 5 órdenes creadas por la API se procesaron **en el
      orden de creación** y quedaron en `cola:envasado`. **CPU del worker
      ocioso: 0,04 %** — bloquea, no consulta en un ciclo (el plan marca eso
      como causal de no avanzar).

## Principales dificultades

1. **El timeout del BRPOP no es opcional.** Con `BRPOP` sin timeout el worker
   queda bloqueado para siempre en una sola llamada: no puede refrescar estado
   ni reaccionar a nada más. Con `timeout=2` el loop "respira" cada 2 segundos
   sin gastar CPU — ese respiro se usará en la Fase 7 para publicar el estado
   de la réplica.

## Qué queda para la siguiente fase

**Fase 6 — condición de carrera** (la fase más importante del proyecto):
provocarla con un reclamo ingenuo de dos pasos, commitearla rota, y arreglarla
volviendo a la extracción atómica.
