"""Estado SUPERADA para la versión de conocimiento reemplazada.

Revisión: 0004_version_superada
Revisión anterior: 0003_sistema_experto

Hasta ahora, al activar una versión la anterior quedaba en `estado='ACTIVADA'`
con `activa=false`. Esa combinación se lee como si la versión siguiera vigente y
obliga a mirar dos columnas para saber cuál manda. Con `SUPERADA` el estado dice
por sí solo en qué punto del ciclo está cada versión.

Es idempotente a propósito. La migración 0003 construye su CHECK importando
`ESTADO_VERSION`, así que una base creada después de añadir el valor ya lo admite
y aquí solo se reescribe la restricción con el mismo contenido; una base migrada
antes es la que realmente necesita esta revisión.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from poscosegran.db.enums import ESTADO_VERSION

revision = "0004_version_superada"
down_revision = "0003_sistema_experto"
branch_labels = None
depends_on = None

ESQUEMA = "poscosegran"
TABLA = "version_conocimiento"
RESTRICCION = f"ck_{TABLA}_estado_version"

ANTERIORES = ("PROPUESTA", "ACTIVADA", "DESCARTADA")


def _lista(valores: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def _restriccion(valores: tuple[str, ...]) -> None:
    op.execute(sa.text(f"ALTER TABLE {ESQUEMA}.{TABLA} DROP CONSTRAINT IF EXISTS {RESTRICCION}"))
    op.execute(
        sa.text(
            f"ALTER TABLE {ESQUEMA}.{TABLA} ADD CONSTRAINT {RESTRICCION} "
            f"CHECK (estado IN ({_lista(valores)}))"
        )
    )


def upgrade() -> None:
    _restriccion(ESTADO_VERSION)
    op.execute(
        sa.text(
            f"UPDATE {ESQUEMA}.{TABLA} SET estado = 'SUPERADA' "
            f"WHERE estado = 'ACTIVADA' AND activa = false"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"UPDATE {ESQUEMA}.{TABLA} SET estado = 'ACTIVADA' WHERE estado = 'SUPERADA'"
        )
    )
    _restriccion(ANTERIORES)
