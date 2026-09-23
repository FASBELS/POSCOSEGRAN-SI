"""Módulo de adquisición del conocimiento.

Solo el rol INGENIERO_CONOCIMIENTO propone y activa versiones. Cada propuesta se
valida con el mismo cargador que el motor y se mide contra los casos de referencia
y las últimas evaluaciones emitidas antes de poder activarse. Activar una versión
no recalcula evaluaciones anteriores: cada una conserva la versión con que se emitió.
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, status

from ...db.modelos import Evaluacion, VersionConocimiento
from ...esquemas import contrato as api
from ...seguridad.dependencias import IdentidadDep, SesionDep
from ...seguridad.permisos import AccesoDenegado, RecursoInaccesible
from ...servicios import auditoria
from ...servicios import conocimiento as servicio
from ...sistema_experto import adquisicion, serializacion

enrutador = APIRouter(prefix="/api/v1/adquisicion", tags=["adquisicion"])

EVALUACIONES_HISTORICAS = 200


def _exigir_ingeniero(identidad) -> None:  # type: ignore[no-untyped-def]
    if not identidad.es_ingeniero_conocimiento:
        raise AccesoDenegado("se requiere el rol INGENIERO_CONOCIMIENTO")


def _resumen(v: VersionConocimiento) -> api.VersionConocimientoResumen:
    return api.VersionConocimientoResumen(
        id=v.id,
        version_base=v.version_base,
        version_parametros=v.version_parametros,
        version_motor=v.version_motor,
        hash_base=v.hash_contenido,
        estado=v.estado,  # type: ignore[arg-type]
        activa=v.activa,
        motivo=v.motivo or v.notas,
        id_version_origen=v.id_version_origen,
        cargada_en=v.cargada_en,
        activada_en=v.activada_en,
    )


def _parametros(base) -> list[api.Parametro]:  # type: ignore[no-untyped-def]
    return [
        api.Parametro(
            nombre=p.nombre, valor=float(p.valor), unidad=p.unidad, fundamento=p.fundamento,  # type: ignore[arg-type]
            fuentes=list(p.fuentes), descripcion=p.descripcion,
        )
        for p in base.parametros.values()
    ]


def _casos_historicos(sesion) -> list[tuple[str, str, object]]:  # type: ignore[no-untyped-def]
    """Últimas evaluaciones emitidas con hechos reproducibles."""
    filas = sesion.scalars(
        sa.select(Evaluacion).order_by(Evaluacion.fecha_evaluacion.desc()).limit(EVALUACIONES_HISTORICAS)
    ).all()
    casos = []
    for fila in filas:
        hechos = (fila.entrada_efectiva or {}).get("_hechos_iniciales")
        if hechos is not None:
            casos.append((f"historica:{fila.id}", "historica", serializacion.desde_json(hechos)))
    return casos


@enrutador.get("/versiones", response_model=list[api.VersionConocimientoResumen])
def versiones(sesion: SesionDep, identidad: IdentidadDep) -> list[api.VersionConocimientoResumen]:
    _exigir_ingeniero(identidad)
    filas = sesion.scalars(sa.select(VersionConocimiento).order_by(VersionConocimiento.cargada_en.desc())).all()
    return [_resumen(v) for v in filas]


@enrutador.get("/versiones/{id_version}", response_model=api.DetalleVersion)
def detalle(id_version: uuid.UUID, sesion: SesionDep, identidad: IdentidadDep) -> api.DetalleVersion:
    _exigir_ingeniero(identidad)
    version = sesion.get(VersionConocimiento, id_version)
    if version is None:
        raise RecursoInaccesible(str(id_version))
    base = servicio.base_de(version)
    cambios: list[api.CambioParametro] = []
    if version.id_version_origen:
        origen = sesion.get(VersionConocimiento, version.id_version_origen)
        if origen is not None and origen.contenido is not None:
            anterior = servicio.base_de(origen)
            cambios = [
                api.CambioParametro(nombre=n, anterior=float(anterior.parametro(n)), nuevo=float(p.valor), unidad=p.unidad)
                for n, p in base.parametros.items()
                if n in anterior.parametros and anterior.parametro(n) != p.valor
            ]
    return api.DetalleVersion(
        version=_resumen(version),
        parametros=_parametros(base),
        reglas=list(version.contenido["operativa"]["reglas"]),  # type: ignore[index]
        cambios_respecto_origen=cambios,
    )


@enrutador.post("/propuestas", response_model=api.PropuestaResultado)
def proponer(entrada: api.PropuestaEntrada, sesion: SesionDep, identidad: IdentidadDep) -> api.PropuestaResultado:
    """Valida y mide una propuesta partiendo de la versión activa.

    Con guardar=false solo simula. Con guardar=true y una propuesta válida, la
    registra como PROPUESTA; activarla es un paso aparte.
    """
    _exigir_ingeniero(identidad)
    activa_fila, activa = servicio.base_activa(sesion)
    casos = adquisicion.cargar_casos_referencia() + _casos_historicos(sesion)
    propuesta = adquisicion.proponer(
        activa,
        motivo=entrada.motivo,
        version_base=entrada.version_base,
        version_parametros=entrada.version_parametros,
        parametros=entrada.parametros,
        reglas=entrada.reglas,
        casos=casos,
    )
    errores = list(propuesta.errores)
    if propuesta.valida:
        repetida = sesion.scalar(
            sa.select(VersionConocimiento).where(
                VersionConocimiento.version_base == propuesta.version_base,
                VersionConocimiento.version_parametros == propuesta.version_parametros,
            )
        )
        if repetida is not None:
            errores.append(
                f"ya existe la versión {propuesta.version_base}/{propuesta.version_parametros}: use otro número"
            )

    registrada = None
    if entrada.guardar and not errores:
        assert propuesta.base is not None and propuesta.contenido is not None
        registrada = servicio.registrar(
            sesion,
            base=propuesta.base,
            contenido=dict(propuesta.contenido),
            estado="PROPUESTA",
            motivo=propuesta.motivo,
            ruta_archivo="adquisicion",
            id_origen=activa_fila.id,
            id_responsable=identidad.id,
        )
        auditoria.registrar(
            sesion, identidad, accion="proponer_version_conocimiento", recurso_tipo="version_conocimiento",
            recurso_id=registrada.id, metodo="POST", ruta="/adquisicion/propuestas", estado_http=200,
            resumen={
                "version": f"{propuesta.version_base}/{propuesta.version_parametros}",
                "parametros": {c.nombre: [str(c.anterior), str(c.nuevo)] for c in propuesta.cambios_parametros},
                "reglas": [f"{c.tipo}:{c.produccion}" for c in propuesta.cambios_reglas],
                "cambian": propuesta.impacto.cambian if propuesta.impacto else None,
            },
        )

    impacto = propuesta.impacto
    return api.PropuestaResultado(
        valida=not errores,
        errores=errores,
        advertencias=list(propuesta.advertencias),
        version_base=propuesta.version_base,
        version_parametros=propuesta.version_parametros,
        cambios_parametros=[
            api.CambioParametro(nombre=c.nombre, anterior=float(c.anterior), nuevo=float(c.nuevo), unidad=c.unidad)
            for c in propuesta.cambios_parametros
        ],
        cambios_reglas=[api.CambioRegla(produccion=c.produccion, regla=c.regla, tipo=c.tipo) for c in propuesta.cambios_reglas],  # type: ignore[arg-type]
        impacto=None if impacto is None else api.Impacto(
            evaluados=impacto.evaluados,
            cambian=impacto.cambian,
            transiciones=impacto.transiciones,
            nuevas_autorizaciones=impacto.nuevas_autorizaciones,
            casos=[
                api.CasoAfectado(
                    id=c.id, origen=c.origen, decision_antes=c.decision_antes, decision_despues=c.decision_despues,
                    rama_antes=c.rama_antes, rama_despues=c.rama_despues,
                    reglas_nuevas=list(c.reglas_nuevas), reglas_retiradas=list(c.reglas_retiradas),
                )
                for c in impacto.casos[:100]
            ],
        ),
        version=_resumen(registrada) if registrada is not None else None,
    )


@enrutador.post("/versiones/{id_version}/activar", response_model=api.VersionConocimientoResumen)
def activar(
    id_version: uuid.UUID, entrada: api.ActivacionEntrada, sesion: SesionDep, identidad: IdentidadDep
) -> api.VersionConocimientoResumen:
    """Activa una versión registrada. Las nuevas evaluaciones la usarán; las emitidas no cambian."""
    _exigir_ingeniero(identidad)
    version = sesion.get(VersionConocimiento, id_version, with_for_update=True)
    if version is None:
        raise RecursoInaccesible(str(id_version))
    if version.activa:
        raise HTTPException(status.HTTP_409_CONFLICT, "la versión ya está activa")
    if version.estado == "DESCARTADA":
        raise HTTPException(status.HTTP_409_CONFLICT, "una versión descartada no se activa: proponga una nueva")
    servicio.base_de(version)  # revalida el contenido antes de activarlo
    anterior = servicio.version_activa(sesion)
    servicio.activar(sesion, version, identidad.id)
    auditoria.registrar(
        sesion, identidad, accion="activar_version_conocimiento", recurso_tipo="version_conocimiento",
        recurso_id=version.id, metodo="POST", ruta=f"/adquisicion/versiones/{id_version}/activar",
        estado_http=200,
        resumen={
            "activada": f"{version.version_base}/{version.version_parametros}",
            "anterior": f"{anterior.version_base}/{anterior.version_parametros}",
            "motivo": entrada.motivo,
        },
    )
    return _resumen(version)
