"""Acceso de desarrollo explícito. Nunca se monta en producción."""
import hmac
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ..config import obtener_configuracion
from ..db.modelos import Usuario
from ..db.sesion import unidad_de_trabajo
from ..seguridad.limites import LimitadorVentana

enrutador = APIRouter(prefix="/auth/local", tags=["desarrollo"])
limite = LimitadorVentana(10)
USUARIOS = {
    "productor": uuid.UUID("00000000-0000-4000-8000-000000000001"),
    "tecnico": uuid.UUID("00000000-0000-4000-8000-000000000002"),
    "administrador": uuid.UUID("00000000-0000-4000-8000-000000000003"),
    "ingeniero": uuid.UUID("00000000-0000-4000-8000-000000000004"),
    "revisor": uuid.UUID("00000000-0000-4000-8000-000000000005"),
}
ALIAS_USUARIOS = {"testeo": "productor"}

# Rol de cada usuario local; el nombre de usuario no siempre coincide con el rol.
ROLES_LOCALES = {
    "productor": "PRODUCTOR",
    "tecnico": "TECNICO",
    "administrador": "ADMINISTRADOR",
    "ingeniero": "INGENIERO_CONOCIMIENTO",
    "revisor": "INGENIERO_CONOCIMIENTO",
}


class AccesoLocal(BaseModel):
    usuario: str
    password: str


@enrutador.post("/sesion")
def sesion_local(entrada: AccesoLocal, request: Request) -> dict[str, str | int]:
    cfg = obtener_configuracion()
    if not limite.permitir(request.client.host if request.client else "local"):
        raise HTTPException(429, "Demasiados intentos; espere un minuto")
    usuario = ALIAS_USUARIOS.get(entrada.usuario, entrada.usuario)
    identificador = USUARIOS.get(usuario)
    if identificador is None or not hmac.compare_digest(
        entrada.password.encode(), (cfg.auth_local_password or "").encode()
    ):
        raise HTTPException(401, "Credenciales incorrectas")
    with unidad_de_trabajo() as db:
        usuario = db.get(Usuario, identificador)
        if usuario is None or not usuario.activo:
            raise HTTPException(403, "Ejecute la preparación del entorno local")
    ahora = datetime.now(UTC)
    vencimiento = ahora + timedelta(hours=8)
    assert cfg.jwt_secreto is not None
    token = jwt.encode({"sub": str(identificador), "iat": ahora, "exp": vencimiento,
                        "aud": cfg.jwt_audiencia, "iss": cfg.jwt_emisor},
                       cfg.jwt_secreto, algorithm="HS256")
    return {"access_token": token, "expires_at": int(vencimiento.timestamp())}
