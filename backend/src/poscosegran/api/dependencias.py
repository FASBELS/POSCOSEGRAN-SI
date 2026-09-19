"""Precondiciones e idempotencia comunes a las escrituras."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import Header, Response
from sqlalchemy.orm import Session

from ..config import obtener_configuracion
from ..seguridad.identidad import Identidad
from ..servicios import concurrencia, idempotencia

ClaveIdempotencia = Annotated[uuid.UUID | None, Header(alias="Idempotency-Key")]
IfMatch = Annotated[str | None, Header(alias="If-Match")]
IfNoneMatch = Annotated[str | None, Header(alias="If-None-Match")]


def exigir_clave(clave: uuid.UUID | None) -> uuid.UUID:
    if clave is None:
        raise concurrencia.PrecondicionRequerida("Idempotency-Key es obligatorio")
    return clave


def reservar(
    sesion: Session,
    identidad: Identidad,
    clave: uuid.UUID | None,
    metodo: str,
    ruta: str,
    cuerpo: Any,
) -> idempotencia.RespuestaRepetida | None:
    return idempotencia.reservar(
        sesion,
        clave=exigir_clave(clave),
        id_usuario=identidad.id,
        metodo=metodo,
        ruta=ruta,
        cuerpo=cuerpo,
        horas_retencion=obtener_configuracion().idempotencia_horas_retencion,
    )


def completar(
    sesion: Session,
    identidad: Identidad,
    clave: uuid.UUID | None,
    estado_http: int,
    id_recurso: uuid.UUID | None,
    cuerpo: dict[str, Any] | None,
) -> None:
    idempotencia.completar(
        sesion,
        clave=exigir_clave(clave),
        id_usuario=identidad.id,
        estado_http=estado_http,
        id_recurso=id_recurso,
        cuerpo=cuerpo,
    )


def etiquetar(respuesta: Response, revision: int) -> None:
    respuesta.headers["ETag"] = concurrencia.etiqueta(revision)
