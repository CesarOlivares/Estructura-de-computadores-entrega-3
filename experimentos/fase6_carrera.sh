#!/usr/bin/env bash
# Experimento Fase 6: ¿se procesan órdenes duplicadas?
#
# Encola N órdenes (ids 1..N) directo en cola:envasado y, cuando la cola se
# vacía, cuenta con el hash conteo:procesadas:envasado cuántas veces procesó
# ESA ETAPA cada una. Con el reclamo ingenuo se esperan duplicados; con el
# atómico, cero.
#
# El contador es por etapa a propósito: un lote pasa por las cuatro estaciones,
# así que un contador único para toda la línea leería el avance normal de un
# lote como si lo hubieran procesado cuatro veces. Lo que se mide aquí es si
# dos réplicas DE ENVASADO tomaron el mismo lote.
#
# Uso:   ./experimentos/fase6_carrera.sh [N]      (default N=200)
# Antes: levantar la línea con el modo a probar, p. ej.:
#   MODO_RECLAMO=ingenuo CICLO_ENVASADO=0.05 docker compose up -d --scale envasado=3
#
# La versión de un clic de este mismo experimento está al final del tablero
# (http://localhost:8501), y usa las mismas funciones de reclamo.
set -e
N=${1:-200}
cd "$(dirname "$0")/.."

echo "== limpiando colas y contadores =="
# Se vacían TODAS las colas de la línea, no solo la de envasado: si quedaran
# lotes de una corrida anterior circulando por sellado o esterilización,
# seguirían moviéndose durante esta medición y ensuciarían el resultado.
docker compose exec -T redis redis-cli DEL \
  cola:fileteado cola:envasado cola:sellado cola:esterilizacion cola:listos \
  conteo:procesadas:envasado conteo:replica > /dev/null

echo "== encolando $N ordenes en cola:envasado =="
docker compose exec -T redis sh -c "for i in \$(seq 1 $N); do redis-cli LPUSH cola:envasado \$i > /dev/null; done"

echo "== esperando a que la cola se vacie =="
while [ "$(docker compose exec -T redis redis-cli LLEN cola:envasado | tr -d '\r')" != "0" ]; do
  sleep 1
done
sleep 3  # margen para los ciclos en curso

echo "== resultado =="
docker compose exec -T redis redis-cli HGETALL conteo:procesadas:envasado | tr -d '\r' | paste - - | \
  awk -v n="$N" '
    { total += $2; vistas++
      if ($2 > 1) { dup++; print "  DUPLICADA: orden", $1, "procesada", $2, "veces" } }
    END { print "ordenes distintas procesadas: " vistas "/" n
          print "procesamientos totales:       " total
          print "ordenes duplicadas:           " dup+0
          print "ordenes perdidas:             " n-vistas }'

echo "== procesadas por replica de envasado =="
# Solo las réplicas de envasado: las de las otras etapas están procesando los
# mismos lotes más adelante en la línea y no participan de esta carrera.
docker compose exec -T redis redis-cli HGETALL conteo:replica | tr -d '\r' | paste - - | \
  grep '^envasado' || echo "  (sin réplicas de envasado con trabajo hecho)"
