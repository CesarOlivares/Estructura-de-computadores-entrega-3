#!/usr/bin/env bash
# Experimentos Fase 14 (1, 2 y 3): inyectar carga a ritmo constante y medir.
#
# Crea una orden real via POST /ordenes cada INTERVALO segundos durante
# DURACION segundos, y al final consulta /metricas y /metricas/cuello.
# El ritmo constante importa: inyectar todo de golpe apila los lotes en la
# PRIMERA cola y el cuello medido seria fileteado (correcto, pero para la
# pregunta equivocada — ver bitacora de la Fase 10).
#
# Uso:   ./experimentos/fase14_carga.sh [INTERVALO] [DURACION] [ETIQUETA]
#        (defaults: 5 s entre ordenes, 180 s de inyeccion)
# Antes: levantar la linea con la escala del experimento, p. ej.:
#   docker compose up -d --scale envasado=2
#
# Resultados: se imprimen y quedan en experimentos/resultados/<ETIQUETA>.json
set -e
INTERVALO=${1:-5}
DURACION=${2:-180}
ETIQUETA=${3:-experimento}
cd "$(dirname "$0")/.."
mkdir -p experimentos/resultados

echo "== inyectando 1 orden cada ${INTERVALO}s durante ${DURACION}s =="
fin=$(( $(date +%s) + DURACION ))
creadas=0
while [ "$(date +%s)" -lt "$fin" ]; do
  curl -s -o /dev/null -X POST http://localhost:8000/ordenes \
       -H "Content-Type: application/json" \
       -d '{"producto":"jurel-425g","cantidad":500}' || true
  creadas=$((creadas + 1))
  sleep "$INTERVALO"
done
echo "   $creadas ordenes creadas"

# Medir en regimen: las ultimas ordenes aun estan dentro de la linea, que es
# exactamente el momento que interesa fotografiar.
echo "== metricas (ventana 60 s) =="
curl -s "http://localhost:8001/metricas?ventana_s=60" | tee "experimentos/resultados/${ETIQUETA}-metricas.json" | python -m json.tool
echo "== cuello de botella =="
curl -s "http://localhost:8001/metricas/cuello?ventana_s=60" | tee "experimentos/resultados/${ETIQUETA}-cuello.json" | python -m json.tool
echo "== carga por replica (hash estado:replicas) =="
docker compose exec -T redis redis-cli HGETALL conteo:replica | tr -d '\r' | paste - -
