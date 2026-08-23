# Imagen única para las 4 estaciones: la etapa se decide por variables de
# entorno al desplegar, no por la imagen (misma imagen, 4 configuraciones).
#
# El contexto de build es `servicios/` (no `servicios/estacion/`), porque la
# imagen necesita además el paquete `comun/`, que comparte con el tablero:
# las dos formas de reclamar trabajo se definen una sola vez, en
# comun/reclamo.py, y las ejecutan tanto las estaciones como la demostración
# de la UI. Ver el docstring de ese archivo.
FROM python:3.12-slim

# Sin buffer: los logs salen al instante en `docker compose logs -f`.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY estacion/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY comun/ ./comun/
COPY estacion/worker.py estacion/bd.py ./

CMD ["python", "worker.py"]
