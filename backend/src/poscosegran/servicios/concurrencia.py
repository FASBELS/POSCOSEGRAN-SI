"""Revisiones, ETag y precondiciones.

Un comando de unidad declara qué revisiones creyó estar usando. El servidor las
comprueba dentro de la transacción para no decidir sobre condiciones que
cambiaron mientras tanto.
"""

from __future__ import annotations

import re

ETAG = re.compile(r'^(?:W/)?"(\d+)"$')


class PrecondicionRequerida(Exception):
    """Falta If-Match o If-None-Match. Se traduce a 428."""


class ConflictoRevision(Exception):
    """La revisión enviada no es la vigente. Se traduce a 409."""

    def __init__(self, esperada: int, recibida: int | None) -> None:
        super().__init__(f"revisión vigente {esperada}, recibida {recibida}")
        self.esperada = esperada
        self.recibida = recibida


def etiqueta(revision: int) -> str:
    return f'"{revision}"'


def revision_desde_if_match(cabecera: str | None) -> int:
    if cabecera is None or not cabecera.strip():
        raise PrecondicionRequerida("If-Match es obligatorio")
    coincidencia = ETAG.match(cabecera.strip())
    if coincidencia is None:
        raise PrecondicionRequerida("If-Match debe contener la revisión entre comillas")
    return int(coincidencia.group(1))


def exigir_revision(esperada: int, recibida: int | None) -> None:
    if recibida != esperada:
        raise ConflictoRevision(esperada, recibida)


def exigir_revisiones_unidad(
    *, revision_unidad_vigente: int, revision_almacen_vigente: int,
    revision_unidad_recibida: int, revision_almacen_recibida: int,
) -> None:
    """Ambas revisiones se comprueban juntas: un cambio de almacén afecta a la unidad."""
    exigir_revision(revision_unidad_vigente, revision_unidad_recibida)
    exigir_revision(revision_almacen_vigente, revision_almacen_recibida)
