"""Punto de entrada del motor para el resto del backend.

El motor de inferencia vive en poscosegran.sistema_experto y es genérico: todo el
conocimiento del dominio —reglas, umbrales, tablas y prioridades— se lee de la
base de conocimiento. Este módulo solo decide qué base usar cuando el llamador no
indica una: la de los archivos del repositorio, que es la semilla de la versión
activa.

En producción el servicio de evaluaciones pasa siempre la versión activa de la
base de datos, de modo que el conocimiento adquirido gobierna las decisiones.
"""

from __future__ import annotations

from ..sistema_experto import base_conocimiento
from ..sistema_experto.base_conocimiento import BaseConocimiento
from ..sistema_experto.calculos import CalculosTiempo
from ..sistema_experto.motor import VERSION_MOTOR, Motor, Resultado
from .hechos import Instantanea

__all__ = ["CalculosTiempo", "Resultado", "VERSION_MOTOR", "evaluar"]


def evaluar(instantanea: Instantanea, base: BaseConocimiento | None = None) -> Resultado:
    return Motor(base or base_conocimiento.cargar()).evaluar(instantanea)
