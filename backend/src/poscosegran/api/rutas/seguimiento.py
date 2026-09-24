"""Controles, planes, dictámenes, incidencias, resoluciones y admisiones."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated, Any
from sqlalchemy.orm import Session

import sqlalchemy as sa
from fastapi import APIRouter, Query, status, HTTPException

from ...db.modelos import (
    Admision,
    Unidad,
    Almacen,
    Evento,
    Control,
    Dictamen,
    Evaluacion,
    Incidencia,
    Plan,
    Resolucion,
    RevisionIncidencia,
)
from ...esquemas import contrato as api
from ...seguridad.dependencias import IdentidadDep, SesionDep
from ...seguridad.permisos import (
    RecursoInaccesible,
    exigir_acceso_incidencia,
    exigir_acceso_unidad,
    exigir_tecnico_asignado,
)
from ...servicios import auditoria, concurrencia, observaciones, vigencia as servicio_vigencia
from .. import paginacion
from ..dependencias import ClaveIdempotencia, completar, reservar

enrutador = APIRouter(prefix="/api/v1", tags=["seguimiento"])

REQUISITOS_CONTROL: dict[str, tuple[str, ...]] = {
    "INGRESO": (
        "humedad_grano", "metodo_humedad", "temperatura_grano", "recipiente_limpio",
        "recipiente_seco", "material_grado_alimentario", "recipiente_resistente",
        "cierre_seguro", "distancia_piso", "distancia_pared", "distancia_techo",
        "insectos_vivos", "moho_visible", "granos_defectuosos",
    ),
    "GRANO": ("humedad_grano", "temperatura_grano", "insectos_vivos", "moho_visible"),
    "EXTERIOR": ("sello_integro", "cierre_seguro", "perforacion_barrera", "bolsa_roida"),
    "ALMACEN": (
        "temperatura_almacen", "hr_almacen", "limpieza_diaria",
        "polvo_humo_gases_vapores", "quimicos_combustibles_en_almacen",
    ),
}


def _revisiones(sesion: SesionDep, identidad: IdentidadDep, id_unidad: uuid.UUID, entrada: api.Revisiones):  
    ambito = exigir_acceso_unidad(sesion, identidad, id_unidad, escritura=True)
    concurrencia.exigir_revisiones_unidad(
        revision_unidad_vigente=ambito.revision_unidad,
        revision_almacen_vigente=ambito.revision_almacen,
        revision_unidad_recibida=entrada.revision_unidad,
        revision_almacen_recibida=entrada.revision_almacen,
    )
    fila = sesion.get(Unidad, id_unidad)
    assert fila is not None
    fila.revision += 1
    fila.actualizado_en = datetime.now(UTC)
    return ambito


def _pagina(sesion: Session, consulta: Any, orden_fecha: Any, orden_id: Any, cursor: str | None, limite: int | None) -> tuple[list[Any], str | None]:
    tope = paginacion.limitar(limite)
    posicion = paginacion.decodificar(cursor)
    if posicion:
        consulta = consulta.where(sa.tuple_(orden_fecha, orden_id) < sa.tuple_(*(sa.literal(v) for v in posicion)))
    filas = sesion.scalars(consulta.order_by(orden_fecha.desc(), orden_id.desc()).limit(tope + 1)).all()
    siguiente = (
        paginacion.codificar(getattr(filas[tope - 1], orden_fecha.key), filas[tope - 1].id)
        if len(filas) > tope
        else None
    )
    return list(filas[:tope]), siguiente


@enrutador.get("/unidades/{id_unidad}/controles", response_model=api.Pagina[api.Control])
def listar_controles(
    id_unidad: uuid.UUID,
    sesion: SesionDep,
    identidad: IdentidadDep,
    cursor: str | None = None,
    limite: Annotated[int | None, Query(ge=1, le=paginacion.LIMITE_MAXIMO)] = None,
) -> api.Pagina[api.Control]:
    exigir_acceso_unidad(sesion, identidad, id_unidad)
    filas, siguiente = _pagina(
        sesion,
        sa.select(Control).where(Control.id_unidad == id_unidad),
        Control.fecha, Control.id, cursor, limite,
    )
    return api.Pagina.model_validate(dict(items=[_control(f) for f in filas], siguiente_cursor=siguiente))


def _control(fila: Control) -> api.Control:
    return api.Control.model_validate(dict(
        id=fila.id, id_unidad=fila.id_unidad, tipo=fila.tipo, fecha=fila.fecha,
        completo=fila.completo, campos_pendientes=list(fila.campos_pendientes),
        id_responsable=fila.id_responsable, evidencia=fila.evidencia,
    ))


@enrutador.post(
    "/unidades/{id_unidad}/controles", response_model=api.Control,
    status_code=status.HTTP_201_CREATED,
)
def registrar_control(
    id_unidad: uuid.UUID,
    entrada: api.ControlEntrada,
    sesion: SesionDep,
    identidad: IdentidadDep,
    idempotency_key: ClaveIdempotencia = None,
) -> api.Control:
    """'completo' lo decide el servidor comparando requisitos y observaciones."""
    repetida = reservar(
        sesion, identidad, idempotency_key, "POST", f"/unidades/{id_unidad}/controles",
        entrada.model_dump(mode="json"),
    )
    if repetida is not None and repetida.cuerpo is not None:
        return api.Control.model_validate(repetida.cuerpo)

    if entrada.fecha > datetime.now(UTC):
        raise HTTPException(422, "Un control no puede estar en el futuro")
    _revisiones(sesion, identidad, id_unidad, entrada)
    aportados = {
        observacion.campo
        for observacion in entrada.observaciones
        if observacion.captura == "APORTADO" and observaciones.validar(observacion)[0] == "VALIDO"
    }
    requisitos = REQUISITOS_CONTROL[entrada.tipo]
    pendientes = [campo for campo in requisitos if campo not in aportados]

    fila = Control(
        id_unidad=id_unidad,
        tipo=entrada.tipo,
        fecha=entrada.fecha,
        completo=not pendientes,
        campos_pendientes=pendientes,
        evidencia=entrada.evidencia,
        id_responsable=identidad.id,
    )
    sesion.add(fila)
    sesion.flush()
    filas_obs = [observaciones.a_fila(observacion, id_unidad=id_unidad,
                  id_responsable=identidad.id, id_control=fila.id)
                  for observacion in entrada.observaciones]
    from ...servicios import evaluaciones
    from ...dominio import motor
    unidad = sesion.get(Unidad, id_unidad)
    assert unidad is not None
    almacen = sesion.get(Almacen, unidad.id_almacen)
    assert almacen is not None
    comando = api.EvaluacionEntrada(revision_unidad=unidad.revision,
        revision_almacen=almacen.revision, fase="SEGUIMIENTO",
        observaciones=entrada.observaciones,
        historial=api.HistorialEntrada(fecha_inicio_historial=None, vida_previa_documentada=None,
                                      evidencia_vida_previa=None, intervalos_historial=[]),
        dias_previstos_restantes=None, fecha_salida_prevista=None)
    instantanea, _ = evaluaciones.construir_instantanea(sesion, unidad=unidad, almacen=almacen,
        entrada=comando, filas_actuales=filas_obs, ahora=datetime.now(UTC))
    from ...servicios import conocimiento as servicio_conocimiento
    _, base = servicio_conocimiento.base_activa(sesion)
    evaluaciones.sincronizar_incidencias(sesion, id_unidad, motor.evaluar(instantanea, base), None)
    sesion.add_all(filas_obs)

    salida = _control(fila)
    auditoria.registrar(
        sesion, identidad, accion="registrar_control", recurso_tipo="control", recurso_id=fila.id,
        metodo="POST", ruta=f"/unidades/{id_unidad}/controles", estado_http=201,
        resumen={"tipo": fila.tipo, "completo": fila.completo},
    )
    completar(sesion, identidad, idempotency_key, 201, fila.id, salida.model_dump(mode="json"))
    return salida


@enrutador.get("/unidades/{id_unidad}/planes", response_model=api.Pagina[api.Plan])
def listar_planes(
    id_unidad: uuid.UUID,
    sesion: SesionDep,
    identidad: IdentidadDep,
    cursor: str | None = None,
    limite: Annotated[int | None, Query(ge=1, le=paginacion.LIMITE_MAXIMO)] = None,
) -> api.Pagina[api.Plan]:
    exigir_acceso_unidad(sesion, identidad, id_unidad)
    filas, siguiente = _pagina(
        sesion, sa.select(Plan).where(Plan.id_unidad == id_unidad),
        Plan.creado_en, Plan.id, cursor, limite,
    )
    return api.Pagina.model_validate(dict(items=[_plan(f) for f in filas], siguiente_cursor=siguiente))


def _plan(fila: Plan) -> api.Plan:
    return api.Plan.model_validate(dict(
        id=fila.id, id_unidad=fila.id_unidad, fecha_proximo_control=fila.fecha_proximo_control,
        intervalo_dias=fila.intervalo_dias, fecha_salida_prevista=fila.fecha_salida_prevista,
        actividades=fila.actividades, vigente=fila.vigente, id_responsable=fila.id_responsable,
    ))


@enrutador.post(
    "/unidades/{id_unidad}/planes", response_model=api.Plan, status_code=status.HTTP_201_CREATED
)
def registrar_plan(
    id_unidad: uuid.UUID,
    entrada: api.PlanEntrada,
    sesion: SesionDep,
    identidad: IdentidadDep,
    idempotency_key: ClaveIdempotencia = None,
) -> api.Plan:
    """Registrar un plan no equivale a cumplirlo: solo deja constancia de su existencia."""
    repetida = reservar(
        sesion, identidad, idempotency_key, "POST", f"/unidades/{id_unidad}/planes",
        entrada.model_dump(mode="json"),
    )
    if repetida is not None and repetida.cuerpo is not None:
        return api.Plan.model_validate(repetida.cuerpo)

    if entrada.fecha_proximo_control <= datetime.now(UTC) or entrada.fecha_salida_prevista < entrada.fecha_proximo_control:
        raise HTTPException(422, "El plan requiere control futuro antes de la salida")
    _revisiones(sesion, identidad, id_unidad, entrada)
    sesion.execute(
        sa.update(Plan).where(Plan.id_unidad == id_unidad, Plan.vigente.is_(True)).values(vigente=False)
    )
    fila = Plan(
        id_unidad=id_unidad,
        fecha_proximo_control=entrada.fecha_proximo_control,
        intervalo_dias=entrada.intervalo_dias,
        fecha_salida_prevista=entrada.fecha_salida_prevista,
        actividades=entrada.actividades,
        vigente=True,
        id_responsable=identidad.id,
    )
    sesion.add(fila)
    sesion.flush()
    salida = _plan(fila)
    auditoria.registrar(
        sesion, identidad, accion="registrar_plan", recurso_tipo="plan", recurso_id=fila.id,
        metodo="POST", ruta=f"/unidades/{id_unidad}/planes", estado_http=201,
        resumen={"intervalo_dias": fila.intervalo_dias},
    )
    completar(sesion, identidad, idempotency_key, 201, fila.id, salida.model_dump(mode="json"))
    return salida


@enrutador.get("/unidades/{id_unidad}/dictamenes", response_model=api.Pagina[api.Dictamen])
def listar_dictamenes(
    id_unidad: uuid.UUID,
    sesion: SesionDep,
    identidad: IdentidadDep,
    cursor: str | None = None,
    limite: Annotated[int | None, Query(ge=1, le=paginacion.LIMITE_MAXIMO)] = None,
) -> api.Pagina[api.Dictamen]:
    exigir_acceso_unidad(sesion, identidad, id_unidad)
    filas, siguiente = _pagina(
        sesion, sa.select(Dictamen).where(Dictamen.id_unidad == id_unidad),
        Dictamen.emitido_en, Dictamen.id, cursor, limite,
    )
    ahora = datetime.now(UTC)
    return api.Pagina.model_validate(dict(items=[_dictamen(f, ahora) for f in filas], siguiente_cursor=siguiente))


def _dictamen(fila: Dictamen, ahora: datetime) -> api.Dictamen:
    return api.Dictamen.model_validate(dict(
        id=fila.id, id_unidad=fila.id_unidad, humedad_min=float(fila.humedad_min),
        humedad_max=float(fila.humedad_max), plazo_maximo_dias=fila.plazo_maximo_dias,
        emitido_en=fila.emitido_en, vence_en=fila.vence_en, condiciones=fila.condiciones,
        evidencia=fila.evidencia, id_tecnico=fila.id_tecnico,
        vigente=fila.anulado_en is None and fila.vence_en > ahora,
    ))


@enrutador.post(
    "/unidades/{id_unidad}/dictamenes", response_model=api.Dictamen,
    status_code=status.HTTP_201_CREATED,
)
def emitir_dictamen(
    id_unidad: uuid.UUID,
    entrada: api.DictamenEntrada,
    sesion: SesionDep,
    identidad: IdentidadDep,
    idempotency_key: ClaveIdempotencia = None,
) -> api.Dictamen:
    """Exige técnico asignado: ser propietario de la unidad no habilita esta acción."""
    repetida = reservar(
        sesion, identidad, idempotency_key, "POST", f"/unidades/{id_unidad}/dictamenes",
        entrada.model_dump(mode="json"),
    )
    if repetida is not None and repetida.cuerpo is not None:
        return api.Dictamen.model_validate(repetida.cuerpo)

    ambito = exigir_tecnico_asignado(sesion, identidad, id_unidad)
    concurrencia.exigir_revisiones_unidad(
        revision_unidad_vigente=ambito.revision_unidad,
        revision_almacen_vigente=ambito.revision_almacen,
        revision_unidad_recibida=entrada.revision_unidad,
        revision_almacen_recibida=entrada.revision_almacen,
    )
    if entrada.vence_en <= datetime.now(UTC):
        raise HTTPException(422, "El dictamen debe tener vencimiento futuro")
    unidad = sesion.get(Unidad, id_unidad)
    assert unidad is not None
    unidad.revision += 1
    fila = Dictamen(
        id_unidad=id_unidad,
        humedad_min=entrada.humedad_min,
        humedad_max=entrada.humedad_max,
        plazo_maximo_dias=entrada.plazo_maximo_dias,
        vence_en=entrada.vence_en,
        condiciones=entrada.condiciones,
        evidencia=entrada.evidencia,
        id_tecnico=identidad.id,
    )
    sesion.add(fila)
    sesion.flush()
    salida = _dictamen(fila, datetime.now(UTC))
    auditoria.registrar(
        sesion, identidad, accion="emitir_dictamen", recurso_tipo="dictamen", recurso_id=fila.id,
        metodo="POST", ruta=f"/unidades/{id_unidad}/dictamenes", estado_http=201,
        resumen={"banda": [float(fila.humedad_min), float(fila.humedad_max)]},
    )
    completar(sesion, identidad, idempotency_key, 201, fila.id, salida.model_dump(mode="json"))
    return salida


def _incidencia(fila: Incidencia) -> api.Incidencia:
    return api.Incidencia.model_validate(dict(
        id=fila.id, id_unidad=fila.id_unidad, revision=fila.revision, tipo=fila.tipo,
        estado=fila.estado, causas=list(fila.causas), creada_en=fila.creada_en,
        cerrada_en=fila.cerrada_en,
    ))


@enrutador.get("/unidades/{id_unidad}/incidencias", response_model=api.Pagina[api.Incidencia])
def listar_incidencias(
    id_unidad: uuid.UUID,
    sesion: SesionDep,
    identidad: IdentidadDep,
    cursor: str | None = None,
    limite: Annotated[int | None, Query(ge=1, le=paginacion.LIMITE_MAXIMO)] = None,
    estado: Annotated[str | None, Query(pattern="^(ABIERTA|CERRADA)$")] = None,
) -> api.Pagina[api.Incidencia]:
    exigir_acceso_unidad(sesion, identidad, id_unidad)
    consulta = sa.select(Incidencia).where(Incidencia.id_unidad == id_unidad)
    if estado:
        consulta = consulta.where(Incidencia.estado == estado)
    filas, siguiente = _pagina(sesion, consulta, Incidencia.creada_en, Incidencia.id, cursor, limite)
    return api.Pagina.model_validate(dict(items=[_incidencia(f) for f in filas], siguiente_cursor=siguiente))


@enrutador.get("/incidencias/{id_incidencia}", response_model=api.Incidencia)
def obtener_incidencia(
    id_incidencia: uuid.UUID, sesion: SesionDep, identidad: IdentidadDep
) -> api.Incidencia:
    exigir_acceso_incidencia(sesion, identidad, id_incidencia)
    fila = sesion.get(Incidencia, id_incidencia)
    assert fila is not None
    return _incidencia(fila)


@enrutador.get("/incidencias/{id_incidencia}/revisiones", response_model=api.Pagina[api.Revision])
def listar_revisiones(
    id_incidencia: uuid.UUID,
    sesion: SesionDep,
    identidad: IdentidadDep,
    cursor: str | None = None,
    limite: Annotated[int | None, Query(ge=1, le=paginacion.LIMITE_MAXIMO)] = None,
) -> api.Pagina[api.Revision]:
    exigir_acceso_incidencia(sesion, identidad, id_incidencia)
    filas, siguiente = _pagina(
        sesion,
        sa.select(RevisionIncidencia).where(RevisionIncidencia.id_incidencia == id_incidencia),
        RevisionIncidencia.fecha, RevisionIncidencia.id, cursor, limite,
    )
    return api.Pagina.model_validate(dict(
        items=[
            api.Revision.model_validate(dict(
                id=f.id, id_incidencia=f.id_incidencia, resultado=f.resultado,
                evidencia=f.evidencia, id_tecnico=f.id_tecnico, fecha=f.fecha,
            ))
            for f in filas
        ],
        siguiente_cursor=siguiente,
    ))


@enrutador.post(
    "/incidencias/{id_incidencia}/revisiones", response_model=api.Revision,
    status_code=status.HTTP_201_CREATED,
)
def registrar_revision(
    id_incidencia: uuid.UUID,
    entrada: api.RevisionEntrada,
    sesion: SesionDep,
    identidad: IdentidadDep,
    idempotency_key: ClaveIdempotencia = None,
) -> api.Revision:
    """Registrar una revisión no autoriza almacenamiento ni cierra el episodio."""
    repetida = reservar(
        sesion, identidad, idempotency_key, "POST", f"/incidencias/{id_incidencia}/revisiones",
        entrada.model_dump(mode="json"),
    )
    if repetida is not None and repetida.cuerpo is not None:
        return api.Revision.model_validate(repetida.cuerpo)

    ambito = exigir_acceso_incidencia(sesion, identidad, id_incidencia, tecnico=True)
    _revisiones(sesion, identidad, ambito.id_unidad, entrada)
    incidencia = sesion.get(Incidencia, id_incidencia, with_for_update=True)
    assert incidencia is not None
    concurrencia.exigir_revision(incidencia.revision, entrada.revision_incidencia)

    fila = RevisionIncidencia(
        id_incidencia=id_incidencia,
        resultado=entrada.resultado,
        evidencia=entrada.evidencia,
        id_tecnico=identidad.id,
    )
    sesion.add(fila)
    incidencia.revision += 1
    sesion.flush()
    salida = api.Revision.model_validate(dict(
        id=fila.id, id_incidencia=fila.id_incidencia, resultado=fila.resultado,
        evidencia=fila.evidencia, id_tecnico=fila.id_tecnico, fecha=fila.fecha,
    ))
    auditoria.registrar(
        sesion, identidad, accion="registrar_revision", recurso_tipo="incidencia",
        recurso_id=id_incidencia, metodo="POST",
        ruta=f"/incidencias/{id_incidencia}/revisiones", estado_http=201,
        revision_resultante=incidencia.revision, resumen={"resultado": fila.resultado},
    )
    completar(sesion, identidad, idempotency_key, 201, fila.id, salida.model_dump(mode="json"))
    return salida


@enrutador.get(
    "/incidencias/{id_incidencia}/resoluciones", response_model=api.Pagina[api.Resolucion]
)
def listar_resoluciones(
    id_incidencia: uuid.UUID,
    sesion: SesionDep,
    identidad: IdentidadDep,
    cursor: str | None = None,
    limite: Annotated[int | None, Query(ge=1, le=paginacion.LIMITE_MAXIMO)] = None,
) -> api.Pagina[api.Resolucion]:
    exigir_acceso_incidencia(sesion, identidad, id_incidencia)
    filas, siguiente = _pagina(
        sesion, sa.select(Resolucion).where(Resolucion.id_incidencia == id_incidencia),
        Resolucion.fecha, Resolucion.id, cursor, limite,
    )
    return api.Pagina.model_validate(dict(
        items=[
            api.Resolucion.model_validate(dict(
                id=f.id, id_incidencia=f.id_incidencia, evidencia=f.evidencia,
                disposicion=f.disposicion, id_tecnico=f.id_tecnico, fecha=f.fecha,
            ))
            for f in filas
        ],
        siguiente_cursor=siguiente,
    ))


@enrutador.post(
    "/incidencias/{id_incidencia}/resoluciones", response_model=api.Resolucion,
    status_code=status.HTTP_201_CREATED,
)
def resolver_incidencia(
    id_incidencia: uuid.UUID,
    entrada: api.ResolucionEntrada,
    sesion: SesionDep,
    identidad: IdentidadDep,
    idempotency_key: ClaveIdempotencia = None,
) -> api.Resolucion:
    """Cierra el episodio con evidencia y disposición: es el único modo de levantarlo."""
    repetida = reservar(
        sesion, identidad, idempotency_key, "POST", f"/incidencias/{id_incidencia}/resoluciones",
        entrada.model_dump(mode="json"),
    )
    if repetida is not None and repetida.cuerpo is not None:
        return api.Resolucion.model_validate(repetida.cuerpo)

    ambito = exigir_acceso_incidencia(sesion, identidad, id_incidencia, tecnico=True)
    _revisiones(sesion, identidad, ambito.id_unidad, entrada)
    incidencia = sesion.get(Incidencia, id_incidencia, with_for_update=True)
    assert incidencia is not None
    concurrencia.exigir_revision(incidencia.revision, entrada.revision_incidencia)
    if incidencia.estado == "CERRADA":
        raise concurrencia.ConflictoRevision(incidencia.revision, entrada.revision_incidencia)

    fila = Resolucion(
        id_incidencia=id_incidencia,
        evidencia=entrada.evidencia,
        disposicion=entrada.disposicion,
        id_tecnico=identidad.id,
    )
    sesion.add(fila)
    incidencia.estado = "CERRADA"
    incidencia.cerrada_en = datetime.now(UTC)
    incidencia.revision += 1
    sesion.flush()
    salida = api.Resolucion.model_validate(dict(
        id=fila.id, id_incidencia=fila.id_incidencia, evidencia=fila.evidencia,
        disposicion=fila.disposicion, id_tecnico=fila.id_tecnico, fecha=fila.fecha,
    ))
    auditoria.registrar(
        sesion, identidad, accion="resolver_incidencia", recurso_tipo="incidencia",
        recurso_id=id_incidencia, metodo="POST",
        ruta=f"/incidencias/{id_incidencia}/resoluciones", estado_http=201,
        revision_resultante=incidencia.revision, resumen={"disposicion": fila.disposicion},
    )
    completar(sesion, identidad, idempotency_key, 201, fila.id, salida.model_dump(mode="json"))
    return salida


@enrutador.post(
    "/unidades/{id_unidad}/admisiones", response_model=api.Admision,
    status_code=status.HTTP_201_CREATED,
)
def registrar_admision(
    id_unidad: uuid.UUID,
    entrada: api.AdmisionEntrada,
    sesion: SesionDep,
    identidad: IdentidadDep,
    idempotency_key: ClaveIdempotencia = None,
) -> api.Admision:
    """No se admite con una vigencia distinta de VIGENTE: se comprueba antes de actuar."""
    repetida = reservar(
        sesion, identidad, idempotency_key, "POST", f"/unidades/{id_unidad}/admisiones",
        entrada.model_dump(mode="json"),
    )
    if repetida is not None and repetida.cuerpo is not None:
        return api.Admision.model_validate(repetida.cuerpo)

    ambito = exigir_acceso_unidad(sesion, identidad, id_unidad, escritura=True)
    concurrencia.exigir_revisiones_unidad(
        revision_unidad_vigente=ambito.revision_unidad,
        revision_almacen_vigente=ambito.revision_almacen,
        revision_unidad_recibida=entrada.revision_unidad,
        revision_almacen_recibida=entrada.revision_almacen)
    evaluacion = sesion.get(Evaluacion, entrada.id_evaluacion)
    if evaluacion is None or evaluacion.id_unidad != id_unidad:
        raise RecursoInaccesible(str(entrada.id_evaluacion))

    estado = servicio_vigencia.calcular(sesion, id_unidad)
    if estado.estado != "VIGENTE" or estado.id_evaluacion != entrada.id_evaluacion:
        raise concurrencia.ConflictoRevision(entrada.revision_unidad, entrada.revision_unidad)

    fila = Admision(
        id_unidad=id_unidad,
        id_evaluacion=entrada.id_evaluacion,
        tipo=entrada.tipo,
        id_responsable=identidad.id,
    )
    sesion.add(fila)
    sesion.flush()
    salida = api.Admision.model_validate(dict(
        id=fila.id, id_unidad=fila.id_unidad, id_evaluacion=fila.id_evaluacion,
        tipo=fila.tipo, registrado_en=fila.registrado_en, id_responsable=fila.id_responsable,
    ))
    auditoria.registrar(
        sesion, identidad, accion="registrar_admision", recurso_tipo="admision",
        recurso_id=fila.id, metodo="POST", ruta=f"/unidades/{id_unidad}/admisiones",
        estado_http=201, resumen={"tipo": fila.tipo},
    )
    completar(sesion, identidad, idempotency_key, 201, fila.id, salida.model_dump(mode="json"))
    return salida


@enrutador.get("/unidades/{id_unidad}/eventos", response_model=api.Pagina[api.Evento])
def listar_eventos(id_unidad: uuid.UUID, sesion: SesionDep, identidad: IdentidadDep,
                   cursor: str | None = None, limite: Annotated[int | None, Query(ge=1, le=100)] = None) -> api.Pagina[api.Evento]:
    exigir_acceso_unidad(sesion, identidad, id_unidad)
    filas, siguiente = _pagina(sesion, sa.select(Evento).where(Evento.id_unidad == id_unidad),
                               Evento.fecha, Evento.id, cursor, limite)
    return api.Pagina.model_validate(dict(items=[api.Evento.model_validate(dict(id=f.id, id_unidad=f.id_unidad, tipo=f.tipo, fecha=f.fecha,
                                       evidencia=f.evidencia, id_responsable=f.id_responsable))
                            for f in filas], siguiente_cursor=siguiente))


@enrutador.post("/unidades/{id_unidad}/eventos", response_model=api.Evento, status_code=201)
def registrar_evento(id_unidad: uuid.UUID, entrada: api.EventoEntrada, sesion: SesionDep,
                     identidad: IdentidadDep, idempotency_key: ClaveIdempotencia = None) -> api.Evento:
    repetida = reservar(sesion, identidad, idempotency_key, "POST",
                        f"/unidades/{id_unidad}/eventos", entrada.model_dump(mode="json"))
    if repetida is not None and repetida.cuerpo is not None:
        return api.Evento.model_validate(repetida.cuerpo)
    if entrada.fecha > datetime.now(UTC):
        raise HTTPException(422, "El evento no puede estar en el futuro")
    ambito = _revisiones(sesion, identidad, id_unidad, entrada)
    fila = Evento(id_unidad=id_unidad, tipo=entrada.tipo, fecha=entrada.fecha,
                  evidencia=entrada.evidencia, id_responsable=identidad.id)
    sesion.add(fila)
    if entrada.tipo == "LIMPIEZA_GENERAL":
        almacen = sesion.get(Almacen, ambito.id_almacen)
        assert almacen is not None
        almacen.revision += 1
        almacen.actualizado_en = datetime.now(UTC)
        observacion = api.ObservacionEntrada.model_validate(dict(campo="fecha_limpieza_general", captura="APORTADO",
            valor=entrada.fecha.isoformat(), unidad="TEXTO", valor_original=None,
            fecha_observacion=entrada.fecha, metodo="Registro de limpieza",
            evidencia=entrada.evidencia, motivo_no_aplica=None))
        for unidad in sesion.scalars(sa.select(Unidad).where(Unidad.id_almacen == ambito.id_almacen)):
            sesion.add(observaciones.a_fila(observacion, id_unidad=unidad.id, id_responsable=identidad.id))
    sesion.flush()
    salida = api.Evento.model_validate(dict(id=fila.id, id_unidad=id_unidad, tipo=fila.tipo, fecha=fila.fecha,
                        evidencia=fila.evidencia, id_responsable=fila.id_responsable))
    auditoria.registrar(sesion, identidad, accion="registrar_evento", recurso_tipo="evento",
                        recurso_id=fila.id, metodo="POST", ruta=f"/unidades/{id_unidad}/eventos",
                        estado_http=201, resumen={"tipo": fila.tipo})
    completar(sesion, identidad, idempotency_key, 201, fila.id, salida.model_dump(mode="json"))
    return salida
