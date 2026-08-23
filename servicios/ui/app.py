"""
Tablero de operaciones de la linea de produccion — Caso 2.

Consume los servicios reales: orders-api para ingresar lotes y metrics-api para
todos los numeros. No hay simulacion ni datos de ejemplo; si un servicio no
responde, la pantalla lo dice y explica que hacer.

UNA sola pantalla que se lee de arriba a abajo, sin pestanas ni nada escondido.
El orden va de la pregunta mas urgente a la menos:

    1. ¿Hay algun problema?           -> el cartel
    2. ¿Cuanto se esta produciendo?   -> tres numeros
    3. ¿Donde esta cada lote ahora?   -> el diagrama de la linea
    4. ¿Esto viene empeorando?        -> el grafico de esperas
    5. ¿Por que confiar en esto?      -> la demostracion de la carrera

Los cuatro primeros son el tablero de operacion y se refrescan solos. El quinto
es de otra naturaleza —no se monitorea, se ejecuta a pedido— y por eso va al
final, despues de un separador: responde la pregunta de fondo del Caso 2,
"¿como se yo que dos maquinas no toman el mismo lote?", ejecutando el
experimento en vivo en vez de afirmarlo.

Cubre lo que el enunciado pide de la UI: timeline de produccion, indicador de
carga por replica, alerta visual de cuello de botella e interaccion real. Y lo
que la rubrica exige aparte: historico ademas de tiempo real, y mensajes claros
cuando algo falla.

app.py solo dibuja. Todo lo que sea red vive en datos.py, y la mecanica del
experimento en carrera.py.
"""

import time

import streamlit as st

import carrera
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


# ==========================================================================
# 5. ¿Por que confiar en que esto esta bien hecho?
#
# La seccion de demostracion. Va al final y separada a proposito: el tablero
# de arriba es para operar la linea, esto es para entender por que funciona.
# Quien solo quiere ver la produccion no necesita bajar hasta aca; quien
# pregunta "¿y como se yo que dos maquinas no toman el mismo lote?" encuentra
# la respuesta ejecutable, no una afirmacion.
# ==========================================================================

st.divider()
st.markdown("## Por qué la línea no produce el mismo lote dos veces")
st.markdown(
    "Envasado es la etapa replicada: dos o tres máquinas comen de **una misma "
    "cola**. Nadie les asigna trabajo — cada una **pide** el siguiente lote "
    "cuando queda libre, y por eso el reparto se adapta solo a lo rápida que "
    "sea cada una. Pero pedir de una cola compartida abre un riesgo: si dos "
    "máquinas piden al mismo tiempo, el lote tiene que llevárselo "
    "**exactamente una**.\n\n"
    "Con una sola máquina el problema no existe. Aparece recién al replicar, y "
    "no se ve leyendo el código de una réplica: hay que mirar qué pasa *entre* "
    "dos.")

izquierda, derecha = st.columns(2)
with izquierda:
    st.markdown(estilo.pasos(
        "Reclamo en dos pasos",
        ["Mirar cuál es el próximo lote de la cola — <code>LRANGE</code>",
         "Sacarlo de la cola — <code>LREM</code>"],
        "Entre el paso 1 y el 2 el lote <b>sigue en la cola</b>. Otra máquina "
        "que mire en ese instante ve el mismo lote: las dos lo envasan y la "
        "planta gasta el doble de materia prima para un solo pedido.",
        malo=True), unsafe_allow_html=True)
with derecha:
    st.markdown(estilo.pasos(
        "Reclamo atómico — lo que usa la línea",
        ["Sacar el próximo lote de la cola — <code>BRPOP</code>"],
        "Mirar y sacar son <b>un solo acto indivisible</b>. Redis atiende los "
        "comandos de a uno, así que no existe ningún instante en que dos "
        "máquinas puedan ver disponible el mismo lote.",
        malo=False), unsafe_allow_html=True)

st.markdown("#### Comprobarlo aquí mismo")
st.caption(
    "El botón encola la misma cantidad de lotes dos veces y los reparte entre "
    "varias máquinas que compiten: primero con el reclamo en dos pasos, después "
    "con el atómico. Ejecuta **las mismas funciones que usan las estaciones** "
    "(`servicios/comun/reclamo.py`) contra el Redis real, sobre una cola aparte "
    "que se borra al terminar — la línea de producción de arriba no se toca.")

