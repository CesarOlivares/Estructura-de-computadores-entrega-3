"""Servicio de Órdenes (orders-api).

Contrato en docs/diseno.md §1.1. Al crear una orden, su id se encola en
cola:fileteado (Redis) para que la línea la procese. Las órdenes se guardan
EN MEMORIA todavía: la persistencia en SQLite llega en la Fase 8.
"""

import os
from datetime import datetime, timezone
from typing import Optional

import redis
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

# Conexión a Redis: host y puerto SIEMPRE por variables de entorno, nunca
# escritos a mano — en Docker el host es el nombre del servicio ("redis").
r = redis.Redis(
    host=os.environ.get("REDIS_HOST", "redis"),
    port=int(os.environ.get("REDIS_PORT", "6379")),
    decode_responses=True,
)
COLA_PRIMERA_ETAPA = os.environ.get("COLA_PRIMERA_ETAPA", "cola:fileteado")

app = FastAPI(
    title="orders-api",
    description="Crea y consulta órdenes de producción de la línea conservera",
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


# --- Almacenamiento en memoria (temporal, ver docstring del módulo) --------

ordenes: dict[int, dict] = {}
siguiente_id = 1

# Catálogo de estados válidos (docs/diseno.md §2): la etapa actual no es un
# estado guardado, se deriva de los eventos (desde la Fase 8).
ESTADOS = ("en_proceso", "terminada")


# --- Endpoints -------------------------------------------------------------


@app.post("/ordenes", status_code=201)
def crear_orden(entrada: OrdenEntrada) -> dict:
    """Crea una orden y encola su id en la primera etapa de la línea.

    Si Redis no responde, la orden NO se crea y se responde 503: una orden
    guardada pero nunca encolada quedaría en_proceso para siempre.
    """
    global siguiente_id
    orden = {
        "id": siguiente_id,
        "producto": entrada.producto,
        "cantidad": entrada.cantidad,
        "estado": "en_proceso",
        "creada_en": datetime.now(timezone.utc).isoformat(),
        "terminada_en": None,
    }
    try:
        r.lpush(COLA_PRIMERA_ETAPA, str(orden["id"]))
    except redis.exceptions.RedisError:
        raise HTTPException(
            status_code=503,
            detail="sin conexión con el servicio de coordinación (Redis); intente de nuevo",
        )
    ordenes[siguiente_id] = orden
    siguiente_id += 1
    return orden


@app.get("/ordenes/{orden_id}")
def obtener_orden(orden_id: int) -> dict:
    """Devuelve una orden por id, o 404 si no existe."""
    if orden_id not in ordenes:
        raise HTTPException(status_code=404, detail=f"la orden {orden_id} no existe")
    return ordenes[orden_id]


@app.get("/ordenes")
def listar_ordenes(
    estado: Optional[str] = Query(default=None, pattern="^(en_proceso|terminada)$"),
) -> list[dict]:
    """Lista las órdenes; con ?estado= filtra por estado (422 si el valor no existe)."""
    todas = list(ordenes.values())
    if estado is None:
        return todas
    return [o for o in todas if o["estado"] == estado]


@app.get("/salud")
def salud() -> dict:
    """Healthcheck: si responde, el servicio está vivo."""
    return {"estado": "ok"}
