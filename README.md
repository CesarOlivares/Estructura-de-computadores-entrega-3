# Estructura de Computadores — Evaluación 3

**Caso 2: Línea de Producción con Balanceo Dinámico** · ECSD 2026-1 · USACH

Simulación distribuida de una planta conservera ficticia de jurel en lata (425 g),
con cuatro etapas en serie y balanceo dinámico de carga en la etapa replicada:

```
cola → FILETEADO → cola → ENVASADO → cola → SELLADO → cola → ESTERILIZACIÓN → listos
         ×1                ×2–3              ×1                 ×1
```

## Integrantes

- César Olivares
- (segundo integrante)

## Stack

| Componente | Tecnología |
|---|---|
| Servicios | Python + FastAPI |
| Interfaz | Streamlit |
| Coordinación / colas | Redis |
| Persistencia | SQLite |
| Despliegue | Docker Compose |

## Estructura del repositorio

```
docs/fases/      Bitácoras por fase: qué se logró, dificultades, pendientes
demo/            Prototipo desechable de cola + workers (Fase 1)
servicios/       Servicios del sistema (en construcción)
```

## Ejecución

> **En construcción.** El objetivo es que todo el sistema se levante con un solo
> comando (`docker compose up`); las instrucciones completas de instalación,
> configuración y ejecución se completan en la fase de reproducibilidad.
