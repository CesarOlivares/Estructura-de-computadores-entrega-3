# Demo desechable — Fase 1

Prototipo de usar y botar para entender el mecanismo de cola compartida antes
de construir los servicios reales sobre él. **No es parte del sistema final.**

## Qué demuestra

Varios trabajadores compitiendo por la misma cola de Redis mediante `BRPOP`
(extracción atómica y bloqueante): cada orden la procesa **exactamente un**
trabajador — cero duplicados, cero pérdidas — sin ningún coordinador extra.

## Cómo ejecutarla

```bash
# 1. Redis en un contenedor
docker run -d --name demo-redis -p 6379:6379 redis

# 2. Dependencia de Python
pip install redis

# 3. En tres terminales distintas, un trabajador por terminal
python demo/trabajador.py

# 4. En una cuarta terminal, el productor
python demo/productor.py
```

## Resultado de la prueba (verificado en la Fase 1)

Con 3 trabajadores de igual velocidad y 15 órdenes: reparto **5 / 5 / 5**,
suma exacta 15, ninguna orden repetida entre trabajadores.

> Observación para el informe: con trabajadores de igual velocidad el reparto
> coincide con un round-robin. Eso es coincidencia, no mecanismo. La
> diferencia se demuestra en la Fase 7, cuando una réplica lenta pasa a
> procesar menos que las rápidas.
