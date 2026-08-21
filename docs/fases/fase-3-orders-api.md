# Fase 3 — `orders-api` mínima en Docker

**Estado: CERRADA (21/08/2026)**

## Objetivo

Primer servicio real corriendo en Docker: crear y consultar órdenes vía HTTP,
con validación de entradas. Sin Redis ni base de datos todavía — las órdenes
viven en memoria a propósito (la cola llega en la Fase 4, la persistencia en
la 8); esta fase valida el **contrato HTTP** de `docs/diseno.md` §1.1.

## Qué se logró

- [x] `servicios/ordenes/app.py`: `POST /ordenes`, `GET /ordenes/{id}`,
      `GET /ordenes` (con filtro `?estado=`), `GET /salud`. Comentado.
- [x] Validación con Pydantic: `cantidad` entera > 0, `producto` no vacío
      (un validador extra rechaza el caso de solo espacios, que `min_length`
      no atrapa).
- [x] `Dockerfile` (python:3.12-slim, capas ordenadas para cachear el
      `pip install`) y `docker-compose.yml` con el servicio.
- [x] **Prueba oficial de la fase**: orden válida → **201** con id; cantidad
      negativa → **422** (ni 500 ni 201). Además: producto de solo espacios
      → 422, id inexistente → 404 con mensaje, filtro inválido → 422,
      `/salud` → 200. **8/8 casos pasando**, re-verificados tras fijar las
      versiones de las dependencias.
- [x] Revisión cruzada (4 revisores + verificación adversarial) antes de
      commitear; hallazgos aplicados (ver dificultades).

## Principales dificultades

1. **Dependencias sin versión = build no reproducible.** La primera versión de
   `requirements.txt` decía solo `fastapi` y `uvicorn`: el build del profesor
   habría instalado lo último de PyPI en ese momento, no lo probado hoy —
   riesgo directo contra la Fase 13 ("clonar + `docker compose up` funciona").
   Se fijaron las versiones exactas del contenedor verificado
   (`fastapi==0.141.1`, `uvicorn==0.52.4`, `pydantic==2.13.4`) y se
   reconstruyó y re-probó con ellas.

2. **`min_length=1` no valida lo que parece.** Un producto de `"   "` (solo
   espacios) pasa el largo mínimo. Hizo falta un `field_validator` que haga
   `strip()` y rechace el vacío real. Lección: las reglas de validación hay
   que probarlas con el caso malicioso, no solo con el caso feliz.

## Decisiones tomadas en esta fase

- Almacenamiento en un diccionario en memoria, declarado como andamiaje en el
  docstring: se pierde al reiniciar y se reemplaza por SQLite en la Fase 8.
- El contador de ids (`siguiente_id`) no lleva lock: con un solo worker de
  uvicorn no hay carrera observable (se ejercitó con cientos de POST
  concurrentes sin duplicados) y la asignación de ids pasa a SQLite en la
  Fase 8. Documentado aquí porque es pregunta fácil de defensa.

## Preguntas que podrían hacernos (defensa)

1. **¿Por qué 422 y no 400 para entradas inválidas?** 422 es "entiendo el
   formato pero los datos no cumplen las reglas"; FastAPI lo genera solo desde
   los modelos de Pydantic, con el detalle del campo que falló. Es la mitad
   del requisito de manejo básico de errores del enunciado.
2. **¿Es thread-safe el contador de ids?** Con un worker de uvicorn, sí en la
   práctica (GIL + ventana mínima); en riguroso no, y no lo blindamos porque
   este almacenamiento es temporal: en la Fase 8 el id lo asigna SQLite.
3. **¿Por qué las órdenes se pierden al reiniciar?** Decisión de fase: primero
   validar el contrato HTTP aislado; la persistencia es la Fase 8. El plan
   prohíbe adelantar funcionalidades antes del núcleo.
4. **¿Por qué fijar versiones en `requirements.txt`?** Para que el build de
   cualquier máquina instale exactamente lo verificado. Sin fijar, un release
   nuevo de FastAPI podría cambiar el comportamiento el día de la revisión.

## Qué queda para la siguiente fase

**Fase 4 — Redis y la cola**: agregar `redis` al compose y encolar el id de
cada orden nueva en `cola:fileteado` (host por variable de entorno). Pendiente
de equipo que sigue vivo: el cuestionario de la Fase 2 entre ambos.
