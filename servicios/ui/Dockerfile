# Imagen del tablero (Streamlit).
#
# El contexto de build es esta misma carpeta, igual que las demas estaciones del
# compose. La UI no comparte codigo con los otros servicios: habla con ellos por
# HTTP y por Redis, nada mas.
FROM python:3.12-slim

WORKDIR /app

# Las dependencias primero y en su propia capa: mientras requirements.txt no
# cambie, Docker reutiliza la capa y no vuelve a instalar nada.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

# --server.headless evita que intente abrir un navegador dentro del contenedor.
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
