"""Configuración validada; las credenciales de migración no se usan en la API."""
from functools import lru_cache
from typing import Annotated, Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="POSCOSEGRAN_", env_file=".env", extra="ignore"
    )
    entorno: Literal["local", "pruebas", "produccion"] = "local"
    bd_url_app: str
    bd_eco_sql: bool = False
    bd_pool_tamano: int = Field(default=5, ge=1)
    bd_pool_desborde: int = Field(default=10, ge=0)
    jwt_modo: Literal["JWKS", "SECRETO_COMPARTIDO"] = "JWKS"
    jwt_algoritmos: Annotated[list[str], NoDecode] = ["ES256", "RS256"]
    jwt_secreto: str | None = Field(default=None, repr=False)
    jwt_emisor: str
    jwt_audiencia: str = "authenticated"
    jwt_jwks_url: str | None = None
    jwt_jwks_ttl_segundos: int = Field(default=300, ge=1)
    jwt_margen_reloj_segundos: int = Field(default=30, ge=0, le=60)
    cors_origenes: Annotated[list[str], NoDecode] = []
    limite_peticiones_por_minuto: int = Field(default=120, ge=1)
    limite_peticiones_escritura_por_minuto: int = Field(default=30, ge=1)
    idempotencia_horas_retencion: int = Field(default=24, ge=1)
    auth_local_habilitada: bool = False
    auth_local_password: str | None = Field(default=None, repr=False)
    # Separación de funciones en adquisición: quien propone una versión no la activa.
    # La excepción existe para demostrar el ciclo completo con una sola cuenta en un
    # entorno de desarrollo; el validador de abajo la prohíbe en producción.
    adquisicion_permitir_autoactivacion: bool = False

    @field_validator("jwt_algoritmos", "cors_origenes", mode="before")
    @classmethod
    def separar(cls, valor: object) -> object:
        if isinstance(valor, str):
            return [parte.strip() for parte in valor.split(",") if parte.strip()]
        return valor

    @model_validator(mode="after")
    def coherencia(self) -> Self:
        if self.auth_local_habilitada and (
            self.entorno == "produccion" or self.jwt_modo != "SECRETO_COMPARTIDO"
            or len(self.auth_local_password or "") < 12
        ):
            raise ValueError("Acceso local requiere entorno local/pruebas y contraseña de 12 caracteres")
        if self.adquisicion_permitir_autoactivacion and self.entorno == "produccion":
            raise ValueError(
                "La separación de funciones en adquisición no se puede desactivar en producción"
            )
        if not self.bd_url_app.startswith("postgresql+psycopg://"):
            raise ValueError("Se requiere PostgreSQL con Psycopg")
        permitidos = {"RS256", "ES256"} if self.jwt_modo == "JWKS" else {"HS256"}
        if not self.jwt_algoritmos or not set(self.jwt_algoritmos) <= permitidos:
            raise ValueError("Algoritmos incompatibles con el modo JWT")
        if self.jwt_modo == "JWKS" and not (self.jwt_jwks_url or "").startswith("https://"):
            raise ValueError("JWKS requiere una URL HTTPS")
        if self.jwt_modo == "SECRETO_COMPARTIDO":
            if self.entorno == "produccion" or len(self.jwt_secreto or "") < 32:
                raise ValueError("Secreto compartido solo en local/pruebas, mínimo 32 caracteres")
        if any("*" in origen or not origen.startswith(("http://", "https://"))
               for origen in self.cors_origenes):
            raise ValueError("CORS exige orígenes explícitos")
        return self


@lru_cache
def obtener_configuracion() -> Configuracion:
    return Configuracion()
