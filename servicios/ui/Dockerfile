# Imagen del tablero (Streamlit).
#
# El contexto de build es `servicios/` (no `servicios/ui/`). El tablero habla
# con el resto del sistema por HTTP y por Redis, pero comparte UN paquete de
# código: `comun/`, donde viven las dos formas de reclamar trabajo. La sección
# de demostración del tablero ejecuta esas funciones tal cual, para que lo que
# se ve en pantalla sea el mismo código que corre en las estaciones y no una
# reimplementación que pueda quedar desincronizada.
FROM python:3.12-slim

WORKDIR /app

# Las dependencias primero y en su propia capa: mientras requirements.txt no
# cambie, Docker reutiliza la capa y no vuelve a instalar nada.
COPY ui/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY comun/ ./comun/
COPY ui/ ./

EXPOSE 8501

# --server.headless evita que intente abrir un navegador dentro del contenedor.
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
