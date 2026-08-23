#!/usr/bin/env bash
# Equivalente de INICIAR.bat para macOS y Linux.
#
# Mismo recorrido: comprobar Docker, levantar la linea, esperar al tablero y
# abrirlo en el navegador. Aqui no se intenta arrancar Docker Desktop solo:
# en macOS y Linux el motor suele ser un servicio ya en marcha, y adivinar como
# levantarlo (systemd, colima, orbstack, Docker Desktop) daria mas problemas
# que los que resuelve.
#
# Uso:  ./iniciar.sh      (si hace falta:  chmod +x iniciar.sh)
set -euo pipefail
cd "$(dirname "$0")"

echo
echo "  LINEA DE PRODUCCION - Conservera de jurel"
echo "  Estructura de Computadores, Evaluacion 3 - Caso 2"
echo "  ---------------------------------------------------------------"
echo

if ! command -v docker >/dev/null 2>&1; then
  echo "  [X] No se encontro Docker. Instala Docker Desktop o el motor de Docker."
  exit 1
fi

echo "  [1/4] Comprobando Docker..."
if ! docker info >/dev/null 2>&1; then
  echo "  [X] El motor de Docker no responde. Arrancalo y vuelve a ejecutar esto."
  exit 1
fi
echo "        Docker responde."

echo
echo "  [2/4] Construyendo y levantando los servicios."
echo "        La primera vez tarda unos minutos."
echo
docker compose up -d --build

echo
echo "  [3/4] Esperando a que el tablero responda..."
for _ in $(seq 1 40); do
  if [ "$(docker inspect -f '{{.State.Health.Status}}' ui 2>/dev/null || true)" = "healthy" ]; then
    echo "        Listo."
    break
  fi
  sleep 3
done

echo
echo "  [4/4] Abriendo http://localhost:8501"
if command -v open >/dev/null 2>&1; then open http://localhost:8501            # macOS
elif command -v xdg-open >/dev/null 2>&1; then xdg-open http://localhost:8501 >/dev/null 2>&1 &  # Linux
else echo "        Abrelo a mano: http://localhost:8501"; fi

cat <<'FIN'

  ---------------------------------------------------------------
  El sistema quedo corriendo en segundo plano.

  Tablero .............. http://localhost:8501
  API de ordenes ....... http://localhost:8000/docs
  API de metricas ...... http://localhost:8001/docs

  Para detenerlo:  docker compose down
  ---------------------------------------------------------------
FIN
