"""Servicio de Órdenes (orders-api).

Contrato en docs/diseno.md §1.1. Al crear una orden: se guarda en SQLite,
se registra su evento `entra_cola` de la primera etapa, y su id se encola en
cola:fileteado (Redis) — todo dentro de una transacción, para que una falla
de Redis no deje órdenes fantasma en la base.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as PlazoAgotado
from datetime import datetime, timezone
from typing import Optional

import redis
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

import bd

# Conexión a Redis: host y puerto SIEMPRE por variables de entorno, nunca
# escritos a mano — en Docker el host es el nombre del servicio ("redis").
r = redis.Redis(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    decode_responses=True,
    # Fase 12: sin estos timeouts, una petición con Redis caído se queda
    # esperando el timeout de TCP del sistema operativo (minutos) y el 503
    # nunca llega. Con ellos, la falla se detecta en ~2 s y se responde 503.
    socket_timeout=2,
    socket_connect_timeout=2,
)
COLA_PRIMERA_ETAPA = os.environ.get("COLA_PRIMERA_ETAPA", "cola:fileteado")
PRIMERA_ETAPA = COLA_PRIMERA_ETAPA.split(":", 1)[1]  # "cola:fileteado" -> "fileteado"

app = FastAPI(
    title="orders-api",
    description="Crea y consulta órdenes de producción de la línea conservera",
)

bd.inicializar()

# --- Plazo duro para detectar a Redis caído (Fase 12) -----------------------
# socket_connect_timeout NO cubre la resolución DNS: con el contenedor de
# Redis detenido, su nombre desaparece del DNS interno de Docker y getaddrinfo
# tarda ~45 s en rendirse — el 503 llegaría tardísimo (medido en la Fase 12).
# El PING se corre en un hilo aparte y se espera a lo más PLAZO_REDIS_S; si no
# llega, Redis se da por caído YA y el hilo muere solo cuando el sistema
# operativo suelte la consulta DNS.
PLAZO_REDIS_S = float(os.environ.get("PLAZO_REDIS_S", "2"))
_hilos_ping = ThreadPoolExecutor(max_workers=2)


def verificar_redis() -> None:
    """Corta con 503 en ≤PLAZO_REDIS_S segundos si Redis no responde."""
    futuro = _hilos_ping.submit(r.ping)
    try:
        futuro.result(timeout=PLAZO_REDIS_S)
    except (PlazoAgotado, redis.exceptions.RedisError):
        futuro.cancel()  # si quedó en cola, que no corra después de viejo
        raise HTTPException(
            status_code=503,
            detail="sin conexión con el servicio de coordinación (Redis); intente de nuevo",
        )


# --- Modelos (el contrato de entrada/salida) -------------------------------


class OrdenEntrada(BaseModel):
    """Cuerpo de POST /ordenes. Pydantic valida y responde 422 si no cumple."""

    producto: str = Field(min_length=1, description="Formato del producto, ej: jurel-425g")
    cantidad: int = Field(gt=0, description="Latas del lote, entero mayor que 0")

    @field_validator("producto")
    @classmethod
    def producto_no_puede_ser_solo_espacios(cls, valor: str) -> str:
        # min_length=1 no atrapa "   "; este validador sí.
        if not valor.strip():
            raise ValueError("producto no puede ser vacío ni solo espacios")
        return valor.strip()


# --- Endpoints -------------------------------------------------------------


@app.post("/ordenes", status_code=201)
def crear_orden(entrada: OrdenEntrada) -> dict:
    """Crea una orden, registra su entrada a la cola y la encola en Redis.

    El LPUSH va DENTRO de la transacción de SQLite: si Redis no responde, el
    INSERT se deshace, no se crea nada y se responde 503 — una orden guardada
    pero nunca encolada quedaría en_proceso para siempre.
    """
    # Primero el portero: si Redis está caído, 503 en ~2 s en vez de colgarse
    # esperando al DNS. El try/except de abajo sigue cubriendo la carrera rara
    # de que Redis se caiga justo entre este chequeo y el LPUSH.
    verificar_redis()
    ahora = datetime.now(timezone.utc).isoformat()
    try:
        with bd.transaccion() as con:
            cursor = con.execute(
                "INSERT INTO ordenes (producto, cantidad, estado, creada_en) VALUES (?, ?, ?, ?)",
                (entrada.producto, entrada.cantidad, "en_proceso", ahora),
            )
            orden_id = cursor.lastrowid
            con.execute(
                "INSERT INTO eventos (orden_id, etapa, replica_id, tipo, timestamp)"
                " VALUES (?, ?, ?, ?, ?)",
                (orden_id, PRIMERA_ETAPA, "orders-api", "entra_cola", ahora),
            )
            r.lpush(COLA_PRIMERA_ETAPA, str(orden_id))
    except redis.exceptions.RedisError:
        raise HTTPException(
            status_code=503,
            detail="sin conexión con el servicio de coordinación (Redis); intente de nuevo",
        )
    return {
        "id": orden_id,
        "producto": entrada.producto,
        "cantidad": entrada.cantidad,
        "estado": "en_proceso",
        "creada_en": ahora,
        "terminada_en": None,
    }


@app.get("/ordenes/{orden_id}")
def obtener_orden(orden_id: int) -> dict:
    """Devuelve una orden por id, o 404 si no existe."""
    with bd.transaccion() as con:
        fila = con.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,)).fetchone()
    if fila is None:
        raise HTTPException(status_code=404, detail=f"la orden {orden_id} no existe")
    return dict(fila)


@app.get("/ordenes")
def listar_ordenes(
    estado: Optional[str] = Query(default=None, pattern="^(en_proceso|terminada)$"),
) -> list[dict]:
    """Lista las órdenes; con ?estado= filtra por estado (422 si el valor no existe)."""
    with bd.transaccion() as con:
        if estado is None:
            filas = con.execute("SELECT * FROM ordenes ORDER BY id").fetchall()
        else:
            filas = con.execute(
                "SELECT * FROM ordenes WHERE estado = ? ORDER BY id", (estado,)
            ).fetchall()
    return [dict(fila) for fila in filas]


@app.get("/salud")
def salud() -> dict:
    """Healthcheck: si responde, el servicio está vivo."""
    return {"estado": "ok"}
