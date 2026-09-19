"""Verificación de credenciales, configurable entre JWKS y secreto compartido.

Reglas que no se relajan en ningún modo:
- El algoritmo se toma de una lista permitida, nunca de la cabecera del token.
- 'none' se rechaza siempre.
- Emisor, audiencia y expiración se comprueban contra valores exactos.
- Un token sin 'sub' con forma de UUID no identifica a nadie.
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient

from ..config import Configuracion


class CredencialInvalida(Exception):
    """El token no se pudo verificar. El motivo no se detalla al cliente."""

    def __init__(self, motivo: str) -> None:
        super().__init__(motivo)
        self.motivo = motivo


class _CacheJWKS:
    """Cache con expiración propia: PyJWKClient no controla el TTL por sí solo."""

    def __init__(self, url: str, ttl_segundos: int) -> None:
        self._url = url
        self._ttl = ttl_segundos
        self._cliente: PyJWKClient | None = None
        self._obtenido_en = 0.0
        self._cerrojo = threading.Lock()

    def cliente(self) -> PyJWKClient:
        with self._cerrojo:
            vencido = (time.monotonic() - self._obtenido_en) > self._ttl
            if self._cliente is None or vencido:
                self._cliente = PyJWKClient(self._url, cache_keys=True, timeout=5)
                self._obtenido_en = time.monotonic()
            return self._cliente


class VerificadorJWT:
    def __init__(self, cfg: Configuracion) -> None:
        self._cfg = cfg
        self._jwks = (
            _CacheJWKS(cfg.jwt_jwks_url, cfg.jwt_jwks_ttl_segundos)
            if cfg.jwt_modo == "JWKS" and cfg.jwt_jwks_url
            else None
        )

    def _clave(self, token: str) -> Any:
        if self._jwks is not None:
            try:
                return self._jwks.cliente().get_signing_key_from_jwt(token).key
            except (jwt.PyJWKClientError, httpx.HTTPError) as exc:
                raise CredencialInvalida("no se pudo obtener la clave de firma") from exc
        return self._cfg.jwt_secreto

    def verificar(self, token: str) -> uuid.UUID:
        """Devuelve el identificador del sujeto o lanza CredencialInvalida."""
        try:
            datos = jwt.decode(
                token,
                self._clave(token),
                algorithms=list(self._cfg.jwt_algoritmos),
                issuer=self._cfg.jwt_emisor,
                audience=self._cfg.jwt_audiencia,
                leeway=self._cfg.jwt_margen_reloj_segundos,
                options={
                    "require": ["exp", "iat", "sub", "aud", "iss"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise CredencialInvalida("credencial expirada") from exc
        except jwt.InvalidTokenError as exc:
            raise CredencialInvalida("credencial no válida") from exc

        sujeto = datos.get("sub")
        try:
            return uuid.UUID(str(sujeto))
        except (ValueError, TypeError) as exc:
            raise CredencialInvalida("sujeto sin forma de identificador") from exc
