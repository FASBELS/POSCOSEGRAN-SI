"""Huella de contenido y concurrencia optimista."""

from __future__ import annotations

import pytest

from poscosegran.servicios.concurrencia import (
    ConflictoRevision,
    PrecondicionRequerida,
    etiqueta,
    exigir_revision,
    exigir_revisiones_unidad,
    revision_desde_if_match,
)
from poscosegran.servicios.idempotencia import huella


def test_huella_ignora_el_orden_de_las_claves() -> None:
    assert huella({"a": 1, "b": 2}) == huella({"b": 2, "a": 1})


def test_huella_distingue_contenidos_distintos() -> None:
    assert huella({"humedad_grano": 12.5}) != huella({"humedad_grano": 12.6})


def test_huella_distingue_tipos() -> None:
    """Un booleano y su texto no son el mismo contenido."""
    assert huella({"moho_visible": True}) != huella({"moho_visible": "true"})


def test_etiqueta_y_lectura_de_if_match() -> None:
    assert revision_desde_if_match(etiqueta(7)) == 7
    assert revision_desde_if_match('W/"7"') == 7


@pytest.mark.parametrize("cabecera", [None, "", "7", "abc", '"7'])
def test_if_match_mal_formado_exige_precondicion(cabecera: str | None) -> None:
    with pytest.raises(PrecondicionRequerida):
        revision_desde_if_match(cabecera)


def test_revision_obsoleta_es_conflicto() -> None:
    with pytest.raises(ConflictoRevision):
        exigir_revision(5, 4)


def test_revision_de_almacen_tambien_se_comprueba() -> None:
    """Un cambio del almacén invalida el comando aunque la unidad no haya cambiado."""
    with pytest.raises(ConflictoRevision):
        exigir_revisiones_unidad(
            revision_unidad_vigente=3,
            revision_almacen_vigente=9,
            revision_unidad_recibida=3,
            revision_almacen_recibida=8,
        )
