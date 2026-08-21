"""Acceso a SQLite (esquema en docs/diseno.md §2).

La base vive en un volumen de Docker compartido (DB_RUTA) y la escriben varios
contenedores a la vez (orders-api y las estaciones). Reglas para que eso
funcione sin pisarse:

- WAL (write-ahead log): los lectores no bloquean a los escritores.
- busy_timeout: si otro proceso tiene el lock de escritura, se espera en vez
  de fallar al instante.
- Una conexión POR OPERACIÓN, nunca una global compartida entre hilos.
"""

import os
import sqlite3
from contextlib import contextmanager

DB_RUTA = os.environ.get("DB_RUTA", "/datos/planta.db")


def conexion() -> sqlite3.Connection:
    con = sqlite3.connect(DB_RUTA, timeout=10)
    con.row_factory = sqlite3.Row  # las filas se leen como diccionarios
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=10000")
    return con


@contextmanager
def transaccion():
    """Uso: `with bd.transaccion() as con:` — commit al salir bien, rollback
    si algo explota adentro, y la conexión se cierra siempre."""
    con = conexion()
    try:
        with con:
            yield con
    finally:
        con.close()


def inicializar() -> None:
    """Crea las tablas si no existen. La llaman todos los servicios al partir:
    el primero que llega las crea y el resto no hace nada."""
    with transaccion() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS ordenes (
                   id           INTEGER PRIMARY KEY AUTOINCREMENT,
                   producto     TEXT    NOT NULL,
                   cantidad     INTEGER NOT NULL CHECK (cantidad > 0),
                   estado       TEXT    NOT NULL DEFAULT 'en_proceso',
                   creada_en    TEXT    NOT NULL,
                   terminada_en TEXT
               )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS eventos (
                   id         INTEGER PRIMARY KEY AUTOINCREMENT,
                   orden_id   INTEGER NOT NULL REFERENCES ordenes(id),
                   etapa      TEXT    NOT NULL,
                   replica_id TEXT    NOT NULL,
                   tipo       TEXT    NOT NULL,
                   timestamp  TEXT    NOT NULL
               )"""
        )
