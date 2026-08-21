"""
Paleta y componentes visuales del tablero.

REGLA DE COLOR: el color marca importancia, no identidad.

Lo normal se dibuja en gris. El color fuerte queda reservado para lo que
requiere atencion: ambar si una etapa esta acumulando trabajo, rojo si esta
atascada. Asi la vista va sola al problema.

Pintar las cuatro etapas de cuatro colores distintos —que es lo que uno hace
por instinto— logra lo contrario: las cuatro gritan igual de fuerte y la que
tiene el problema no se distingue de las que van bien.

La identidad de cada etapa sigue existiendo, pero en el papel secundario que le
corresponde: un punto de 8 px junto al nombre, del mismo color que su linea en
el grafico. Sirve para conectar ambas vistas, no para llamar la atencion.

Nada depende SOLO del color: cada estado lleva icono y texto al lado, y los
colores estan validados para distinguirse tambien con daltonismo.
"""

# --- Estado: la unica dimension que se pinta fuerte ------------------------
COLOR_ESTADO = {
    "normal": "#898781",       # gris: no pide atencion
    "advertencia": "#fab219",  # ambar
    "critico": "#d03b3b",      # rojo
}
ICONO_ESTADO = {"normal": "✓", "advertencia": "▲", "critico": "■"}
TEXTO_ESTADO = {"normal": "Al día", "advertencia": "Acumulando", "critico": "Atascada"}
VERDE_OK = "#0ca30c"  # solo para el cartel de "todo en orden"

# --- Identidad de etapa: papel secundario, solo el punto y la linea --------
COLOR_ETAPA = {
    "fileteado":      "#2a78d6",
    "envasado":       "#eb6834",
    "sellado":        "#1baf7a",
    "esterilizacion": "#eda100",
}

# --- Tinta y superficies ---------------------------------------------------
SUPERFICIE = "#fcfcfb"
PLANO = "#f9f9f7"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_MUDA = "#898781"
REJILLA = "#e1e0d9"
BORDE = "rgba(11,11,11,0.10)"

NOMBRE_ETAPA = {
    "fileteado": "Fileteado",
    "envasado": "Envasado",
    "sellado": "Sellado",
    "esterilizacion": "Esterilización",
}

# Que hace cada etapa, en una linea: quien mira la pantalla no tiene por que
# saber que es esterilizar en una conservera.
QUE_HACE = {
    "fileteado": "Se filetea el pescado",
    "envasado": "Se llenan las latas",
    "sellado": "Se cierran las latas",
    "esterilizacion": "Se esterilizan en autoclave",
}

TIPOGRAFIA = 'system-ui, -apple-system, "Segoe UI", sans-serif'


