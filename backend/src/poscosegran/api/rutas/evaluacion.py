"""Borradores, evaluaciones, historial y vigencia."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

import sqlalchemy as sa
from fastapi import APIRouter, Query, Response, status, HTTPException

from ...db.modelos import Almacen, Borrador, Evaluacion, Unidad, VersionConocimiento
from ...dominio import motor
from ...esquemas import contrato as api
from ...seguridad.dependencias import IdentidadDep, SesionDep
from ...seguridad.permisos import RecursoInaccesible, exigir_acceso_unidad
from ...servicios import auditoria, concurrencia, evaluaciones, observaciones, presentacion
from ...servicios import vigencia as servicio_vigencia
from .. import paginacion
from ..dependencias import ClaveIdempotencia, IfMatch, IfNoneMatch, completar, etiquetar, reservar

enrutador = APIRouter(prefix="/api/v1", tags=["evaluacion"])


def _version_activa(sesion: SesionDep) -> VersionConocimiento:
    version = sesion.scalar(
        sa.select(VersionConocimiento).where(VersionConocimiento.activa.is_(True))
    )
    if version is None:
        raise HTTPException(503,
            "no hay una versión de la base de conocimiento activa: cargue el catálogo "
            "antes de evaluar"
        )
    return version


@enrutador.get("/unidades/{id_unidad}/borrador", response_model=api.Borrador)
def obtener_borrador(
    id_unidad: uuid.UUID, sesion: SesionDep, identidad: IdentidadDep, respuesta: Response
) -> api.Borrador:
    exigir_acceso_unidad(sesion, identidad, id_unidad)
    fila = sesion.scalar(
        sa.select(Borrador).where(
            Borrador.id_unidad == id_unidad, Borrador.id_usuario == identidad.id
        )
    )
    if fila is None:
        raise RecursoInaccesible(str(id_unidad))
    etiquetar(respuesta, fila.revision)
    return api.Borrador(
        id=fila.id,
        id_unidad=fila.id_unidad,
        revision=fila.revision,
        contenido=api.EvaluacionEntrada.model_validate(fila.contenido),
        actualizado_en=fila.actualizado_en,
    )


@enrutador.put("/unidades/{id_unidad}/borrador", response_model=api.Borrador)
def guardar_borrador(
    id_unidad: uuid.UUID,
    entrada: api.EvaluacionEntrada,
    sesion: SesionDep,
    identidad: IdentidadDep,
    respuesta: Response,
    if_match: IfMatch = None,
    if_none_match: IfNoneMatch = None,
    idempotency_key: ClaveIdempotencia = None,
) -> api.Borrador:
    """Un borrador no autoriza nada ni invalida el resultado vigente.

    Comunicar un hallazgo adverso real exige enviarlo como evaluación o control.
    """
    repetida = reservar(sesion, identidad, idempotency_key, "PUT",
                        f"/unidades/{id_unidad}/borrador", entrada.model_dump(mode="json"))
    if repetida is not None and repetida.cuerpo is not None:
        salida = api.Borrador.model_validate(repetida.cuerpo)
        respuesta.status_code = repetida.estado_http
        etiquetar(respuesta, salida.revision)
        return salida
    exigir_acceso_unidad(sesion, identidad, id_unidad, escritura=True)
    fila = sesion.scalar(
        sa.select(Borrador)
        .where(Borrador.id_unidad == id_unidad, Borrador.id_usuario == identidad.id)
        .with_for_update()
    )

    if fila is None:
        if (if_none_match or "").strip() != "*":
            raise concurrencia.PrecondicionRequerida("crear un borrador exige If-None-Match: *")
        fila = Borrador(
            id_unidad=id_unidad,
            id_usuario=identidad.id,
            contenido=entrada.model_dump(mode="json"),
        )
        sesion.add(fila)
        sesion.flush()
        respuesta.status_code = status.HTTP_201_CREATED
    else:
        concurrencia.exigir_revision(fila.revision, concurrencia.revision_desde_if_match(if_match))
        fila.contenido = entrada.model_dump(mode="json")
        fila.revision += 1
        fila.actualizado_en = datetime.now(UTC)

    etiquetar(respuesta, fila.revision)
    salida = api.Borrador(
        id=fila.id,
        id_unidad=fila.id_unidad,
        revision=fila.revision,
        contenido=api.EvaluacionEntrada.model_validate(fila.contenido),
        actualizado_en=fila.actualizado_en,
    )
    completar(sesion, identidad, idempotency_key, respuesta.status_code or 200,
              fila.id, salida.model_dump(mode="json"))
    auditoria.registrar(sesion, identidad, accion="guardar_borrador", recurso_tipo="borrador",
                        recurso_id=fila.id, metodo="PUT", ruta=f"/unidades/{id_unidad}/borrador",
                        estado_http=respuesta.status_code or 200, revision_resultante=fila.revision,
                        resumen={})
    return salida



@enrutador.post(
    "/unidades/{id_unidad}/evaluaciones",
    response_model=api.ResultadoEvaluacion,
    status_code=status.HTTP_201_CREATED,
)
def evaluar(
    id_unidad: uuid.UUID,
    entrada: api.EvaluacionEntrada,
    sesion: SesionDep,
    identidad: IdentidadDep,
    idempotency_key: ClaveIdempotencia = None,
) -> api.ResultadoEvaluacion:
    """Emite una evaluación. SIN_CONCLUSION_AUTOMATICA es una respuesta exitosa."""
    repetida = reservar(
        sesion,
        identidad,
        idempotency_key,
        "POST",
        f"/unidades/{id_unidad}/evaluaciones",
        entrada.model_dump(mode="json"),
    )
    if repetida is not None and repetida.cuerpo is not None:
        return api.ResultadoEvaluacion.model_validate(repetida.cuerpo)

    ambito = exigir_acceso_unidad(sesion, identidad, id_unidad, escritura=True)
    concurrencia.exigir_revisiones_unidad(
        revision_unidad_vigente=ambito.revision_unidad,
        revision_almacen_vigente=ambito.revision_almacen,
        revision_unidad_recibida=entrada.revision_unidad,
        revision_almacen_recibida=entrada.revision_almacen,
    )

    unidad = sesion.get(Unidad, id_unidad, with_for_update=True)
    almacen = sesion.get(Almacen, ambito.id_almacen)
    assert unidad is not None and almacen is not None
    version = _version_activa(sesion)

    filas = [
        observaciones.a_fila(
            observacion, id_unidad=id_unidad, id_responsable=identidad.id
        )
        for observacion in entrada.observaciones
    ]

    # El reloj de la evaluación pertenece al servidor.
    ahora = datetime.now(UTC)
    instantanea, aplicadas = evaluaciones.construir_instantanea(
        sesion, unidad=unidad, almacen=almacen, entrada=entrada, filas_actuales=filas, ahora=ahora
    )
    resultado = motor.evaluar(instantanea)
    # Una nueva declaración no puede borrar consumo documentado anteriormente.
    from dataclasses import replace
    previa = sesion.get(Evaluacion, unidad.id_evaluacion_actual) if unidad.id_evaluacion_actual else None
    if previa and previa.vida_minima_documentada is not None and (resultado.calculos.vida_minima_documentada or 0) < previa.vida_minima_documentada:
        instantanea = replace(instantanea, historial=replace(instantanea.historial,
            vida_previa_documentada=previa.vida_minima_documentada, intervalos=()),
            datos_inconsistentes=(*instantanea.datos_inconsistentes, "vida_previa_menor_al_historial_persistido"))
        resultado = motor.evaluar(instantanea)

    unidad.revision += 1
    fila_evaluacion = evaluaciones.persistir(
        sesion,
        unidad=unidad,
        almacen=almacen,
        instantanea=instantanea,
        entrada=entrada,
        resultado=resultado,
        aplicadas=aplicadas,
        id_responsable=identidad.id,
        version=version,
    )
    evaluaciones.sincronizar_incidencias(sesion, id_unidad, resultado, fila_evaluacion.id)
    # La captura enviada queda en la evaluación inmutable. El borrador de este
    # usuario ya no debe reaparecer sobre una nueva inspección.
    sesion.execute(sa.delete(Borrador).where(
        Borrador.id_unidad == id_unidad, Borrador.id_usuario == identidad.id
    ))
    sesion.flush()

    salida = api.ResultadoEvaluacion(
        evaluacion=presentacion.evaluacion(sesion, fila_evaluacion),
        vigencia=servicio_vigencia.calcular(sesion, id_unidad),
    )
    auditoria.registrar(
        sesion, identidad, accion="crear_evaluacion", recurso_tipo="evaluacion",
        recurso_id=fila_evaluacion.id, metodo="POST",
        ruta=f"/unidades/{id_unidad}/evaluaciones", estado_http=201,
        revision_resultante=unidad.revision,
        resumen={
            "decision_final": resultado.decision_final,
            "rama_r30": resultado.rama_r30,
            "reglas_activadas": list(resultado.reglas_activadas),
        },
    )
    completar(
        sesion, identidad, idempotency_key, 201, fila_evaluacion.id, salida.model_dump(mode="json")
    )
    return salida


@enrutador.get("/evaluaciones/{id_evaluacion}", response_model=api.ResultadoEvaluacion)
def obtener_evaluacion(
    id_evaluacion: uuid.UUID, sesion: SesionDep, identidad: IdentidadDep
) -> api.ResultadoEvaluacion:
    fila = sesion.get(Evaluacion, id_evaluacion)
    if fila is None:
        raise RecursoInaccesible(str(id_evaluacion))
    exigir_acceso_unidad(sesion, identidad, fila.id_unidad)
    vigencia = servicio_vigencia.calcular(sesion, fila.id_unidad)
    if vigencia.id_evaluacion != fila.id:
        vigencia = vigencia.model_copy(update={"id_evaluacion": fila.id, "estado": "INVALIDADA",
            "causas": ["Existe una evaluación posterior para esta unidad."],
            "fecha_proximo_control": fila.fecha_proximo_control,
            "fecha_vencimiento_autorizacion": fila.fecha_vencimiento_autorizacion})
    return api.ResultadoEvaluacion(
        evaluacion=presentacion.evaluacion(sesion, fila),
        vigencia=vigencia,
    )


@enrutador.get(
    "/unidades/{id_unidad}/historial", response_model=api.Pagina[api.ResultadoEvaluacion]
)
def historial(
    id_unidad: uuid.UUID,
    sesion: SesionDep,
    identidad: IdentidadDep,
    cursor: str | None = None,
    limite: Annotated[int | None, Query(ge=1, le=paginacion.LIMITE_MAXIMO)] = None,
) -> api.Pagina[api.ResultadoEvaluacion]:
    exigir_acceso_unidad(sesion, identidad, id_unidad)
    tope = paginacion.limitar(limite)
    consulta = sa.select(Evaluacion).where(Evaluacion.id_unidad == id_unidad)
    posicion = paginacion.decodificar(cursor)
    if posicion:
        consulta = consulta.where(
            sa.tuple_(Evaluacion.fecha_evaluacion, Evaluacion.id) < sa.tuple_(*(sa.literal(v) for v in posicion))
        )
    filas = sesion.scalars(
        consulta.order_by(Evaluacion.fecha_evaluacion.desc(), Evaluacion.id.desc()).limit(tope + 1)
    ).all()
    siguiente = (
        paginacion.codificar(filas[tope - 1].fecha_evaluacion, filas[tope - 1].id)
        if len(filas) > tope
        else None
    )
    # La vigencia es la de la unidad hoy; las evaluaciones antiguas siguen siendo
    # historia, no autorizaciones paralelas.
    actual = servicio_vigencia.calcular(sesion, id_unidad)
    return api.Pagina(
        items=[
            api.ResultadoEvaluacion(
                evaluacion=presentacion.evaluacion(sesion, fila),
                vigencia=actual if fila.id == actual.id_evaluacion else api.Vigencia(
                    id_unidad=id_unidad,
                    id_evaluacion=fila.id,
                    estado="INVALIDADA",
                    consultada_en=actual.consultada_en,
                    fecha_proximo_control=fila.fecha_proximo_control,
                    fecha_vencimiento_autorizacion=fila.fecha_vencimiento_autorizacion,
                    causas=["Existe una evaluación posterior para esta unidad."],
                ),
            )
            for fila in filas[:tope]
        ],
        siguiente_cursor=siguiente,
    )


@enrutador.get("/unidades/{id_unidad}/vigencia", response_model=api.Vigencia)
def consultar_vigencia(
    id_unidad: uuid.UUID, sesion: SesionDep, identidad: IdentidadDep
) -> api.Vigencia:
    exigir_acceso_unidad(sesion, identidad, id_unidad)
    return servicio_vigencia.calcular(sesion, id_unidad)
