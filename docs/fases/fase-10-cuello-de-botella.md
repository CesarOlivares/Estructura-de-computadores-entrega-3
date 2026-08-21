# Fase 10 — Cuello de botella y estados

**Estado: CERRADA (21/08/2026)**

## Objetivo

`GET /metricas/cuello`: detectar en vivo qué etapa está atascada, clasificar
cada etapa en `normal` / `advertencia` / `critico`, y que esos estados cambien
**solos** con la carga (criterio en `docs/diseno.md` §4).

## Qué se logró

- [x] `detectar_cuello()` en `metricas/app.py`: la etapa con mayor espera
      promedio en la ventana, si supera su umbral de advertencia; `null` si
      ninguna lo supera.
- [x] Decisión abierta #2 cerrada: ventana 60 s, advertencia ≥ 1.5× ciclo,
      crítico ≥ 3× ciclo (relativos al ciclo de **cada** etapa; tabla y
      justificación en `docs/diseno.md` §4).
- [x] Umbrales conectados al compose: `TIEMPOS_CICLO` se arma con los mismos
      `CICLO_*` de las estaciones — si un experimento cambia un ciclo, los
      umbrales se ajustan solos.
- [x] **Prueba oficial de saturación** (ver evidencia abajo).

## Prueba de saturación

Carga: 12 órdenes, una cada 5 s. Fileteado (ciclo 4 s) absorbe ese ritmo;
envasado (ciclo 12 s, 1 réplica) recibe cada 5 s y drena cada 12 s → se atasca.

Estados observados vía `GET /metricas/cuello` (poll cada 5 s, se registra
cada cambio):

| Hora | Evento |
|---|---|
| 14:28:42 | Inicio de la carga — todo `normal`, `cuello: null` |
| 14:29:48 | Envasado pasa a **advertencia** solo (espera prom. 30.38 s > 18 s = 1.5×12). Fileteado 0.06 s, sellado 0.26 s, esterilización 0.28 s: siguen `normal` |
| 14:30:15 | Envasado pasa a **crítico** solo (espera > 36 s = 3×12) |
| ~14:31 | Última orden del backlog sale de la línea |
| 14:32:08 | Todo vuelve a **`normal` sin intervención**, `cuello: null` — las esperas altas salieron de la ventana de 60 s |

Verificación del "no avanzar si" del plan: la etapa marcada NO es simplemente
la de mayor ciclo — durante la recuperación el **servicio** de envasado seguía
en ~12 s dentro de la ventana y aun así el estado volvió a `normal`, porque lo
que se mide es **espera**. Y esterilización (segundo ciclo más largo, 7 s)
jamás salió de `normal`.

## Principales dificultades

1. **Calibrar la carga de la prueba.** Un burst de 12 órdenes simultáneas
   satura también fileteado (recibe 12 de golpe y drena cada 4 s), y el
   experimento pierde limpieza porque dos etapas alarman a la vez. Con 1
   orden cada 5 s, fileteado absorbe (5 > 4) y solo envasado se atasca
   (5 < 12): el cuello aparece donde la teoría dice. Lección para la Fase 14:
   el ritmo de creación es parte del diseño del experimento, no un detalle.

## Decisiones tomadas en esta fase

- **Umbrales relativos al ciclo de cada etapa, no absolutos.** Un umbral
  absoluto marcaría siempre a la etapa de ciclo largo, que es medir servicio
  disfrazado. Con umbrales relativos, envasado en régimen normal (espera < 18 s)
  no alarma, y sellado con 10 s de espera (>3× su ciclo) sí — como corresponde.
- **Sin espera medible en la ventana → `normal`.** Si nadie arrancó una orden
  en la etapa durante la ventana, no hay evidencia de atasco. Esto es lo que
  hace que el estado **vuelva solo** a normal al bajar la carga.

## Qué queda para la siguiente fase

**Fase 11 — UI Streamlit**: timeline, carga por réplica, alerta de cuello y
histórico. Requiere además `GET /metricas/historico` (contrato en
`docs/diseno.md` §1.3), que se implementará junto con la UI que lo consume.
