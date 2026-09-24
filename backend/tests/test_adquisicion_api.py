"""Ciclo de vida de una versión de conocimiento, por HTTP y contra PostgreSQL real.

Cubre lo que el módulo de Python no puede demostrar por sí solo: permisos, estados,
auditoría, separación de funciones y qué ocurre cuando dos activaciones coinciden.
"""

from __future__ import annotations

import itertools
import threading
import uuid

import pytest
import sqlalchemy as sa

pytestmark = pytest.mark.bd

MOTIVO = "Revisión técnica documentada de la campaña 2026"

_contador = itertools.count(1)


def _propuesta_unica() -> tuple[str, float]:
    n = next(_contador)
    return f"9.{n}.{uuid.uuid4().hex[:6]}", round(13.05 + n * 0.01, 2)


def _proponer(client, headers, *, rol="INGENIERO", guardar=False, motivo=MOTIVO, **extra):
    version, humedad = _propuesta_unica()
    cuerpo = {
        "motivo": motivo,
        "parametros": {"humedad_admision_max": humedad},
        "reglas": {},
        "version_parametros": version,
        "version_base": None,
        "guardar": guardar,
    }
    cuerpo.update(extra)
    return client.post("/api/v1/adquisicion/propuestas", json=cuerpo, headers=headers(rol))


def _propuesta_guardada(client, headers, rol="INGENIERO"):
    respuesta = _proponer(client, headers, rol=rol, guardar=True)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["valida"], cuerpo["errores"]
    assert cuerpo["version"] is not None
    return cuerpo["version"]




def test_simulacion_valida_mide_impacto_sin_registrar(api_real) -> None:
    client, headers, _ = api_real
    respuesta = _proponer(client, headers)
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["valida"], cuerpo["errores"]
    assert cuerpo["impacto"]["evaluados"] >= 200
    assert cuerpo["cambios_parametros"][0]["nombre"] == "humedad_admision_max"
    assert cuerpo["version"] is None, "una simulación no registra ninguna versión"


def test_la_simulacion_no_expone_identificadores_de_evaluaciones(api_real) -> None:
    """El ingeniero mide el efecto sobre el conjunto, no accede a unidades ajenas."""
    client, headers, _ = api_real
    cuerpo = _proponer(client, headers).json()
    for caso in cuerpo["impacto"]["casos"]:
        if caso["origen"] != "historica":
            continue
        opaco = caso["id"].split(":", 1)[1]
        assert opaco.isdigit(), f"identificador no opaco: {caso['id']}"
        with pytest.raises(ValueError):
            uuid.UUID(opaco)


def test_propuesta_sin_cambios_se_rechaza(api_real) -> None:
    client, headers, _ = api_real
    respuesta = _proponer(client, headers, parametros={})
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert not cuerpo["valida"]
    assert cuerpo["errores"]


def test_propuesta_sin_motivo_se_rechaza_en_el_contrato(api_real) -> None:
    client, headers, _ = api_real
    respuesta = _proponer(client, headers, motivo="")
    assert respuesta.status_code == 422, respuesta.text


