"""Autorización por propiedad y asignación, resuelta contra la base.

Criterios fijados en esta etapa, documentados en docs/SEGURIDAD.md:
- El productor accede a lo suyo: lotes propios y almacenes propios.
- El técnico accede a lo asignado, por almacén o por lote.
- ADMINISTRADOR no obtiene competencia técnica ni acceso a datos de producción
  por el hecho de ser administrador. La provisión de roles y asignaciones se
  realiza mediante el procedimiento administrativo documentado, no por la API.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy.orm import Session

from ..db.modelos import (
    Almacen,
    AsignacionAlmacen,
    AsignacionLote,
    Incidencia,
    Lote,
    Unidad,
    UsuarioRol,
)
from .identidad import Identidad


class AccesoDenegado(Exception):
    """Sin permiso sobre el recurso. Se traduce a 403."""


class RecursoInaccesible(Exception):
    """No existe o no es visible para quien pregunta. Se traduce a 404."""


@dataclass(frozen=True, slots=True)
class AmbitoUnidad:
    id_unidad: uuid.UUID
    id_lote: uuid.UUID
    id_almacen: uuid.UUID
    id_propietario_lote: uuid.UUID
    id_propietario_almacen: uuid.UUID
    revision_unidad: int
    revision_almacen: int


def cargar_roles(sesion: Session, id_usuario: uuid.UUID) -> frozenset[str]:
    filas = sesion.scalars(sa.select(UsuarioRol.rol).where(UsuarioRol.id_usuario == id_usuario))
    return frozenset(filas)


def _ambito(sesion: Session, id_unidad: uuid.UUID) -> AmbitoUnidad:
    fila = sesion.execute(
        sa.select(
            Unidad.id,
            Unidad.id_lote,
            Unidad.id_almacen,
            Lote.id_propietario,
            Almacen.id_propietario,
            Unidad.revision,
            Almacen.revision,
        )
        .join(Lote, Lote.id == Unidad.id_lote)
        .join(Almacen, Almacen.id == Unidad.id_almacen)
        .where(Unidad.id == id_unidad)
    ).first()
    if fila is None:
        raise RecursoInaccesible(str(id_unidad))
    return AmbitoUnidad(*fila)


def _tiene_asignacion(sesion: Session, identidad: Identidad, ambito: AmbitoUnidad) -> bool:
    if not identidad.es_tecnico:
        return False
    por_almacen = sa.select(sa.literal(1)).where(
        AsignacionAlmacen.id_tecnico == identidad.id,
        AsignacionAlmacen.id_almacen == ambito.id_almacen,
        AsignacionAlmacen.vigente.is_(True),
    )
    por_lote = sa.select(sa.literal(1)).where(
        AsignacionLote.id_tecnico == identidad.id,
        AsignacionLote.id_lote == ambito.id_lote,
        AsignacionLote.vigente.is_(True),
    )
    return sesion.execute(por_almacen.union_all(por_lote).limit(1)).first() is not None


def _es_propietario(identidad: Identidad, ambito: AmbitoUnidad) -> bool:
    return identidad.id in (ambito.id_propietario_lote, ambito.id_propietario_almacen)


def exigir_acceso_unidad(
    sesion: Session, identidad: Identidad, id_unidad: uuid.UUID, *, escritura: bool = False
) -> AmbitoUnidad:
    """Comprueba acceso y devuelve el ámbito con las revisiones vigentes.

    Se devuelve 404 y no 403 cuando el recurso no es visible, para no confirmar
    la existencia de datos ajenos.
    """
    ambito = _ambito(sesion, id_unidad)
    if _es_propietario(identidad, ambito) or _tiene_asignacion(sesion, identidad, ambito):
        return ambito
    raise RecursoInaccesible(str(id_unidad))


def exigir_tecnico_asignado(
    sesion: Session, identidad: Identidad, id_unidad: uuid.UUID
) -> AmbitoUnidad:
    """Para dictámenes, revisiones y resoluciones. Ser propietario no basta."""
    ambito = _ambito(sesion, id_unidad)
    if _tiene_asignacion(sesion, identidad, ambito):
        return ambito
    if _es_propietario(identidad, ambito):
        raise AccesoDenegado("la acción requiere un técnico asignado a la unidad")
    raise RecursoInaccesible(str(id_unidad))


def exigir_acceso_lote(
    sesion: Session, identidad: Identidad, id_lote: uuid.UUID, *, escritura: bool = False
) -> None:
    fila = sesion.execute(sa.select(Lote.id_propietario).where(Lote.id == id_lote)).first()
    if fila is None:
        raise RecursoInaccesible(str(id_lote))
    if fila[0] == identidad.id:
        return
    asignado = sesion.execute(
        sa.select(sa.literal(1)).where(
            AsignacionLote.id_tecnico == identidad.id,
            AsignacionLote.id_lote == id_lote,
            AsignacionLote.vigente.is_(True),
        )
    ).first()
    if asignado is not None and identidad.es_tecnico:
        return
    raise RecursoInaccesible(str(id_lote))


def exigir_acceso_almacen(
    sesion: Session, identidad: Identidad, id_almacen: uuid.UUID, *, escritura: bool = False
) -> None:
    fila = sesion.execute(sa.select(Almacen.id_propietario).where(Almacen.id == id_almacen)).first()
    if fila is None:
        raise RecursoInaccesible(str(id_almacen))
    if fila[0] == identidad.id:
        return
    asignado = sesion.execute(
        sa.select(sa.literal(1)).where(
            AsignacionAlmacen.id_tecnico == identidad.id,
            AsignacionAlmacen.id_almacen == id_almacen,
            AsignacionAlmacen.vigente.is_(True),
        )
    ).first()
    if asignado is not None and identidad.es_tecnico:
        return
    raise RecursoInaccesible(str(id_almacen))


def exigir_acceso_incidencia(
    sesion: Session, identidad: Identidad, id_incidencia: uuid.UUID, *, tecnico: bool = False
) -> AmbitoUnidad:
    fila = sesion.execute(
        sa.select(Incidencia.id_unidad).where(Incidencia.id == id_incidencia)
    ).first()
    if fila is None:
        raise RecursoInaccesible(str(id_incidencia))
    if tecnico:
        return exigir_tecnico_asignado(sesion, identidad, fila[0])
    return exigir_acceso_unidad(sesion, identidad, fila[0])
