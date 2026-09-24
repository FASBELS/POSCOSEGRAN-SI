"""Cambios completos de reglas operativas y sus fichas documentales."""

from __future__ import annotations

import copy

import pytest

from poscosegran.sistema_experto import adquisicion, base_conocimiento


@pytest.fixture(scope="module")
def activa():
    return base_conocimiento.cargar()


def _regla(activa, codigo):
    return copy.deepcopy(next(r for r in activa.contenido["operativa"]["reglas"] if r["id"] == codigo))


def _ficha(activa, codigo):
    return copy.deepcopy(next(f for f in activa.contenido["documental"]["reglas"] if f["id"] == codigo))


def _proponer(activa, **cambios):
    return adquisicion.proponer(
        activa,
        motivo="Revisión técnica documentada de las reglas",
        version_base="2.1",
        casos=[],
        **cambios,
    )


def test_agregar_regla_y_ficha(activa):
    regla = _regla(activa, "R31")
    regla["id"] = "R53"
    regla["entonces"]["hallazgo"] = "INFRAESTRUCTURA_CON_FILTRACION_ADICIONAL"
    ficha = _ficha(activa, "R31")
    ficha["id"] = "R53"
    propuesta = _proponer(activa, reglas={"R53": regla}, fichas={"R53": ficha})

    assert propuesta.valida, propuesta.errores
    assert propuesta.cambios_reglas[0].tipo == "NUEVA"
    assert propuesta.base is not None
    assert any(r["id"] == "R53" for r in propuesta.contenido["operativa"]["reglas"])
    assert any(f["id"] == "R53" for f in propuesta.contenido["documental"]["reglas"])
    assert "R53" not in {r["id"] for r in activa.contenido["operativa"]["reglas"]}


def test_editar_regla_y_ficha(activa):
    regla = _regla(activa, "R31")
    regla["entonces"]["mensaje"] = "Mensaje actualizado para la filtración."
    ficha = _ficha(activa, "R31")
    ficha["accion"] = "Revisar la filtración antes de almacenar."
    propuesta = _proponer(activa, reglas={"R31": regla}, fichas={"R31": ficha})

    assert propuesta.valida, propuesta.errores
    assert [c.tipo for c in propuesta.cambios_reglas] == ["MODIFICADA"]
    assert next(f for f in propuesta.contenido["documental"]["reglas"] if f["id"] == "R31")["accion"] == ficha["accion"]


def test_retirar_regla_adicional_y_ficha(activa):
    propuesta = _proponer(activa, reglas={"R52": None})

    assert propuesta.valida, propuesta.errores
    assert propuesta.cambios_reglas[0].tipo == "RETIRADA"
    assert "R52" not in {r["id"] for r in propuesta.contenido["operativa"]["reglas"]}
    assert "R52" not in {f["id"] for f in propuesta.contenido["documental"]["reglas"]}
    assert "R52" not in propuesta.contenido["operativa"]["fundamentos"]


def test_retirar_regla_base_se_rechaza(activa):
    propuesta = _proponer(activa, reglas={"R01": None})
    assert not propuesta.valida
    assert any("no se puede retirar" in error for error in propuesta.errores)


def test_nueva_regla_sin_ficha_se_rechaza(activa):
    regla = _regla(activa, "R31")
    regla["id"] = "R53"
    propuesta = _proponer(activa, reglas={"R53": regla})
    assert not propuesta.valida
    assert any("R53" in error for error in propuesta.errores)
