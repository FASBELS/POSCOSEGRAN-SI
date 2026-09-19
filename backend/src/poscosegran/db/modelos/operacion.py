"""Auditoría e idempotencia.

La auditoría no guarda tokens, cabeceras de autorización ni secretos: solo el
identificador de usuario, la acción y un resumen del cambio.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..base import AHORA, Base, columna_id, fk_uuid


class RegistroAuditoria(Base):
    __tablename__ = "auditoria"

    id: Mapped[uuid.UUID] = columna_id()
    ocurrido_en: Mapped[datetime] = mapped_column(server_default=AHORA, index=True)
    id_usuario: Mapped[uuid.UUID | None] = fk_uuid("usuario.id", nullable=True, index=True)
    roles: Mapped[list[str]] = mapped_column(ARRAY(sa.Text), server_default=sa.text("'{}'::text[]"))
    accion: Mapped[str] = mapped_column(sa.Text, index=True)
    recurso_tipo: Mapped[str] = mapped_column(sa.Text)
    recurso_id: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid, nullable=True, index=True)
    metodo: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    ruta: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    estado_http: Mapped[int | None] = mapped_column(sa.SmallInteger, nullable=True)
    revision_resultante: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    id_solicitud: Mapped[uuid.UUID] = mapped_column(sa.Uuid, index=True)
    resumen: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        sa.Index("ix_auditoria_recurso", "recurso_tipo", "recurso_id", sa.text("ocurrido_en DESC")),
    )


class ClaveIdempotencia(Base):
    """Reintento idéntico devuelve el recurso original; distinto contenido, 409."""

    __tablename__ = "idempotencia"

    id: Mapped[uuid.UUID] = columna_id()
    clave: Mapped[uuid.UUID] = mapped_column(sa.Uuid)
    id_usuario: Mapped[uuid.UUID] = fk_uuid("usuario.id")
    metodo: Mapped[str] = mapped_column(sa.Text)
    ruta: Mapped[str] = mapped_column(sa.Text)
    huella_cuerpo: Mapped[str] = mapped_column(sa.Text, comment="SHA-256 del cuerpo normalizado.")
    estado: Mapped[str] = mapped_column(sa.Text, comment="EN_CURSO | COMPLETADA")
    estado_http: Mapped[int | None] = mapped_column(sa.SmallInteger, nullable=True)
    id_recurso: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid, nullable=True)
    cuerpo_respuesta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    creada_en: Mapped[datetime] = mapped_column(server_default=AHORA)
    expira_en: Mapped[datetime] = mapped_column(index=True)

    __table_args__ = (
        sa.UniqueConstraint("clave", "id_usuario"),
        sa.CheckConstraint("estado IN ('EN_CURSO', 'COMPLETADA')", name="estado_valido"),
        sa.CheckConstraint(
            "estado <> 'COMPLETADA' OR estado_http IS NOT NULL", name="completada_con_estado",
        ),
    )
