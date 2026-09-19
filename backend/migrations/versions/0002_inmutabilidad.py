"""Inmutabilidad del historial y protección contra borrado.

Revisión: 0002_inmutabilidad
Revisión anterior: 0001_linea_base

Una evaluación es una instantánea: se corrige emitiendo otra, nunca editando la
anterior. Las observaciones, controles, eventos, revisiones, resoluciones y
admisiones siguen el mismo criterio. Las reglas viven en la base y no solo en la
aplicación, para que ni una consulta manual ni un script futuro puedan reescribir
el historial en silencio.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_inmutabilidad"
down_revision = "0001_linea_base"
branch_labels = None
depends_on = None

ESQUEMA = "poscosegran"

# Historial estricto: ni UPDATE ni DELETE.
TABLAS_INMUTABLES = (
    "evaluacion",
    "evaluacion_motivo",
    "motivo_evidencia",
    "motivo_fuente",
    "evaluacion_accion",
    "evaluacion_dato_pendiente",
    "evaluacion_estimacion",
    "observacion",
    "observacion_aplicada",
    "control",
    "evento",
    "revision_incidencia",
    "resolucion",
    "admision",
    "auditoria",
)

# Se pueden actualizar con auditoría, pero nunca borrar.
TABLAS_SIN_BORRADO = (
    "almacen",
    "lote",
    "recipiente",
    "unidad",
    "incidencia",
    "plan",
    "dictamen",
    "usuario",
    "usuario_rol",
    "asignacion_almacen",
    "asignacion_lote",
    "version_conocimiento",
    "fuente",
    "regla",
)


def _tablas_existentes(nombres: tuple[str, ...]) -> list[str]:
    inspector = sa.inspect(op.get_bind())
    presentes = set(inspector.get_table_names(schema=ESQUEMA))
    return [nombre for nombre in nombres if nombre in presentes]


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
            CREATE OR REPLACE FUNCTION {ESQUEMA}.impedir_modificacion()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
              RAISE EXCEPTION
                'registro inmutable en %.%: corrija mediante un nuevo registro trazable',
                TG_TABLE_SCHEMA, TG_TABLE_NAME
                USING ERRCODE = '23514';
            END;
            $$;
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE OR REPLACE FUNCTION {ESQUEMA}.impedir_borrado()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
              RAISE EXCEPTION
                'no se elimina historial en %.%: use un evento o una anulación trazable',
                TG_TABLE_SCHEMA, TG_TABLE_NAME
                USING ERRCODE = '23514';
            END;
            $$;
            """
        )
    )

    for tabla in _tablas_existentes(TABLAS_INMUTABLES):
        op.execute(
            sa.text(
                f"""
                CREATE TRIGGER tg_{tabla}_inmutable
                BEFORE UPDATE OR DELETE ON {ESQUEMA}.{tabla}
                FOR EACH ROW EXECUTE FUNCTION {ESQUEMA}.impedir_modificacion();
                """
            )
        )

    for tabla in _tablas_existentes(TABLAS_SIN_BORRADO):
        op.execute(
            sa.text(
                f"""
                CREATE TRIGGER tg_{tabla}_sin_borrado
                BEFORE DELETE ON {ESQUEMA}.{tabla}
                FOR EACH ROW EXECUTE FUNCTION {ESQUEMA}.impedir_borrado();
                """
            )
        )


def downgrade() -> None:
    for tabla in _tablas_existentes(TABLAS_INMUTABLES):
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS tg_{tabla}_inmutable ON {ESQUEMA}.{tabla}"))
    for tabla in _tablas_existentes(TABLAS_SIN_BORRADO):
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS tg_{tabla}_sin_borrado ON {ESQUEMA}.{tabla}"))
    op.execute(sa.text(f"DROP FUNCTION IF EXISTS {ESQUEMA}.impedir_modificacion()"))
    op.execute(sa.text(f"DROP FUNCTION IF EXISTS {ESQUEMA}.impedir_borrado()"))
