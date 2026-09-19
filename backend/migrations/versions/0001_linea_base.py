"""Línea base del esquema poscosegran.

Revisión: 0001_linea_base
Revisión anterior: None

Esta primera revisión crea el esquema a partir de los modelos declarativos. Es
una línea base deliberada: no existía base previa y así el esquema y el ORM no
pueden divergir en el punto de partida. A partir de aquí toda migración se
escribe de forma explícita, y `alembic check` debe salir limpio antes de
publicar cualquier cambio de modelos.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from poscosegran.db.base import ESQUEMA, Base
from poscosegran.db import modelos  # noqa: F401  (registra las tablas)

revision = "0001_linea_base"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conexion = op.get_bind()
    if not sa.inspect(conexion).has_schema(ESQUEMA):
        op.execute(sa.text(f'CREATE SCHEMA "{ESQUEMA}"'))
    # gen_random_uuid() proviene de pgcrypto en PostgreSQL anteriores a 13.
    # PostgreSQL 16 incluye gen_random_uuid(); no necesita CREATE EXTENSION.
    Base.metadata.create_all(bind=conexion)


def downgrade() -> None:
    conexion = op.get_bind()
    Base.metadata.drop_all(bind=conexion)
