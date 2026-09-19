"""Caso base B de la sección 9 y utilidades para construirlo.

Lote chulpi en INGRESO, no hermético, humedad confirmada 12,5 %, grano y almacén
a 10 °C, HR 50 %, clima no cálido, listas físicas y sanitarias conformes,
inspecciones de ingreso completas, sin incidencias, vida previa documentada 0,10,
plazo restante 20 días y tiempo de referencia 200 días.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from poscosegran.dominio.hechos import (
    Controles,
    Fase,
    Historial,
    Instantanea,
    Modalidad,
    Plan,
)
from poscosegran.dominio.valores import Conjunto, Dato, EstadoDato, F, V

AHORA = datetime(2026, 9, 13, 9, 0, tzinfo=UTC)


def num(campo: str, valor: str, unidad: str = "PCT_BH", **extra: Any) -> Dato:
    return Dato(
        campo=campo,
        estado=EstadoDato.VALIDO,
        valor=Decimal(valor),
        unidad=unidad,
        fecha_observacion=AHORA,
        metodo="INSTRUMENTAL",
        **extra,
    )


def bul(campo: str, valor: bool) -> Dato:
    return Dato(
        campo=campo,
        estado=EstadoDato.VALIDO,
        valor=valor,
        unidad="BOOLEANO",
        fecha_observacion=AHORA,
        metodo="OBSERVACION",
    )


def txt(campo: str, valor: str) -> Dato:
    return Dato(
        campo=campo,
        estado=EstadoDato.VALIDO,
        valor=valor,
        unidad="TEXTO",
        fecha_observacion=AHORA,
        metodo="REGISTRO",
    )


def fec(campo: str, valor: datetime) -> Dato:
    return Dato(
        campo=campo,
        estado=EstadoDato.VALIDO,
        valor=valor,
        unidad="TEXTO",
        fecha_observacion=AHORA,
        metodo="REGISTRO",
    )


def desconocido(campo: str) -> Dato:
    return Dato(campo=campo, estado=EstadoDato.DESCONOCIDO)


def datos_base() -> dict[str, Dato]:
    datos: dict[str, Dato] = {}

    # Humedad y su confirmación
    datos["humedad_grano"] = num("humedad_grano", "12.5")
    datos["metodo_humedad"] = txt("metodo_humedad", "INSTRUMENTAL")
    datos["temperatura_muestra"] = num("temperatura_muestra", "10", "CELSIUS")
    for campo in (
        "equipo_humedad_verificado",
        "muestra_representativa",
        "procedimiento_medicion_cumplido",
    ):
        datos[campo] = bul(campo, True)

    datos["aw_medida"] = bul("aw_medida", False)

    # Temperaturas y ambiente
    datos["temperatura_grano"] = num("temperatura_grano", "10", "CELSIUS")
    datos["punto_medicion"] = txt("punto_medicion", "CENTRO")
    datos["metodo_termico"] = txt("metodo_termico", "SONDA")
    datos["temperatura_almacen"] = num("temperatura_almacen", "10", "CELSIUS")
    datos["hr_almacen"] = num("hr_almacen", "50", "PCT_HR")

    # Plagas y deterioro: observados y negativos
    for campo in (
        "insectos_vivos", "granos_perforados", "polvillo_inusual", "exuvias_larvas",
        "ruido_alimentacion", "heces_roedores_aves_entorno", "huellas", "bolsa_roida",
        "grano_derramado_por_plaga", "moho_visible", "olor_anormal", "condensacion_interna",
        "germinacion", "heces_visibles",
    ):
        datos[campo] = bul(campo, False)

    # Calidad física
    datos["suciedad_origen_animal"] = num("suciedad_origen_animal", "0.0", "PCT_MASA")
    datos["granos_defectuosos"] = num("granos_defectuosos", "2.0", "PCT_MASA")
    datos["granos_enfermos"] = num("granos_enfermos", "0.1", "PCT_MASA")
    datos["granos_quebrados"] = num("granos_quebrados", "3.0", "PCT_MASA")
    datos["materia_organica_extrana"] = num("materia_organica_extrana", "0.5", "PCT_MASA")
    datos["materia_inorganica_extrana"] = num("materia_inorganica_extrana", "0.1", "PCT_MASA")

    # Recipiente y estiba
    for campo in (
        "recipiente_limpio", "recipiente_seco", "material_grado_alimentario",
        "recipiente_resistente", "cierre_seguro",
    ):
        datos[campo] = bul(campo, True)
    datos["distancia_piso"] = num("distancia_piso", "0.20", "METROS")
    datos["distancia_pared"] = num("distancia_pared", "0.60", "METROS")
    datos["distancia_techo"] = num("distancia_techo", "1.20", "METROS")

    # Higiene y calidad del aire
    datos["fecha_limpieza_general"] = fec("fecha_limpieza_general", AHORA - timedelta(days=3))
    datos["limpieza_diaria"] = bul("limpieza_diaria", True)
    datos["limpieza_previa_nuevo_lote"] = bul("limpieza_previa_nuevo_lote", True)
    datos["limpieza_tras_operaciones"] = bul("limpieza_tras_operaciones", True)
    datos["polvo_humo_gases_vapores"] = bul("polvo_humo_gases_vapores", False)
    datos["quimicos_combustibles_en_almacen"] = bul("quimicos_combustibles_en_almacen", False)

    return datos


def base(**cambios: Any) -> Instantanea:
    datos = cambios.pop("datos", None) or datos_base()
    inst = Instantanea(
        fecha_evaluacion=AHORA,
        fase=Fase.INGRESO,
        tipo_almacenamiento=Modalidad.NO_HERMETICO,
        clima_calido=F,
        datos=Conjunto(datos),
        historial=Historial(
            fecha_inicio_historial=AHORA - timedelta(days=20),
            vida_previa_documentada=Decimal("0.10"),
            evidencia_vida_previa="registro de secado y envasado",
        ),
        dias_almacenados=0,
        dias_previstos_restantes=20,
        fecha_salida_prevista=AHORA + timedelta(days=20),
        controles=Controles(
            fecha_inspeccion_grano=AHORA,
            fecha_control_almacen=AHORA,
            ingreso_inspeccionado=V,
            hay_evento_que_invalida_control=F,
        ),
        plan=Plan(),
    )
    return replace(inst, **cambios) if cambios else inst


def con(inst: Instantanea, **datos: Dato) -> Instantanea:
    """Devuelve la instantánea con los datos indicados sustituidos."""
    mezcla = dict(inst.datos.datos)
    mezcla.update(datos)
    return replace(inst, datos=Conjunto(mezcla))


def sin(inst: Instantanea, *campos: str) -> Instantanea:
    mezcla = dict(inst.datos.datos)
    for campo in campos:
        mezcla[campo] = desconocido(campo)
    return replace(inst, datos=Conjunto(mezcla))
