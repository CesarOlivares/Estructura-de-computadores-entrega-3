# Imagen única para las 4 estaciones: la etapa se decide por variables de
# entorno al desplegar, no por la imagen (misma imagen, 4 configuraciones).
FROM python:3.12-slim

# Sin buffer: los logs salen al instante en `docker compose logs -f`.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY worker.py bd.py ./

CMD ["python", "worker.py"]
