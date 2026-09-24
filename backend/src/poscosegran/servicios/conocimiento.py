"""Versión de la base de conocimiento con que se evalúa.

El motor nunca lee archivos en producción: evalúa con el contenido de la versión
activa guardada en la base de datos. Las bases construidas se memorizan por id de
versión, que es inmutable en su contenido.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..db.modelos import Fuente, Regla, VersionConocimiento
from ..sistema_experto.base_conocimiento import BaseConocimiento, desde_contenido
from ..sistema_experto.motor import VERSION_MOTOR

_bases: dict[uuid.UUID, BaseConocimiento] = {}

# Candado de transacción con el que se serializan las activaciones. Dos peticiones
# simultáneas no pueden medir el impacto contra la misma versión vigente y dejar dos
# activas: la segunda espera y vuelve a leer el estado ya actualizado.
CANDADO_ACTIVACION = 0x504F5343


def bloquear_activacion(sesion: Session) -> None:
    """Toma el candado de activación hasta el final de la transacción."""
    sesion.execute(sa.select(sa.func.pg_advisory_xact_lock(CANDADO_ACTIVACION)))


def version_activa(sesion: Session) -> VersionConocimiento:
    version = sesion.scalar(sa.select(VersionConocimiento).where(VersionConocimiento.activa.is_(True)))
    if version is None:
        raise HTTPException(
            503,
            "no hay una versión de la base de conocimiento activa: cárguela con "
            "python -m poscosegran.conocimiento.cargar --activar antes de evaluar",
        )
    return version


def base_de(version: VersionConocimiento) -> BaseConocimiento:
    if version.contenido is None:
        raise HTTPException(
            503,
            f"la versión {version.version_base}/{version.version_parametros} se registró antes de que la "
            "base se guardara como datos: vuelva a cargarla con python -m poscosegran.conocimiento.cargar --activar",
        )
    if version.id not in _bases:
        _bases[version.id] = desde_contenido(version.contenido)
    return _bases[version.id]


def base_activa(sesion: Session) -> tuple[VersionConocimiento, BaseConocimiento]:
    version = version_activa(sesion)
    return version, base_de(version)


def registrar(
    sesion: Session,
    *,
    base: BaseConocimiento,
    contenido: dict[str, Any],
    estado: str,
    motivo: str | None,
    ruta_archivo: str,
    id_origen: uuid.UUID | None = None,
    id_responsable: uuid.UUID | None = None,
) -> VersionConocimiento:
    """Registra una versión con su catálogo documental. No la activa."""
    version = VersionConocimiento(
        version_base=base.version_base,
        version_parametros=base.version_parametros,
        version_motor=VERSION_MOTOR,
        hash_contenido=base.hash,
        ruta_archivo=ruta_archivo,
        notas=motivo,
        activa=False,
        contenido=contenido,
        estado=estado,
        motivo=motivo,
        id_version_origen=id_origen,
        cargada_por=id_responsable,
    )
    sesion.add(version)
    sesion.flush()

    documental = base.documental
    for fuente in documental.get("fuentes", []):
        sesion.add(Fuente(id_version=version.id, codigo=fuente["id"], referencia_markdown=fuente["referencia_markdown"]))
    for es_rama, clave in ((False, "reglas"), (True, "ramas_r30")):
        for orden, regla in enumerate(documental.get(clave, []), start=1):
            sesion.add(
                Regla(
                    id_version=version.id,
                    codigo=regla["id"],
                    es_rama=es_rama,
                    orden=orden,
                    antecedente=regla["antecedente"],
                    consecuente=regla["consecuente"],
                    accion=regla["accion"],
                    fundamento_markdown=regla["fundamento_markdown"],
                )
            )
    sesion.flush()
    return version


def activar(sesion: Session, version: VersionConocimiento, id_responsable: uuid.UUID | None) -> None:
    """Deja una sola versión activa. Las evaluaciones emitidas no se recalculan.

    La versión que deja de estar vigente pasa a SUPERADA: su estado dice por sí solo
    que ya no manda, sin tener que cruzarlo con `activa`.
    """
    sesion.execute(
        sa.update(VersionConocimiento)
        .where(VersionConocimiento.activa.is_(True))
        .values(activa=False, estado="SUPERADA")
    )
    sesion.flush()
    version.activa = True
    version.estado = "ACTIVADA"
    version.activada_en = datetime.now(UTC)
    version.activada_por = id_responsable
    sesion.flush()


def descartar(sesion: Session, version: VersionConocimiento, motivo: str) -> None:
    """Cierra una propuesta que no se va a activar. No toca ninguna otra versión."""
    version.estado = "DESCARTADA"
    version.motivo = motivo
    sesion.flush()
