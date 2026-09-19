"""Configuración de pruebas.

Las pruebas marcadas con @pytest.mark.bd exigen una base PostgreSQL migrada en
POSCOSEGRAN_BD_URL_PRUEBAS. Sin esa variable se omiten: no se simula PostgreSQL
con SQLite, porque los disparadores, los índices parciales y los arrays no se
comportan igual y una prueba que pasa en SQLite no demuestra nada aquí.
"""

from __future__ import annotations

import os

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from poscosegran.db.modelos import Usuario, UsuarioRol

import pytest


@pytest.fixture(scope="session")
def url_bd() -> str:
    url = os.environ.get("POSCOSEGRAN_BD_URL_PRUEBAS")
    if not url:
        pytest.skip("POSCOSEGRAN_BD_URL_PRUEBAS no está definida")
    return url


@pytest.fixture(scope="session")
def motor(url_bd: str):  # type: ignore[no-untyped-def]
    from sqlalchemy import create_engine

    motor = create_engine(url_bd, future=True)
    yield motor
    motor.dispose()


@pytest.fixture
def configuracion_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSCOSEGRAN_ENTORNO", "pruebas")
    monkeypatch.setenv("POSCOSEGRAN_BD_URL_APP", "postgresql+psycopg://x:y@localhost/z")
    monkeypatch.setenv("POSCOSEGRAN_JWT_MODO", "SECRETO_COMPARTIDO")
    monkeypatch.setenv("POSCOSEGRAN_JWT_ALGORITMOS", "HS256")
    monkeypatch.setenv("POSCOSEGRAN_JWT_SECRETO", "s" * 48)
    monkeypatch.setenv("POSCOSEGRAN_JWT_EMISOR", "https://emisor.ejemplo/auth/v1")
    monkeypatch.setenv("POSCOSEGRAN_JWT_AUDIENCIA", "authenticated")


@pytest.fixture
def api_real(url_bd, monkeypatch):
    from poscosegran.config import obtener_configuracion
    from poscosegran.db import sesion as db
    from poscosegran.seguridad import dependencias as seguridad
    monkeypatch.setenv("POSCOSEGRAN_AUTH_LOCAL_HABILITADA", "false")
    monkeypatch.setenv("POSCOSEGRAN_ENTORNO", "pruebas")
    monkeypatch.setenv("POSCOSEGRAN_BD_URL_APP", url_bd)
    monkeypatch.setenv("POSCOSEGRAN_JWT_MODO", "SECRETO_COMPARTIDO")
    monkeypatch.setenv("POSCOSEGRAN_JWT_ALGORITMOS", "HS256")
    monkeypatch.setenv("POSCOSEGRAN_JWT_SECRETO", "pruebas-locales-" * 4)
    monkeypatch.setenv("POSCOSEGRAN_JWT_EMISOR", "http://localhost/auth/v1")
    monkeypatch.setenv("POSCOSEGRAN_LIMITE_PETICIONES_POR_MINUTO", "10000")
    monkeypatch.setenv("POSCOSEGRAN_LIMITE_PETICIONES_ESCRITURA_POR_MINUTO", "10000")
    obtener_configuracion.cache_clear()
    if db._motor:
        db._motor.dispose()
    db._motor = db._fabrica = None
    seguridad._verificador = seguridad._limitador_lectura = seguridad._limitador_escritura = None
    from poscosegran.api.app import crear_app
    from poscosegran.conocimiento.cargar import cargar
    cargar(Path(__file__).parents[2] / "knowledge/catalogo.yaml", activar=True, notas=None)
    users = {}
    with Session(create_engine(url_bd)) as session, session.begin():
        for rol in ("PRODUCTOR", "TECNICO", "ADMINISTRADOR", "AJENO"):
            usuario = Usuario(id=uuid.uuid4(), nombre=rol)
            session.add(usuario)
            session.flush()
            session.add(UsuarioRol(id_usuario=usuario.id, rol="PRODUCTOR" if rol == "AJENO" else rol, otorgado_por="pytest"))
            users[rol] = usuario.id
    client = TestClient(crear_app(), raise_server_exceptions=False)

    def headers(rol="PRODUCTOR", key=None):
        now = datetime.now(UTC)
        token = jwt.encode({"sub": str(users[rol]), "iss": "http://localhost/auth/v1",
                            "aud": "authenticated", "iat": now, "exp": now + timedelta(hours=1)},
                           "pruebas-locales-" * 4, algorithm="HS256")
        return {"Authorization": f"Bearer {token}", "Idempotency-Key": key or str(uuid.uuid4())}
    client.headers.update(headers())
    yield client, headers, users
    client.close()

