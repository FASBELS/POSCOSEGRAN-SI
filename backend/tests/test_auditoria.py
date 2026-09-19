"""La auditoría no debe poder guardar una credencial."""

from __future__ import annotations

from poscosegran.servicios.auditoria import depurar


def test_omite_claves_sensibles_en_cualquier_nivel() -> None:
    entrada = {
        "campo": "humedad_grano",
        "Authorization": "Bearer abc.def.ghi",
        "anidado": {"token": "xyz", "valor": 12.5, "lista": [{"password": "p"}]},
    }
    salida = depurar(entrada)
    assert salida["Authorization"] == "[omitido]"
    assert salida["anidado"]["token"] == "[omitido]"
    assert salida["anidado"]["lista"][0]["password"] == "[omitido]"
    assert salida["anidado"]["valor"] == 12.5
    assert salida["campo"] == "humedad_grano"


def test_conserva_lo_que_no_es_sensible() -> None:
    assert depurar({"decision_final": "CUARENTENA"}) == {"decision_final": "CUARENTENA"}
