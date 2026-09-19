"""Borradores, observaciones, controles y eventos.

Una observación es inmutable: corregir significa registrar otra, no editar la
anterior. El historial temporal se reconstruye por (id_unidad, campo, fecha).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..base import AHORA, ESQUEMA, Base, columna_id, enum_texto, fk_uuid
from ..enums import (
    APLICABILIDAD,
    CAPTURA,
    ESTADO_DATO,
    PROCEDENCIA,
    TIPO_CONTROL,
    TIPO_EVENTO,
    UNIDAD_DATO,
)


class Borrador(Base):
    """Captura en curso. Un borrador por usuario y unidad; nunca autoriza nada."""

    __tablename__ = "borrador"

    id: Mapped[uuid.UUID] = columna_id()
    id_unidad: Mapped[uuid.UUID] = fk_uuid("unidad.id", index=True)
    id_usuario: Mapped[uuid.UUID] = fk_uuid("usuario.id", index=True)
    contenido: Mapped[dict[str, Any]] = mapped_column(JSONB)
    revision: Mapped[int] = mapped_column(sa.Integer, default=1, server_default=sa.text("1"))
    actualizado_en: Mapped[datetime] = mapped_column(server_default=AHORA)

    __table_args__ = (
        sa.UniqueConstraint("id_unidad", "id_usuario"),
        sa.CheckConstraint("revision >= 1", name="revision_positiva"),
    )


class Control(Base):
    """Inspección registrada. 'completo' lo determina el servidor al crearla."""

    __tablename__ = "control"

    id: Mapped[uuid.UUID] = columna_id()
    id_unidad: Mapped[uuid.UUID] = fk_uuid("unidad.id", index=True)
    tipo: Mapped[str] = mapped_column(enum_texto("tipo_control", TIPO_CONTROL))
    fecha: Mapped[datetime] = mapped_column()
    completo: Mapped[bool] = mapped_column(sa.Boolean)
    campos_pendientes: Mapped[list[str]] = mapped_column(
        ARRAY(sa.Text), server_default=sa.text("'{}'::text[]")
    )
    evidencia: Mapped[str] = mapped_column(sa.Text)
    id_responsable: Mapped[uuid.UUID] = fk_uuid("usuario.id")
    creado_en: Mapped[datetime] = mapped_column(server_default=AHORA)

    __table_args__ = (
        sa.Index("ix_control_unidad_tipo_fecha", "id_unidad", "tipo", sa.text("fecha DESC")),
        sa.CheckConstraint("length(btrim(evidencia)) > 0", name="evidencia_no_vacia"),
    )


class Evento(Base):
    """Hecho operativo que puede invalidar verificaciones anteriores.

    Registrar un evento nunca reinicia la vida consumida ni reactiva una
    autorización histórica.
    """

    __tablename__ = "evento"

    id: Mapped[uuid.UUID] = columna_id()
    id_unidad: Mapped[uuid.UUID] = fk_uuid("unidad.id", index=True)
    tipo: Mapped[str] = mapped_column(enum_texto("tipo_evento", TIPO_EVENTO))
    fecha: Mapped[datetime] = mapped_column()
    evidencia: Mapped[str] = mapped_column(sa.Text)
    id_responsable: Mapped[uuid.UUID] = fk_uuid("usuario.id")
    creado_en: Mapped[datetime] = mapped_column(server_default=AHORA)

    __table_args__ = (
        sa.Index("ix_evento_unidad_tipo_fecha", "id_unidad", "tipo", sa.text("fecha DESC")),
        sa.CheckConstraint("length(btrim(evidencia)) > 0", name="evidencia_no_vacia"),
    )


class Observacion(Base):
    """Un valor capturado para un campo de la matriz.

    El valor se guarda en la columna de su tipo, no en texto: un booleano nunca
    queda como 'true'. 'DESCONOCIDO' significa ausencia, no falso ni cero.
    """

    __tablename__ = "observacion"

    id: Mapped[uuid.UUID] = columna_id()
    id_unidad: Mapped[uuid.UUID] = fk_uuid("unidad.id", index=True)
    id_control: Mapped[uuid.UUID | None] = fk_uuid("control.id", nullable=True, index=True)
    id_evaluacion_origen: Mapped[uuid.UUID | None] = mapped_column(
        sa.Uuid,
        sa.ForeignKey(
            f"{ESQUEMA}.evaluacion.id",
            ondelete="RESTRICT",
            use_alter=True,
            name="fk_observacion_id_evaluacion_origen",
        ),
        nullable=True,
        index=True,
    )

    campo: Mapped[str] = mapped_column(sa.Text)
    captura: Mapped[str] = mapped_column(enum_texto("captura", CAPTURA))
    unidad_dato: Mapped[str] = mapped_column(enum_texto("unidad_dato", UNIDAD_DATO))

    valor_numero: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 4), nullable=True)
    valor_booleano: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    valor_texto: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    valor_original: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    fecha_observacion: Mapped[datetime | None] = mapped_column(nullable=True)
    metodo: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    evidencia: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    motivo_no_aplica: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    aplicabilidad: Mapped[str] = mapped_column(enum_texto("aplicabilidad", APLICABILIDAD))
    estado_dato: Mapped[str | None] = mapped_column(
        enum_texto("estado_dato", ESTADO_DATO), nullable=True
    )
    procedencia: Mapped[str] = mapped_column(enum_texto("procedencia", PROCEDENCIA))
    incidencias_validacion: Mapped[list[str]] = mapped_column(
        ARRAY(sa.Text), server_default=sa.text("'{}'::text[]")
    )
    id_responsable: Mapped[uuid.UUID] = fk_uuid("usuario.id")
    creada_en: Mapped[datetime] = mapped_column(server_default=AHORA)

    __table_args__ = (
        sa.CheckConstraint(
            "(CASE WHEN valor_numero IS NOT NULL THEN 1 ELSE 0 END) "
            "+ (CASE WHEN valor_booleano IS NOT NULL THEN 1 ELSE 0 END) "
            "+ (CASE WHEN valor_texto IS NOT NULL THEN 1 ELSE 0 END) <= 1",
            name="un_solo_valor",
        ),
        sa.CheckConstraint(
            "captura <> 'APORTADO' OR ("
            "  (valor_numero IS NOT NULL OR valor_booleano IS NOT NULL OR valor_texto IS NOT NULL)"
            "  AND fecha_observacion IS NOT NULL AND metodo IS NOT NULL)",
            name="aportado_exige_valor_fecha_metodo",
        ),
        sa.CheckConstraint(
            "captura <> 'DESCONOCIDO' OR ("
            "  valor_numero IS NULL AND valor_booleano IS NULL AND valor_texto IS NULL)",
            name="desconocido_sin_valor",
        ),
        sa.CheckConstraint(
            "captura <> 'NO_APLICA' OR ("
            "  valor_numero IS NULL AND valor_booleano IS NULL AND valor_texto IS NULL"
            "  AND motivo_no_aplica IS NOT NULL)",
            name="no_aplica_exige_motivo",
        ),
        # estado_dato nulo se reserva a NO_APLICA validado; nunca equivale a FALSO.
        sa.CheckConstraint(
            "estado_dato IS NOT NULL OR aplicabilidad = 'NO_APLICA'",
            name="estado_nulo_solo_no_aplica",
        ),
        sa.CheckConstraint(
            "unidad_dato <> 'BOOLEANO' OR valor_numero IS NULL",
            name="booleano_sin_numero",
        ),
        sa.Index(
            "ix_observacion_unidad_campo_fecha",
            "id_unidad",
            "campo",
            sa.text("fecha_observacion DESC NULLS LAST"),
        ),
    )
