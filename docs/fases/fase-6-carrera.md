# Fase 6 — Condición de carrera: provocarla y resolverla

**Estado: CERRADA (21/08/2026)** — la fase más importante del proyecto.

## Objetivo

Demostrar con datos que dos réplicas pueden tomar la misma orden si el reclamo
no es atómico, y que la extracción atómica lo elimina. El par de commits
"romper → arreglar" es la evidencia de que se entendió el problema antes de
resolverlo.

## Cómo se hizo

- **Reclamo ingenuo** (commit `reproduce race condition with naive claiming`):
  dos operaciones separadas — mirar el último de la cola con `LRANGE` y
  después sacarlo con `LREM` — con una pausa configurable entre ambas
  (`DEMORA_INGENUA=0.1 s`) que ensancha la ventana para hacer visible en
  segundos lo que en la realidad pasa en microsegundos. El error clave:
  **ignorar el resultado de `LREM`**, que avisaría que otra réplica ya se
  llevó la orden.
- **Reclamo atómico** (commit `implement atomic order claiming`): volver a
  `BRPOP`, una sola operación indivisible; Redis garantiza que cada elemento
  se entrega a exactamente una réplica.
- El modo queda tras la variable `MODO_RECLAMO` (default `atomico`); el
  ingenuo se conserva **solo** para reproducir la demo en la presentación.
- Experimento reproducible: `experimentos/fase6_carrera.sh` — encola 200
  órdenes en `cola:envasado` con 3 réplicas y cuenta cuántas veces se procesó
  cada una (hash `conteo:procesadas`).

## Resultados medidos (21/08/2026, 3 réplicas, 200 órdenes, ciclo 0.05 s)

| Métrica | Reclamo ingenuo | Reclamo atómico |
|---|---|---|
| Órdenes distintas procesadas | 200/200 | 200/200 |
| **Procesamientos totales** | **598** | **200** |
| **Órdenes duplicadas** | **200 (todas)** | **0** |
| Órdenes perdidas | 0 | 0 |
| Reparto entre réplicas | 200/199/199 | 67/66/67 |

Con el reclamo ingenuo prácticamente **cada orden fue procesada por las 3
réplicas** (598 procesamientos para 200 órdenes = 3× el trabajo, y en una
planta real, 3× el producto). Con el atómico, exactamente un procesamiento
por orden. La prueba del plan exigía "al menos 1 duplicado" y "exactamente 0
en 200": ambas se cumplen con margen.

## Principales dificultades

1. **La carrera no aparece sola: hay que ensancharla.** Con el ciclo corto y
   sin la pausa artificial, la ventana entre `LRANGE` y `LREM` es de
   microsegundos y el experimento podía salir "limpio" por suerte. La
   `DEMORA_INGENUA` configurable hace el fallo determinista y demostrable en
   vivo — y es honesta: no cambia la naturaleza del error, solo su
   probabilidad.

2. **`LREM` devuelve cuántos elementos borró, y el código ingenuo lo ignora.**
   Un reclamo "menos ingenuo" podría chequear ese retorno (si borró 0, otro
   ganó) — funcionaría, pero seguiría siendo mirar-y-sacar en dos pasos, con
   más código y más casos borde que una sola operación atómica. Argumento
   para la defensa: la solución correcta no es "chequear mejor", es **eliminar
   la ventana**.

## Decisiones tomadas en esta fase

- El reclamo ingenuo queda en el código tras `MODO_RECLAMO` (documentado como
  roto) para poder reproducir la demo; el default es siempre atómico.
- Los contadores `conteo:procesadas` y `conteo:replica` (Redis) quedan como
  instrumentación permanente: sirven para este experimento y para medir el
  reparto de la Fase 7.

## Qué queda para la siguiente fase

**Fase 7 — balanceo dinámico**: N réplicas con identidad expuesta
(`GET /estado`) y una réplica lenta que debe procesar visiblemente menos.
