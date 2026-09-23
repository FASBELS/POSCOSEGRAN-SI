"""Catálogo de la versión activa de la base de conocimiento: solo lectura.

Los umbrales no se editan desde aquí. Cambiarlos exige una nueva versión, que se
propone, valida y activa en el módulo de adquisición (rutas /adquisicion).
"""

from __future__ import annotations

import sqlalchemy as sa
from fastapi import APIRouter

from ...db.modelos import Fuente, Regla, VersionConocimiento
from ...esquemas import contrato as api
from ...seguridad.dependencias import IdentidadDep, SesionDep
from ...seguridad.permisos import RecursoInaccesible
from ...servicios import conocimiento as servicio_conocimiento

enrutador = APIRouter(prefix="/api/v1", tags=["conocimiento"])


@enrutador.get("/conocimiento", response_model=api.Catalogo)
def catalogo(sesion: SesionDep, identidad: IdentidadDep) -> api.Catalogo:
    version = sesion.scalar(
        sa.select(VersionConocimiento).where(VersionConocimiento.activa.is_(True))
    )
    if version is None:
        raise RecursoInaccesible("catalogo")

    reglas = sesion.scalars(
        sa.select(Regla).where(Regla.id_version == version.id).order_by(Regla.es_rama, Regla.orden)
    ).all()
    fuentes = sesion.scalars(
        sa.select(Fuente).where(Fuente.id_version == version.id).order_by(Fuente.codigo)
    ).all()

    def _regla(fila: Regla) -> api.Regla:
        return api.Regla(
            id=fila.codigo,
            antecedente=fila.antecedente,
            consecuente=fila.consecuente,
            accion=fila.accion,
            fundamento_markdown=fila.fundamento_markdown,
        )

    base = servicio_conocimiento.base_de(version) if version.contenido is not None else None
    parametros = [] if base is None else [
        api.Parametro(
            nombre=p.nombre, valor=float(p.valor), unidad=p.unidad, fundamento=p.fundamento,
            fuentes=list(p.fuentes), descripcion=p.descripcion,
        )
        for p in base.parametros.values()
    ]

    return api.Catalogo(
        version_parametros=version.version_parametros,
        hash_base=version.hash_contenido,
        parametros=parametros,
        uso_campos={} if base is None else {c: list(r) for c, r in base.uso_de_campos.items()},
        version_base=version.version_base,
        reglas=[_regla(f) for f in reglas if not f.es_rama],
        ramas_r30=[_regla(f) for f in reglas if f.es_rama],
        fuentes=[
            api.Fuente(id=f.codigo, referencia_markdown=f.referencia_markdown) for f in fuentes
        ],
    )
