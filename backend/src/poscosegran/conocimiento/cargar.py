"""Carga y activación de una versión del catálogo.

Uso:
    python -m poscosegran.conocimiento.cargar knowledge/catalogo.yaml --activar

No inventa contenido: si el archivo no cubre las 30 reglas, las nueve ramas y
sus fuentes, la validación falla y no se registra ninguna versión.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import sqlalchemy as sa
import yaml

from ..db.modelos import Fuente, Regla, VersionConocimiento
from ..db.sesion import unidad_de_trabajo
from .esquema import Catalogo


def leer(ruta: Path) -> tuple[Catalogo, str]:
    contenido = ruta.read_bytes()
    digestion = hashlib.sha256(contenido).hexdigest()
    datos = yaml.safe_load(contenido.decode("utf-8"))
    return Catalogo.model_validate(datos), digestion


def cargar(ruta: Path, *, activar: bool, notas: str | None) -> str:
    catalogo, digestion = leer(ruta)
    with unidad_de_trabajo() as sesion:
        duplicada = sesion.scalar(
            sa.select(VersionConocimiento).where(VersionConocimiento.hash_contenido == digestion)
        )
        if duplicada is not None:
            if activar and not duplicada.activa:
                sesion.execute(sa.update(VersionConocimiento).where(VersionConocimiento.activa.is_(True)).values(activa=False))
                duplicada.activa = True
            return f"ya registrada: {duplicada.version_base} ({digestion[:12]})"

        if activar:
            sesion.execute(
                sa.update(VersionConocimiento)
                .where(VersionConocimiento.activa.is_(True))
                .values(activa=False)
            )

        version = VersionConocimiento(
            version_base=catalogo.version_base,
            version_parametros=catalogo.version_parametros,
            version_motor=catalogo.version_motor,
            hash_contenido=digestion,
            ruta_archivo=str(ruta),
            notas=notas,
            activa=activar,
        )
        sesion.add(version)
        sesion.flush()

        for orden, fuente in enumerate(catalogo.fuentes, start=1):
            sesion.add(
                Fuente(
                    id_version=version.id,
                    codigo=fuente.id,
                    referencia_markdown=fuente.referencia_markdown,
                )
            )
        for orden, regla in enumerate(catalogo.reglas, start=1):
            sesion.add(_fila(version.id, regla, es_rama=False, orden=orden))
        for orden, rama in enumerate(catalogo.ramas_r30, start=1):
            sesion.add(_fila(version.id, rama, es_rama=True, orden=orden))

        return f"registrada {catalogo.version_base} ({digestion[:12]}), activa={activar}"


def _fila(id_version, regla, *, es_rama: bool, orden: int) -> Regla:  # type: ignore[no-untyped-def]
    return Regla(
        id_version=id_version,
        codigo=regla.id,
        es_rama=es_rama,
        orden=orden,
        antecedente=regla.antecedente,
        consecuente=regla.consecuente,
        accion=regla.accion,
        fundamento_markdown=regla.fundamento_markdown,
    )


def main(argumentos: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description="Carga una versión del catálogo.")
    analizador.add_argument("ruta", type=Path)
    analizador.add_argument("--activar", action="store_true")
    analizador.add_argument("--notas", default=None)
    opciones = analizador.parse_args(argumentos)

    if not opciones.ruta.exists():
        print(f"no existe: {opciones.ruta}", file=sys.stderr)
        return 2
    print(cargar(opciones.ruta, activar=opciones.activar, notas=opciones.notas))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
