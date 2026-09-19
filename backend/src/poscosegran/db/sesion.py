"""Motor, sesiones y unidad de trabajo.

La conexión usa siempre la credencial de aplicación. La de migraciones no se
carga aquí: vive en Alembic y no debe estar disponible en tiempo de ejecución.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import obtener_configuracion
from .base import ESQUEMA

_motor: Engine | None = None
_fabrica: sessionmaker[Session] | None = None


def obtener_motor() -> Engine:
    global _motor
    if _motor is None:
        cfg = obtener_configuracion()
        _motor = create_engine(
            cfg.bd_url_app,
            echo=cfg.bd_eco_sql,
            pool_size=cfg.bd_pool_tamano,
            max_overflow=cfg.bd_pool_desborde,
            pool_pre_ping=True,
            future=True,
        )

        @event.listens_for(_motor, "connect")
        def _fijar_ruta_busqueda(dbapi_conn, _registro) -> None:  # type: ignore[no-untyped-def]
            with dbapi_conn.cursor() as cur:
                cur.execute(f"SET search_path TO {ESQUEMA}")

    return _motor


def obtener_fabrica() -> sessionmaker[Session]:
    global _fabrica
    if _fabrica is None:
        _fabrica = sessionmaker(bind=obtener_motor(), expire_on_commit=False, future=True)
    return _fabrica


@contextmanager
def unidad_de_trabajo(id_usuario: uuid.UUID | None = None) -> Iterator[Session]:
    """Una transacción por operación: o se guarda todo, o no se guarda nada.

    Si el usuario es conocido se publica en una variable de sesión para que las
    políticas RLS opcionales (sql/rls_opcional.sql) puedan leerlo. Esto es
    defensa en profundidad: la autorización real la aplica la capa de permisos,
    porque el pool comparte conexiones entre usuarios y una política que
    dependa solo de la conexión no identifica a nadie por sí misma.
    """
    sesion = obtener_fabrica()()
    try:
        if id_usuario is not None:
            sesion.execute(
                text("SELECT set_config('poscosegran.id_usuario', :valor, true)"),
                {"valor": str(id_usuario)},
            )
        yield sesion
        sesion.commit()
    except Exception:
        sesion.rollback()
        raise
    finally:
        sesion.close()
