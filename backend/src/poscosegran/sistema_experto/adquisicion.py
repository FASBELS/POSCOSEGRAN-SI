"""Módulo de adquisición del conocimiento.

Es la vía por la que el ingeniero del conocimiento modifica la base sin tocar el
motor. Un cambio sigue siempre el mismo ciclo:

    proponer   partir de la versión activa y cambiar parámetros o reglas, con motivo;
    validar    la base resultante debe pasar el mismo cargador que la versión activa:
               sintaxis, referencias, ciclos, coherencia con el documento y
               restricciones de integridad;
    medir      evaluar los casos de referencia —y las evaluaciones históricas que se
               aporten— con la versión activa y con la propuesta, y listar qué
               decisiones cambiarían;
    activar    solo una propuesta válida y revisada; la activación la registra la
               capa de servicios, y las evaluaciones ya emitidas no se recalculan.

Nada de esto escribe en disco ni en base de datos: devuelve la propuesta y su
impacto, y la capa de servicios decide qué persistir.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..conocimiento.esquema import Catalogo
from ..dominio.hechos import Instantanea
from . import serializacion
from .base_conocimiento import BaseConocimiento, BaseInvalida, desde_contenido, ruta_por_defecto
from .motor import Motor

LONGITUD_MINIMA_MOTIVO = 15


@dataclass(frozen=True, slots=True)
class CambioParametro:
    nombre: str
    anterior: Decimal
    nuevo: Decimal
    unidad: str


@dataclass(frozen=True, slots=True)
class CambioRegla:
    produccion: str
    regla: str
    tipo: str  # MODIFICADA | NUEVA | RETIRADA


@dataclass(frozen=True, slots=True)
class CasoAfectado:
    id: str
    origen: str
    decision_antes: str
    decision_despues: str
    rama_antes: str
    rama_despues: str
    reglas_nuevas: tuple[str, ...]
    reglas_retiradas: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Impacto:
    evaluados: int
    cambian: int
    transiciones: dict[str, int]
    casos: tuple[CasoAfectado, ...]
    nuevas_autorizaciones: int


@dataclass(frozen=True)
class Propuesta:
    valida: bool
    errores: tuple[str, ...]
    advertencias: tuple[str, ...]
    version_base: str
    version_parametros: str
    motivo: str
    cambios_parametros: tuple[CambioParametro, ...]
    cambios_reglas: tuple[CambioRegla, ...]
    impacto: Impacto | None
    contenido: Mapping[str, Any] | None = field(repr=False, default=None)
    base: BaseConocimiento | None = field(repr=False, default=None)


# --- Casos de referencia -------------------------------------------------------------


def cargar_casos_referencia(ruta: Path | None = None) -> list[tuple[str, str, Instantanea]]:
    ruta = ruta or (ruta_por_defecto() / "casos_referencia.json")
    if not ruta.exists():
        return []
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    return [
        (ident, ident.split(":", 1)[0], inst)
        for ident, inst, _ in serializacion.cargar_casos(contenido)
    ]


# --- Propuesta --------------------------------------------------------------------------


def _decimal(valor: Any) -> Decimal | None:
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return None
    return numero if numero.is_finite() else None


def proponer(
    activa: BaseConocimiento,
    *,
    motivo: str,
    version_parametros: str | None = None,
    version_base: str | None = None,
    parametros: Mapping[str, Any] | None = None,
    reglas: Mapping[str, Mapping[str, Any] | None] | None = None,
    fichas: Mapping[str, Mapping[str, Any]] | None = None,
    casos: Iterable[tuple[str, str, Instantanea]] | None = None,
) -> Propuesta:
    """Construye, valida y mide una propuesta a partir de la versión activa.

    `reglas` asocia el id de una regla de producción con su nueva definición
    completa; None la retira. Un id nuevo la añade al final de su etapa.
    """
    errores: list[str] = []
    advertencias: list[str] = []
    parametros = dict(parametros or {})
    reglas = dict(reglas or {})
    fichas = dict(fichas or {})

    if len(motivo.strip()) < LONGITUD_MINIMA_MOTIVO:
        errores.append(f"el motivo debe explicar el cambio (mínimo {LONGITUD_MINIMA_MOTIVO} caracteres)")

    contenido = copy.deepcopy(dict(activa.contenido))
    operativa = contenido["operativa"]
    documental = contenido["documental"]

    cambios_parametros: list[CambioParametro] = []
    for nombre, valor in parametros.items():
        if nombre not in operativa["parametros"]:
            errores.append(f"parámetro desconocido: {nombre}")
            continue
        nuevo = _decimal(valor)
        if nuevo is None:
            errores.append(f"parámetro {nombre}: '{valor}' no es un número")
            continue
        anterior = activa.parametro(nombre)
        if nuevo == anterior:
            continue
        operativa["parametros"][nombre]["valor"] = float(nuevo) if nuevo != nuevo.to_integral() else int(nuevo)
        cambios_parametros.append(
            CambioParametro(nombre, anterior, nuevo, activa.parametros[nombre].unidad)
        )

    cambios_reglas: list[CambioRegla] = []
    por_id = {r["id"]: i for i, r in enumerate(operativa["reglas"])}
    retiradas_documentales: set[str] = set()
    for ident, definicion in reglas.items():
        if definicion is None:
            if ident not in por_id:
                errores.append(f"no existe la regla {ident} que se quiere retirar")
                continue
            retirada = operativa["reglas"][por_id[ident]]
            codigo = retirada.get("regla", ident)
            if not re.fullmatch(r"R[0-9]{2,}", codigo) or int(codigo[1:]) < 31:
                errores.append(f"la regla base {ident} no se puede retirar")
                continue
            retiradas_documentales.add(codigo)
            cambios_reglas.append(CambioRegla(ident, codigo, "RETIRADA"))
            continue
        if not isinstance(definicion, Mapping):
            errores.append(f"regla {ident}: la definición debe ser un objeto")
            continue
        nueva = {**definicion, "id": ident}
        if ident not in por_id and (
            not re.fullmatch(r"R[0-9]{2,}", ident)
            or int(ident[1:]) < 31
            or ident != f"R{int(ident[1:]):02d}"
            or nueva.get("regla", ident) != ident
        ):
            errores.append(f"la regla nueva {ident} debe tener un código R31+ y el mismo código documental")
            continue
        if ident in por_id:
            if nueva == operativa["reglas"][por_id[ident]]:
                continue
            operativa["reglas"][por_id[ident]] = nueva
            cambios_reglas.append(CambioRegla(ident, nueva.get("regla", ident), "MODIFICADA"))
        else:
            operativa["reglas"].append(nueva)
            cambios_reglas.append(CambioRegla(ident, nueva.get("regla", ident), "NUEVA"))
    retiradas = {c.produccion for c in cambios_reglas if c.tipo == "RETIRADA"}
    operativa["reglas"] = [r for r in operativa["reglas"] if r["id"] not in retiradas]

    for codigo in retiradas_documentales:
        if not any(r.get("regla", r["id"]) == codigo for r in operativa["reglas"]):
            documental["reglas"] = [f for f in documental["reglas"] if f["id"] != codigo]
            operativa["fundamentos"].pop(codigo, None)
    for codigo, ficha in fichas.items():
        if codigo in retiradas_documentales and codigo not in {
            r.get("regla", r["id"]) for r in operativa["reglas"]
        }:
            errores.append(f"la ficha {codigo} corresponde a una regla retirada")
            continue
        if codigo not in {r.get("regla", r["id"]) for r in operativa["reglas"]}:
            errores.append(f"la ficha {codigo} no tiene una regla operativa")
            continue
        nueva_ficha = {**ficha, "id": codigo}
        anterior_ficha = next((f for f in documental["reglas"] if f["id"] == codigo), None)
        if anterior_ficha == nueva_ficha:
            continue
        if anterior_ficha is None:
            documental["reglas"].append(nueva_ficha)
            if not any(c.regla == codigo for c in cambios_reglas):
                cambios_reglas.append(CambioRegla(codigo, codigo, "NUEVA"))
        else:
            documental["reglas"] = [nueva_ficha if f["id"] == codigo else f for f in documental["reglas"]]
            if not any(c.regla == codigo for c in cambios_reglas):
                cambios_reglas.append(CambioRegla(codigo, codigo, "MODIFICADA"))
        operativa["fundamentos"][codigo] = {
            "tipo": nueva_ficha["fundamento"], "fuentes": list(nueva_ficha["fuentes"])
        }
    documental["reglas"].sort(key=lambda f: int(f["id"][1:]))

    if not cambios_parametros and not cambios_reglas:
        errores.append("la propuesta no cambia nada respecto de la versión activa")

    if cambios_reglas and not version_base:
        errores.append("un cambio de reglas exige una nueva versión de la base")
    nueva_version_base = version_base or activa.version_base
    nueva_version_parametros = version_parametros or activa.version_parametros
    if (nueva_version_base, nueva_version_parametros) == (activa.version_base, activa.version_parametros):
        errores.append("la propuesta necesita un número de versión distinto del activo")
    operativa["version_base"] = nueva_version_base
    operativa["version_parametros"] = nueva_version_parametros
    documental["version_base"] = nueva_version_base
    documental["version_parametros"] = nueva_version_parametros

    base: BaseConocimiento | None = None
    try:
        Catalogo.model_validate(documental)
    except ValidationError as error:
        errores.extend(str(item["msg"]) for item in error.errors())
    try:
        base = desde_contenido(contenido)
    except BaseInvalida as error:
        errores.extend(error.errores)

    impacto = None
    if base is not None:
        impacto = medir_impacto(activa, base, casos if casos is not None else cargar_casos_referencia())
        if impacto.nuevas_autorizaciones:
            advertencias.append(
                f"{impacto.nuevas_autorizaciones} casos que hoy no se autorizan pasarían a autorizarse: "
                "revise que el cambio tiene fundamento técnico antes de activarlo"
            )
        if any(c.tipo == "RETIRADA" for c in cambios_reglas):
            advertencias.append("se retira una regla de producción: revise que el catálogo sigue siendo completo")
        cambiados_publicados = [
            c.nombre for c in cambios_parametros if activa.parametros[c.nombre].fundamento == "PUBLICADO"
        ]
        if cambiados_publicados:
            advertencias.append(
                "se modifican umbrales publicados en una fuente: "
                + ", ".join(cambiados_publicados)
                + ". Actualice su fundamento o fuente."
            )

    return Propuesta(
        valida=not errores,
        errores=tuple(errores),
        advertencias=tuple(advertencias),
        version_base=nueva_version_base,
        version_parametros=nueva_version_parametros,
        motivo=motivo.strip(),
        cambios_parametros=tuple(cambios_parametros),
        cambios_reglas=tuple(cambios_reglas),
        impacto=impacto,
        contenido=contenido if not errores else None,
        base=base if not errores else None,
    )


def medir_impacto(
    activa: BaseConocimiento,
    propuesta: BaseConocimiento,
    casos: Iterable[tuple[str, str, Instantanea]],
) -> Impacto:
    """Evalúa cada caso con ambas versiones y recoge los que cambian de decisión."""
    motor_activo, motor_propuesto = Motor(activa), Motor(propuesta)
    autorizadas = activa.decisiones_autorizadas
    afectados: list[CasoAfectado] = []
    transiciones: dict[str, int] = {}
    evaluados = 0
    nuevas_autorizaciones = 0
    for ident, origen, inst in casos:
        evaluados += 1
        antes, despues = motor_activo.evaluar(inst), motor_propuesto.evaluar(inst)
        reglas_antes, reglas_despues = set(antes.reglas_activadas), set(despues.reglas_activadas)
        if (antes.decision_final, antes.rama_r30) == (despues.decision_final, despues.rama_r30) and reglas_antes == reglas_despues:
            continue
        if antes.decision_final != despues.decision_final:
            clave = f"{antes.decision_final} → {despues.decision_final}"
            transiciones[clave] = transiciones.get(clave, 0) + 1
            if despues.decision_final in autorizadas and antes.decision_final not in autorizadas:
                nuevas_autorizaciones += 1
        afectados.append(
            CasoAfectado(
                id=ident,
                origen=origen,
                decision_antes=antes.decision_final,
                decision_despues=despues.decision_final,
                rama_antes=antes.rama_r30,
                rama_despues=despues.rama_r30,
                reglas_nuevas=tuple(sorted(reglas_despues - reglas_antes)),
                reglas_retiradas=tuple(sorted(reglas_antes - reglas_despues)),
            )
        )
    cambian = sum(1 for c in afectados if c.decision_antes != c.decision_despues)
    return Impacto(
        evaluados=evaluados,
        cambian=cambian,
        transiciones=dict(sorted(transiciones.items(), key=lambda kv: -kv[1])),
        casos=tuple(afectados),
        nuevas_autorizaciones=nuevas_autorizaciones,
    )