CSS = f"""
<style>
  .stApp {{ background: {PLANO}; }}

  /* --- Cartel de estado: lo primero que se mira ------------------------- */
  .cartel {{
      display: flex; gap: 14px; align-items: center; padding: 17px 20px;
      border-radius: 12px; margin: 4px 0 20px; border: 1px solid;
  }}
  .cartel-icono {{ font-size: 25px; line-height: 1; }}
  .cartel-titulo {{ font: 600 20px/1.25 {TIPOGRAFIA}; color: {TINTA}; }}
  .cartel-detalle {{ font: 400 14px/1.45 {TIPOGRAFIA}; color: {TINTA_2}; margin-top: 3px; }}

  /* --- KPIs: siempre neutros. Un numero no es una alarma ---------------- */
  .kpi-fila {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 0 0 22px; }}
  .kpi {{
      flex: 1 1 180px; background: {SUPERFICIE}; border: 1px solid {BORDE};
      border-radius: 10px; padding: 15px 18px;
  }}
  .kpi-valor {{ font: 600 32px/1.05 {TIPOGRAFIA}; color: {TINTA}; }}
  .kpi-unidad {{ font-size: 16px; font-weight: 500; color: {TINTA_2}; margin-left: 3px; }}
  .kpi-etiqueta {{ font: 500 13px/1.35 {TIPOGRAFIA}; color: {TINTA_2}; margin-top: 6px; }}

  /* --- La linea de produccion ------------------------------------------- */
  .linea {{ display: flex; align-items: stretch; gap: 2px; overflow-x: auto;
            padding: 6px 0 4px; }}

  .cola {{ display: flex; flex-direction: column; justify-content: center;
           align-items: center; min-width: 68px; padding: 0 2px; }}
  .cola-marcas {{ font-size: 14px; line-height: 1.1; letter-spacing: 1px;
                  text-align: center; max-width: 64px; word-break: break-all;
                  min-height: 17px; }}
  .cola-n {{ font: 600 15px/1.3 {TIPOGRAFIA}; margin-top: 2px; }}
  .cola-cap {{ font: 400 10px/1.25 {TIPOGRAFIA}; color: {TINTA_MUDA}; text-align: center; }}

  /* Tarjeta de etapa. En estado normal es deliberadamente sosa: borde fino
     gris y nada mas. El borde grueso de color aparece SOLO si hay problema. */
  .estacion {{
      flex: 1 1 0; min-width: 152px; background: {SUPERFICIE};
      border: 1px solid {BORDE}; border-radius: 10px; padding: 12px 13px 13px;
  }}
  .estacion-alerta {{ border-width: 1px 1px 1px 4px; }}
  .estacion-cabecera {{ display: flex; align-items: center; gap: 7px; }}
  .estacion-punto {{ width: 8px; height: 8px; border-radius: 50%; flex: 0 0 auto; }}
  .estacion-nombre {{ font: 600 15px/1.25 {TIPOGRAFIA}; color: {TINTA}; }}
  .estacion-hace {{ font: 400 11px/1.35 {TIPOGRAFIA}; color: {TINTA_MUDA}; margin-top: 2px; }}
  .estacion-ciclo {{ font: 400 11px/1.35 {TIPOGRAFIA}; color: {TINTA_2}; margin-top: 5px; }}
  .estacion-estado {{ display: inline-block; font: 600 11px/1.5 {TIPOGRAFIA};
                      margin: 8px 0 6px; padding: 1px 8px; border-radius: 20px; }}

  .replica {{ display: flex; align-items: center; gap: 6px; padding: 4px 0;
              font: 400 11px/1.35 {TIPOGRAFIA}; color: {TINTA_2};
              border-top: 1px solid {REJILLA}; }}
  .replica-luz {{ width: 8px; height: 8px; border-radius: 50%; flex: 0 0 auto; }}
  .replica-n {{ margin-left: auto; font-variant-numeric: tabular-nums;
                font-weight: 600; color: {TINTA}; }}

  .final {{ display: flex; flex-direction: column; justify-content: center;
            align-items: center; min-width: 84px; background: {SUPERFICIE};
            border: 1px solid {BORDE}; border-radius: 10px; padding: 10px 8px; }}
  .final-n {{ font: 600 24px/1.1 {TIPOGRAFIA}; color: {TINTA}; }}
  .final-cap {{ font: 400 10px/1.3 {TIPOGRAFIA}; color: {TINTA_MUDA};
                text-align: center; margin-top: 2px; }}

  .leyenda {{ display: flex; gap: 20px; flex-wrap: wrap; margin: 12px 0 4px;
              font: 400 12px/1.5 {TIPOGRAFIA}; color: {TINTA_MUDA}; }}
  .leyenda b {{ color: {TINTA_2}; font-weight: 600; }}
</style>
"""


def cartel(estado, titulo, detalle):
    """El cartel grande: como esta la linea, en una frase.

    Siempre icono + texto: el color nunca es lo unico que informa.
    """
    color = VERDE_OK if estado == "normal" else COLOR_ESTADO[estado]
    icono = "✓" if estado == "normal" else ICONO_ESTADO[estado]
    return (f'<div class="cartel" style="border-color:{color}; background:{color}12">'
            f'<div class="cartel-icono" style="color:{color}">{icono}</div>'
            f'<div><div class="cartel-titulo">{titulo}</div>'
            f'<div class="cartel-detalle">{detalle}</div></div></div>')


def kpi(valor, unidad, etiqueta):
    """Una baldosa. Numero grande arriba, que significa abajo en castellano."""
    u = f'<span class="kpi-unidad">{unidad}</span>' if unidad else ""
    return (f'<div class="kpi"><div class="kpi-valor">{valor}{u}</div>'
            f'<div class="kpi-etiqueta">{etiqueta}</div></div>')


def fila_kpis(baldosas):
    return f'<div class="kpi-fila">{"".join(baldosas)}</div>'


