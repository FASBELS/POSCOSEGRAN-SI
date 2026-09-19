"""Evaluación y su traza.

Una evaluación es una instantánea inmutable: guarda la entrada efectiva, los
motivos con su evidencia y fuente, las reglas disparadas y las versiones de
conocimiento, parámetros y motor. La vigencia NO se guarda aquí: se calcula al
consultar, con el reloj del servidor.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..base import AHORA, Base, columna_id, enum_texto, fk_uuid
from ..enums import (
    DECISION,
    FASE,
    FUNDAMENTO_MOTIVO,
    OPERADOR,
    RAMA_R30,
    RESPONSABLE_REQUERIDO,
    TIPO_ESTIMACION,
    UNIDAD_DATO,
)


class Evaluacion(Base):
    __tablename__ = "evaluacion"

    id: Mapped[uuid.UUID] = columna_id()
    id_unidad: Mapped[uuid.UUID] = fk_uuid("unidad.id", index=True)
    id_lote: Mapped[uuid.UUID] = fk_uuid("lote.id")
    id_recipiente: Mapped[uuid.UUID] = fk_uuid("recipiente.id")
    id_almacen: Mapped[uuid.UUID] = fk_uuid("almacen.id")

    fecha_evaluacion: Mapped[datetime] = mapped_column(
        server_default=AHORA, comment="Reloj del servidor; el cliente no la impone."
    )
    fase: Mapped[str | None] = mapped_column(enum_texto("fase", FASE), nullable=True)
    decision_final: Mapped[str] = mapped_column(enum_texto("decision", DECISION))
    rama_r30: Mapped[str] = mapped_column(enum_texto("rama_r30", RAMA_R30))

    # Entrada efectiva tal como se aplicó, para poder reproducir la inferencia.
    entrada_efectiva: Mapped[dict[str, Any]] = mapped_column(JSONB)
    revision_unidad_usada: Mapped[int] = mapped_column(sa.Integer)
    revision_almacen_usada: Mapped[int] = mapped_column(sa.Integer)

    reglas_activadas: Mapped[list[str]] = mapped_column(
        ARRAY(sa.Text), server_default=sa.text("'{}'::text[]")
    )

    # CalculosTiempo desplegado en columnas: se consulta y se audita mejor que en JSON.
    vida_consumida: Mapped[Decimal | None] = mapped_column(sa.Numeric(8, 4), nullable=True)
    vida_minima_documentada: Mapped[Decimal | None] = mapped_column(sa.Numeric(8, 4), nullable=True)
    vida_proyectada: Mapped[Decimal | None] = mapped_column(sa.Numeric(8, 4), nullable=True)
    tiempo_referencia_actual: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    celda_tabla_id: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    celda_humedad_fila: Mapped[Decimal | None] = mapped_column(sa.Numeric(6, 2), nullable=True)
    celda_temperatura_columna_f: Mapped[Decimal | None] = mapped_column(
        sa.Numeric(6, 2), nullable=True
    )
    celda_dias_referencia: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)

    fecha_proximo_control: Mapped[datetime | None] = mapped_column(nullable=True)
    fecha_vencimiento_autorizacion: Mapped[datetime | None] = mapped_column(nullable=True)

    version_base: Mapped[str] = mapped_column(sa.Text)
    version_parametros: Mapped[str] = mapped_column(sa.Text)
    version_motor: Mapped[str] = mapped_column(sa.Text)
    id_version_conocimiento: Mapped[uuid.UUID] = fk_uuid("version_conocimiento.id")

    id_responsable: Mapped[uuid.UUID] = fk_uuid("usuario.id")

    __table_args__ = (
        sa.Index("ix_evaluacion_unidad_fecha", "id_unidad", sa.text("fecha_evaluacion DESC"), "id"),
        sa.CheckConstraint(
            "vida_consumida IS NULL OR vida_consumida >= 0", name="vida_no_negativa"
        ),
        # Una decisión no autorizada no lleva vencimiento de autorización.
        sa.CheckConstraint(
            "fecha_vencimiento_autorizacion IS NULL "
            "OR decision_final IN ('AUTORIZAR_ALMACENAMIENTO', 'AUTORIZAR_CON_MONITOREO')",
            name="vencimiento_solo_si_autoriza",
        ),
        sa.CheckConstraint(
            "(celda_tabla_id IS NULL) = (celda_dias_referencia IS NULL)",
            name="celda_completa_o_ausente",
        ),
    )


class Motivo(Base):
    __tablename__ = "evaluacion_motivo"

    id: Mapped[uuid.UUID] = columna_id()
    id_evaluacion: Mapped[uuid.UUID] = fk_uuid("evaluacion.id", index=True)
    orden: Mapped[int] = mapped_column(sa.SmallInteger)
    codigo: Mapped[str] = mapped_column(sa.Text, comment="Motivo.id del contrato.")
    regla: Mapped[str] = mapped_column(sa.Text, index=True)
    mensaje: Mapped[str] = mapped_column(sa.Text)
    fundamento: Mapped[str] = mapped_column(enum_texto("fundamento_motivo", FUNDAMENTO_MOTIVO))

    __table_args__ = (sa.UniqueConstraint("id_evaluacion", "orden"),)


class MotivoEvidencia(Base):
    """Valor observado frente a umbral, con el operador que los comparó."""

    __tablename__ = "motivo_evidencia"

    id: Mapped[uuid.UUID] = columna_id()
    id_motivo: Mapped[uuid.UUID] = fk_uuid("evaluacion_motivo.id", index=True)
    orden: Mapped[int] = mapped_column(sa.SmallInteger)
    campo: Mapped[str] = mapped_column(sa.Text)
    unidad_dato: Mapped[str | None] = mapped_column(
        enum_texto("unidad_dato", UNIDAD_DATO), nullable=True
    )
    fecha_observacion: Mapped[datetime | None] = mapped_column(nullable=True)
    operador: Mapped[str | None] = mapped_column(enum_texto("operador", OPERADOR), nullable=True)

    valor_numero: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 4), nullable=True)
    valor_booleano: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    valor_texto: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    umbral_numero: Mapped[Decimal | None] = mapped_column(sa.Numeric(12, 4), nullable=True)
    umbral_booleano: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    umbral_texto: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("id_motivo", "orden"),
        sa.CheckConstraint(
            "(CASE WHEN valor_numero IS NOT NULL THEN 1 ELSE 0 END) "
            "+ (CASE WHEN valor_booleano IS NOT NULL THEN 1 ELSE 0 END) "
            "+ (CASE WHEN valor_texto IS NOT NULL THEN 1 ELSE 0 END) <= 1",
            name="un_solo_valor",
        ),
        sa.CheckConstraint(
            "(CASE WHEN umbral_numero IS NOT NULL THEN 1 ELSE 0 END) "
            "+ (CASE WHEN umbral_booleano IS NOT NULL THEN 1 ELSE 0 END) "
            "+ (CASE WHEN umbral_texto IS NOT NULL THEN 1 ELSE 0 END) <= 1",
            name="un_solo_umbral",
        ),
    )


class MotivoFuente(Base):
    __tablename__ = "motivo_fuente"

    id: Mapped[uuid.UUID] = columna_id()
    id_motivo: Mapped[uuid.UUID] = fk_uuid("evaluacion_motivo.id", index=True)
    id_fuente: Mapped[str] = mapped_column(sa.Text, comment="S01–S09 del catálogo.")
    localizador: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    __table_args__ = (sa.UniqueConstraint("id_motivo", "id_fuente", "localizador"),)


class AccionRequerida(Base):
    __tablename__ = "evaluacion_accion"

    id: Mapped[uuid.UUID] = columna_id()
    id_evaluacion: Mapped[uuid.UUID] = fk_uuid("evaluacion.id", index=True)
    orden: Mapped[int] = mapped_column(sa.SmallInteger)
    codigo: Mapped[str] = mapped_column(sa.Text)
    descripcion: Mapped[str] = mapped_column(sa.Text)
    responsable_requerido: Mapped[str] = mapped_column(
        enum_texto("responsable_requerido", RESPONSABLE_REQUERIDO)
    )
    id_incidencia: Mapped[uuid.UUID | None] = fk_uuid("incidencia.id", nullable=True)

    __table_args__ = (sa.UniqueConstraint("id_evaluacion", "orden"),)


class DatoPendiente(Base):
    __tablename__ = "evaluacion_dato_pendiente"

    id: Mapped[uuid.UUID] = columna_id()
    id_evaluacion: Mapped[uuid.UUID] = fk_uuid("evaluacion.id", index=True)
    orden: Mapped[int] = mapped_column(sa.SmallInteger)
    campo: Mapped[str] = mapped_column(sa.Text)
    motivo: Mapped[str] = mapped_column(sa.Text)
    paso: Mapped[int] = mapped_column(sa.SmallInteger)

    __table_args__ = (
        sa.UniqueConstraint("id_evaluacion", "orden"),
        sa.CheckConstraint("paso BETWEEN 1 AND 6", name="paso_valido"),
    )


class Estimacion(Base):
    """Sustitución declarada: qué se reemplazó y por qué. Nunca se presenta como medición."""

    __tablename__ = "evaluacion_estimacion"

    id: Mapped[uuid.UUID] = columna_id()
    id_evaluacion: Mapped[uuid.UUID] = fk_uuid("evaluacion.id", index=True)
    orden: Mapped[int] = mapped_column(sa.SmallInteger)
    tipo: Mapped[str] = mapped_column(enum_texto("tipo_estimacion", TIPO_ESTIMACION))
    descripcion: Mapped[str] = mapped_column(sa.Text)
    campos: Mapped[list[str]] = mapped_column(ARRAY(sa.Text))
    id_tabla: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    __table_args__ = (sa.UniqueConstraint("id_evaluacion", "orden"),)


class ObservacionAplicada(Base):
    """Observaciones efectivamente usadas, incluidas las recuperadas del historial."""

    __tablename__ = "observacion_aplicada"

    id: Mapped[uuid.UUID] = columna_id()
    id_evaluacion: Mapped[uuid.UUID] = fk_uuid("evaluacion.id", index=True)
    id_observacion: Mapped[uuid.UUID] = fk_uuid("observacion.id")
    orden: Mapped[int] = mapped_column(sa.SmallInteger)
    creada_en: Mapped[datetime] = mapped_column(server_default=AHORA)

    __table_args__ = (
        sa.UniqueConstraint("id_evaluacion", "id_observacion"),
        sa.UniqueConstraint("id_evaluacion", "orden"),
    )
