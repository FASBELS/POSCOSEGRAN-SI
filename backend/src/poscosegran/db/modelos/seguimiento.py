"""Planes, dictámenes, incidencias, revisiones, resoluciones y admisiones.

Una incidencia sobrevive a cualquier cambio de medición: solo se cierra con su
resolución registrada. Registrar un plan no equivale a cumplirlo.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from ..base import AHORA, Base, columna_id, enum_texto, fk_uuid
from ..enums import (
    ESTADO_INCIDENCIA,
    RESULTADO_REVISION,
    TIPO_ADMISION,
    TIPO_INCIDENCIA,
)


class Plan(Base):
    __tablename__ = "plan"

    id: Mapped[uuid.UUID] = columna_id()
    id_unidad: Mapped[uuid.UUID] = fk_uuid("unidad.id", index=True)
    fecha_proximo_control: Mapped[datetime] = mapped_column()
    intervalo_dias: Mapped[int] = mapped_column(sa.Integer)
    fecha_salida_prevista: Mapped[datetime] = mapped_column()
    actividades: Mapped[str] = mapped_column(sa.Text)
    vigente: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default=sa.true())
    id_responsable: Mapped[uuid.UUID] = fk_uuid("usuario.id")
    creado_en: Mapped[datetime] = mapped_column(server_default=AHORA)

    __table_args__ = (
        sa.CheckConstraint("intervalo_dias > 0", name="intervalo_positivo"),
        sa.Index(
            "ux_plan_vigente_por_unidad",
            "id_unidad",
            unique=True,
            postgresql_where=sa.text("vigente"),
        ),
    )


class Dictamen(Base):
    """Autorización técnica acotada para la banda condicional de humedad.

    'vigente' se deriva al consultar de vence_en y anulado_en; no se guarda.
    """

    __tablename__ = "dictamen"

    id: Mapped[uuid.UUID] = columna_id()
    id_unidad: Mapped[uuid.UUID] = fk_uuid("unidad.id", index=True)
    humedad_min: Mapped[Decimal] = mapped_column(sa.Numeric(6, 2))
    humedad_max: Mapped[Decimal] = mapped_column(sa.Numeric(6, 2))
    plazo_maximo_dias: Mapped[int] = mapped_column(sa.Integer)
    emitido_en: Mapped[datetime] = mapped_column(server_default=AHORA)
    vence_en: Mapped[datetime] = mapped_column()
    condiciones: Mapped[str] = mapped_column(sa.Text)
    evidencia: Mapped[str] = mapped_column(sa.Text)
    id_tecnico: Mapped[uuid.UUID] = fk_uuid("usuario.id")
    anulado_en: Mapped[datetime | None] = mapped_column(nullable=True)
    motivo_anulacion: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    __table_args__ = (
        sa.CheckConstraint("humedad_min <= humedad_max", name="banda_coherente"),
        sa.CheckConstraint("plazo_maximo_dias > 0", name="plazo_positivo"),
        sa.CheckConstraint("vence_en > emitido_en", name="vence_despues_de_emitir"),
        sa.CheckConstraint(
            "anulado_en IS NULL OR motivo_anulacion IS NOT NULL", name="anulacion_con_motivo"
        ),
        sa.Index("ix_dictamen_unidad_vence", "id_unidad", sa.text("vence_en DESC")),
    )


class Incidencia(Base):
    __tablename__ = "incidencia"

    id: Mapped[uuid.UUID] = columna_id()
    id_unidad: Mapped[uuid.UUID] = fk_uuid("unidad.id", index=True)
    tipo: Mapped[str] = mapped_column(enum_texto("tipo_incidencia", TIPO_INCIDENCIA))
    estado: Mapped[str] = mapped_column(enum_texto("estado_incidencia", ESTADO_INCIDENCIA))
    causas: Mapped[list[str]] = mapped_column(ARRAY(sa.Text))
    id_evaluacion_origen: Mapped[uuid.UUID | None] = fk_uuid("evaluacion.id", nullable=True)
    revision: Mapped[int] = mapped_column(sa.Integer, default=1, server_default=sa.text("1"))
    creada_en: Mapped[datetime] = mapped_column(server_default=AHORA)
    cerrada_en: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        sa.CheckConstraint(
            "(estado = 'CERRADA') = (cerrada_en IS NOT NULL)", name="cierre_coherente"
        ),
        sa.CheckConstraint("revision >= 1", name="revision_positiva"),
        # Un solo episodio abierto por unidad y tipo: evita duplicar cuarentenas.
        sa.Index(
            "ux_incidencia_abierta_por_tipo",
            "id_unidad",
            "tipo",
            unique=True,
            postgresql_where=sa.text("estado = 'ABIERTA'"),
        ),
    )


class RevisionIncidencia(Base):
    __tablename__ = "revision_incidencia"

    id: Mapped[uuid.UUID] = columna_id()
    id_incidencia: Mapped[uuid.UUID] = fk_uuid("incidencia.id", index=True)
    resultado: Mapped[str] = mapped_column(enum_texto("resultado_revision", RESULTADO_REVISION))
    evidencia: Mapped[str] = mapped_column(sa.Text)
    id_tecnico: Mapped[uuid.UUID] = fk_uuid("usuario.id")
    fecha: Mapped[datetime] = mapped_column(server_default=AHORA)

    __table_args__ = (
        sa.CheckConstraint("length(btrim(evidencia)) > 0", name="evidencia_no_vacia"),
    )


class Resolucion(Base):
    """Cierre del episodio. Registrar una revisión no autoriza almacenamiento."""

    __tablename__ = "resolucion"

    id: Mapped[uuid.UUID] = columna_id()
    id_incidencia: Mapped[uuid.UUID] = fk_uuid("incidencia.id", index=True)
    evidencia: Mapped[str] = mapped_column(sa.Text)
    disposicion: Mapped[str] = mapped_column(sa.Text)
    id_tecnico: Mapped[uuid.UUID] = fk_uuid("usuario.id")
    fecha: Mapped[datetime] = mapped_column(server_default=AHORA)

    __table_args__ = (
        sa.CheckConstraint("length(btrim(evidencia)) > 0", name="evidencia_no_vacia"),
        sa.CheckConstraint("length(btrim(disposicion)) > 0", name="disposicion_no_vacia"),
    )


class Admision(Base):
    """Acto de admitir el ingreso o la continuidad, apoyado en una evaluación vigente."""

    __tablename__ = "admision"

    id: Mapped[uuid.UUID] = columna_id()
    id_unidad: Mapped[uuid.UUID] = fk_uuid("unidad.id", index=True)
    id_evaluacion: Mapped[uuid.UUID] = fk_uuid("evaluacion.id")
    tipo: Mapped[str] = mapped_column(enum_texto("tipo_admision", TIPO_ADMISION))
    registrado_en: Mapped[datetime] = mapped_column(server_default=AHORA)
    id_responsable: Mapped[uuid.UUID] = fk_uuid("usuario.id")

    __table_args__ = (
        sa.Index("ix_admision_unidad_fecha", "id_unidad", sa.text("registrado_en DESC")),
    )
