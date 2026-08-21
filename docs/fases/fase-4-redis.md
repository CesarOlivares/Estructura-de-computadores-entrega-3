# Fase 4 — Redis y la cola

**Estado: CERRADA (21/08/2026)**

## Objetivo

Conectar `orders-api` con Redis: cada orden nueva encola su id en
`cola:fileteado`, la entrada de la línea de producción.

## Qué se logró

- [x] Servicio `redis` (imagen `redis:7`) en el compose, con **healthcheck**
      (`redis-cli ping`); `ordenes` arranca solo cuando Redis está sano
      (`depends_on: condition: service_healthy`).
- [x] `POST /ordenes` hace `LPUSH` del id a `cola:fileteado`. El nombre de la
      cola y el host de Redis van por variables de entorno, no en el código.
- [x] Si Redis no responde, la orden **no se crea** y la API responde **503**
      con mensaje claro. Se decidió así porque una orden guardada pero nunca
      encolada quedaría `en_proceso` para siempre — preferimos rechazar y que
      el operador reintente.
- [x] **Prueba oficial**: `POST /ordenes` → id 1; `LRANGE cola:fileteado 0 -1`
      muestra `1`. **Prueba extra**: con `docker compose stop redis`, POST →
      `503 {"detail": "sin conexión con el servicio de coordinación..."}` y la
      cola no cambió.
- [x] `redis==8.1.0` fijado en requirements (misma política de la Fase 3).

## Principales dificultades

1. **Decidir el orden entre guardar y encolar.** Si se guarda primero y el
   `LPUSH` falla, queda una orden huérfana; si se encola primero y el guardado
   falla, queda un id fantasma en la cola. Se eligió encolar primero y guardar
   después porque en esta fase el guardado en memoria no puede fallar; al
   migrar a SQLite (Fase 8) la secuencia se revisará dentro de una transacción.

## Qué queda para la siguiente fase

**Fase 5 — Una estación consume**: `servicios/estacion/worker.py` genérico
(BRPOP → ciclo → LPUSH) y la etapa de fileteado en el compose.
