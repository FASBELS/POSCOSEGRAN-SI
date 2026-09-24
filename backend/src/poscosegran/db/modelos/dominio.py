"""Almacén, lote, recipiente y unidad de evaluación."""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from ..base import AHORA, ESQUEMA, Base, columna_id, enum_texto, fk_uuid
from ..enums import MODALIDAD, USO_FINAL, VARIEDAD


class Almacen(Base):
    __tablename__ = "almacen"

    id: Mapped[uuid.UUID] = columna_id()
    id_propietario: Mapped[uuid.UUID] = fk_uuid("usuario.id", index=True)
    nombre: Mapped[str] = mapped_column(sa.Text)
    ubicacion: Mapped[str] = mapped_column(sa.Text)
    clima_calido: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    fundamento_clima: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    revision: Mapped[int] = mapped_column(sa.Integer, default=1, server_default=sa.text("1"))
    creado_en: Mapped[datetime] = mapped_column(server_default=AHORA)
    actualizado_en: Mapped[datetime] = mapped_column(server_default=AHORA)

    __table_args__ = (
        sa.CheckConstraint(
            "clima_calido IS NULL OR (fundamento_clima IS NOT NULL "
            "AND length(btrim(fundamento_clima)) > 0)",
            name="clima_exige_fundamento",
        ),
        sa.CheckConstraint("revision >= 1", name="revision_positiva"),
    )


class Lote(Base):
    __tablename__ = "lote"

    id: Mapped[uuid.UUID] = columna_id()
    id_propietario: Mapped[uuid.UUID] = fk_uuid("usuario.id", index=True)
    codigo: Mapped[str] = mapped_column(sa.Text)
    variedad: Mapped[str] = mapped_column(enum_texto("variedad", VARIEDAD))
    uso_final: Mapped[str] = mapped_column(enum_texto("uso_final", USO_FINAL))
    revision: Mapped[int] = mapped_column(sa.Integer, default=1, server_default=sa.text("1"))
    creado_en: Mapped[datetime] = mapped_column(server_default=AHORA)
    actualizado_en: Mapped[datetime] = mapped_column(server_default=AHORA)

    __table_args__ = (
        sa.UniqueConstraint("id_propietario", "codigo"),
        sa.CheckConstraint("revision >= 1", name="revision_positiva"),
    )


class Recipiente(Base):
    """Identidad estable del envase, independiente de la unidad que lo evalúa."""

    __tablename__ = "recipiente"

    id: Mapped[uuid.UUID] = columna_id()
    nombre: Mapped[str] = mapped_column(sa.Text)
    creado_en: Mapped[datetime] = mapped_column(server_default=AHORA)


class Unidad(Base):
    """Lote + recipiente + almacén: el objeto que se evalúa.

    revision_almacen no se almacena; se lee de Almacen.revision al serializar,
    para que un cambio del almacén se refleje en todas sus unidades sin copia.
    """

    __tablename__ = "unidad"

    id: Mapped[uuid.UUID] = columna_id()
    id_lote: Mapped[uuid.UUID] = fk_uuid("lote.id", index=True)
    id_almacen: Mapped[uuid.UUID] = fk_uuid("almacen.id", index=True)
    id_recipiente: Mapped[uuid.UUID] = fk_uuid("recipiente.id", unique=True)
    nombre_recipiente: Mapped[str] = mapped_column(sa.Text)
    tipo_almacenamiento: Mapped[str | None] = mapped_column(
        enum_texto("modalidad", MODALIDAD), nullable=True
    )
    id_evaluacion_actual: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid,
        sa.ForeignKey(
            f"{ESQUEMA}.evaluacion.id",
            ondelete="RESTRICT",
            use_alter=True,
            name="fk_unidad_id_evaluacion_actual",
        ),
        nullable=True,
    )
    revision: Mapped[int] = mapped_column(sa.Integer, default=1, server_default=sa.text("1"))
    creado_en: Mapped[datetime] = mapped_column(server_default=AHORA)
    actualizado_en: Mapped[datetime] = mapped_column(server_default=AHORA)

    __table_args__ = (
        sa.UniqueConstraint("id_lote", "nombre_recipiente"),
        sa.CheckConstraint("revision >= 1", name="revision_positiva"),
    )
