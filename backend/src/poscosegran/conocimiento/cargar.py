"""Carga y activación de la base de conocimiento desde knowledge/.

Uso:
    python -m poscosegran.conocimiento.cargar [knowledge/] --activar

Lee base_conocimiento.yaml (operativa) y catalogo.yaml (documental), los valida
juntos con el mismo cargador que usa el motor y los registra como una versión.
Si la validación falla no se registra nada: el conocimiento no se completa por
inferencia. Volver a cargar el mismo contenido no duplica la versión.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import sqlalchemy as sa

from ..db.modelos import VersionConocimiento
from ..db.sesion import unidad_de_trabajo
from ..servicios import conocimiento as servicio
from ..sistema_experto import base_conocimiento
from ..sistema_experto.base_conocimiento import BaseInvalida
from .esquema import Catalogo


def cargar(carpeta: Path, *, activar: bool, notas: str | None) -> str:
    if carpeta.is_file():  
        carpeta = carpeta.parent
    contenido = base_conocimiento.leer_archivos(carpeta)
    Catalogo.model_validate(contenido["documental"])  
    base = base_conocimiento.desde_contenido(contenido)

    with unidad_de_trabajo() as sesion:
        existente = sesion.scalar(
            sa.select(VersionConocimiento).where(VersionConocimiento.hash_contenido == base.hash)
        )
        if existente is not None:
            if activar and not existente.activa:
                servicio.activar(sesion, existente, None)
            return f"ya registrada: {base.version_base}/{base.version_parametros} ({base.hash[:12]})"

        version = servicio.registrar(
            sesion,
            base=base,
            contenido=contenido,
            estado="ACTIVADA",
            motivo=notas or "Carga desde los archivos de knowledge/",
            ruta_archivo=str(carpeta),
        )
        if activar:
            servicio.activar(sesion, version, None)
        return f"registrada {base.version_base}/{base.version_parametros} ({base.hash[:12]}), activa={activar}"


def main(argumentos: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description="Carga una versión de la base de conocimiento.")
    analizador.add_argument("ruta", type=Path, nargs="?", default=None,
                            help="carpeta knowledge/ (por defecto, la del repositorio)")
    analizador.add_argument("--activar", action="store_true")
    analizador.add_argument("--notas", default=None)
    opciones = analizador.parse_args(argumentos)

    carpeta = opciones.ruta or base_conocimiento.ruta_por_defecto()
    if carpeta.is_file():  
        carpeta = carpeta.parent
    if not (carpeta / "base_conocimiento.yaml").exists():
        print(f"no existe {carpeta / 'base_conocimiento.yaml'}", file=sys.stderr)
        return 2
    try:
        print(cargar(carpeta, activar=opciones.activar, notas=opciones.notas))
    except BaseInvalida as error:
        print("la base de conocimiento no es válida:", file=sys.stderr)
        for mensaje in error.errores:
            print(f"  - {mensaje}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
