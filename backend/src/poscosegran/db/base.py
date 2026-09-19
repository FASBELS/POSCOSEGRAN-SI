"""Declarativa común, esquema privado y utilidades de columnas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, mapped_column

ESQUEMA = "poscosegran"

CONVENCION_NOMBRES = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = sa.MetaData(schema=ESQUEMA, naming_convention=CONVENCION_NOMBRES)
    type_annotation_map = {dict[str, Any]: JSONB, datetime: sa.DateTime(timezone=True)}


def enum_texto(nombre: str, valores: tuple[str, ...]) -> sa.Enum:
    """Texto con restricción CHECK.

    Se prefiere a un tipo ENUM nativo porque añadir un valor no exige ALTER TYPE
    fuera de transacción y porque el conjunto admitido queda legible en el esquema.
    """
    return sa.Enum(
        *valores,
        name=nombre,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        length=max(len(v) for v in valores),
    )


def columna_id() -> Any:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=sa.text("gen_random_uuid()")
    )


def fk_uuid(destino: str, **kwargs: Any) -> Any:
    return mapped_column(UUID(as_uuid=True), sa.ForeignKey(f"{ESQUEMA}.{destino}", ondelete="RESTRICT"), **kwargs)


AHORA = sa.text("now()")
