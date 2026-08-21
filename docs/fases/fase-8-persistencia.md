# Fase 8 — Persistencia

**Estado: CERRADA (21/08/2026)**

## Objetivo

SQLite con las tablas `ordenes` y `eventos` del diseño (§2), montada en un
volumen de Docker, escrita por `orders-api` y por las cuatro estaciones.

## Qué se logró

- [x] `bd.py` en ambos servicios: WAL + `busy_timeout` + una conexión por
      operación (`with bd.transaccion() as con`), para que varios contenedores
      escriban la misma base sin pisarse.
- [x] `orders-api` sobre SQLite: el id ahora lo asigna la base
      (`AUTOINCREMENT`), reemplazando el contador en memoria de la Fase 3 —
      con esto muere también la pregunta del lock.
- [x] `POST /ordenes` transaccional: INSERT de la orden + evento `entra_cola`
      + `LPUSH`, todo o nada. Si Redis falla, el rollback deshace la orden
      (no quedan fantasmas) y se responde 503.
- [x] Estaciones registran eventos: `inicia` al reclamar, `termina` al cerrar
      el ciclo, y el `entra_cola` de la etapa siguiente (lo escribe quien
      encola). La última etapa (la que desemboca en `cola:listos`) además
      marca la orden `terminada` con su `terminada_en`.
- [x] Línea completa en el compose: sellado y esterilización agregados, con
      un ancla YAML (`x-estacion`) para no repetir la configuración común.
- [x] **Pruebas**: 3 órdenes recorrieron las 4 etapas → `terminada`, con
      **exactamente 12 eventos cada una** (3 × 4 etapas, como dice el diseño).
      Tras `docker compose down` + `up`, las órdenes siguen ahí.

## Principales dificultades

1. **SQLite compartida entre 6 contenedores.** SQLite permite UN escritor a
   la vez; con la API y 4+ estaciones escribiendo, un lock mal manejado
   revienta con "database is locked". La combinación WAL (lectores no
   bloquean escritores) + `busy_timeout=10s` (esperar el lock en vez de
   fallar) + transacciones cortas de una conexión por operación lo resuelve
   sin ninguna pieza extra. Vale para el informe: es el mismo problema de
   concurrencia de la Fase 6, ahora en la capa de datos.

2. **El orden de operaciones al crear una orden importa.** Guardar primero y
   encolar después (o al revés) deja estados a medias si algo falla al medio.
   Solución: el `LPUSH` va dentro de la transacción de SQLite — si Redis
   falla, el rollback borra la orden y el sistema queda como si nada.

## Qué queda para la siguiente fase

**Fase 9 — métricas**: `metrics-api` lee `eventos` y calcula espera, servicio
y lead time por etapa (definiciones exactas en `docs/diseno.md` §3).
