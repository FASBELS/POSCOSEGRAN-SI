"""Base de conocimiento como datos y módulo de adquisición.

Revisión: 0003_sistema_experto
Revisión anterior: 0002_inmutabilidad

* version_conocimiento guarda el contenido completo de la base y su ciclo de vida
  (PROPUESTA, ACTIVADA, DESCARTADA), con motivo, origen y responsable.
* Nuevo rol INGENIERO_CONOCIMIENTO, que propone y activa versiones.

Es idempotente a propósito: 0001 crea el esquema desde los modelos actuales, así
que en una base nueva estas columnas ya existen y la revisión no hace nada; en una
base anterior las añade.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

from poscosegran.db.enums import ESTADO_VERSION, ROL

revision = "0003_sistema_experto"
down_revision = "0002_inmutabilidad"
branch_labels = None
depends_on = None

ESQUEMA = "poscosegran"
TABLA = "version_conocimiento"


def _columnas(tabla: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(tabla, schema=ESQUEMA)}


def _lista(valores: tuple[str, ...]) -> str:
    return ", ".join(f"'{v}'" for v in valores)


def upgrade() -> None:
    presentes = _columnas(TABLA)
    nuevas = [
        sa.Column("contenido", JSONB, nullable=True, comment="Base operativa y documental completas."),
        sa.Column("estado", sa.String(max(len(v) for v in ESTADO_VERSION)), nullable=False, server_default="ACTIVADA"),
        sa.Column("motivo", sa.Text, nullable=True),
        sa.Column("id_version_origen", UUID(as_uuid=True), nullable=True),
        sa.Column("activada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activada_por", UUID(as_uuid=True), nullable=True),
    ]
    for columna in nuevas:
        if columna.name not in presentes:
            op.add_column(TABLA, columna, schema=ESQUEMA)

    op.execute(sa.text(f"ALTER TABLE {ESQUEMA}.{TABLA} DROP CONSTRAINT IF EXISTS ck_{TABLA}_estado_version"))
    op.execute(sa.text(
        f"ALTER TABLE {ESQUEMA}.{TABLA} ADD CONSTRAINT ck_{TABLA}_estado_version "
        f"CHECK (estado IN ({_lista(ESTADO_VERSION)}))"
    ))
    for columna, destino in (("id_version_origen", TABLA), ("activada_por", "usuario")):
        nombre = f"fk_{TABLA}_{columna}"
        op.execute(sa.text(f"ALTER TABLE {ESQUEMA}.{TABLA} DROP CONSTRAINT IF EXISTS {nombre}"))
        op.execute(sa.text(
            f"ALTER TABLE {ESQUEMA}.{TABLA} ADD CONSTRAINT {nombre} FOREIGN KEY ({columna}) "
            f"REFERENCES {ESQUEMA}.{destino} (id) ON DELETE RESTRICT"
        ))

    # Rol nuevo: el CHECK y el ancho de la columna dependen de la lista de roles.
    op.execute(sa.text(f"ALTER TABLE {ESQUEMA}.usuario_rol ALTER COLUMN rol TYPE VARCHAR({max(len(r) for r in ROL)})"))
    op.execute(sa.text(f"ALTER TABLE {ESQUEMA}.usuario_rol DROP CONSTRAINT IF EXISTS ck_usuario_rol_rol"))
    op.execute(sa.text(
        f"ALTER TABLE {ESQUEMA}.usuario_rol ADD CONSTRAINT ck_usuario_rol_rol CHECK (rol IN ({_lista(ROL)}))"
    ))


def downgrade() -> None:
    anteriores = tuple(r for r in ROL if r != "INGENIERO_CONOCIMIENTO")
    op.execute(sa.text(f"DELETE FROM {ESQUEMA}.usuario_rol WHERE rol = 'INGENIERO_CONOCIMIENTO'"))
    op.execute(sa.text(f"ALTER TABLE {ESQUEMA}.usuario_rol DROP CONSTRAINT IF EXISTS ck_usuario_rol_rol"))
    op.execute(sa.text(
        f"ALTER TABLE {ESQUEMA}.usuario_rol ADD CONSTRAINT ck_usuario_rol_rol CHECK (rol IN ({_lista(anteriores)}))"
    ))
    for nombre in (f"fk_{TABLA}_id_version_origen", f"fk_{TABLA}_activada_por", f"ck_{TABLA}_estado_version"):
        op.execute(sa.text(f"ALTER TABLE {ESQUEMA}.{TABLA} DROP CONSTRAINT IF EXISTS {nombre}"))
    for columna in ("activada_por", "activada_en", "id_version_origen", "motivo", "estado", "contenido"):
        if columna in _columnas(TABLA):
            op.drop_column(TABLA, columna, schema=ESQUEMA)
