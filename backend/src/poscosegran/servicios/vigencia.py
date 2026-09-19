"""Vigencia consultada, no almacenada.

La decisión histórica no cambia; lo que cambia es si sigue autorizando. Se
calcula con el reloj del servidor en cada consulta y antes de cualquier admisión.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.orm import Session

from ..db.modelos import Evaluacion, Evento, Incidencia, Unidad
from ..esquemas.contrato import Vigencia

AUTORIZADAS = {"AUTORIZAR_ALMACENAMIENTO", "AUTORIZAR_CON_MONITOREO"}


def calcular(sesion: Session, id_unidad: uuid.UUID) -> Vigencia:
    ahora = datetime.now(UTC)
    unidad = sesion.get(Unidad, id_unidad)
    if unidad is None or unidad.id_evaluacion_actual is None:
        return Vigencia(
            id_unidad=id_unidad,
            id_evaluacion=None,
            estado="SIN_EVALUACION",
            consultada_en=ahora,
            fecha_proximo_control=None,
            fecha_vencimiento_autorizacion=None,
            causas=["La unidad no tiene ninguna evaluación registrada."],
        )

    evaluacion = sesion.get(Evaluacion, unidad.id_evaluacion_actual)
    assert evaluacion is not None
    causas: list[str] = []

    if evaluacion.decision_final not in AUTORIZADAS:
        return Vigencia(
            id_unidad=id_unidad,
            id_evaluacion=evaluacion.id,
            estado="NO_AUTORIZADO",
            consultada_en=ahora,
            fecha_proximo_control=evaluacion.fecha_proximo_control,
            fecha_vencimiento_autorizacion=None,
            causas=[f"La última evaluación resolvió {evaluacion.decision_final}."],
        )

    # Un episodio abierto o un evento posterior invalidan una autorización previa.
    abiertas = sesion.scalars(
        sa.select(Incidencia.tipo).where(
            Incidencia.id_unidad == id_unidad,
            Incidencia.estado == "ABIERTA",

        )
    ).all()
    causas.extend(f"Incidencia {tipo} abierta después de la evaluación." for tipo in abiertas)

    eventos = sesion.scalars(
        sa.select(Evento.tipo).where(
            Evento.id_unidad == id_unidad, Evento.creado_en > evaluacion.fecha_evaluacion
        )
    ).all()
    causas.extend(f"Evento {tipo} posterior a la evaluación." for tipo in eventos)

    if evaluacion.revision_almacen_usada != _revision_almacen(sesion, evaluacion.id_almacen):
        causas.append("El almacén cambió después de la evaluación.")
    if evaluacion.revision_unidad_usada != unidad.revision:
        causas.append("La unidad cambió después de la evaluación.")

    if causas:
        return Vigencia(
            id_unidad=id_unidad,
            id_evaluacion=evaluacion.id,
            estado="INVALIDADA",
            consultada_en=ahora,
            fecha_proximo_control=evaluacion.fecha_proximo_control,
            fecha_vencimiento_autorizacion=evaluacion.fecha_vencimiento_autorizacion,
            causas=causas,
        )

    vencimiento = evaluacion.fecha_vencimiento_autorizacion
    if vencimiento is not None and ahora >= vencimiento:
        return Vigencia(
            id_unidad=id_unidad,
            id_evaluacion=evaluacion.id,
            estado="VENCIDA",
            consultada_en=ahora,
            fecha_proximo_control=evaluacion.fecha_proximo_control,
            fecha_vencimiento_autorizacion=vencimiento,
            causas=["La autorización superó su fecha de vencimiento."],
        )

    return Vigencia(
        id_unidad=id_unidad,
        id_evaluacion=evaluacion.id,
        estado="VIGENTE",
        consultada_en=ahora,
        fecha_proximo_control=evaluacion.fecha_proximo_control,
        fecha_vencimiento_autorizacion=vencimiento,
        causas=[],
    )


def _revision_almacen(sesion: Session, id_almacen: uuid.UUID) -> int:
    from ..db.modelos import Almacen

    return sesion.scalar(sa.select(Almacen.revision).where(Almacen.id == id_almacen)) or 0
