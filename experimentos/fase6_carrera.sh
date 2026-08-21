#!/usr/bin/env bash
# Experimento Fase 6: ¿se procesan órdenes duplicadas?
#
# Encola N órdenes (ids 1..N) directo en cola:envasado y, cuando la cola se
# vacía, cuenta con el hash conteo:procesadas cuántas veces se procesó cada
# una. Con el reclamo ingenuo se esperan duplicados; con el atómico, cero.
#
# Uso:   ./experimentos/fase6_carrera.sh [N]      (default N=200)
# Antes: levantar la línea con el modo a probar, p. ej.:
#   MODO_RECLAMO=ingenuo CICLO_ENVASADO=0.05 docker compose up -d --scale envasado=3
set -e
N=${1:-200}
cd "$(dirname "$0")/.."

echo "== limpiando colas y contadores =="
docker compose exec -T redis redis-cli DEL cola:envasado cola:sellado conteo:procesadas conteo:replica > /dev/null

echo "== encolando $N ordenes en cola:envasado =="
docker compose exec -T redis sh -c "for i in \$(seq 1 $N); do redis-cli LPUSH cola:envasado \$i > /dev/null; done"

echo "== esperando a que la cola se vacie =="
while [ "$(docker compose exec -T redis redis-cli LLEN cola:envasado | tr -d '\r')" != "0" ]; do
  sleep 1
done
sleep 3  # margen para los ciclos en curso

echo "== resultado =="
docker compose exec -T redis redis-cli HGETALL conteo:procesadas | tr -d '\r' | paste - - | \
  awk -v n="$N" '
    { total += $2; vistas++
      if ($2 > 1) { dup++; print "  DUPLICADA: orden", $1, "procesada", $2, "veces" } }
    END { print "ordenes distintas procesadas: " vistas "/" n
          print "procesamientos totales:       " total
          print "ordenes duplicadas:           " dup+0
          print "ordenes perdidas:             " n-vistas }'

echo "== procesadas por replica =="
docker compose exec -T redis redis-cli HGETALL conteo:replica | tr -d '\r' | paste - -
