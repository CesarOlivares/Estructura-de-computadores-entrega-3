# Diseño del sistema — Fase 2

> Este documento es el contrato contra el que programan los dos integrantes.
> Si el código y este documento se contradicen, gana este documento (o se
> actualiza aquí primero y después se cambia el código).

Línea de producción simulada de una conservera de jurel en lata (425 g):

```
cola:fileteado → FILETEADO → cola:envasado → ENVASADO → cola:sellado → SELLADO → cola:esterilizacion → ESTERILIZACIÓN → listas
                   ×1  (4 s)                 ×2–3 (12 s)               ×1 (3 s)                          ×1 (7 s)
```

---

## 1. Contratos de las APIs

Convenciones generales:

- Todo es JSON sobre HTTP.
- Fechas en **ISO 8601 UTC** (ej: `2026-08-21T17:30:00+00:00`). La UI convierte a hora local.
- Errores de validación → **422** (los genera FastAPI/Pydantic automáticamente).
- Recurso inexistente → **404** con `{"detail": "..."}`.
- Dependencia caída (Redis/BD) → **503** con mensaje claro (se implementa en Fase 12).
- Todos los servicios exponen `GET /salud` → `200 {"estado": "ok"}` para healthchecks.

### 1.1 `orders-api` (puerto 8000)

#### `POST /ordenes` — crear una orden de producción

Entrada:

```json
{ "producto": "jurel-425g", "cantidad": 10 }
```

| Campo | Regla |
|---|---|
| `producto` | string, no vacío (tampoco solo espacios) |
| `cantidad` | entero **mayor que 0** (latas del lote) |

Respuesta **201**:

```json
{
  "id": 1,
  "producto": "jurel-425g",
  "cantidad": 10,
  "estado": "en_proceso",
  "creada_en": "2026-08-21T17:30:00+00:00",
  "terminada_en": null
}
```

- **422** si la entrada no cumple las reglas (nunca 500, nunca 201).
- Efecto colateral desde la Fase 4: el `id` se encola en `cola:fileteado` (Redis).

#### `GET /ordenes/{id}`

- **200** con la orden completa (incluye `terminada_en`, `null` si sigue en proceso).
- **404** si el id no existe.

#### `GET /ordenes?estado=<en_proceso|terminada>`

- **200** con la lista de órdenes (todas, o filtradas por `estado`).
- **422** si `estado` trae un valor fuera del catálogo.

### 1.2 `estacion` (el mismo servicio desplegado 4 veces)

Configuración por variables de entorno — **nunca** valores escritos en el código:

```
NOMBRE_ETAPA=envasado
COLA_ENTRADA=cola:envasado
COLA_SALIDA=cola:sellado
TIEMPO_CICLO=12
```

#### `GET /estado`

```json
{
  "etapa": "envasado",
  "replica_id": "envasado-a1b2c3",
  "procesadas": 17,
  "ocupada": true,
  "en_cola": 4
}
```

`en_cola` es el largo actual de su cola de entrada (`LLEN`). `replica_id` se genera
al arrancar (nombre de etapa + sufijo único) y aparece también en cada log.

### 1.3 `metrics-api` (puerto 8001)

#### `GET /metricas`

Por etapa, calculado desde la tabla `eventos` (ver §2 y §3):

```json
{
  "ventana_s": 60,
  "etapas": {
    "envasado": {
      "espera_promedio_s": 8.2,
      "servicio_promedio_s": 12.1,
      "en_cola": 4,
      "procesadas": 17
    }
  },
  "lead_time_promedio_s": 31.4
}
```

#### `GET /metricas/cuello`

```json
{
  "cuello": "esterilizacion",
  "estados": { "fileteado": "normal", "envasado": "normal",
               "sellado": "normal", "esterilizacion": "critico" },
  "razon": "espera promedio 14.3 s en la ventana de 60 s, sobre el umbral crítico"
}
```

`cuello` es `null` si ninguna etapa supera el umbral de advertencia.

#### `GET /metricas/historico`

Serie temporal muestreada para los gráficos de la UI (la rúbrica exige histórico
además del tiempo real):

```json
{ "puntos": [ { "timestamp": "...", "etapa": "envasado",
                "espera_promedio_s": 8.2, "en_cola": 4 } ] }
```

---

## 2. Esquema de datos (SQLite)

Dos tablas. Todo lo demás se **calcula** desde `eventos`; no se guarda duplicado,
porque el dato guardado dos veces es el dato que se contradice.

```sql
CREATE TABLE ordenes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    producto     TEXT    NOT NULL,
    cantidad     INTEGER NOT NULL CHECK (cantidad > 0),
    estado       TEXT    NOT NULL DEFAULT 'en_proceso',  -- en_proceso | terminada
    creada_en    TEXT    NOT NULL,                       -- ISO 8601 UTC
    terminada_en TEXT                                    -- NULL hasta terminar
);

CREATE TABLE eventos (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    orden_id  INTEGER NOT NULL REFERENCES ordenes(id),
    etapa     TEXT    NOT NULL,   -- fileteado | envasado | sellado | esterilizacion
    replica_id TEXT   NOT NULL,   -- qué réplica exacta lo hizo
    tipo      TEXT    NOT NULL,   -- entra_cola | inicia | termina
    timestamp TEXT    NOT NULL    -- ISO 8601 UTC
);
```

