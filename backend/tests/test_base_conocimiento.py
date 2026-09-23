"""Pruebas de la arquitectura de sistema experto.

Demuestran, con el código y no con la documentación, que:
  * el conocimiento está en la base y no en el motor (separación);
  * la base se valida antes de usarse;
  * el módulo de explicación reconstruye lo que ocurrió;
  * el módulo de adquisición mide el impacto de un cambio antes de activarlo.
"""

from __future__ import annotations

import ast
import copy
import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from casos.base import base as caso_base
from casos.base import con, desconocido, num
from poscosegran.dominio.hechos import Fase
from poscosegran.dominio.motor import evaluar
from poscosegran.sistema_experto import adquisicion, base_conocimiento, serializacion
from poscosegran.sistema_experto.base_conocimiento import BaseInvalida, desde_contenido
from poscosegran.sistema_experto.explicacion import explicar, por_que_se_pide
from poscosegran.sistema_experto.motor import Motor

PAQUETE = Path(base_conocimiento.__file__).parent


@pytest.fixture(scope="module")
def activa():
    return base_conocimiento.cargar()


def _contenido(activa):
    return copy.deepcopy(dict(activa.contenido))


def _errores(contenido) -> list[str]:
    with pytest.raises(BaseInvalida) as error:
        desde_contenido(contenido)
    return error.value.errores


# --- Base de conocimiento -----------------------------------------------------------


def test_la_base_del_repositorio_es_valida(activa) -> None:
    assert len(activa.parametros) == 29
    assert {r.regla for r in activa.reglas if r.regla.startswith("R") and "." not in r.regla} == {
        f"R{n:02d}" for n in range(1, 30)
    }
    assert [r.rama for r in activa.resolucion] == [f"R30.{n}" for n in range(1, 10)]


def test_ninguna_clave_yaml_se_convierte_en_booleano(activa) -> None:
    """En YAML 1.1 `no:` se lee como False. El operador se llama `negar` por eso."""
    def claves(nodo):
        if isinstance(nodo, dict):
            for clave, valor in nodo.items():
                yield clave
                yield from claves(valor)
        elif isinstance(nodo, list):
            for elemento in nodo:
                yield from claves(elemento)

    assert not [c for c in claves(activa.contenido) if isinstance(c, bool)]


def test_el_motor_no_contiene_umbrales_del_dominio(activa) -> None:
    """Ningún valor de parámetro aparece como literal en el motor ni en el lenguaje.

    Se excluyen los enteros hasta 10: el motor los usa como números de paso del
    formulario y en aritmética, y coinciden por azar con umbrales pequeños.
    """
    valores = {
        float(p.valor) for p in activa.parametros.values()
        if not (p.valor == p.valor.to_integral() and p.valor <= 10)
    }
    for modulo in ("motor.py", "lenguaje.py", "base_hechos.py", "calculos.py"):
        arbol = ast.parse((PAQUETE / modulo).read_text(encoding="utf-8"))
        literales = {
            float(n.value) for n in ast.walk(arbol)
            if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)
        }
        assert not (literales & valores), f"{modulo} contiene umbrales: {literales & valores}"


def test_cambiar_un_parametro_cambia_la_decision(activa) -> None:
    """Separación: el mismo motor decide distinto con otra base."""
    inst = con(caso_base(), humedad_grano=num("humedad_grano", "14.5"))
    assert Motor(activa).evaluar(inst).decision_final == "BLOQUEAR_INGRESO"

    contenido = _contenido(activa)
    contenido["operativa"]["parametros"]["humedad_admision_max"]["valor"] = 15
    contenido["operativa"]["parametros"]["humedad_base_max"]["valor"] = 14.5
    contenido["operativa"]["version_parametros"] = "prueba"
    otra = desde_contenido(contenido)
    resultado = Motor(otra).evaluar(inst)
    assert resultado.decision_final != "BLOQUEAR_INGRESO"
    assert "R01" not in resultado.reglas_activadas
    assert resultado.version_parametros == "prueba"
    assert resultado.hash_base != activa.hash


def test_retirar_una_regla_la_desactiva(activa) -> None:
    contenido = _contenido(activa)
    contenido["operativa"]["reglas"] = [r for r in contenido["operativa"]["reglas"] if r["id"] != "R18"]
    # El cargador exige las 29 reglas del catálogo: retirarla invalida la base.
    assert any("R18" in e for e in _errores(contenido))


