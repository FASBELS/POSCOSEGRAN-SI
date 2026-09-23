"""Acceso a la tabla de tiempo de referencia de la base de conocimiento.

Los valores no están aquí: se leen de knowledge/base_conocimiento.yaml. Se conserva
este módulo para que las pruebas y los scripts puedan consultar la selección de
celda sin construir un motor completo.
"""

from __future__ import annotations

from decimal import Decimal

from ..sistema_experto import base_conocimiento
from ..sistema_experto.base_conocimiento import Celda


def seleccionar(humedad: Decimal, temperatura_c: Decimal) -> Celda | None:
    return base_conocimiento.cargar().tabla_tiempo.seleccionar(humedad, temperatura_c)
