"""Cursor opaco y estable: fecha descendente e identificador como desempate."""

from __future__ import annotations

from fastapi import HTTPException
import base64
import binascii
import json
import uuid
from datetime import datetime
from typing import Any

LIMITE_POR_DEFECTO = 20
LIMITE_MAXIMO = 100


def codificar(fecha: datetime, identificador: uuid.UUID) -> str:
    crudo = json.dumps({"f": fecha.isoformat(), "i": str(identificador)}).encode("utf-8")
    return base64.urlsafe_b64encode(crudo).decode("ascii").rstrip("=")


def decodificar(cursor: str | None) -> tuple[datetime, uuid.UUID] | None:
    if not cursor:
        return None
    relleno = "=" * (-len(cursor) % 4)
    try:
        datos: dict[str, Any] = json.loads(base64.urlsafe_b64decode(cursor + relleno))
        return datetime.fromisoformat(datos["f"]), uuid.UUID(datos["i"])
    except (binascii.Error, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422, "cursor no interpretable") from exc


def limitar(limite: int | None) -> int:
    if limite is None:
        return LIMITE_POR_DEFECTO
    return max(1, min(limite, LIMITE_MAXIMO))
