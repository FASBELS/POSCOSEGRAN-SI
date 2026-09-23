"""Identidad verificada de quien realiza la petición."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Identidad:
    """Resultado de verificar el token más los roles leídos de la base.

    Los roles nunca provienen del token: el cliente no decide sus permisos.
    """

    id: uuid.UUID
    roles: frozenset[str] = field(default_factory=frozenset)
    id_solicitud: uuid.UUID = field(default_factory=uuid.uuid4)

    @property
    def es_tecnico(self) -> bool:
        return "TECNICO" in self.roles

    @property
    def es_productor(self) -> bool:
        return "PRODUCTOR" in self.roles

    @property
    def es_administrador(self) -> bool:
        return "ADMINISTRADOR" in self.roles

    @property
    def es_ingeniero_conocimiento(self) -> bool:
        """Propone y activa versiones de la base; no evalúa unidades por ese rol."""
        return "INGENIERO_CONOCIMIENTO" in self.roles
