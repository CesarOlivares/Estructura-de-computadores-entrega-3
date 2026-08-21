# Imagen del orders-api. python:3.12-slim: la variante completa pesa ~10x más
# y no aporta nada que este servicio use.
FROM python:3.12-slim

WORKDIR /app

# Primero las dependencias, después el código: así Docker reutiliza la capa de
# pip install cuando solo cambia app.py y la reconstrucción tarda segundos.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py bd.py ./

# 0.0.0.0 y no 127.0.0.1: dentro del contenedor, 127.0.0.1 solo se vería a sí
# mismo y el puerto publicado no recibiría nada.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
