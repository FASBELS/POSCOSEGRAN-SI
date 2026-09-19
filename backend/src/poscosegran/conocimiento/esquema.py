"""Forma validada del catálogo de conocimiento.

Se carga desde un archivo versionado, no desde la API. El catálogo describe las
reglas; no las ejecuta. La transcripción a reglas ejecutables es de la etapa 7.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CODIGO_REGLA = re.compile(r"^R(0[1-9]|[12][0-9]|30)$")
CODIGO_RAMA = re.compile(r"^R30\.[1-9]$")
CODIGO_FUENTE = re.compile(r"^S0[1-9]$")


class FuenteCatalogo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    referencia_markdown: str = Field(min_length=1)

    @field_validator("id")
    @classmethod
    def _codigo(cls, valor: str) -> str:
        if not CODIGO_FUENTE.match(valor):
            raise ValueError("la fuente debe identificarse como S01…S09")
        return valor


class ReglaCatalogo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    antecedente: str = Field(min_length=1)
    consecuente: str = Field(min_length=1)
    accion: str = Field(min_length=1)
    fundamento_markdown: str = Field(min_length=1)
    fundamento: Literal["PUBLICADO", "TRANSFERIDO", "POLITICA_PROTOTIPO", "MIXTO"]
    fuentes: list[str] = Field(default_factory=list)


class Catalogo(BaseModel):
    """R01–R30 completas, las nueve ramas de R30 y las fuentes que las respaldan."""

    model_config = ConfigDict(extra="forbid")

    version_base: str = Field(min_length=1)
    version_parametros: str = Field(min_length=1)
    version_motor: str = Field(min_length=1)
    reglas: list[ReglaCatalogo]
    ramas_r30: list[ReglaCatalogo]
    fuentes: list[FuenteCatalogo]

    @model_validator(mode="after")
    def _completitud(self) -> "Catalogo":
        codigos = [regla.id for regla in self.reglas]
        esperados = [f"R{numero:02d}" for numero in range(1, 31)]
        if codigos != esperados:
            faltan = sorted(set(esperados) - set(codigos))
            sobran = sorted(set(codigos) - set(esperados))
            raise ValueError(
                f"las reglas deben ser R01…R30 en orden. Faltan: {faltan or 'ninguna'}. "
                f"No reconocidas: {sobran or 'ninguna'}"
            )

        ramas = [rama.id for rama in self.ramas_r30]
        esperadas = [f"R30.{numero}" for numero in range(1, 10)]
        if ramas != esperadas:
            raise ValueError(
                "las ramas deben ser R30.1…R30.9 en el orden de resolución de la base"
            )

        declaradas = {fuente.id for fuente in self.fuentes}
        for regla in [*self.reglas, *self.ramas_r30]:
            desconocidas = sorted(set(regla.fuentes) - declaradas)
            if desconocidas:
                raise ValueError(f"{regla.id} cita fuentes no declaradas: {desconocidas}")
            if regla.fundamento in {"PUBLICADO", "TRANSFERIDO", "MIXTO"} and not regla.fuentes:
                raise ValueError(f"{regla.id} declara fundamento {regla.fundamento} sin fuente")
        return self
