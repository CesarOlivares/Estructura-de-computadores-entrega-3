# Imagen del metrics-api. Misma receta que orders-api (ver ese Dockerfile
# para el porqué de slim, el orden de las capas y el 0.0.0.0).
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py bd.py ./

# Puerto 8001: el 8000 ya lo ocupa orders-api (docs/diseno.md §1.3).
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
