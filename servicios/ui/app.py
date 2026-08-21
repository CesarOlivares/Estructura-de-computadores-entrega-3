"""
Tablero de operaciones de la linea de produccion — Caso 2.

Consume los servicios reales: orders-api para ingresar lotes y metrics-api para
todos los numeros. No hay simulacion ni datos de ejemplo; si un servicio no
responde, la pantalla lo dice y explica que hacer.

UNA sola pantalla que se lee de arriba a abajo, sin pestanas ni nada escondido.
El orden va de la pregunta mas urgente a la menos:

    1. ¿Hay algun problema?          -> el cartel
    2. ¿Cuanto se esta produciendo?  -> tres numeros
    3. ¿Donde esta cada lote ahora?  -> el diagrama de la linea
    4. ¿Esto viene empeorando?       -> el grafico

Cubre lo que el enunciado pide de la UI: timeline de produccion, indicador de
carga por replica, alerta visual de cuello de botella e interaccion real. Y lo
que la rubrica exige aparte: historico ademas de tiempo real, y mensajes claros
cuando algo falla.

app.py solo dibuja. Todo lo que sea red vive en datos.py.
"""

import time

import streamlit as st

import datos
import estilo
import graficos

st.set_page_config(page_title="Línea de producción — conservera de jurel",
                   page_icon="🥫", layout="wide")
st.markdown(estilo.CSS, unsafe_allow_html=True)

# Cuantos puntos del historico se guardan. A 2 s por muestra, 300 puntos son
# unos 10 minutos, que es mas que suficiente para ver una tendencia.
MAX_HISTORICO = 300


def formatear(valor, sufijo=""):
    """Muestra un guion cuando todavia no hay dato, en vez de inventar un 0.

    Un 0 y un "aun no medido" significan cosas distintas y no pueden verse
    iguales. metrics-api devuelve null cuando no hubo mediciones en la ventana.
    """
    return "–" if valor is None else f"{valor:.0f}{sufijo}"


# ==========================================================================
# Panel lateral: primero la accion, despues los ajustes
# ==========================================================================

with st.sidebar:
    st.markdown("### 🥫 Línea de producción")
    st.caption("Conservera de jurel en lata de 425 g")

    st.divider()

    st.markdown("#### Ingresar un lote")
    st.caption("Un lote entra por el principio de la línea y la recorre entera.")
    with st.form("ingresar", clear_on_submit=False):
        cantidad = st.number_input("Latas del lote", min_value=1, max_value=100_000,
                                   value=500, step=100)
        enviar = st.form_submit_button("Ingresar lote a la línea",
                                       width="stretch", type="primary")

    if enviar:
        ok, texto = datos.crear_orden("jurel-425g", int(cantidad))
        st.session_state["mensaje"] = ("ok" if ok else "error", texto)

    mensaje = st.session_state.get("mensaje")
    if mensaje:
        (st.success if mensaje[0] == "ok" else st.error)(mensaje[1])

    st.divider()

    with st.expander("Ajustes"):
        ventana_s = st.slider(
            "Promediar los últimos (s)", 15, 300, 60, step=15,
            help="Las esperas se promedian solo dentro de esta ventana, para que "
                 "el tablero refleje lo que pasa ahora y no el arrastre de hace "
                 "diez minutos.")
        refresco = st.selectbox("Actualizar cada", [1, 2, 5, 10], index=1,
                                format_func=lambda s: f"{s} s")
        if st.button("Borrar el histórico del gráfico", width="stretch"):
            st.session_state["historico"] = []

    st.divider()
    st.caption("**Servicios**")
    for nombre, valor in datos.salud().items():
        st.caption(f'{"🟢" if valor == "ok" else "🔴"} {nombre} — {valor}')


# ==========================================================================
# La pantalla
# ==========================================================================

st.markdown("## Tablero de operaciones")
st.markdown("Cada **lote** de latas recorre cuatro etapas en orden. Aquí se ve "
            "dónde está cada lote ahora mismo y en qué etapa se está acumulando "
            "el trabajo.")

st.session_state.setdefault("historico", [])
st.session_state.setdefault("t0", time.time())