with st.expander("Parámetros del experimento"):
    ajuste_1, ajuste_2 = st.columns(2)
    n_lotes = ajuste_1.slider("Lotes a encolar en cada modo", 40, 300,
                              carrera.LOTES, step=20)
    n_replicas = ajuste_2.slider("Máquinas compitiendo por la cola", 2, 6,
                                 carrera.REPLICAS)
    st.caption(
        f"La ventana del reclamo en dos pasos se ensancha a "
        f"{carrera.DEMORA_S:g} s. La carrera existe igual sin esa pausa, pero "
        f"dura microsegundos y el resultado saldría intermitente: a veces "
        f"limpio por suerte. Ensancharla no cambia la naturaleza del error, "
        f"solo lo vuelve reproducible en vivo.")

if st.button("Ejecutar la comparación", type="primary"):
    try:
        with st.status("Encolando lotes…", expanded=False) as avance:
            def paso(modo, resultado):
                hecho = ("reclamo en dos pasos" if modo == "ingenuo"
                         else "reclamo atómico")
                avance.update(label=f"Listo el {hecho}: "
                                    f'{resultado["procesamientos"]} envasados.')

            st.session_state["carrera"] = carrera.comparar(
                lotes=n_lotes, replicas=n_replicas, al_terminar_modo=paso)
            avance.update(label="Comparación lista.", state="complete")
    except carrera.ErrorDeDemo as error:
        st.session_state.pop("carrera", None)
        st.error(f"**No se pudo ejecutar la demostración.** {error}")
        st.info(datos.diagnostico())

resultados = st.session_state.get("carrera")
if resultados:
    sin_solucion, con_solucion = resultados["ingenuo"], resultados["atomico"]

    def contar(texto, n):
        """Singular o plural, sin el '(s)' que delata que nadie lo reviso."""
        return f"{n} {texto}" if n == 1 else f"{n} {texto}s"

    def detalle(dato):
        """Que significa el resultado, en consecuencias y no en numeros."""
        if dato["perdidos"]:
            # No deberia pasar en ninguno de los dos modos; si pasa, se dice.
            return (f'{contar("lote", dato["perdidos"])} quedaron sin procesar. '
                    "Revisa el registro del tablero.")
        if not dato["duplicados"]:
            return ("Cada lote se envasó exactamente una vez: ni duplicados ni "
                    "lotes perdidos.")
        return (f'{contar("lote", dato["duplicados"])} se envasaron más de una '
                f'vez — hasta {dato["max_veces"]} veces el mismo. Son '
                f'{dato["de_mas"]} lotes de más: materia prima gastada en '
                "producto que nadie pidió.")

    tarjeta_1, tarjeta_2 = st.columns(2)
    for columna, dato, modo in ((tarjeta_1, sin_solucion, "Sin la solución"),
                                (tarjeta_2, con_solucion, "Con la solución")):
        with columna:
            # El color sale del resultado medido, no del modo: si alguna vez el
            # reclamo atomico produjera un duplicado, esta tarjeta se pondria
            # roja sola. Un tablero que solo sabe confirmar lo que espera no
            # sirve para comprobar nada.
            st.markdown(estilo.veredicto(
                malo=bool(dato["duplicados"] or dato["perdidos"]),
                modo=modo,
                valor=dato["procesamientos"],
                unidad=f'lotes envasados para {dato["lotes"]} pedidos',
                detalle=detalle(dato)), unsafe_allow_html=True)

    st.plotly_chart(graficos.comparacion_carrera(sin_solucion, con_solucion),
                    width="stretch", config={"displayModeBar": False})

    reparto = " · ".join(f"{nombre}: {n}"
                         for nombre, n in con_solucion["reparto"].items())
    st.caption(
        f'{con_solucion["replicas"]} máquinas · reparto con el reclamo atómico '
        f"— {reparto}. El reparto es parejo porque las máquinas de esta prueba "
        f"tienen todas el mismo ciclo; el experimento de balanceo con una "
        f"réplica lenta está en `experimentos/fase7_balanceo.sh`. "
        f'Duración: {sin_solucion["segundos"] + con_solucion["segundos"]:.1f} s.')
