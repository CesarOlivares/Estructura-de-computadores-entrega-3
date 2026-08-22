"""Servicio de Métricas (metrics-api).

Contrato en docs/diseno.md §1.3; definiciones exactas en §3:

    espera(orden, etapa)   = t_inicia(etapa)  - t_entra_cola(etapa)
    servicio(orden, etapa) = t_termina(etapa) - t_inicia(etapa)
    lead_time(orden)       = terminada_en     - creada_en

Nada de esto se guarda: se calcula SIEMPRE desde la tabla `eventos` (y
`ordenes` para el lead time). Los promedios usan una ventana móvil para
reflejar el presente y no el arrastre histórico. `en_cola` sale de Redis
(LLEN) porque es el único dato que vive en las colas, no en la base.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as PlazoAgotado
from datetime import datetime, timedelta, timezone
from typing import Optional

import redis
from fastapi import FastAPI, Query

import bd

# Las etapas de la línea, en orden. Configurables para no fijarlas en código.
ETAPAS = os.environ.get("ETAPAS", "fileteado,envasado,sellado,esterilizacion").split(",")
VENTANA_S = float(os.environ.get("VENTANA_S", "60"))

# --- Cuello de botella (Fase 10) ---------------------------------------------
# Criterio (docs/diseno.md §4): la etapa con MAYOR espera promedio en la
# ventana, si supera su umbral de advertencia. Espera, no servicio: un ciclo
# largo es una tarea lenta; un atasco es trabajo llegando más rápido de lo
# que se drena, y eso se ve en la espera.
#
# Los umbrales son RELATIVOS al tiempo de ciclo de cada etapa: 10 s de espera
# son gravísimos para sellado (ciclo 3 s) y poca cosa para envasado (12 s).
# Un umbral absoluto igual para todas señalaría siempre a la etapa lenta,
# que es justamente el error que este criterio evita.
TIEMPOS_CICLO = {
    nombre: float(ciclo)
    for nombre, ciclo in (
        par.split(":")
        for par in os.environ.get(
            "TIEMPOS_CICLO", "fileteado:4,envasado:12,sellado:3,esterilizacion:7"
        ).split(",")
    )
}
FACTOR_ADVERTENCIA = float(os.environ.get("FACTOR_ADVERTENCIA", "1.5"))
FACTOR_CRITICO = float(os.environ.get("FACTOR_CRITICO", "3"))

r = redis.Redis(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    decode_responses=True,
    # Fase 12: con Redis caído, cada LLEN esperaría el timeout de TCP del
    # sistema operativo (minutos) y /metricas se colgaría. Con esto, el LLEN
    # falla en ~2 s, en_cola sale null y el resto de la respuesta sigue válido.
    socket_timeout=2,
    socket_connect_timeout=2,
)

app = FastAPI(
    title="metrics-api",
    description="Métricas de la línea: espera, servicio y lead time por etapa",
)

bd.inicializar()

# --- Plazo duro para leer las colas (Fase 12) --------------------------------
# socket_connect_timeout no cubre la resolución DNS: con Redis detenido su
# nombre desaparece del DNS de Docker y getaddrinfo tarda ~45 s en rendirse.
# Los LLEN se piden TODOS juntos (pipeline) en un hilo aparte con plazo: si no
# llegan a tiempo, en_cola sale null para todas las etapas y el resto de la
# respuesta sigue siendo válido — /metricas nunca se cuelga por Redis.
PLAZO_REDIS_S = float(os.environ.get("PLAZO_REDIS_S", "2"))
_hilos_redis = ThreadPoolExecutor(max_workers=2)


def largos_de_colas() -> dict:
    """{etapa: largo de su cola}, o todo None si Redis no responde a tiempo."""

    def _todos() -> dict:
        canal = r.pipeline()
        for etapa in ETAPAS:
            canal.llen(f"cola:{etapa}")
        return dict(zip(ETAPAS, canal.execute()))

    futuro = _hilos_redis.submit(_todos)
    try:
        return futuro.result(timeout=PLAZO_REDIS_S)
    except (PlazoAgotado, redis.exceptions.RedisError):
        futuro.cancel()  # si quedó en cola, que no corra después de viejo
        return {etapa: None for etapa in ETAPAS}


def _ts(texto: str) -> datetime:
    return datetime.fromisoformat(texto)


def _cargar_tiempos() -> dict:
    """Agrupa los eventos por (orden, etapa): {(orden_id, etapa): {tipo: ts}}."""
    with bd.transaccion() as con:
        eventos = con.execute(
            "SELECT orden_id, etapa, tipo, timestamp FROM eventos"
        ).fetchall()
    tiempos: dict = {}
    for ev in eventos:
        clave = (ev["orden_id"], ev["etapa"])
        tiempos.setdefault(clave, {})[ev["tipo"]] = _ts(ev["timestamp"])
    return tiempos


def _promedio(valores: list) -> Optional[float]:
    return round(sum(valores) / len(valores), 2) if valores else None


def calcular_metricas(ventana_s: float) -> dict:
    """Espera/servicio promedio por etapa en la ventana, en_cola y lead time."""
    corte = datetime.now(timezone.utc) - timedelta(seconds=ventana_s)
    tiempos = _cargar_tiempos()
    largos = largos_de_colas()  # una sola consulta a Redis, con plazo

    etapas = {}
    for etapa in ETAPAS:
        esperas, servicios, procesadas = [], [], 0
        for (_, et), t in tiempos.items():
            if et != etapa:
                continue
            if "termina" in t:
                procesadas += 1
            # La espera se cuenta cuando la orden ARRANCA dentro de la ventana;
            # el servicio, cuando TERMINA dentro de la ventana.
            if "inicia" in t and "entra_cola" in t and t["inicia"] >= corte:
                esperas.append((t["inicia"] - t["entra_cola"]).total_seconds())
            if "termina" in t and "inicia" in t and t["termina"] >= corte:
                servicios.append((t["termina"] - t["inicia"]).total_seconds())
        etapas[etapa] = {
            "espera_promedio_s": _promedio(esperas),
            "servicio_promedio_s": _promedio(servicios),
            "en_cola": largos[etapa],  # None si Redis no respondió a tiempo
            "procesadas": procesadas,
        }

    with bd.transaccion() as con:
        terminadas = con.execute(
            "SELECT creada_en, terminada_en FROM ordenes WHERE estado = 'terminada'"
        ).fetchall()
    leads = [
        (_ts(o["terminada_en"]) - _ts(o["creada_en"])).total_seconds()
        for o in terminadas
        if _ts(o["terminada_en"]) >= corte
    ]
    return {
        "ventana_s": ventana_s,
        "etapas": etapas,
        "lead_time_promedio_s": _promedio(leads),
    }


def clasificar(espera: Optional[float], ciclo: float) -> str:
    """normal / advertencia / critico según la espera contra el ciclo de la etapa.

    Sin espera medible en la ventana (nadie arrancó una orden ahí) no hay
    evidencia de atasco: normal. Así la etapa VUELVE SOLA a normal cuando la
    carga baja y sus esperas viejas salen de la ventana.
    """
    if espera is None:
        return "normal"
    if espera >= ciclo * FACTOR_CRITICO:
        return "critico"
    if espera >= ciclo * FACTOR_ADVERTENCIA:
        return "advertencia"
    return "normal"


def detectar_cuello(ventana_s: float) -> dict:
    """Contrato en docs/diseno.md §1.3: {cuello, estados, razon}."""
    datos = calcular_metricas(ventana_s)

    estados = {}
    cuello, espera_cuello = None, None
    for etapa in ETAPAS:
        espera = datos["etapas"][etapa]["espera_promedio_s"]
        estados[etapa] = clasificar(espera, TIEMPOS_CICLO[etapa])
        # Candidata a cuello: sobre advertencia y con la mayor espera de todas.
        if estados[etapa] != "normal" and (espera_cuello is None or espera > espera_cuello):
            cuello, espera_cuello = etapa, espera

    if cuello is None:
        razon = f"ninguna etapa supera su umbral de advertencia en la ventana de {ventana_s:g} s"
    else:
        umbral = "crítico" if estados[cuello] == "critico" else "de advertencia"
        razon = (
            f"espera promedio {espera_cuello:g} s en la ventana de {ventana_s:g} s, "
            f"sobre el umbral {umbral} ({TIEMPOS_CICLO[cuello]:g} s de ciclo × "
            f"{FACTOR_CRITICO if estados[cuello] == 'critico' else FACTOR_ADVERTENCIA:g})"
        )
    return {"cuello": cuello, "estados": estados, "razon": razon, "ventana_s": ventana_s}


@app.get("/metricas")
def metricas(ventana_s: Optional[float] = Query(default=None, gt=0)) -> dict:
    """Promedios por etapa en la ventana móvil (default VENTANA_S)."""
    return calcular_metricas(ventana_s or VENTANA_S)


@app.get("/metricas/cuello")
def cuello(ventana_s: Optional[float] = Query(default=None, gt=0)) -> dict:
    """Qué etapa es el cuello de botella y por qué (null si no hay)."""
    return detectar_cuello(ventana_s or VENTANA_S)


@app.get("/salud")
def salud() -> dict:
    """Healthcheck: si responde, el servicio está vivo."""
    return {"estado": "ok"}
