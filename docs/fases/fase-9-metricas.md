# Fase 9 — Métricas

**Estado: CERRADA (21/08/2026)**

## Objetivo

`metrics-api` lee la tabla `eventos` y calcula, por etapa, espera y servicio
promedio en ventana móvil, más órdenes en cola y lead time promedio
(definiciones exactas en `docs/diseno.md` §3).

## Qué se logró

- [x] `servicios/metricas/app.py` con `GET /metricas` y `GET /salud`.
- [x] `bd.py` compartido (misma copia que ordenes y estacion), Dockerfile y
      requirements con las mismas versiones fijadas.
- [x] Servicio `metricas` en el compose, puerto **8001**, solo lectura de la
      base y de Redis.
- [x] **Prueba oficial**: con 3 órdenes recorriendo la línea completa,
      `GET /metricas?ventana_s=90` devolvió servicios promedio de
      **4.27 / 12.31 / 3.16 / 7.17 s** contra ciclos configurados de
      **4 / 12 / 3 / 7 s** — coherentes (el ~0.2 s extra es el registro de
      eventos en SQLite). Lead time promedio 43.94 s. La mayor espera fue la
      de envasado (9.58 s), esperable con 1 réplica: las órdenes llegan cada
      4 s y se drenan cada 12 s.

## Principales dificultades

1. **La fase quedó cortada a medias en una sesión**: `app.py` escrito pero
   sin `bd.py`, Dockerfile, requirements ni entrada en el compose, y sin
   commit. Lección de método: commitear solo fases verificadas está bien,
   pero conviene anotar en la bitácora el punto exacto de corte para poder
   retomar sin arqueología.

## Decisiones tomadas en esta fase

- **La espera de cada etapa se mide contra su propio `entra_cola`**, no contra
  `creada_en` (ya estaba en `docs/diseno.md` §3; aquí solo se implementó).
- **Ventana móvil asimétrica a propósito**: la espera de una orden cuenta si su
  `inicia` cae en la ventana; el servicio, si su `termina` cae en la ventana.
  Cada métrica se ancla al evento que la completa.
- `en_cola` sale de Redis (`LLEN`) y no de la base, porque el largo instantáneo
  de la cola es el único dato que vive en las colas. Si Redis no responde, se
  devuelve `null` en ese campo y el resto de la métrica sigue siendo válida.

## Qué queda para la siguiente fase

**Fase 10 — cuello de botella**: `GET /metricas/cuello` con el criterio de
`docs/diseno.md` §4 (mayor espera promedio en ventana móvil, sobre umbral) y
cierre de la decisión abierta #2 (umbrales y tamaño de ventana).
