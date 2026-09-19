"""Registro de auditoría.

Nunca recibe el token, la cabecera Authorization ni el cuerpo completo de una
petición: solo un resumen con los campos que cambiaron.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from ..db.modelos import RegistroAuditoria
from ..seguridad.identidad import Identidad

_CLAVES_PROHIBIDAS = {
    "authorization", "token", "access_token", "refresh_token", "id_token",
    "password", "contrasena", "secreto", "apikey", "api_key", "service_role",
    "cookie", "set-cookie", "jwt",
}


def depurar(valor: Any) -> Any:
    """Quita cualquier clave que pueda contener una credencial, a cualquier nivel."""
    if isinstance(valor, dict):
        return {
            clave: ("[omitido]" if str(clave).lower() in _CLAVES_PROHIBIDAS else depurar(subvalor))
            for clave, subvalor in valor.items()
        }
    if isinstance(valor, list):
        return [depurar(elemento) for elemento in valor]
    return valor


def registrar(
    sesion: Session,
    identidad: Identidad | None,
    *,
    accion: str,
    recurso_tipo: str,
    recurso_id: uuid.UUID | None = None,
    metodo: str | None = None,
    ruta: str | None = None,
    estado_http: int | None = None,
    revision_resultante: int | None = None,
    resumen: dict[str, Any] | None = None,
) -> None:
    """Se añade a la misma transacción que el cambio: si algo falla, no queda rastro falso."""
    sesion.add(
        RegistroAuditoria(
            id_usuario=identidad.id if identidad else None,
            roles=sorted(identidad.roles) if identidad else [],
            accion=accion,
            recurso_tipo=recurso_tipo,
            recurso_id=recurso_id,
            metodo=metodo,
            ruta=ruta,
            estado_http=estado_http,
            revision_resultante=revision_resultante,
            id_solicitud=identidad.id_solicitud if identidad else uuid.uuid4(),
            resumen=depurar(resumen) if resumen is not None else None,
        )
    )
