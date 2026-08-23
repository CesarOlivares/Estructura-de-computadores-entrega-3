"""
Los graficos del tablero.

Son DOS, y responden preguntas distintas:

    evolucion()            monitoreo: ¿la espera de alguna etapa viene subiendo?
    comparacion_carrera()  demostracion: ¿que cambia el reclamo atomico?

El primero pertenece a la operacion en vivo; el segundo a la seccion de
demostracion, que se ejecuta a pedido. Ninguno duplica lo que ya muestra el
diagrama de la linea —cuanto lleva hecho cada replica, cuantos lotes esperan,
en que estado esta cada etapa—: repetir eso en barras no agrega informacion,
agrega pantalla que hay que leer.

En evolucion() se grafica el TIEMPO DE ESPERA, no el de servicio: que una etapa
demore mucho no la convierte en cuello de botella; que los lotes se le acumulen
esperando, si.

Jerarquia visual, igual que en el resto del tablero: lo que requiere atencion
va en su color de estado y con trazo grueso; lo que va bien queda en gris fino,
como contexto. El color dice "mira aca", no "yo soy fileteado".
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from estilo import (COLOR_ESTADO, NOMBRE_ETAPA, REJILLA, SUPERFICIE, TINTA,
                    TINTA_2, TINTA_MUDA, TIPOGRAFIA)

# Gris de contexto para las etapas sin problema. Mas claro que la tinta muda
# para que quede claramente por detras de la etapa destacada.
GRIS_CONTEXTO = "#c3c2b7"

_EJE = dict(showgrid=True, gridcolor=REJILLA, gridwidth=1, zeroline=False,
            linecolor=REJILLA, tickfont=dict(color=TINTA_MUDA, size=11))


def evolucion(historico, etapas, cuello):
    """Una linea por etapa: cuanto esperan los lotes antes de entrar a cada una.

    `historico` es una lista de {t, esperas: {etapa: segundos|None}}.
    `cuello` es el nombre de la etapa atascada, o None.

    Devuelve None si aun no hay mediciones, para que quien llama muestre un
    mensaje en vez de un grafico vacio.
    """
    if not historico:
        return None

    figura = go.Figure()
    finales = []

    for datos in etapas:
        nombre = datos["etapa"]
        xs, ys = [], []
        for punto in historico:
            valor = punto["esperas"].get(nombre)
            if valor is not None:
                xs.append(punto["t"])
                ys.append(valor)
        if not xs:
            continue

        destacada = nombre == cuello
        color = COLOR_ESTADO.get(datos.get("estado"), GRIS_CONTEXTO) if destacada \
            else GRIS_CONTEXTO

        figura.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", name=NOMBRE_ETAPA.get(nombre, nombre),
            line=dict(color=color, width=3 if destacada else 1.5,
                      shape="spline", smoothing=0.4),
            # La etapa destacada se dibuja encima de las demas.
            hovertemplate="<b>%{fullData.name}</b><br>esperan %{y:.0f} s<extra></extra>",
        ))
        finales.append((ys[-1], xs[-1], NOMBRE_ETAPA.get(nombre, nombre),
                        color, destacada))

    if not finales:
        return None

    # Etiquetas directas al final de cada linea, con deteccion de colision.
    #
    # Cuando la linea va bien, varias etapas tienen espera 0 y sus trazos
    # terminan uno encima de otro: escribir las cuatro etiquetas ahi produce un
    # borron ilegible. Si dos chocan se omite la de abajo, pero la de la etapa
    # destacada se escribe SIEMPRE: es la que hay que poder leer.
    alturas = [f[0] for f in finales]
    separacion = (max(alturas) - min(alturas) or 1) * 0.12
    puestas = []
    for y, x, nombre, color, destacada in sorted(finales,
                                                 key=lambda f: (not f[4], -f[0])):
        if not destacada and any(abs(y - p) < separacion for p in puestas):
            continue
        puestas.append(y)
        figura.add_annotation(
            x=x, y=y, text="  " + nombre, showarrow=False,
            xanchor="left", yanchor="middle",
            font=dict(size=11, color=color if destacada else TINTA_MUDA,
                      weight="bold" if destacada else "normal"))

    figura.update_layout(
        paper_bgcolor=SUPERFICIE, plot_bgcolor=SUPERFICIE,
        font=dict(family=TIPOGRAFIA, size=12, color=TINTA_2),
        height=280, hovermode="x unified", showlegend=False,
        margin=dict(l=8, r=120, t=14, b=8),
        hoverlabel=dict(bgcolor=SUPERFICIE, bordercolor=REJILLA,
                        font=dict(family=TIPOGRAFIA, size=12, color=TINTA)),
        xaxis=dict(**_EJE, title=dict(text="segundos transcurridos",
                                      font=dict(size=11, color=TINTA_MUDA))),
        yaxis=dict(**_EJE, rangemode="tozero",
                   title=dict(text="segundos de espera",
                              font=dict(size=11, color=TINTA_MUDA))),
    )
    return figura


def comparacion_carrera(sin_solucion, con_solucion):
    """Los dos modos de reclamo, lado a lado y en la misma escala.

    Cada panel responde la misma pregunta —¿cuántos lotes se procesaron una
    vez, cuántos dos, cuántos tres?— sobre la misma cantidad de lotes pedidos.
    Un sistema correcto tiene UNA barra, en "1 vez", de la altura del pedido.
    Cualquier barra a la derecha de esa es producto fabricado dos veces.

    Compartir el eje Y no es un detalle: es lo que convierte dos gráficos en
    una comparación. Con escalas propias, ambos panales se verían igual de
    llenos y la diferencia —que es de cantidad, no de forma— desaparecería.

    Se respeta la regla de color del tablero: el gris es lo normal y el rojo
    marca el defecto. El panel de la derecha no se pinta de verde; su mensaje
    es justamente que no tiene nada rojo.
    """
    veces_max = max(sin_solucion["max_veces"], con_solucion["max_veces"], 1)
    categorias = list(range(1, veces_max + 1))
    etiquetas = ["1 vez"] + [f"{k} veces" for k in categorias[1:]]

    figura = make_subplots(
        rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.06,
        subplot_titles=("SIN la solución · reclamo en dos pasos",
                        "CON la solución · reclamo atómico"))

    for columna, datos in ((1, sin_solucion), (2, con_solucion)):
        alturas = [datos["distribucion"].get(k, 0) for k in categorias]
        # El rojo se reserva para las columnas que representan un defecto: un
        # lote procesado más de una vez. La columna "1 vez" es lo esperado y
        # por eso va en gris, en los dos paneles.
        colores = [GRIS_CONTEXTO if k == 1 else COLOR_ESTADO["critico"]
                   for k in categorias]
        figura.add_trace(go.Bar(
            x=etiquetas, y=alturas, marker_color=colores,
            text=[str(a) if a else "" for a in alturas],
            textposition="outside", textfont=dict(size=12, color=TINTA_2),
            cliponaxis=False, showlegend=False,
            hovertemplate="%{y} lotes se procesaron %{x}<extra></extra>",
        ), row=1, col=columna)

    # Los títulos de panel los crea make_subplots como anotaciones con su
    # tipografía por defecto; hay que rehacerlas para que no desentonen.
    for anotacion in figura.layout.annotations:
        anotacion.font = dict(family=TIPOGRAFIA, size=12, color=TINTA_2)

    figura.add_annotation(
        text="veces que la línea procesó el mismo lote",
        xref="paper", yref="paper", x=0.5, y=-0.19, showarrow=False,
        font=dict(family=TIPOGRAFIA, size=11, color=TINTA_MUDA))

    figura.update_layout(
        paper_bgcolor=SUPERFICIE, plot_bgcolor=SUPERFICIE,
        font=dict(family=TIPOGRAFIA, size=12, color=TINTA_2),
        height=330, bargap=0.45, showlegend=False,
        margin=dict(l=8, r=8, t=42, b=52),
        hoverlabel=dict(bgcolor=SUPERFICIE, bordercolor=REJILLA,
                        font=dict(family=TIPOGRAFIA, size=12, color=TINTA)),
    )
    figura.update_xaxes(**_EJE)
    # rangemode + un 12% de aire arriba para que las etiquetas de las barras
    # más altas no queden cortadas contra el borde del gráfico.
    tope = max([sin_solucion["distribucion"].get(k, 0) for k in categorias]
               + [con_solucion["distribucion"].get(k, 0) for k in categorias] + [1])
    figura.update_yaxes(**_EJE, range=[0, tope * 1.12])
    figura.update_yaxes(title=dict(text="cantidad de lotes",
                                   font=dict(size=11, color=TINTA_MUDA)),
                        row=1, col=1)
    return figura
