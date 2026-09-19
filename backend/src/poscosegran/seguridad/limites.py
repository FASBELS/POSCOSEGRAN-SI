"""Límite de peticiones por usuario.

Implementación en memoria: sirve para un proceso. Con varias réplicas hace falta
un contador compartido; queda anotado como pendiente en docs/SEGURIDAD.md.
"""

from __future__ import annotations

import threading
import time
from collections import deque


class LimitadorVentana:
    def __init__(self, maximo_por_minuto: int) -> None:
        self._maximo = maximo_por_minuto
        self._eventos: dict[str, deque[float]] = {}
        self._cerrojo = threading.Lock()

    def permitir(self, clave: str) -> bool:
        ahora = time.monotonic()
        with self._cerrojo:
            cola = self._eventos.setdefault(clave, deque())
            while cola and (ahora - cola[0]) > 60.0:
                cola.popleft()
            if len(cola) >= self._maximo:
                return False
            cola.append(ahora)
            return True

    def limpiar(self) -> None:
        ahora = time.monotonic()
        with self._cerrojo:
            vacias = [k for k, c in self._eventos.items() if not c or (ahora - c[-1]) > 300]
            for clave in vacias:
                self._eventos.pop(clave, None)
