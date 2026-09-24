"""Forma validada del catálogo de conocimiento.

Se carga desde un archivo versionado, no desde la API. El catálogo describe las
reglas; no las ejecuta. La transcripción a reglas ejecutables es de la etapa 7.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

CODIGO_REGLA = re.compile(r"^R[0-9]{2,}$")
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
    """R01–R30 completas, reglas adicionales y las nueve ramas de R30."""

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
        esperados_30 = [f"R{numero:02d}" for numero in range(1, 31)]
        adicionales = codigos[30:]
        validos = all(
            CODIGO_REGLA.fullmatch(codigo)
            and int(codigo[1:]) >= 31
            and codigo == f"R{int(codigo[1:]):02d}"
            for codigo in adicionales
        )
        ordenados = validos and adicionales == sorted(adicionales, key=lambda codigo: int(codigo[1:]))
        if codigos[:30] != esperados_30 or not validos or not ordenados or len(set(codigos)) != len(codigos):
            faltan = sorted(set(esperados_30) - set(codigos))
            raise ValueError(
                "las reglas deben conservar R01…R30 en orden y añadir códigos R31+ "
                f"únicos y ordenados. Faltan reglas base: {faltan or 'ninguna'}"
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
