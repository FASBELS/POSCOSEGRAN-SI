"""Dependencias FastAPI de identidad y límite de peticiones."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..db.modelos import Usuario

from ..config import Configuracion, obtener_configuracion
from ..db.sesion import unidad_de_trabajo
from .identidad import Identidad
from .jwt import CredencialInvalida, VerificadorJWT
from .limites import LimitadorVentana
from .permisos import cargar_roles

_verificador: VerificadorJWT | None = None
_limitador_lectura: LimitadorVentana | None = None
_limitador_escritura: LimitadorVentana | None = None


def obtener_verificador() -> VerificadorJWT:
    global _verificador
    if _verificador is None:
        _verificador = VerificadorJWT(obtener_configuracion())
    return _verificador


def _limitadores(cfg: Configuracion) -> tuple[LimitadorVentana, LimitadorVentana]:
    global _limitador_lectura, _limitador_escritura
    if _limitador_lectura is None or _limitador_escritura is None:
        _limitador_lectura = LimitadorVentana(cfg.limite_peticiones_por_minuto)
        _limitador_escritura = LimitadorVentana(cfg.limite_peticiones_escritura_por_minuto)
    return _limitador_lectura, _limitador_escritura


def _token_desde_cabecera(autorizacion: str | None) -> str:
    if not autorizacion:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "sesion_requerida")
    partes = autorizacion.split(" ", 1)
    if len(partes) != 2 or partes[0].lower() != "bearer" or not partes[1].strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "sesion_requerida")
    return partes[1].strip()


def identidad_actual(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> Identidad:
    """Verifica la credencial y carga los roles desde la base, no del token."""
    token = _token_desde_cabecera(authorization)
    try:
        id_usuario = obtener_verificador().verificar(token)
    except CredencialInvalida as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "sesion_invalida") from exc

    with unidad_de_trabajo() as sesion:
        usuario = sesion.get(Usuario, id_usuario)
        if usuario is None or not usuario.activo:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "usuario_no_habilitado")
        roles = cargar_roles(sesion, id_usuario)

    id_solicitud = getattr(request.state, "id_solicitud", None) or uuid.uuid4()
    identidad = Identidad(id=id_usuario, roles=roles, id_solicitud=id_solicitud)

    cfg = obtener_configuracion()
    lectura, escritura = _limitadores(cfg)
    limitador = escritura if request.method in {"POST", "PUT", "PATCH", "DELETE"} else lectura
    if not limitador.permitir(str(identidad.id)):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "limite_peticiones")

    request.state.identidad = identidad
    return identidad


def sesion_bd(
    request: Request,
    identidad: Annotated[Identidad, Depends(identidad_actual)],
) -> Iterator[Session]:
    with unidad_de_trabajo(identidad.id) as sesion:
        # Serializa comandos de este piloto entre todos los workers. La transacción
        # abarca precondiciones, instantánea y efectos; lecturas nunca toman el lock.
        if request.method in {"POST", "PUT", "PATCH"}:
            sesion.execute(text("SELECT pg_advisory_xact_lock(7342026)"))
        yield sesion


IdentidadDep = Annotated[Identidad, Depends(identidad_actual)]
SesionDep = Annotated[Session, Depends(sesion_bd)]
