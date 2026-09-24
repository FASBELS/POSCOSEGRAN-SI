"""Entorno de Alembic.

Usa POSCOSEGRAN_BD_URL_MIGRACIONES, que debe apuntar a una credencial con
privilegios de DDL distinta de la credencial de aplicación.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool, text, inspect
from dotenv import load_dotenv
load_dotenv()

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from poscosegran.db.base import ESQUEMA, Base  
from poscosegran.db import modelos  

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

url = os.environ.get("POSCOSEGRAN_BD_URL_MIGRACIONES") or os.environ.get("POSCOSEGRAN_BD_URL_APP")
if not url:
    raise RuntimeError(
        "Defina POSCOSEGRAN_BD_URL_MIGRACIONES con la credencial de migraciones."
    )
if url.startswith("postgres://"):
    url = "postgresql+psycopg://" + url.removeprefix("postgres://")
elif url.startswith("postgresql://"):
    url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))

metadatos = Base.metadata


def _incluir(objeto, nombre, tipo, reflejado, comparado) -> bool:  
    """Alembic solo gobierna el esquema de la aplicación."""
    if tipo == "table":
        return objeto.schema == ESQUEMA
    return True


def ejecutar_sin_conexion() -> None:
    context.configure(
        url=url,
        target_metadata=metadatos,
        literal_binds=True,
        include_schemas=True,
        version_table_schema=ESQUEMA,
        include_object=_incluir,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def ejecutar_con_conexion() -> None:
    motor = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with motor.connect() as conexion:
        if not inspect(conexion).has_schema(ESQUEMA):
            conexion.execute(text(f'CREATE SCHEMA "{ESQUEMA}"'))
        conexion.commit()
        context.configure(
            connection=conexion,
            target_metadata=metadatos,
            include_schemas=True,
            version_table_schema=ESQUEMA,
            include_object=_incluir,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    ejecutar_sin_conexion()
else:
    ejecutar_con_conexion()
