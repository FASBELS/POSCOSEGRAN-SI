"""API integrada: recursos, evaluaciones, seguimiento, conocimiento y salud."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

import sqlalchemy as sa
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from ..config import obtener_configuracion
from ..db.sesion import obtener_motor
from .errores import registrar_manejadores
from .rutas import conocimiento, evaluacion, recursos, seguimiento, adquisicion


def crear_app() -> FastAPI:
    cfg = obtener_configuracion()
    app = FastAPI(
        title="POSCOSEGRAN API",
        version="0.7.0",
        description=(
            "Sistema experto para condiciones de almacenamiento poscosecha de maíz "
            "chulpi. Evalúa condiciones de almacenamiento; no certifica inocuidad, "
            "ausencia de micotoxinas ni aptitud para consumo."
        ),
        docs_url="/documentacion" if cfg.entorno != "produccion" else None,
        redoc_url=None,
    )

    if cfg.cors_origenes:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cfg.cors_origenes,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "PUT", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "If-Match", "If-None-Match", "Idempotency-Key"],
            expose_headers=["ETag", "X-Id-Solicitud"],
            max_age=600,
        )

    @app.middleware("http")
    async def _identificador_solicitud(
        request: Request, siguiente: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.id_solicitud = uuid.uuid4()
        respuesta = await siguiente(request)
        respuesta.headers["X-Id-Solicitud"] = str(request.state.id_solicitud)
        return respuesta

    registrar_manejadores(app)
    if cfg.auth_local_habilitada:
        from .local import enrutador
        app.include_router(enrutador)

    for modulo in (recursos, evaluacion, seguimiento, conocimiento, adquisicion):
        app.include_router(modulo.enrutador)

    @app.get("/salud", tags=["operacion"])
    def salud() -> dict[str, str]:
        return {"estado": "activo", "version": app.version}

    @app.get("/salud/bd", tags=["operacion"])
    def salud_bd() -> dict[str, str]:
        with obtener_motor().connect() as conexion:
            conexion.execute(sa.text("SELECT 1"))
        return {"estado": "conectado"}

    return app
