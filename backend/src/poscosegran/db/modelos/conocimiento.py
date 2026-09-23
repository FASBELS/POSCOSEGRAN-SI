"""Versiones de la base de conocimiento y su catálogo.

Cada versión guarda su contenido completo (base operativa y documental), de modo
que el motor evalúa con la versión activa de la base de datos y una evaluación
antigua se puede reproducir con la versión exacta con que se emitió.

Las versiones nacen de dos formas: cargando los archivos de knowledge/ (semilla)
o desde el módulo de adquisición, como propuesta que el ingeniero del
conocimiento valida y activa. Los usuarios de campo no editan umbrales.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from typing import Any

from ..base import AHORA, Base, columna_id, enum_texto, fk_uuid
from ..enums import ESTADO_VERSION


class VersionConocimiento(Base):
    __tablename__ = "version_conocimiento"

    id: Mapped[uuid.UUID] = columna_id()
    version_base: Mapped[str] = mapped_column(sa.Text)
    version_parametros: Mapped[str] = mapped_column(sa.Text)
    version_motor: Mapped[str] = mapped_column(sa.Text)
    hash_contenido: Mapped[str] = mapped_column(sa.Text, comment="SHA-256 del archivo cargado.")
    ruta_archivo: Mapped[str] = mapped_column(sa.Text)
    notas: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    activa: Mapped[bool] = mapped_column(sa.Boolean, default=False, server_default=sa.false())
    cargada_en: Mapped[datetime] = mapped_column(server_default=AHORA)
    cargada_por: Mapped[uuid.UUID | None] = fk_uuid("usuario.id", nullable=True)

    # Migración 0003: módulo de adquisición.
    contenido: Mapped[dict[str, Any] | None] = mapped_column(
        nullable=True, comment="Base operativa y documental completas."
    )
    estado: Mapped[str] = mapped_column(
        enum_texto("estado_version", ESTADO_VERSION), default="ACTIVADA", server_default="ACTIVADA"
    )
    motivo: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    id_version_origen: Mapped[uuid.UUID | None] = fk_uuid("version_conocimiento.id", nullable=True)
    activada_en: Mapped[datetime | None] = mapped_column(nullable=True)
    activada_por: Mapped[uuid.UUID | None] = fk_uuid("usuario.id", nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("version_base", "version_parametros", "version_motor"),
        sa.Index("ux_version_conocimiento_activa", "activa", unique=True, postgresql_where=sa.text("activa")),
    )


class Fuente(Base):
    __tablename__ = "fuente"

    id: Mapped[uuid.UUID] = columna_id()
    id_version: Mapped[uuid.UUID] = fk_uuid("version_conocimiento.id", index=True)
    codigo: Mapped[str] = mapped_column(sa.Text, comment="S01–S09.")
    referencia_markdown: Mapped[str] = mapped_column(sa.Text)

    __table_args__ = (sa.UniqueConstraint("id_version", "codigo"),)


class Regla(Base):
    """R01–R30 y las nueve ramas de R30, en la misma tabla."""

    __tablename__ = "regla"

    id: Mapped[uuid.UUID] = columna_id()
    id_version: Mapped[uuid.UUID] = fk_uuid("version_conocimiento.id", index=True)
    codigo: Mapped[str] = mapped_column(sa.Text, comment="R01…R30, R30.1…R30.9.")
    es_rama: Mapped[bool] = mapped_column(sa.Boolean)
    orden: Mapped[int] = mapped_column(sa.Integer)
    antecedente: Mapped[str] = mapped_column(sa.Text)
    consecuente: Mapped[str] = mapped_column(sa.Text)
    accion: Mapped[str] = mapped_column(sa.Text)
    fundamento_markdown: Mapped[str] = mapped_column(sa.Text)

    __table_args__ = (
        sa.UniqueConstraint("id_version", "codigo"),
        sa.UniqueConstraint("id_version", "es_rama", "orden"),
    )
