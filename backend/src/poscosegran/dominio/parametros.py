"""Parámetros del prototipo, sección 3.1 de la base 2.0.

Se modifican con versión, motivo y responsable, nunca como ajuste oculto del
motor. La versión viaja en cada evaluación para poder reproducir el resultado.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

VERSION_PARAMETROS = "1.0"
VERSION_MOTOR = "0.7.0"


@dataclass(frozen=True, slots=True)
class Parametros:
    humedad_base_max: Decimal = Decimal("13")
    humedad_admision_max: Decimal = Decimal("14")
    temperatura_alerta: Decimal = Decimal("25")
    hr_almacen_no_hermetico_max_exclusiva: Decimal = Decimal("60")
    aw_alerta: Decimal = Decimal("0.70")
    aumento_termico_alerta: Decimal = Decimal("2")
    intervalo_termico_max_horas: int = 720
    hr_aireacion_max_exclusiva: Decimal = Decimal("70")
    muestra_fria_umbral: Decimal = Decimal("4.4")
    plazo_corto_max_dias: int = 30
    control_no_hermetico_normal_dias: int = 14
    control_con_riesgo_dias: int = 7
    control_exterior_hermetico_normal_dias: int = 30
    control_almacen_sin_riesgo_dias: int = 14
    vida_alerta: Decimal = Decimal("0.80")
    vida_limite: Decimal = Decimal("1.00")
    limite_calido_no_hermetico_dias: int = 90
    insectos_temperatura_min: Decimal = Decimal("15")
    insectos_temperatura_max: Decimal = Decimal("35")
    estiba_piso_min: Decimal = Decimal("0.15")
    estiba_pared_min: Decimal = Decimal("0.50")
    estiba_techo_min: Decimal = Decimal("1.00")
    suciedad_animal_max: Decimal = Decimal("0.1")
    defectuosos_max: Decimal = Decimal("7")
    enfermos_max: Decimal = Decimal("0.5")
    quebrados_max: Decimal = Decimal("6")
    materia_organica_max: Decimal = Decimal("1.5")
    materia_inorganica_max: Decimal = Decimal("0.5")

    version: str = VERSION_PARAMETROS


PARAMETROS = Parametros()