**Cuándo se escribe cada evento:**

| Momento | Quién escribe | Evento |
|---|---|---|
| La orden entra a una cola | quien la encola (orders-api o la estación anterior) | `entra_cola` |
| Una réplica la saca de la cola (`BRPOP`) | la réplica | `inicia` |
| La réplica termina el ciclo | la réplica | `termina` |

Una orden que recorre las 4 etapas genera **12 eventos** (3 por etapa). El último
`termina` de esterilización además marca `ordenes.estado = 'terminada'` y
`terminada_en`.

**Estados de la orden** (solo dos, a propósito): `en_proceso` desde la creación,
`terminada` al salir de esterilización. "En qué etapa va" no es un estado
guardado: se **deriva** del último evento de la orden.

---

## 3. Métricas: definiciones exactas

Por orden y por etapa, usando los timestamps de `eventos`:

```
espera(orden, etapa)   = t_inicia(etapa)  - t_entra_cola(etapa)   ← cuánto esperó en ESA cola
servicio(orden, etapa) = t_termina(etapa) - t_inicia(etapa)       ← cuánto tardó el ciclo
lead_time(orden)       = t_termina(esterilizacion) - creada_en    ← puerta a puerta
```

> Nota: el plan resume `espera = t_inicio − t_creada`, que es el caso de una sola
> etapa. Con 4 etapas en serie, la espera **de cada etapa** se mide contra su
> propio `entra_cola`; si se midiera contra `creada_en`, la espera de sellado
> incluiría todo lo que pasó en fileteado y envasado, y señalaría al culpable
> equivocado.

Los promedios de `/metricas` se calculan sobre una **ventana móvil** (default
60 s): solo eventos cuyo `termina`/`inicia` cae dentro de la ventana. Así el
indicador refleja el presente, no el arrastre histórico.

---

## 4. Criterio de cuello de botella — decisión abierta #1: CERRADA

**Decisión (nuestra, no del enunciado — el enunciado no define el criterio):**

> El cuello de botella es la etapa con **mayor tiempo de espera promedio en la
> ventana móvil**, siempre que ese promedio supere el umbral de advertencia.
> Si ninguna lo supera, no hay cuello de botella (`cuello: null`).

Por qué espera y no las alternativas:

1. **No tiempo de servicio**: un servicio de 12 s solo dice que la tarea es larga.
   Una etapa lenta con cola vacía no es un atasco, es una tarea lenta.
2. **No largo de cola a secas**: depende del ritmo de llegada instantáneo y
   oscila; además una cola corta con espera creciente ya es un atasco naciente.
3. **La espera creciente es la definición operativa de atasco**: el trabajo llega
   más rápido de lo que esa etapa lo drena. Es exactamente lo que un jefe de
   planta llamaría cuello de botella.

Clasificación por etapa: `normal` / `advertencia` / `critico` según umbrales
sobre la espera promedio. **Los valores exactos de los umbrales y el tamaño
definitivo de la ventana quedan para la Fase 10** (decisión abierta #2), cuando
haya datos reales para calibrarlos. Valores provisionales de trabajo: ventana
60 s; advertencia ≈ 1.5× el tiempo de ciclo de la etapa; crítico ≈ 3×.

---

## 5. Supuestos vigentes (del plan §5, se declaran en el informe)

1. Tiempos de ciclo (4/12/3/7 s) inventados para que el experimento sea demostrable.
2. "Procesar" = esperar el tiempo de ciclo; no hay trabajo real.
3. Un lote = una cantidad de latas del mismo formato; no se modelan latas individuales.
4. Entidades persistidas decididas por nosotros: órdenes y eventos (+ métricas derivadas).
5. El criterio de cuello de botella y sus umbrales son definición nuestra (§4).

---

## 6. Cuestionario de la fase (la prueba para avanzar)

Ambos integrantes deben poder responder esto **sin mirar el documento**:

**¿Qué devuelve `POST /ordenes` cuando sale bien y cuando sale mal?**
Bien: `201` con `{id, producto, cantidad, estado, creada_en}`. Mal (cantidad ≤ 0,
producto vacío, campos faltantes): `422` con el detalle de validación. Nunca 500.

**¿Qué campos tiene un evento y en qué momentos se escribe uno?**
`orden_id, etapa, replica_id, tipo, timestamp`. Se escribe al **entrar a una
cola** (`entra_cola`), al **ser tomada por una réplica** (`inicia`) y al
**terminar el ciclo** (`termina`). 3 por etapa, 12 por orden completa.

**¿Cómo se decide que una estación es cuello de botella?**
Por **espera promedio en ventana móvil** (no por tiempo de servicio ni largo de
cola): la etapa con mayor espera promedio, si supera el umbral de advertencia.
La espera de cada etapa se mide contra su propio `entra_cola`.