@pytest.mark.parametrize(
    "mutacion, fragmento",
    [
        (lambda o: o["reglas"][2].update({"si": {"sumar": [1, 2]}}), "exactamente un operador"),
        (lambda o: o["reglas"][2]["si"].update({"sumar": 1}), "claves no reconocidas"),
        (lambda o: o["reglas"][2].update({"si": {"dato": "humedad_grano", "op": "GT", "valor": {"param": "inexistente"}}}), "parámetro desconocido"),
        (lambda o: o["reglas"][2].update({"si": {"definicion": "inexistente"}}), "definición desconocida"),
        (lambda o: o["reglas"][2].update({"si": {"dato": "humedad_grano", "op": "MAYOR", "valor": 1}}), "comparación desconocido"),
        (lambda o: o["definiciones"]["estiba_apta"].update({"todos": [{"definicion": "estiba_apta"}]}), "ciclo"),
        (lambda o: o["resolucion"].pop(), "siempre"),
        (lambda o: o["resolucion"].reverse(), "no coinciden"),
        (lambda o: o["parametros"]["vida_alerta"].update({"valor": 1.2}), "restricción incumplida"),
        (lambda o: o["parametros"]["humedad_base_max"].update({"valor": 15}), "restricción incumplida"),
        (lambda o: o["reglas"][2]["entonces"].update({"solicitudes": ["APLAUDIR"]}), "solicitud desconocida"),
        (lambda o: o["fundamentos"]["R24"].update({"fuentes": []}), "exige al menos una fuente"),
    ],
)
def test_el_validador_rechaza_bases_defectuosas(activa, mutacion, fragmento) -> None:
    contenido = _contenido(activa)
    mutacion(contenido["operativa"])
    assert any(fragmento in e for e in _errores(contenido)), _errores(contenido)


def test_casos_de_referencia_se_reproducen(activa) -> None:
    ruta = base_conocimiento.ruta_por_defecto() / "casos_referencia.json"
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    casos = serializacion.cargar_casos(contenido)
    assert len(casos) >= 200
    assert {e["decision"] for _, _, e in casos} == set(base_conocimiento.DECISIONES)
    motor = Motor(activa)
    fallos = []
    for ident, inst, esperado in casos:
        r = motor.evaluar(inst)
        obtenido = {
            "decision": r.decision_final,
            "rama": r.rama_r30,
            "reglas": sorted(r.reglas_activadas),
            "motivos": sorted(m.id for m in r.motivos),
            "pendientes": sorted({p.campo for p in r.datos_pendientes}),
        }
        if obtenido != esperado:
            fallos.append(ident)
    assert not fallos, f"{len(fallos)} casos cambian: {fallos[:5]}"


def test_serializacion_ida_y_vuelta() -> None:
    inst = replace(caso_base(), fase=Fase.SEGUIMIENTO)
    ida = serializacion.a_json(inst)
    assert serializacion.a_json(serializacion.desde_json(json.loads(json.dumps(ida)))) == ida


# --- Motor --------------------------------------------------------------------------------


def test_traza_registra_encadenamiento_en_dos_pasadas() -> None:
    """R19 depende de R20, que va después en la agenda: se dispara en la pasada 2."""
    from casos.base import bul

    r = evaluar(con(caso_base(), heces_visibles=bul("heces_visibles", True)))
    pasos = {a.regla: a for a in r.traza}
    assert pasos["R20"].pasada == 1
    assert pasos["R19"].pasada == 2
    assert "CONTAMINACION_ANIMAL_OBSERVADA" in pasos["R19"].soportes
    assert r.decision_final == "CUARENTENA"


def test_resolucion_evalua_todas_las_ramas_pero_decide_una() -> None:
    r = evaluar(caso_base())
    assert [x.rama for x in r.ramas] == [f"R30.{n}" for n in range(1, 10)]
    assert r.rama_r30 == "R30.8"
    assert next(x for x in r.ramas if x.rama == "R30.9").valor == "VERDADERO"


# --- Explicación ------------------------------------------------------------------------


def test_explicacion_como(activa) -> None:
    from casos.base import bul

    e = explicar(evaluar(con(caso_base(), moho_visible=bul("moho_visible", True))), activa)
    assert [p.regla for p in e.cadena] == ["R18", "R19"]
    assert e.cadena[0].porque == ("moho visible",)
    assert "R19" in e.resumen
    assert e.etiqueta == "Separar y solicitar evaluación técnica"


def test_explicacion_por_que_no(activa) -> None:
    inst = con(caso_base(), equipo_humedad_verificado=desconocido("equipo_humedad_verificado"))
    e = explicar(evaluar(inst), activa)
    assert e.decision == "SIN_CONCLUSION_AUTOMATICA"
    r308 = next(r for r in e.por_que_no if r.rama == "R30.8")
    assert any("equipo verificado (desconocido)" in f for f in r308.faltan)


def test_explicacion_de_autorizacion(activa) -> None:
    e = explicar(evaluar(caso_base()), activa)
    assert e.decision == "AUTORIZAR_ALMACENAMIENTO"
    assert "se cumplieron todas sus condiciones" in e.resumen
    assert {"R03", "R06"} <= {p.regla for p in e.cadena}
    assert e.por_que_no == ()


