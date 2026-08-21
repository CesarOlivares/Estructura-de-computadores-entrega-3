#!/usr/bin/env bash
# Experimento Fase 7: ¿el reparto se adapta a la velocidad de cada réplica?
#
# Con 2 réplicas normales + 1 lenta (el doble de tiempo de ciclo) sobre la
# misma cola, encola N órdenes y muestra cuántas procesó cada una. Si el
# balanceo es por demanda, la lenta procesa visiblemente menos (~la mitad).
# Un round-robin repartiría N/3 a cada una sin importar la velocidad.
#
# Uso:   ./experimentos/fase7_balanceo.sh [N]      (default N=60)
# Antes: levantar 2 réplicas normales + la lenta (perfil experimento):
#   CICLO_ENVASADO=1.2 CICLO_ENVASADO_LENTO=2.4 \
#     docker compose --profile experimento up -d --scale envasado=2
set -e
N=${1:-60}
cd "$(dirname "$0")/.."

echo "== limpiando colas y contadores =="
docker compose exec -T redis redis-cli DEL cola:envasado cola:sellado conteo:procesadas conteo:replica > /dev/null

echo "== encolando $N ordenes en cola:envasado =="
docker compose exec -T redis sh -c "for i in \$(seq 1 $N); do redis-cli LPUSH cola:envasado \$i > /dev/null; done"

echo "== esperando a que la cola se vacie =="
while [ "$(docker compose exec -T redis redis-cli LLEN cola:envasado | tr -d '\r')" != "0" ]; do
  sleep 1
done
sleep 4  # margen para los ciclos en curso (la lenta puede seguir trabajando)

echo "== ordenes procesadas por replica =="
docker compose exec -T redis redis-cli HGETALL conteo:replica | tr -d '\r' | paste - - | sort -t'	' -k2 -rn
echo "(total esperado: $N, sin duplicados; la replica 'envasado-lento-*' debe tener menos)"