def test_propuesta_con_contenido_invalido_se_rechaza(api_real) -> None:
    client, headers, _ = api_real
    respuesta = _proponer(
        client, headers, parametros={"parametro_que_no_existe": 1.0}
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert not cuerpo["valida"]
    assert any("parametro_que_no_existe" in e for e in cuerpo["errores"]), cuerpo["errores"]


def test_guardar_registra_la_propuesta_en_estado_propuesta(api_real) -> None:
    client, headers, _ = api_real
    version = _propuesta_guardada(client, headers)
    assert version["estado"] == "PROPUESTA"
    assert version["activa"] is False




@pytest.mark.parametrize("rol", ["PRODUCTOR", "TECNICO", "ADMINISTRADOR"])
def test_solo_el_ingeniero_del_conocimiento_opera_el_modulo(api_real, rol) -> None:
    client, headers, _ = api_real
    assert client.get("/api/v1/adquisicion/versiones", headers=headers(rol)).status_code == 403
    assert _proponer(client, headers, rol=rol).status_code == 403


def test_el_ingeniero_del_conocimiento_accede(api_real) -> None:
    client, headers, _ = api_real
    assert client.get("/api/v1/adquisicion/versiones", headers=headers("INGENIERO")).status_code == 200




def test_descartar_una_propuesta_y_repetir_el_descarte(api_real) -> None:
    client, headers, _ = api_real
    version = _propuesta_guardada(client, headers)
    ruta = f"/api/v1/adquisicion/versiones/{version['id']}/descartar"

    primera = client.post(ruta, json={"motivo": MOTIVO}, headers=headers("INGENIERO"))
    assert primera.status_code == 200, primera.text
    assert primera.json()["estado"] == "DESCARTADA"

    segunda = client.post(ruta, json={"motivo": MOTIVO}, headers=headers("INGENIERO"))
    assert segunda.status_code == 200, segunda.text
    assert segunda.json()["estado"] == "DESCARTADA"


def test_descartar_exige_motivo(api_real) -> None:
    client, headers, _ = api_real
    version = _propuesta_guardada(client, headers)
    respuesta = client.post(
        f"/api/v1/adquisicion/versiones/{version['id']}/descartar",
        json={"motivo": ""}, headers=headers("INGENIERO"),
    )
    assert respuesta.status_code == 422, respuesta.text


def test_no_se_activa_una_version_descartada(api_real) -> None:
    client, headers, _ = api_real
    version = _propuesta_guardada(client, headers)
    client.post(
        f"/api/v1/adquisicion/versiones/{version['id']}/descartar",
        json={"motivo": MOTIVO}, headers=headers("INGENIERO"),
    )
    respuesta = client.post(
        f"/api/v1/adquisicion/versiones/{version['id']}/activar",
        json={"motivo": MOTIVO}, headers=headers("REVISOR"),
    )
    assert respuesta.status_code == 409, respuesta.text
    assert "DESCARTADA" in respuesta.json()["mensaje"]




def test_activar_deja_la_anterior_como_superada(api_real, motor) -> None:
    client, headers, _ = api_real
    version = _propuesta_guardada(client, headers)
    anterior = next(
        v for v in client.get("/api/v1/adquisicion/versiones", headers=headers("INGENIERO")).json()
        if v["activa"]
    )

    respuesta = client.post(
        f"/api/v1/adquisicion/versiones/{version['id']}/activar",
        json={"motivo": MOTIVO}, headers=headers("REVISOR"),
    )
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["estado"] == "ACTIVADA"
    assert respuesta.json()["activa"] is True

    versiones = {
        v["id"]: v
        for v in client.get("/api/v1/adquisicion/versiones", headers=headers("INGENIERO")).json()
    }
    assert versiones[anterior["id"]]["estado"] == "SUPERADA"
    assert versiones[anterior["id"]]["activa"] is False
    assert sum(1 for v in versiones.values() if v["activa"]) == 1


def test_quien_propone_no_activa(api_real) -> None:
    """Separación de funciones: hacen falta cuatro ojos sobre un cambio de conocimiento."""
    client, headers, _ = api_real
    version = _propuesta_guardada(client, headers, rol="INGENIERO")
    respuesta = client.post(
        f"/api/v1/adquisicion/versiones/{version['id']}/activar",
        json={"motivo": MOTIVO}, headers=headers("INGENIERO"),
    )
    assert respuesta.status_code == 409, respuesta.text
    assert "no puede activarla" in respuesta.json()["mensaje"]

    revisada = client.post(
        f"/api/v1/adquisicion/versiones/{version['id']}/activar",
        json={"motivo": MOTIVO}, headers=headers("REVISOR"),
    )
    assert revisada.status_code == 200, revisada.text


def test_no_se_activa_dos_veces_la_misma_version(api_real) -> None:
    client, headers, _ = api_real
    version = _propuesta_guardada(client, headers)
    ruta = f"/api/v1/adquisicion/versiones/{version['id']}/activar"
    assert client.post(ruta, json={"motivo": MOTIVO}, headers=headers("REVISOR")).status_code == 200
    repetida = client.post(ruta, json={"motivo": MOTIVO}, headers=headers("REVISOR"))
    assert repetida.status_code == 409, repetida.text


def test_dos_activaciones_concurrentes_dejan_una_sola_version_activa(api_real, motor) -> None:
    """El candado de activación serializa; el índice parcial es la última defensa."""
    client, headers, _ = api_real
    primera = _propuesta_guardada(client, headers)
    segunda = _propuesta_guardada(client, headers)

    respuestas: list[int] = []
    barrera = threading.Barrier(2)

    def activar(version) -> None:  
        barrera.wait()
        respuesta = client.post(
            f"/api/v1/adquisicion/versiones/{version['id']}/activar",
            json={"motivo": MOTIVO}, headers=headers("REVISOR"),
        )
        respuestas.append(respuesta.status_code)

    hilos = [threading.Thread(target=activar, args=(v,)) for v in (primera, segunda)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=120)

    assert len(respuestas) == 2, "alguna activación no terminó"
    assert all(codigo in (200, 409) for codigo in respuestas), respuestas
    with motor.begin() as conexion:
        activas = conexion.execute(
            sa.text("SELECT count(*) FROM poscosegran.version_conocimiento WHERE activa")
        ).scalar_one()
    assert activas == 1




def test_cada_cambio_de_estado_queda_auditado_con_su_impacto(api_real, motor) -> None:
    client, headers, _ = api_real
    version = _propuesta_guardada(client, headers)
    client.post(
        f"/api/v1/adquisicion/versiones/{version['id']}/activar",
        json={"motivo": MOTIVO}, headers=headers("REVISOR"),
    )
    descartada = _propuesta_guardada(client, headers)
    client.post(
        f"/api/v1/adquisicion/versiones/{descartada['id']}/descartar",
        json={"motivo": MOTIVO}, headers=headers("INGENIERO"),
    )

    with motor.begin() as conexion:
        filas = conexion.execute(
            sa.text(
                "SELECT accion, resumen FROM poscosegran.auditoria "
                "WHERE recurso_id IN (:a, :b) ORDER BY ocurrido_en"
            ),
            {"a": version["id"], "b": descartada["id"]},
        ).all()
    acciones = {fila[0] for fila in filas}
    assert {
        "proponer_version_conocimiento",
        "activar_version_conocimiento",
        "descartar_version_conocimiento",
    } <= acciones, acciones

    activacion = next(f[1] for f in filas if f[0] == "activar_version_conocimiento")
    assert "impacto" in activacion, "la activación debe guardar el impacto que volvió a medir"
    assert activacion["impacto"]["evaluados"] >= 200
    assert activacion["superada"]
