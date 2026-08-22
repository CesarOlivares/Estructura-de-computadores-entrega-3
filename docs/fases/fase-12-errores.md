# Fase 12 — Errores, logging y healthchecks

**Estado: CERRADA (22/08/2026)**

## Objetivo

Que el sistema falle **explicándose**: códigos HTTP correctos en todos los
servicios, logs que digan qué réplica hizo qué, healthchecks en el compose, y
que matar Redis produzca un mensaje claro en vez de un cuelgue.

## Qué se logró

- [x] **Códigos HTTP correctos**, verificados contra el sistema corriendo:
  `404` (orden inexistente), `422` (cantidad inválida, filtro de estado
  inválido) y `503` (dependencia caída) — nunca 500, nunca un cuelgue.
- [x] **503 rápido con Redis caído**: `POST /ordenes` responde
  `503 "sin conexión con el servicio de coordinación (Redis)"` en **2,1 s**
  (antes de esta fase: se colgaba **46 s**, medido).
- [x] **`GET /metricas` nunca se cuelga por Redis**: con Redis caído responde
  `200` en **2,0 s** con `en_cola: null` en todas las etapas; el resto de la
  respuesta (esperas, servicios, lead time) sale de SQLite y sigue válido.
- [x] **Healthchecks de todos los servicios** en `docker-compose.yml`:
  `docker compose ps` muestra los 9 contenedores `healthy`.
- [x] **Logging con `replica_id`**: ya existía desde la Fase 7 — cada línea de
  las estaciones sale como `[envasado-a1b2c3] procesando orden 19`. Esta fase
  lo verificó; no hubo que agregarlo. `ordenes` y `metricas` corren una sola
  instancia y los logs de acceso de uvicorn ya identifican el servicio.
- [x] **Recuperación verificada**: al volver Redis, se creó una orden nueva y
  recorrió las cuatro etapas hasta `terminada` sin reiniciar ningún servicio.

## Principales dificultades

1. **`socket_connect_timeout` no bastó: el cuelgue estaba en el DNS.**

   - *Síntoma:* tras agregar `socket_timeout=2, socket_connect_timeout=2` al
     cliente Redis (lo que la Fase 11 dejó anotado como causa de fondo),
     `POST /ordenes` con Redis detenido **seguía colgado**: 46 s medidos.
   - *Causa:* esos timeouts acotan el *connect* y las lecturas del socket,
     pero **no la resolución DNS**. Al detener el contenedor, Docker borra el
     nombre `redis` de su DNS interno, y `getaddrinfo` se queda reintentando
     (~45 s en la libc de la imagen) **antes** de que exista socket alguno que
     acotar. Se comprobó aislado: un `LPUSH` con ambos timeouts en 2 s tardó
     46,45 s en fallar con "Name or service not known".
   - *Solución:* un **plazo duro en un hilo aparte**. La consulta a Redis se
     ejecuta en un `ThreadPoolExecutor` y se espera su resultado a lo más
     `PLAZO_REDIS_S` (2 s): si no llega, se da a Redis por caído ya — 503 en
     `ordenes`, `en_cola: null` en `metricas` y en el `/estado` de las
     estaciones. El hilo bloqueado muere solo cuando el sistema operativo
     suelta la consulta DNS.
   - *Lección:* "le puse timeout" no es una afirmación verificable hasta medir
     el camino **completo** de la falla. Había tres relojes en juego (DNS,
     connect, lectura) y el timeout configurado solo cubría dos.

2. **El portero va antes de la transacción.** En `ordenes`, el chequeo con
   plazo se hace **antes** de abrir la transacción de SQLite (`verificar_redis()`
   → PING). Si se hiciera adentro, cada intento con Redis caído abriría y
   desharía una transacción para nada. El `try/except` alrededor del `LPUSH`
   se conserva: cubre la carrera (rara) de que Redis muera justo entre el
   chequeo y el encolado, y en ese caso el INSERT se deshace igual que antes.

3. **Healthchecks sin curl.** Las imágenes `python:slim` no traen `curl`, así
   que el healthcheck usa la python de la propia imagen
   (`urllib.request.urlopen('http://localhost:.../salud')`). Nota: que
   `ordenes` esté `healthy` con Redis caído es **correcto** — el healthcheck
   responde "el servicio está vivo", y el servicio está vivo: contesta 503,
   que es exactamente lo que debe hacer.

## Decisiones tomadas en esta fase

### Plazo duro con hilo, no reintentos

El enunciado dice explícitamente que **no se exige tolerancia a fallos** (sin
reintentos ni circuit breaker). Por eso la solución detecta y **avisa** — 503,
mensaje claro, `null` honesto — pero no reintenta ni degrada a un plan B. El
worker de estación es la única excepción y ya lo era: su bucle reintenta el
`BRPOP` cada 2 s porque un worker sin bucle de reintento simplemente moriría.

### Los healthchecks miden vida, no dependencias

`/salud` responde 200 si el proceso atiende HTTP, sin consultar Redis ni la
base. Alternativa descartada: un `/salud` que verifique dependencias — habría
hecho que Docker marcara `unhealthy` (y con `depends_on`, reiniciara en
cascada) a servicios que están perfectamente vivos y explicándose con 503.
La caída de una dependencia ya se ve donde corresponde: en la respuesta de los
endpoints que la usan y en el semáforo de la UI.

## Verificación

Secuencia completa contra el sistema real (`docker compose up -d --scale envasado=2`):

| Paso | Resultado medido |
|---|---|
| `POST /ordenes` válido | `201`, la orden recorre las 4 etapas (lead time ~29,6 s con ciclos 4/12/3/7) |
| `POST /ordenes` con cantidad −5 | `422` |
| `GET /ordenes/9999` | `404` |
| `GET /ordenes?estado=invalido` | `422` |
| `docker compose stop redis` → `POST /ordenes` | **`503` en 2,1 s**, mensaje claro |
| ídem → `GET /metricas` | **`200` en 2,0 s**, `en_cola: null` |
| ídem → UI | responde; el tablero explica y nombra a Redis (`diagnostico()`, Fase 11) |
| `docker compose start redis` → orden nueva | `201` y llega a `terminada` sin reiniciar nada |
| `docker compose ps` | 9/9 contenedores `healthy` |

## Qué queda para la siguiente fase

**Fase 13 — Reproducibilidad.** El README ya está (lo dejó la Fase 11);
faltan el `.env.example` documentando todas las variables (incluida la nueva
`PLAZO_REDIS_S`) y la prueba de clon limpio: clonar en una carpeta vacía y que
`docker compose up` funcione sin ningún paso manual.
