"""Traducción de excepciones al ErrorAPI del contrato.

El cliente conserva el formulario ante cualquiera de estos errores: ninguno
significa que se haya emitido una evaluación.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request, status
from starlette.exceptions import HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ..seguridad.permisos import AccesoDenegado, RecursoInaccesible
from ..servicios.concurrencia import ConflictoRevision, PrecondicionRequerida
from ..servicios.idempotencia import ClaveReutilizada, OperacionEnCurso

registro = logging.getLogger("poscosegran")


def _cuerpo(
    codigo: str, mensaje: str, id_solicitud: uuid.UUID, campos: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    return {
        "codigo": codigo,
        "mensaje": mensaje,
        "campos": campos or [],
        "id_solicitud": str(id_solicitud),
    }


def _id_solicitud(request: Request) -> uuid.UUID:
    valor = getattr(request.state, "id_solicitud", None)
    return valor if isinstance(valor, uuid.UUID) else uuid.uuid4()


def registrar_manejadores(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def _http(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, headers=exc.headers,
                            content=_cuerpo(str(exc.detail), str(exc.detail), _id_solicitud(request)))

    @app.exception_handler(RecursoInaccesible)
    async def _inaccesible(request: Request, exc: RecursoInaccesible) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_cuerpo("no_encontrado", "Recurso inexistente o no accesible.", _id_solicitud(request)),
        )

    @app.exception_handler(AccesoDenegado)
    async def _denegado(request: Request, exc: AccesoDenegado) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=_cuerpo("sin_permiso", str(exc), _id_solicitud(request)),
        )

    @app.exception_handler(PrecondicionRequerida)
    async def _precondicion(request: Request, exc: PrecondicionRequerida) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            content=_cuerpo("precondicion_requerida", str(exc), _id_solicitud(request)),
        )

    @app.exception_handler(ConflictoRevision)
    async def _conflicto(request: Request, exc: ConflictoRevision) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_cuerpo(
                "revision_obsoleta",
                "El recurso cambió. Recargue la unidad y el almacén antes de reenviar.",
                _id_solicitud(request),
            ),
        )

    @app.exception_handler(ClaveReutilizada)
    async def _clave(request: Request, exc: ClaveReutilizada) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_cuerpo(
                "clave_idempotencia_reutilizada",
                "La clave ya se usó con otro contenido.",
                _id_solicitud(request),
            ),
        )

    @app.exception_handler(OperacionEnCurso)
    async def _en_curso(request: Request, exc: OperacionEnCurso) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_cuerpo(
                "operacion_en_curso", "La operación original aún se está procesando.", _id_solicitud(request)
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def _estructura(request: Request, exc: RequestValidationError) -> JSONResponse:
        campos = [
            {
                "ruta": ".".join(str(parte) for parte in error.get("loc", ())),
                "codigo": str(error.get("type", "invalido")),
                "mensaje": str(error.get("msg", "")),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_cuerpo(
                "estructura_invalida", "El cuerpo no cumple el contrato.", _id_solicitud(request), campos
            ),
        )

    @app.exception_handler(Exception)
    async def _interno(request: Request, exc: Exception) -> JSONResponse:
        id_solicitud = _id_solicitud(request)
        registro.exception("fallo no controlado", extra={"id_solicitud": str(id_solicitud)})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_cuerpo("error_interno", "No se pudo completar la operación.", id_solicitud),
        )
