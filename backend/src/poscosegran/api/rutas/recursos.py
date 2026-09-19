"""Perfil, inicio, almacenes, lotes y unidades."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import sqlalchemy as sa
from fastapi import APIRouter, Query, Response, status

from ...db.modelos import (
    Almacen,
    AsignacionAlmacen,
    AsignacionLote,
    Evaluacion,
    Incidencia,
    Lote,
    Recipiente,
    Unidad,
    Usuario,
)
from ...esquemas import contrato as api
from ...seguridad.dependencias import IdentidadDep, SesionDep
from ...seguridad.permisos import (
    AccesoDenegado,
    RecursoInaccesible,
    exigir_acceso_almacen,
    exigir_acceso_lote,
    exigir_acceso_unidad,
)
from ...servicios import auditoria, concurrencia, presentacion
from .. import paginacion
from ..dependencias import ClaveIdempotencia, IfMatch, completar, etiquetar, reservar

enrutador = APIRouter(prefix="/api/v1", tags=["recursos"])


def _almacenes_visibles(identidad: IdentidadDep) -> sa.ColumnElement[bool]:
    return sa.or_(
        Almacen.id_propietario == identidad.id,
        Almacen.id.in_(
            sa.select(AsignacionAlmacen.id_almacen).where(
                AsignacionAlmacen.id_tecnico == identidad.id,
                sa.literal(identidad.es_tecnico),
                AsignacionAlmacen.vigente.is_(True),
            )
        ),
    )


def _lotes_visibles(identidad: IdentidadDep) -> sa.ColumnElement[bool]:
    return sa.or_(
        Lote.id_propietario == identidad.id,
        Lote.id.in_(
            sa.select(AsignacionLote.id_lote).where(
                AsignacionLote.id_tecnico == identidad.id, AsignacionLote.vigente.is_(True),
                sa.literal(identidad.es_tecnico)
            )
        ),
    )


@enrutador.get("/me", response_model=api.Perfil)
def perfil(sesion: SesionDep, identidad: IdentidadDep) -> api.Perfil:
    usuario = sesion.get(Usuario, identidad.id)
    if usuario is None:
        raise RecursoInaccesible(str(identidad.id))
    return api.Perfil.model_validate(dict(id=usuario.id, nombre=usuario.nombre, roles=sorted(identidad.roles)))


@enrutador.get("/inicio", response_model=api.Inicio)
def inicio(sesion: SesionDep, identidad: IdentidadDep) -> api.Inicio:
    """Resumen de la unidad de trabajo. Consultar nunca crea ni cierra nada."""
    ahora = datetime.now(UTC)
    visibles = (sa.select(Unidad.id).join(Lote, Lote.id == Unidad.id_lote)
                .join(Almacen, Almacen.id == Unidad.id_almacen)
                .where(sa.or_(_lotes_visibles(identidad), _almacenes_visibles(identidad))))
    total = sesion.scalar(sa.select(sa.func.count()).select_from(visibles.subquery())) or 0

    cuarentenas = sesion.scalar(
        sa.select(sa.func.count())
        .select_from(Incidencia)
        .where(
            Incidencia.estado == "ABIERTA",
            Incidencia.tipo == "CUARENTENA",
            Incidencia.id_unidad.in_(visibles),
        )
    ) or 0

    correcciones = sesion.scalar(
        sa.select(sa.func.count())
        .select_from(Evaluacion)
        .where(
            Evaluacion.decision_final == "CORREGIR_Y_REEVALUAR",
            Evaluacion.id.in_(sa.select(Unidad.id_evaluacion_actual).where(Unidad.id.in_(visibles))),
        )
    ) or 0

    proximos = sesion.execute(
        sa.select(Unidad.id, Unidad.nombre_recipiente, Evaluacion.fecha_proximo_control)
        .join(Evaluacion, Evaluacion.id == Unidad.id_evaluacion_actual)
        .where(
            Unidad.id.in_(visibles),
            Evaluacion.fecha_proximo_control.isnot(None),
            Evaluacion.fecha_proximo_control <= ahora + timedelta(days=30),
        )
        .order_by(Evaluacion.fecha_proximo_control)
        .limit(20)
    ).all()

    return api.Inicio.model_validate(dict(
        unidades_total=total,
        cuarentenas_abiertas=cuarentenas,
        correcciones_pendientes=correcciones,
        controles_proximos=[
            api.ControlProximo.model_validate(dict(
                id_unidad=fila[0],
                nombre=fila[1],
                fecha=fila[2],
                estado="ATRASADO" if fila[2] < ahora else "PENDIENTE",
            ))
            for fila in proximos
        ],
    ))


@enrutador.get("/almacenes", response_model=api.Pagina[api.Almacen])
def listar_almacenes(
    sesion: SesionDep,
    identidad: IdentidadDep,
    cursor: str | None = None,
    limite: Annotated[int | None, Query(ge=1, le=paginacion.LIMITE_MAXIMO)] = None,
) -> api.Pagina[api.Almacen]:
    tope = paginacion.limitar(limite)
    consulta = sa.select(Almacen).where(_almacenes_visibles(identidad))
    posicion = paginacion.decodificar(cursor)
    if posicion:
        consulta = consulta.where(
            sa.tuple_(Almacen.creado_en, Almacen.id) < sa.tuple_(*(sa.literal(v) for v in posicion))
        )
    filas = sesion.scalars(
        consulta.order_by(Almacen.creado_en.desc(), Almacen.id.desc()).limit(tope + 1)
    ).all()
    siguiente = (
        paginacion.codificar(filas[tope - 1].creado_en, filas[tope - 1].id)
        if len(filas) > tope
        else None
    )
    return api.Pagina.model_validate(dict(items=[presentacion.almacen(f) for f in filas[:tope]], siguiente_cursor=siguiente))


@enrutador.post("/almacenes", response_model=api.Almacen, status_code=status.HTTP_201_CREATED)
def crear_almacen(
    entrada: api.AlmacenEntrada,
    sesion: SesionDep,
    identidad: IdentidadDep,
    respuesta: Response,
    idempotency_key: ClaveIdempotencia = None,
) -> api.Almacen:
    repetida = reservar(
        sesion, identidad, idempotency_key, "POST", "/almacenes", entrada.model_dump(mode="json")
    )
    if repetida is not None and repetida.cuerpo is not None:
        return api.Almacen.model_validate(repetida.cuerpo)

    if not identidad.roles.intersection({"PRODUCTOR", "TECNICO"}):
        raise AccesoDenegado("Crear un almacén requiere productor o técnico")
    fila = Almacen(id_propietario=identidad.id, **entrada.model_dump())
    sesion.add(fila)
    sesion.flush()
    salida = presentacion.almacen(fila)
    auditoria.registrar(
        sesion, identidad, accion="crear_almacen", recurso_tipo="almacen",
        recurso_id=fila.id, metodo="POST", ruta="/almacenes", estado_http=201,
        revision_resultante=fila.revision, resumen={"nombre": fila.nombre},
    )
    completar(sesion, identidad, idempotency_key, 201, fila.id, salida.model_dump(mode="json"))
    etiquetar(respuesta, fila.revision)
    return salida


@enrutador.get("/almacenes/{id_almacen}", response_model=api.Almacen)
def obtener_almacen(
    id_almacen: uuid.UUID, sesion: SesionDep, identidad: IdentidadDep, respuesta: Response
) -> api.Almacen:
    exigir_acceso_almacen(sesion, identidad, id_almacen)
    fila = sesion.get(Almacen, id_almacen)
    assert fila is not None
    etiquetar(respuesta, fila.revision)
    return presentacion.almacen(fila)


@enrutador.patch("/almacenes/{id_almacen}", response_model=api.Almacen)
def actualizar_almacen(
    id_almacen: uuid.UUID,
    entrada: api.AlmacenEntrada,
    sesion: SesionDep,
    identidad: IdentidadDep,
    respuesta: Response,
    if_match: IfMatch = None,
) -> api.Almacen:
    exigir_acceso_almacen(sesion, identidad, id_almacen, escritura=True)
    fila = sesion.get(Almacen, id_almacen, with_for_update=True)
    assert fila is not None
    concurrencia.exigir_revision(fila.revision, concurrencia.revision_desde_if_match(if_match))

    cambios = entrada.model_dump()
    ubicacion_cambia = cambios["ubicacion"] != fila.ubicacion
    for campo, valor in cambios.items():
        setattr(fila, campo, valor)
    fila.revision += 1
    fila.actualizado_en = datetime.now(UTC)

    auditoria.registrar(
        sesion, identidad, accion="actualizar_almacen", recurso_tipo="almacen",
        recurso_id=fila.id, metodo="PATCH", ruta=f"/almacenes/{id_almacen}", estado_http=200,
        revision_resultante=fila.revision,
        # Un cambio de ubicación invalida los controles de sus unidades: la nueva
        # revisión del almacén hace que las autorizaciones previas dejen de ser vigentes.
        resumen={"ubicacion_modificada": ubicacion_cambia},
    )
    etiquetar(respuesta, fila.revision)
    return presentacion.almacen(fila)


@enrutador.get("/lotes", response_model=api.Pagina[api.Lote])
def listar_lotes(
    sesion: SesionDep,
    identidad: IdentidadDep,
    cursor: str | None = None,
    limite: Annotated[int | None, Query(ge=1, le=paginacion.LIMITE_MAXIMO)] = None,
    q: str | None = None,
) -> api.Pagina[api.Lote]:
    tope = paginacion.limitar(limite)
    consulta = sa.select(Lote).where(_lotes_visibles(identidad))
    if q:
        consulta = consulta.where(Lote.codigo.ilike(f"%{q}%"))
    posicion = paginacion.decodificar(cursor)
    if posicion:
        consulta = consulta.where(sa.tuple_(Lote.creado_en, Lote.id) < sa.tuple_(*(sa.literal(v) for v in posicion)))
    filas = sesion.scalars(
        consulta.order_by(Lote.creado_en.desc(), Lote.id.desc()).limit(tope + 1)
    ).all()
    siguiente = (
        paginacion.codificar(filas[tope - 1].creado_en, filas[tope - 1].id)
        if len(filas) > tope
        else None
    )
    return api.Pagina.model_validate(dict(
        items=[
            api.Lote.model_validate(dict(
                id=f.id, id_propietario=f.id_propietario, codigo=f.codigo, variedad=f.variedad,
                uso_final=f.uso_final, revision=f.revision, creado_en=f.creado_en,
            ))
            for f in filas[:tope]
        ],
        siguiente_cursor=siguiente,
    ))


@enrutador.post("/lotes", response_model=api.Lote, status_code=status.HTTP_201_CREATED)
def crear_lote(
    entrada: api.LoteEntrada,
    sesion: SesionDep,
    identidad: IdentidadDep,
    respuesta: Response,
    idempotency_key: ClaveIdempotencia = None,
) -> api.Lote:
    repetida = reservar(
        sesion, identidad, idempotency_key, "POST", "/lotes", entrada.model_dump(mode="json")
    )
    if repetida is not None and repetida.cuerpo is not None:
        return api.Lote.model_validate(repetida.cuerpo)

    if "PRODUCTOR" not in identidad.roles:
        raise AccesoDenegado("Crear un lote requiere rol PRODUCTOR")
    # El propietario es siempre el usuario autenticado: no se acepta del cliente.
    fila = Lote(id_propietario=identidad.id, **entrada.model_dump())
    sesion.add(fila)
    sesion.flush()
    salida = api.Lote.model_validate(dict(
        id=fila.id, id_propietario=fila.id_propietario, codigo=fila.codigo,
        variedad=fila.variedad, uso_final=fila.uso_final, revision=fila.revision,
        creado_en=fila.creado_en,
    ))
    auditoria.registrar(
        sesion, identidad, accion="crear_lote", recurso_tipo="lote", recurso_id=fila.id,
        metodo="POST", ruta="/lotes", estado_http=201, revision_resultante=fila.revision,
        resumen={"codigo": fila.codigo},
    )
    completar(sesion, identidad, idempotency_key, 201, fila.id, salida.model_dump(mode="json"))
    etiquetar(respuesta, fila.revision)
    return salida


@enrutador.get("/lotes/{id_lote}", response_model=api.Lote)
def obtener_lote(
    id_lote: uuid.UUID, sesion: SesionDep, identidad: IdentidadDep, respuesta: Response
) -> api.Lote:
    exigir_acceso_lote(sesion, identidad, id_lote)
    fila = sesion.get(Lote, id_lote)
    assert fila is not None
    etiquetar(respuesta, fila.revision)
    return api.Lote.model_validate(dict(
        id=fila.id, id_propietario=fila.id_propietario, codigo=fila.codigo,
        variedad=fila.variedad, uso_final=fila.uso_final, revision=fila.revision,
        creado_en=fila.creado_en,
    ))


@enrutador.patch("/lotes/{id_lote}", response_model=api.Lote)
def actualizar_lote(
    id_lote: uuid.UUID,
    entrada: api.LoteEntrada,
    sesion: SesionDep,
    identidad: IdentidadDep,
    respuesta: Response,
    if_match: IfMatch = None,
) -> api.Lote:
    exigir_acceso_lote(sesion, identidad, id_lote, escritura=True)
    fila = sesion.get(Lote, id_lote, with_for_update=True)
    assert fila is not None
    concurrencia.exigir_revision(fila.revision, concurrencia.revision_desde_if_match(if_match))
    for campo, valor in entrada.model_dump().items():
        setattr(fila, campo, valor)
    fila.revision += 1
    fila.actualizado_en = datetime.now(UTC)
    auditoria.registrar(
        sesion, identidad, accion="actualizar_lote", recurso_tipo="lote", recurso_id=fila.id,
        metodo="PATCH", ruta=f"/lotes/{id_lote}", estado_http=200,
        revision_resultante=fila.revision, resumen={"codigo": fila.codigo},
    )
    etiquetar(respuesta, fila.revision)
    return api.Lote.model_validate(dict(
        id=fila.id, id_propietario=fila.id_propietario, codigo=fila.codigo,
        variedad=fila.variedad, uso_final=fila.uso_final, revision=fila.revision,
        creado_en=fila.creado_en,
    ))


@enrutador.get("/unidades", response_model=api.Pagina[api.Unidad])
def listar_unidades(
    sesion: SesionDep,
    identidad: IdentidadDep,
    cursor: str | None = None,
    limite: Annotated[int | None, Query(ge=1, le=paginacion.LIMITE_MAXIMO)] = None,
    id_lote: uuid.UUID | None = None,
    id_almacen: uuid.UUID | None = None,
) -> api.Pagina[api.Unidad]:
    tope = paginacion.limitar(limite)
    consulta = (
        sa.select(Unidad, Almacen.revision)
        .join(Lote, Lote.id == Unidad.id_lote)
        .join(Almacen, Almacen.id == Unidad.id_almacen)
        .where(sa.or_(_lotes_visibles(identidad), _almacenes_visibles(identidad)))
    )
    if id_lote:
        consulta = consulta.where(Unidad.id_lote == id_lote)
    if id_almacen:
        consulta = consulta.where(Unidad.id_almacen == id_almacen)
    posicion = paginacion.decodificar(cursor)
    if posicion:
        consulta = consulta.where(sa.tuple_(Unidad.creado_en, Unidad.id) < sa.tuple_(*(sa.literal(v) for v in posicion)))
    filas = sesion.execute(
        consulta.order_by(Unidad.creado_en.desc(), Unidad.id.desc()).limit(tope + 1)
    ).all()
    siguiente = (
        paginacion.codificar(filas[tope - 1][0].creado_en, filas[tope - 1][0].id)
        if len(filas) > tope
        else None
    )
    return api.Pagina.model_validate(dict(
        items=[presentacion.unidad(fila[0], fila[1]) for fila in filas[:tope]],
        siguiente_cursor=siguiente,
    ))


@enrutador.post("/unidades", response_model=api.Unidad, status_code=status.HTTP_201_CREATED)
def crear_unidad(
    entrada: api.UnidadEntrada,
    sesion: SesionDep,
    identidad: IdentidadDep,
    respuesta: Response,
    idempotency_key: ClaveIdempotencia = None,
) -> api.Unidad:
    repetida = reservar(
        sesion, identidad, idempotency_key, "POST", "/unidades", entrada.model_dump(mode="json")
    )
    if repetida is not None and repetida.cuerpo is not None:
        return api.Unidad.model_validate(repetida.cuerpo)

    exigir_acceso_lote(sesion, identidad, entrada.id_lote, escritura=True)
    exigir_acceso_almacen(sesion, identidad, entrada.id_almacen, escritura=True)

    recipiente = Recipiente(nombre=entrada.nombre_recipiente)
    sesion.add(recipiente)
    sesion.flush()
    fila = Unidad(
        id_lote=entrada.id_lote,
        id_almacen=entrada.id_almacen,
        id_recipiente=recipiente.id,
        nombre_recipiente=entrada.nombre_recipiente,
        tipo_almacenamiento=entrada.tipo_almacenamiento,
    )
    sesion.add(fila)
    sesion.flush()
    revision_almacen = sesion.scalar(
        sa.select(Almacen.revision).where(Almacen.id == entrada.id_almacen)
    ) or 1
    salida = presentacion.unidad(fila, revision_almacen)
    auditoria.registrar(
        sesion, identidad, accion="crear_unidad", recurso_tipo="unidad", recurso_id=fila.id,
        metodo="POST", ruta="/unidades", estado_http=201, revision_resultante=fila.revision,
        resumen={"nombre_recipiente": fila.nombre_recipiente},
    )
    completar(sesion, identidad, idempotency_key, 201, fila.id, salida.model_dump(mode="json"))
    etiquetar(respuesta, fila.revision)
    return salida


@enrutador.get("/unidades/{id_unidad}", response_model=api.Unidad)
def obtener_unidad(
    id_unidad: uuid.UUID, sesion: SesionDep, identidad: IdentidadDep, respuesta: Response
) -> api.Unidad:
    exigir_acceso_unidad(sesion, identidad, id_unidad)
    fila = sesion.get(Unidad, id_unidad)
    assert fila is not None
    etiquetar(respuesta, fila.revision)
    return presentacion.unidad(fila, sesion.scalar(sa.select(Almacen.revision).where(Almacen.id == fila.id_almacen)) or 0)


@enrutador.patch("/unidades/{id_unidad}", response_model=api.Unidad)
def actualizar_unidad(
    id_unidad: uuid.UUID,
    entrada: api.UnidadEntrada,
    sesion: SesionDep,
    identidad: IdentidadDep,
    respuesta: Response,
    if_match: IfMatch = None,
) -> api.Unidad:
    exigir_acceso_unidad(sesion, identidad, id_unidad, escritura=True)
    fila = sesion.get(Unidad, id_unidad, with_for_update=True)
    assert fila is not None
    concurrencia.exigir_revision(fila.revision, concurrencia.revision_desde_if_match(if_match))

    exigir_acceso_lote(sesion, identidad, entrada.id_lote, escritura=True)
    exigir_acceso_almacen(sesion, identidad, entrada.id_almacen, escritura=True)
    modalidad_cambia = entrada.tipo_almacenamiento != fila.tipo_almacenamiento
    for campo, valor in entrada.model_dump().items():
        setattr(fila, campo, valor)
    fila.revision += 1
    fila.actualizado_en = datetime.now(UTC)

    auditoria.registrar(
        sesion, identidad, accion="actualizar_unidad", recurso_tipo="unidad", recurso_id=fila.id,
        metodo="PATCH", ruta=f"/unidades/{id_unidad}", estado_http=200,
        revision_resultante=fila.revision,
        # Cambiar de modalidad invalida los controles heredados: la vigencia se
        # recalcula al consultar y la autorización anterior deja de aplicarse.
        resumen={"modalidad_modificada": modalidad_cambia},
    )
    etiquetar(respuesta, fila.revision)
    return presentacion.unidad(fila, sesion.scalar(sa.select(Almacen.revision).where(Almacen.id == fila.id_almacen)) or 0)
