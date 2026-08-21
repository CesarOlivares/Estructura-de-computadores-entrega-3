# Fase 7 — Balanceo dinámico con N réplicas

**Estado: CERRADA (21/08/2026)**

## Objetivo

Demostrar que el reparto por demanda (cola *pull*) se adapta solo a la
velocidad de cada réplica — el argumento central del proyecto frente a un
balanceador clásico round-robin.

## Qué se logró

- [x] Réplicas escalables: `docker compose up --scale envasado=N` (el servicio
      no fija `container_name`).
- [x] Identidad por réplica: `replica_id` (etapa + hostname del contenedor) en
      cada línea de log y en `GET /estado` (contrato §1.2: etapa, replica_id,
      procesadas, ocupada, en_cola).
- [x] Latido en Redis: cada réplica publica su estado y su tiempo de ciclo en
      el hash `estado:replicas` — métricas y UI ven todas las réplicas sin
      descubrirlas una a una (con réplicas escaladas el DNS de Docker no
      permite consultarlas individualmente de forma confiable).
- [x] Réplica lenta como servicio `envasado-lento` (misma imagen, misma cola,
      doble ciclo), tras el perfil `experimento` para que el
      `docker compose up` normal no la levante.
- [x] Experimento reproducible: `experimentos/fase7_balanceo.sh`.

## Resultado medido (21/08/2026 — 60 órdenes, ciclos 1.2 s / 1.2 s / 2.4 s)

| Réplica | Tiempo de ciclo | Órdenes procesadas |
|---|---|---|
| envasado-bd090c7c2478 | 1.2 s | **24** |
| envasado-3644cd116529 | 1.2 s | **24** |
| envasado-lento-dfd66937d33e | **2.4 s** | **12** |

Coincide exactamente con la tabla objetivo del plan (~24/~24/~12): la réplica
con el doble de ciclo procesó la mitad, **sin que nadie le asignara menos**:
simplemente pidió trabajo la mitad de veces. Un round-robin le habría dado 20
a cada una y la cola habría crecido detrás de la lenta.

> Nota metodológica: los ciclos del experimento (1.2/2.4 s) son los del diseño
> (12/24 s) divididos por 10 para que la corrida tome ~40 s en vez de ~7 min.
> El reparto depende de la **razón** entre velocidades, no del valor absoluto.
> Los experimentos formales de la Fase 14 se harán con los tiempos reales.

## Principales dificultades

1. **Consultar réplicas escaladas una a una no es confiable**: con
   `--scale envasado=2` ambas comparten el nombre DNS `envasado` y Docker
   resuelve a cualquiera. Por eso el estado por réplica se publica al hash
   `estado:replicas` (cada réplica se reporta a sí misma) en vez de que un
   recolector las encueste. Esto debería documentarse en el informe como
   decisión de arquitectura.

## Qué queda para la siguiente fase

**Fase 8 — persistencia**: SQLite en un volumen; `orders-api` guarda órdenes,
las estaciones registran eventos (`entra_cola` / `inicia` / `termina`).