def test_por_que_se_pide(activa) -> None:
    assert {"R01", "R02", "R03"} <= set(por_que_se_pide("humedad_grano", activa).reglas)
    assert set(por_que_se_pide("hr_aire_exterior", activa).reglas) == {"R10", "R11"}
    assert por_que_se_pide("observaciones_libres", activa).reglas == ()


# --- Adquisición ------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pocos_casos():
    return adquisicion.cargar_casos_referencia()[:80]


def test_propuesta_valida_mide_impacto(activa, pocos_casos) -> None:
    p = adquisicion.proponer(
        activa,
        motivo="Endurecer la admisión tras revisar la guía regional",
        version_parametros="1.1",
        parametros={"humedad_admision_max": "13.5"},
        casos=pocos_casos,
    )
    assert p.valida, p.errores
    assert p.cambios_parametros[0].anterior == Decimal("14")
    assert p.impacto is not None and p.impacto.evaluados == len(pocos_casos)
    assert p.base is not None and p.base.parametro("humedad_admision_max") == Decimal("13.5")
    # La versión activa no cambia: la propuesta es una copia.
    assert activa.parametro("humedad_admision_max") == Decimal("14")


def test_propuesta_sin_cambios_o_sin_motivo_se_rechaza(activa, pocos_casos) -> None:
    sin_cambios = adquisicion.proponer(activa, motivo="Motivo suficientemente largo", version_parametros="1.1",
                                       parametros={"humedad_admision_max": 14}, casos=pocos_casos)
    assert not sin_cambios.valida and any("no cambia nada" in e for e in sin_cambios.errores)
    sin_motivo = adquisicion.proponer(activa, motivo="corto", version_parametros="1.1",
                                      parametros={"humedad_admision_max": 13}, casos=pocos_casos)
    assert not sin_motivo.valida and any("motivo" in e for e in sin_motivo.errores)
    misma_version = adquisicion.proponer(activa, motivo="Motivo suficientemente largo",
                                         parametros={"humedad_admision_max": 13.8}, casos=pocos_casos)
    assert any("versión" in e for e in misma_version.errores)


def test_propuesta_incoherente_se_rechaza(activa, pocos_casos) -> None:
    p = adquisicion.proponer(activa, motivo="Prueba de incoherencia entre umbrales", version_parametros="1.1",
                             parametros={"humedad_base_max": 15}, casos=pocos_casos)
    assert not p.valida
    assert any("humedad_base_max" in e and "humedad_admision_max" in e for e in p.errores)
    assert p.base is None


def test_propuesta_que_relaja_advierte(activa) -> None:
    inst = con(caso_base(), hr_almacen=num("hr_almacen", "62", "PCT_HR"))
    assert evaluar(inst).decision_final == "CORREGIR_Y_REEVALUAR"
    p = adquisicion.proponer(activa, motivo="Relajar HR del almacén para zonas altoandinas", version_parametros="1.1",
                             parametros={"hr_almacen_max": 65}, casos=[("manual:hr62", "manual", inst)])
    assert p.valida
    assert p.impacto.nuevas_autorizaciones == 1
    assert any("pasarían a autorizarse" in a for a in p.advertencias)
    assert any("umbrales publicados" in a for a in p.advertencias)


def test_propuesta_de_regla_exige_version_de_base(activa, pocos_casos) -> None:
    contenido = _contenido(activa)
    r26 = next(r for r in contenido["operativa"]["reglas"] if r["id"] == "R26")
    r26["entonces"]["solicitudes"] = ["SUSPENSION"]
    p = adquisicion.proponer(activa, motivo="Contaminantes químicos suspenden el almacenamiento",
                             reglas={"R26": r26}, casos=pocos_casos)
    assert any("nueva versión de la base" in e for e in p.errores)
    p = adquisicion.proponer(activa, motivo="Contaminantes químicos suspenden el almacenamiento",
                             version_base="2.1", reglas={"R26": r26}, casos=pocos_casos)
    assert p.valida, p.errores
    assert p.cambios_reglas[0].tipo == "MODIFICADA"


def test_inconsistencia_detectada_fuera_del_motor_exige_correccion() -> None:
    """La ruta de evaluación registra contradicciones con el historial persistido."""
    r = evaluar(replace(caso_base(), datos_inconsistentes=("vida_previa_menor_al_historial_persistido",)))
    assert r.decision_final == "CORREGIR_Y_REEVALUAR"
    motivo = next(m for m in r.motivos if m.id == "VALIDACION:DATOS_INCONSISTENTES")
    assert "vida_previa_menor_al_historial_persistido" in motivo.mensaje
