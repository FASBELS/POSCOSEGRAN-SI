"""Claves de idempotencia para POST y PUT.

Reintento idéntico: se devuelve el recurso original sin repetir el efecto.
Misma clave con contenido distinto: 409, porque sería otra operación.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db.modelos import ClaveIdempotencia


class ClaveReutilizada(Exception):
    """Misma clave, distinto contenido. Se traduce a 409."""


class OperacionEnCurso(Exception):
    """Un reintento llegó antes de terminar el primero. Se traduce a 409."""


@dataclass(frozen=True, slots=True)
class RespuestaRepetida:
    estado_http: int
    id_recurso: uuid.UUID | None
    cuerpo: dict[str, Any] | None


def huella(cuerpo: Any) -> str:
    """Huella estable del contenido: el orden de las claves no debe alterarla."""
    normalizado = json.dumps(cuerpo, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()


def reservar(
    sesion: Session,
    *,
    clave: uuid.UUID,
    id_usuario: uuid.UUID,
    metodo: str,
    ruta: str,
    cuerpo: Any,
    horas_retencion: int,
) -> RespuestaRepetida | None:
    """Reserva la clave o devuelve la respuesta ya emitida.

    Devuelve None cuando la operación debe ejecutarse por primera vez.
    """
    digestion = huella(cuerpo)
    existente = sesion.scalar(
        sa.select(ClaveIdempotencia).where(
            ClaveIdempotencia.clave == clave, ClaveIdempotencia.id_usuario == id_usuario
        )
    )
    if existente is not None:
        if existente.huella_cuerpo != digestion or existente.ruta != ruta or existente.metodo != metodo:
            raise ClaveReutilizada(str(clave))
        if existente.estado == "EN_CURSO":
            raise OperacionEnCurso(str(clave))
        return RespuestaRepetida(
            estado_http=existente.estado_http or 200,
            id_recurso=existente.id_recurso,
            cuerpo=existente.cuerpo_respuesta,
        )

    registro = ClaveIdempotencia(
        clave=clave,
        id_usuario=id_usuario,
        metodo=metodo,
        ruta=ruta,
        huella_cuerpo=digestion,
        estado="EN_CURSO",
        expira_en=datetime.now(UTC) + timedelta(hours=horas_retencion),
    )
    sesion.add(registro)
    try:
        sesion.flush()
    except IntegrityError as exc:
        sesion.rollback()
        raise OperacionEnCurso(str(clave)) from exc
    return None


def completar(
    sesion: Session,
    *,
    clave: uuid.UUID,
    id_usuario: uuid.UUID,
    estado_http: int,
    id_recurso: uuid.UUID | None,
    cuerpo: dict[str, Any] | None,
) -> None:
    sesion.execute(
        sa.update(ClaveIdempotencia)
        .where(ClaveIdempotencia.clave == clave, ClaveIdempotencia.id_usuario == id_usuario)
        .values(
            estado="COMPLETADA",
            estado_http=estado_http,
            id_recurso=id_recurso,
            cuerpo_respuesta=cuerpo,
        )
    )


def purgar_vencidas(sesion: Session) -> int:
    resultado = sesion.execute(
        sa.delete(ClaveIdempotencia).where(ClaveIdempotencia.expira_en < datetime.now(UTC))
    )
    return int(resultado.rowcount or 0)
