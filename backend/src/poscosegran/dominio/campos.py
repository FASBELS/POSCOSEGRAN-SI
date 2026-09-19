"""Campos capturables: tipo, unidad y paso del formulario.

El servidor rechaza cualquier clave fuera de esta lista y valida cada valor
contra su fila. Un texto no se convierte en booleano ni un booleano en número.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Tipo = Literal["N", "B", "X", "F"]


@dataclass(frozen=True, slots=True)
class Campo:
    tipo: Tipo
    unidad: str
    paso: int
    admite_no_aplica: bool = False


def _n(unidad: str, paso: int, na: bool = False) -> Campo:
    return Campo("N", unidad, paso, na)


def _b(paso: int, na: bool = False) -> Campo:
    return Campo("B", "BOOLEANO", paso, na)


def _x(paso: int, na: bool = False) -> Campo:
    return Campo("X", "TEXTO", paso, na)


def _f(paso: int, na: bool = False) -> Campo:
    return Campo("F", "TEXTO", paso, na)


CAMPOS: dict[str, Campo] = {
    # Paso 1 — identificación y modalidad
    "clima_calido": _b(1),
    # Paso 2 — mediciones y procedimiento
    "humedad_grano": _n("PCT_BH", 2),
    "metodo_humedad": _x(2),
    "temperatura_muestra": _n("CELSIUS", 2, True),
    "equipo_humedad_verificado": _b(2),
    "muestra_representativa": _b(2),
    "procedimiento_medicion_cumplido": _b(2),
    "aw_medida": _b(2),
    "actividad_agua": _n("FRACCION", 2, True),
    "temperatura_grano": _n("CELSIUS", 2),
    "temperatura_grano_previa": _n("CELSIUS", 2, True),
    "punto_medicion": _x(2),
    "punto_medicion_previo": _x(2, True),
    "metodo_termico": _x(2),
    "metodo_termico_previo": _x(2, True),
    "temperatura_almacen": _n("CELSIUS", 2),
    "hr_almacen": _n("PCT_HR", 2),
    "temperatura_aire_exterior": _n("CELSIUS", 2, True),
    "hr_aire_exterior": _n("PCT_HR", 2, True),
    "lluvia_o_niebla": _b(2, True),
    "humedad_equilibrio_maiz": _n("PCT_BH", 2, True),
    "tabla_equilibrio_id": _x(2, True),
    # Paso 3 — plagas, deterioro y calidad física
    "insectos_vivos": _b(3),
    "granos_perforados": _b(3),
    "polvillo_inusual": _b(3),
    "exuvias_larvas": _b(3),
    "ruido_alimentacion": _b(3),
    "heces_roedores_aves_entorno": _b(3),
    "huellas": _b(3),
    "bolsa_roida": _b(3),
    "grano_derramado_por_plaga": _b(3),
    "moho_visible": _b(3),
    "olor_anormal": _b(3),
    "condensacion_interna": _b(3, True),
    "germinacion": _b(3),
    "suciedad_origen_animal": _n("PCT_MASA", 3),
    "heces_visibles": _b(3),
    "granos_defectuosos": _n("PCT_MASA", 3),
    "granos_enfermos": _n("PCT_MASA", 3),
    "granos_quebrados": _n("PCT_MASA", 3),
    "materia_organica_extrana": _n("PCT_MASA", 3),
    "materia_inorganica_extrana": _n("PCT_MASA", 3),
    # Paso 4 — recipiente, estiba y almacén
    "sello_integro": _b(4, True),
    "perforacion_barrera": _b(4, True),
    "bolsa_abierta_sin_resellar": _b(4, True),
    "cierre_seguro": _b(4),
    "recipiente_limpio": _b(4),
    "recipiente_seco": _b(4),
    "material_grado_alimentario": _b(4),
    "recipiente_resistente": _b(4),
    "distancia_piso": _n("METROS", 4),
    "distancia_pared": _n("METROS", 4),
    "distancia_techo": _n("METROS", 4),
    "fecha_limpieza_general": _f(4),
    "limpieza_previa_nuevo_lote": _b(4, True),
    "limpieza_diaria": _b(4),
    "limpieza_tras_operaciones": _b(4, True),
    "polvo_humo_gases_vapores": _b(4),
    "quimicos_combustibles_en_almacen": _b(4),
    # Paso 5 — historial y control
    "fecha_inspeccion_grano": _f(5, True),
    "fecha_inspeccion_exterior": _f(5, True),
    "fecha_control_almacen": _f(5),
    "ingreso_inspeccionado": _b(5, True),
    "hay_evento_que_invalida_control": _b(5),
    "sensor_interno_hermetico": _b(5, True),
    "temperatura_ambiente_maxima_intervalo": _n("CELSIUS", 5, True),
}

# Dominios numéricos admitidos. Fuera de rango el dato se conserva como INVALIDO
# y produce corrección, pero no participa en comparaciones.
DOMINIOS: dict[str, tuple[float, float]] = {
    "humedad_grano": (0.0, 100.0),
    "actividad_agua": (0.0, 1.0),
    "hr_almacen": (0.0, 100.0),
    "hr_aire_exterior": (0.0, 100.0),
    "humedad_equilibrio_maiz": (0.0, 100.0),
    "suciedad_origen_animal": (0.0, 100.0),
    "granos_defectuosos": (0.0, 100.0),
    "granos_enfermos": (0.0, 100.0),
    "granos_quebrados": (0.0, 100.0),
    "materia_organica_extrana": (0.0, 100.0),
    "materia_inorganica_extrana": (0.0, 100.0),
    "distancia_piso": (0.0, 50.0),
    "distancia_pared": (0.0, 50.0),
    "distancia_techo": (0.0, 50.0),
    "temperatura_grano": (-30.0, 90.0),
    "temperatura_grano_previa": (-30.0, 90.0),
    "temperatura_almacen": (-30.0, 90.0),
    "temperatura_aire_exterior": (-30.0, 90.0),
    "temperatura_muestra": (-30.0, 90.0),
    "temperatura_ambiente_maxima_intervalo": (-30.0, 90.0),
}

METODOS_HUMEDAD = ("INSTRUMENTAL", "LABORATORIO", "ESTIMACION_INDIRECTA")
