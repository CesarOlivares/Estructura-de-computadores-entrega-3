"""
El grafico del tablero.

Hay UNO solo, a proposito. Todo lo demas que se podria graficar —cuanto lleva
hecho cada replica, cuantos lotes esperan en cada cola, en que estado esta cada
etapa— ya se ve en el diagrama de la linea. Repetirlo en barras no agrega
informacion: agrega pantalla que hay que leer.

Lo unico que el diagrama no puede mostrar es la evolucion en el tiempo, y es
justo lo que distingue un atasco real de una rafaga pasajera. Ademas la rubrica
exige historico ademas de tiempo real.

Se grafica el TIEMPO DE ESPERA, no el de servicio: que una etapa demore mucho no
la convierte en cuello de botella; que los lotes se le acumulen esperando, si.

Jerarquia visual, igual que en el resto del tablero: la etapa atascada va en su
color de estado y con trazo grueso; las que van bien quedan en gris fino, como
contexto. El color dice "mira aca", no "yo soy fileteado".
"""

import plotly.graph_objects as go

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
