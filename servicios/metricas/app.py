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
from datetime import datetime, timedelta, timezone
from typing import Optional

import redis
from fastapi import FastAPI, Query

import bd

# Las etapas de la línea, en orden. Configurables para no fijarlas en código.
ETAPAS = os.environ.get("ETAPAS", "fileteado,envasado,sellado,esterilizacion").split(",")
VENTANA_S = float(os.environ.get("VENTANA_S", "60"))

r = redis.Redis(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    decode_responses=True,
)

app = FastAPI(
    title="metrics-api",
    description="Métricas de la línea: espera, servicio y lead time por etapa",
)

bd.inicializar()


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
        try:
            en_cola = r.llen(f"cola:{etapa}")
        except redis.exceptions.RedisError:
            en_cola = None  # sin Redis no se ve la cola; el resto sigue válido
        etapas[etapa] = {
            "espera_promedio_s": _promedio(esperas),
            "servicio_promedio_s": _promedio(servicios),
            "en_cola": en_cola,
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


@app.get("/metricas")
def metricas(ventana_s: Optional[float] = Query(default=None, gt=0)) -> dict:
    """Promedios por etapa en la ventana móvil (default VENTANA_S)."""
    return calcular_metricas(ventana_s or VENTANA_S)


@app.get("/salud")
def salud() -> dict:
    """Healthcheck: si responde, el servicio está vivo."""
    return {"estado": "ok"}
