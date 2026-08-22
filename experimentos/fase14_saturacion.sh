#!/usr/bin/env bash
# Experimento Fase 14 (5): saturacion y recuperacion automatica.
#
# Inyecta una rafaga de N ordenes lo mas rapido posible (mucho mas rapido de
# lo que la linea drena) y luego observa /metricas/cuello cada 15 s. Lo que
# debe verse, sin tocar nada:
#   1. la etapa saturada pasa a advertencia y luego a critico SOLA
#   2. al dejar de inyectar, vuelve a normal SOLA (la ventana movil olvida)
#
# Con una rafaga, la etapa saturada es la PRIMERA (fileteado): todos los lotes
# se apilan en su cola de entrada. Es la leccion de la Fase 10: el cuello
# depende del patron de llegada, no solo de los tiempos de ciclo.
#
# Uso:   ./experimentos/fase14_saturacion.sh [N] [MINUTOS_OBSERVACION]
#        (defaults: 25 ordenes, 6 minutos)
set -e
N=${1:-25}
MINUTOS=${2:-6}
cd "$(dirname "$0")/.."
mkdir -p experimentos/resultados

echo "== rafaga de $N ordenes =="
for i in $(seq 1 "$N"); do
  curl -s -o /dev/null -X POST http://localhost:8000/ordenes \
       -H "Content-Type: application/json" \
       -d '{"producto":"jurel-425g","cantidad":500}' || true
done
echo "   listo. Observando estados cada 15 s durante $MINUTOS min:"

BITACORA="experimentos/resultados/exp5-saturacion.txt"
: > "$BITACORA"
fin=$(( $(date +%s) + MINUTOS * 60 ))
t0=$(date +%s)
while [ "$(date +%s)" -lt "$fin" ]; do
  linea=$(curl -s -m 5 "http://localhost:8001/metricas/cuello?ventana_s=60" | python -c "
import json, sys
d = json.load(sys.stdin)
estados = ' '.join(f'{e}:{s}' for e, s in d['estados'].items())
print(f\"cuello={d['cuello']} {estados}\")" 2>/dev/null || echo "sin respuesta")
  echo "t=$(( $(date +%s) - t0 ))s  $linea" | tee -a "$BITACORA"
  sleep 15
done
echo "== bitacora en $BITACORA =="
