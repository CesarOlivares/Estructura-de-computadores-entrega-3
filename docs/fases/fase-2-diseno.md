# Fase 2 — Diseño en papel

**Estado: DISEÑO LISTO (21/08/2026) — PRUEBA DE EQUIPO PENDIENTE.**
La prueba oficial de la fase (ambos integrantes responden el cuestionario de
`diseno.md` §6 sin mirar el documento) aún no se hace. Según el plan §8 la fase
no está terminada hasta que pase; es **bloqueante antes de repartir las fases
8–11**, donde los dos programan en paralelo contra este contrato.

## Objetivo

Escribir `docs/diseno.md`: los contratos de las tres APIs, el esquema de las
tablas `ordenes` y `eventos`, y el criterio de cuello de botella — para que los
dos integrantes programen contra lo mismo cuando se repartan las fases.

## Qué se logró

- [x] Contratos de `orders-api`, `estacion` y `metrics-api`: método, ruta,
      entrada, respuesta y códigos de estado de cada endpoint.
- [x] Esquema de datos: `ordenes` y `eventos`, con la regla de cuándo se escribe
      cada evento (3 por etapa, 12 por orden completa).
- [x] **Decisión abierta #1 cerrada**: cuello de botella por espera promedio en
      ventana móvil (no servicio, no largo de cola). Justificación en el
      documento. Los umbrales exactos (decisión #2) quedan para la Fase 10.
- [x] Cuestionario de la fase con respuestas, para estudiar antes de la defensa.

## Principales dificultades

1. **La fórmula de espera del plan es ambigua con 4 etapas en serie.** El plan
   define `espera = t_inicio − t_creada`, correcto para una etapa sola. Con
   etapas encadenadas, la espera de cada etapa debe medirse contra su propio
   evento `entra_cola`; medirla contra la creación acumularía las demoras de las
   etapas anteriores y el detector señalaría al culpable equivocado. Quedó
   documentado como refinamiento en `diseno.md` §3.

2. **Resistir la tentación de guardar métricas.** Espera, servicio y lead time
   NO se persisten por orden: se calculan siempre desde `eventos`. Guardarlos
   duplicados es la forma más fácil de que dos números se contradigan en la demo.

## Decisiones tomadas en esta fase

- Ids de orden: enteros autoincrementales (legibles en la demo y naturales en
  SQLite; con un único `orders-api` no hay riesgo de colisión).
- Estados de orden: solo `en_proceso` y `terminada`; la etapa actual se deriva
  del último evento, no se guarda.
- Fechas ISO 8601 UTC en todo el sistema; la UI convierte a hora local.

## Qué queda para la siguiente fase

- **Pendiente de equipo:** la prueba oficial de la fase es que ambos integrantes
  respondan el cuestionario de `diseno.md` §6 sin mirar el documento. Hacerlo
  cuando estén juntos; si alguno duda, releer y repetir.
- Siguiente: **Fase 3 — `orders-api` mínima en Docker** (en memoria, sin Redis),
  programada contra el contrato de `diseno.md` §1.1.
