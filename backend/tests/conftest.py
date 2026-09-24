"""Configuración de pruebas.

Las pruebas marcadas con @pytest.mark.bd exigen una base PostgreSQL migrada en
POSCOSEGRAN_BD_URL_PRUEBAS. Sin esa variable se omiten: no se simula PostgreSQL
con SQLite, porque los disparadores, los índices parciales y los arrays no se
comportan igual y una prueba que pasa en SQLite no demuestra nada aquí.

Omitirlas es aceptable en una máquina de desarrollo, pero no en integración
continua: ahí una suite que "pasa" porque no hay base es exactamente el fallo que
no debe poder ocultarse. Con POSCOSEGRAN_EXIGIR_BD=1 la ausencia de la variable
detiene la sesión en lugar de omitir.
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


def _exige_bd() -> bool:
    return os.environ.get("POSCOSEGRAN_EXIGIR_BD", "").strip().lower() in {"1", "true", "si", "yes"}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """En CI, una prueba de integración omitida por falta de base es un fallo."""
    if not _exige_bd() or os.environ.get("POSCOSEGRAN_BD_URL_PRUEBAS"):
        return
    marcadas = [item.nodeid for item in items if item.get_closest_marker("bd")]
    if marcadas:
        raise pytest.UsageError(
            f"POSCOSEGRAN_EXIGIR_BD está activo y {len(marcadas)} pruebas marcadas 'bd' se "
            "omitirían: defina POSCOSEGRAN_BD_URL_PRUEBAS con una base PostgreSQL migrada."
        )


@pytest.fixture(scope="session")
def url_bd() -> str:
    url = os.environ.get("POSCOSEGRAN_BD_URL_PRUEBAS")
    if not url:
        if _exige_bd():
            pytest.fail("POSCOSEGRAN_BD_URL_PRUEBAS no está definida y POSCOSEGRAN_EXIGIR_BD lo exige")
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
    cargar(Path(__file__).parents[2] / "knowledge", activar=True, notas=None)
    users = {}
    # Dos ingenieros del conocimiento: la separación de funciones en adquisición exige
    # que quien propone una versión y quien la activa sean identidades distintas.
    cuentas = {
        "PRODUCTOR": "PRODUCTOR",
        "TECNICO": "TECNICO",
        "ADMINISTRADOR": "ADMINISTRADOR",
        "AJENO": "PRODUCTOR",
        "INGENIERO": "INGENIERO_CONOCIMIENTO",
        "REVISOR": "INGENIERO_CONOCIMIENTO",
    }
    with Session(create_engine(url_bd)) as session, session.begin():
        for cuenta, rol in cuentas.items():
            usuario = Usuario(id=uuid.uuid4(), nombre=cuenta)
            session.add(usuario)
            session.flush()
            session.add(UsuarioRol(id_usuario=usuario.id, rol=rol, otorgado_por="pytest"))
            users[cuenta] = usuario.id
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