@st.fragment(run_every=refresco)
def tablero():
    try:
        estado = datos.tablero(ventana_s)
    except datos.ErrorDeServicio as error:
        # Un mensaje que se entienda, no un traceback ni una pantalla en blanco.
        # El diagnostico revisa que servicio falta de verdad: si Redis se cae,
        # los demas siguen vivos pero se quedan esperandolo, y culpar al que
        # responde lento manda a buscar el error donde no esta.
        st.error(f"**No se pueden mostrar los datos.** {error}")
        st.info(datos.diagnostico())
        return

    etapas = estado["etapas"]
    cuello = estado["cuello"]
    etapa_cuello = cuello.get("cuello")

    # --- Muestreo del historico -------------------------------------------
    # Ningun servicio guarda la serie temporal, asi que la arma el tablero con
    # lo que ya viene en cada refresco. Vive en memoria de la sesion.
    st.session_state["historico"].append({
        "t": round(time.time() - st.session_state["t0"], 1),
        "esperas": {e["etapa"]: e["espera"] for e in etapas},
    })
    st.session_state["historico"] = st.session_state["historico"][-MAX_HISTORICO:]

    # --- 1. ¿Hay algun problema? ------------------------------------------
    if etapa_cuello:
        nombre = estilo.NOMBRE_ETAPA.get(etapa_cuello, etapa_cuello)
        datos_cuello = next(e for e in etapas if e["etapa"] == etapa_cuello)
        espera = datos_cuello["espera"]
        en_cola = datos_cuello["en_cola"]
        detalle = (f"Los lotes esperan <b>{espera:.0f} segundos</b> antes de entrar "
                   f"a {nombre.lower()}, la espera más larga de la línea.")
        if en_cola:
            detalle += f" Hay <b>{en_cola} lotes</b> haciendo cola."
        detalle += " Es la etapa que marca el ritmo de todo lo demás."
        st.markdown(estilo.cartel(datos_cuello["estado"],
                                  f"El trabajo se está acumulando en {nombre}",
                                  detalle), unsafe_allow_html=True)
    else:
        st.markdown(estilo.cartel(
            "normal", "La línea va al día",
            "Ninguna etapa está acumulando trabajo: los lotes entran a cada "
            "máquina apenas llegan."), unsafe_allow_html=True)

    # --- 2. ¿Cuanto se esta produciendo? ----------------------------------
    st.markdown(estilo.fila_kpis([
        estilo.kpi(estado["en_la_linea"], "", "lotes dentro de la línea ahora"),
        estilo.kpi(estado["terminados"], "", "lotes terminados"),
        estilo.kpi(formatear(estado["lead_time"]), " s",
                   "demora un lote de principio a fin"),
    ]), unsafe_allow_html=True)

    # --- 3. ¿Donde esta cada lote ahora? ----------------------------------
    st.markdown("#### Recorrido de los lotes")
    if not estado["hay_replicas"]:
        st.warning("Ninguna estación está publicando su estado. Puede que las "
                   "estaciones aún estén arrancando, o que Redis no responda.",
                   icon="⚠️")
    piezas = []
    for etapa in etapas:
        piezas.append(estilo.cola(etapa["en_cola"], etapa["estado"]))
        piezas.append(estilo.estacion(etapa))
    piezas.append(estilo.terminados(estado["terminados"]))
    st.markdown(f'<div class="linea">{"".join(piezas)}</div>',
                unsafe_allow_html=True)
    st.markdown(estilo.leyenda(), unsafe_allow_html=True)

    # --- 4. ¿Esto viene empeorando? ---------------------------------------
    st.markdown("#### Cuánto esperan los lotes antes de cada etapa")
    st.caption("Si una línea sube de forma sostenida, esa etapa se está quedando "
               "atrás. Si se mantiene plana, sigue el ritmo aunque sea lenta.")
    figura = graficos.evolucion(st.session_state["historico"], etapas, etapa_cuello)
    if figura is None:
        st.caption("Todavía no hay mediciones. Ingresa algunos lotes y espera "
                   "unos segundos.")
    else:
        st.plotly_chart(figura, width="stretch", config={"displayModeBar": False})

    # El criterio con el que se decidio el estado, para poder defenderlo.
    st.caption(f'Criterio: {cuello.get("razon", "—")}')


tablero()