def cola(n, estado):
    """Los lotes que esperan turno antes de una etapa.

    Las marcas se pintan del color del ESTADO de la etapa que alimentan: una
    pila de lotes solo es preocupante si la etapa que viene no da abasto.
    """
    color = COLOR_ESTADO.get(estado, TINTA_MUDA)
    if n is None:
        # en_cola viene null cuando Redis no responde. Un "?" es honesto; un 0
        # seria mentira.
        marcas = f'<span style="color:{TINTA_MUDA}">?</span>'
        texto, n_txt = "sin dato", "?"
    elif n <= 0:
        marcas = f'<span style="color:{REJILLA}">·</span>'
        texto, n_txt = "esperando", "0"
    else:
        visibles = min(n, 8)
        resto = f'<span style="color:{TINTA_MUDA}">+{n - 8}</span>' if n > 8 else ""
        marcas = f'<span style="color:{color}">{"▮" * visibles}</span>{resto}'
        texto, n_txt = "esperando", str(n)

    tinta = TINTA if (n or 0) > 0 and estado != "normal" else TINTA_2
    return (f'<div class="cola"><div class="cola-marcas">{marcas}</div>'
            f'<div class="cola-n" style="color:{tinta}">{n_txt}</div>'
            f'<div class="cola-cap">{texto}</div></div>')


def estacion(datos):
    """Tarjeta de una etapa, con una linea por replica.

    Muestra a la vez las dos cosas que pide el enunciado: en que estado esta la
    etapa y cuanto lleva hecho cada replica (el indicador de carga).
    """
    nombre = datos["etapa"]
    estado = datos.get("estado", "normal")
    color = COLOR_ESTADO.get(estado, TINTA_MUDA)
    alerta = estado != "normal"

    filas = []
    for i, replica in enumerate(datos.get("replicas", []), start=1):
        trabajando = replica.get("ocupada")
        luz = color if (trabajando and alerta) else (VERDE_OK if trabajando else REJILLA)
        marca = (f' <span style="color:{COLOR_ESTADO["advertencia"]};font-weight:600">'
                 f'lenta</span>') if replica.get("lenta") else ""
        filas.append(
            f'<div class="replica">'
            f'<span class="replica-luz" style="background:{luz}"></span>'
            f'<span>Réplica {i}{marca} · {"trabajando" if trabajando else "libre"}</span>'
            f'<span class="replica-n">{replica.get("procesadas", 0)}</span></div>')
    if not filas:
        filas.append(f'<div class="replica"><span style="color:{TINTA_MUDA}">'
                     f'sin réplicas activas</span></div>')

    ciclo = datos.get("tiempo_ciclo")
    n_rep = len(datos.get("replicas", []))
    detalle = f"{ciclo:g} s por lote" if ciclo else "—"
    if n_rep > 1:
        detalle += f" · {n_rep} réplicas en paralelo"

    estilo_borde = (f'border-color:{color}; background:{color}0a'
                    if alerta else f"border-color:{BORDE}")
    clase = "estacion estacion-alerta" if alerta else "estacion"

    return (f'<div class="{clase}" style="{estilo_borde}">'
            f'<div class="estacion-cabecera">'
            f'<span class="estacion-punto" style="background:'
            f'{COLOR_ETAPA.get(nombre, TINTA_MUDA)}"></span>'
            f'<span class="estacion-nombre">{NOMBRE_ETAPA.get(nombre, nombre)}</span></div>'
            f'<div class="estacion-hace">{QUE_HACE.get(nombre, "")}</div>'
            f'<div class="estacion-ciclo">{detalle}</div>'
            f'<div class="estacion-estado" style="color:{color};background:{color}1a">'
            f'{ICONO_ESTADO[estado]} {TEXTO_ESTADO[estado]}</div>'
            f'{"".join(filas)}</div>')


def terminados(n):
    return (f'<div class="final"><div style="font-size:19px;color:{VERDE_OK}">✓</div>'
            f'<div class="final-n">{n}</div>'
            f'<div class="final-cap">lotes<br>terminados</div></div>')


def leyenda():
    """Explica el diagrama en una linea. Sin esto hay que adivinar que es un ▮."""
    return (
        '<div class="leyenda">'
        f'<span><b>▮</b> = un lote esperando su turno</span>'
        f'<span><span style="display:inline-block;width:8px;height:8px;'
        f'border-radius:50%;background:{VERDE_OK}"></span> réplica trabajando · '
        f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
        f'background:{REJILLA}"></span> libre</span>'
        '<span>El número de cada réplica es <b>cuántos lotes lleva hechos</b></span>'
        '<span>Una <b>réplica</b> es una máquina más trabajando en paralelo</span>'
        '</div>')
