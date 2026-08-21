"""Servicio de Órdenes (orders-api).

Fase 3: versión mínima según el contrato de docs/diseno.md §1.1.
Las órdenes se guardan EN MEMORIA (un diccionario): se pierden al reiniciar el
contenedor. Es intencional — la persistencia en SQLite llega en la Fase 8 y la
cola de Redis en la Fase 4; esta fase solo valida el contrato HTTP.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

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
    """Crea una orden. Desde la Fase 4, además la encola en cola:fileteado."""
    global siguiente_id
    orden = {
        "id": siguiente_id,
        "producto": entrada.producto,
        "cantidad": entrada.cantidad,
        "estado": "en_proceso",
        "creada_en": datetime.now(timezone.utc).isoformat(),
        "terminada_en": None,
    }
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
