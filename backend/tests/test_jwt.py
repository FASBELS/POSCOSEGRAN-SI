"""La verificación de credenciales no se relaja bajo ninguna configuración."""

from __future__ import annotations

import base64
import json
import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from poscosegran.config import Configuracion
from poscosegran.seguridad.jwt import CredencialInvalida, VerificadorJWT

SECRETO = "s" * 48
EMISOR = "https://emisor.ejemplo/auth/v1"
AUDIENCIA = "authenticated"


def _cfg(**cambios: object) -> Configuracion:
    base: dict[str, object] = {
        "entorno": "pruebas",
        "bd_url_app": "postgresql+psycopg://x:y@localhost/z",
        "jwt_modo": "SECRETO_COMPARTIDO",
        "jwt_algoritmos": ["HS256"],
        "jwt_secreto": SECRETO,
        "jwt_emisor": EMISOR,
        "jwt_audiencia": AUDIENCIA,
    }
    base.update(cambios)
    return Configuracion(**base)  


def _token(**cambios: object) -> str:
    ahora = datetime.now(UTC)
    cuerpo: dict[str, object] = {
        "sub": str(uuid.uuid4()),
        "iss": EMISOR,
        "aud": AUDIENCIA,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=10),
    }
    cuerpo.update(cambios)
    return jwt.encode(cuerpo, SECRETO, algorithm="HS256")


def test_token_valido_devuelve_sujeto() -> None:
    sujeto = uuid.uuid4()
    verificador = VerificadorJWT(_cfg())
    assert verificador.verificar(_token(sub=str(sujeto))) == sujeto


def test_token_expirado_se_rechaza() -> None:
    pasado = datetime.now(UTC) - timedelta(hours=2)
    token = _token(iat=pasado, exp=pasado + timedelta(minutes=1))
    with pytest.raises(CredencialInvalida):
        VerificadorJWT(_cfg()).verificar(token)


def test_emisor_distinto_se_rechaza() -> None:
    with pytest.raises(CredencialInvalida):
        VerificadorJWT(_cfg()).verificar(_token(iss="https://otro.ejemplo"))


def test_audiencia_distinta_se_rechaza() -> None:
    with pytest.raises(CredencialInvalida):
        VerificadorJWT(_cfg()).verificar(_token(aud="otra"))


def test_firma_ajena_se_rechaza() -> None:
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "iss": EMISOR,
            "aud": AUDIENCIA,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(minutes=5),
        },
        "o" * 48,
        algorithm="HS256",
    )
    with pytest.raises(CredencialInvalida):
        VerificadorJWT(_cfg()).verificar(token)


def test_algoritmo_none_se_rechaza() -> None:
    """Token sin firma, construido a mano: el verificador no debe aceptarlo jamás."""
    def b64(datos: dict[str, object]) -> str:
        crudo = json.dumps(datos, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(crudo).decode("ascii").rstrip("=")

    vencimiento = int((datetime.now(UTC) + timedelta(minutes=5)).timestamp())
    token = (
        b64({"alg": "none", "typ": "JWT"})
        + "."
        + b64({"sub": str(uuid.uuid4()), "iss": EMISOR, "aud": AUDIENCIA,
               "iat": vencimiento - 300, "exp": vencimiento})
        + "."
    )
    with pytest.raises(CredencialInvalida):
        VerificadorJWT(_cfg()).verificar(token)


def test_sujeto_sin_forma_de_uuid_se_rechaza() -> None:
    with pytest.raises(CredencialInvalida):
        VerificadorJWT(_cfg()).verificar(_token(sub="administrador"))


def test_token_sin_expiracion_se_rechaza() -> None:
    token = jwt.encode(
        {"sub": str(uuid.uuid4()), "iss": EMISOR, "aud": AUDIENCIA, "iat": datetime.now(UTC)},
        SECRETO,
        algorithm="HS256",
    )
    with pytest.raises(CredencialInvalida):
        VerificadorJWT(_cfg()).verificar(token)


def test_configuracion_rechaza_secreto_compartido_en_produccion() -> None:
    with pytest.raises(ValueError):
        _cfg(entorno="produccion")


def test_configuracion_rechaza_jwks_con_algoritmo_simetrico() -> None:
    with pytest.raises(ValueError):
        _cfg(jwt_modo="JWKS", jwt_jwks_url="https://ejemplo/jwks.json", jwt_algoritmos=["HS256"])


def test_configuracion_rechaza_algoritmo_desconocido() -> None:
    with pytest.raises(ValueError):
        _cfg(jwt_algoritmos=["XX999"])
