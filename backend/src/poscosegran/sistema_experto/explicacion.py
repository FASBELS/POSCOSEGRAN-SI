"""Módulo de explicación.

Responde a las tres preguntas clásicas de un sistema experto:

    ¿Cómo?              La cadena de reglas que llevó a la decisión, desde los
                        hechos iniciales hasta la rama de R30 que resolvió.
    ¿Por qué no?        Qué le faltó a cada autorización que no se concedió.
    ¿Por qué se pide?   Qué reglas usan un dato antes de que el usuario lo aporte.

Trabaja solo con la traza que deja el motor y con la base de conocimiento; no
vuelve a razonar sobre el caso, de modo que explica exactamente lo que ocurrió.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .base_conocimiento import BaseConocimiento, _recorrer
from .base_hechos import Activacion, EvaluacionRama
from .base_conocimiento import NOMBRE_SOLICITUD
from .motor import Resultado

ETIQUETA_DECISION = {
    "CUARENTENA": "Separar y solicitar evaluación técnica",
    "BLOQUEAR_INGRESO": "Ingreso no autorizado",
    "RETIRAR_LOTE": "Suspender almacenamiento en las condiciones actuales",
    "CORREGIR_Y_REEVALUAR": "Corregir y volver a evaluar",
    "SIN_CONCLUSION_AUTOMATICA": "Faltan datos o revisión",
    "AUTORIZAR_CON_MONITOREO": "Almacenamiento autorizado con seguimiento reforzado",
    "AUTORIZAR_ALMACENAMIENTO": "Almacenamiento autorizado con controles ordinarios",
}


@dataclass(frozen=True, slots=True)
class Paso:
    orden: int
    regla: str
    etapa: str
    pasada: int
    conclusion: str | None
    solicitudes: tuple[str, ...]
    porque: tuple[str, ...]
    antecedente: str | None


@dataclass(frozen=True, slots=True)
class RamaExplicada:
    rama: str
    decision: str
    aplicada: bool
    valor: str
    faltan: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Explicacion:
    decision: str
    etiqueta: str
    rama: str
    resumen: str
    cadena: tuple[Paso, ...]
    traza_completa: tuple[Paso, ...]
    ramas: tuple[RamaExplicada, ...]
    por_que_no: tuple[RamaExplicada, ...]
    hechos_iniciales: tuple[tuple[str, object, str], ...]
    hechos_inferidos: tuple[str, ...]
    no_aplicables: tuple[str, ...]


def _antecedentes(base: BaseConocimiento) -> dict[str, str]:
    return {r["id"]: r.get("antecedente", "") for r in base.documental.get("reglas", [])} | {
        r["id"]: r.get("antecedente", "") for r in base.documental.get("ramas_r30", [])
    }


def _paso(activacion: Activacion, antecedentes: Mapping[str, str]) -> Paso:
    return Paso(
        orden=activacion.orden,
        regla=activacion.regla,
        etapa=activacion.etapa,
        pasada=activacion.pasada,
        conclusion=activacion.hallazgo,
        solicitudes=activacion.solicitudes,
        porque=activacion.soportes,
        antecedente=antecedentes.get(activacion.regla),
    )


def _atomos(nodo: Any, clave: str, base: BaseConocimiento | None = None, vistas: frozenset[str] = frozenset()) -> set[str]:
    """Átomos de un tipo en una condición, siguiendo las definiciones que usa."""
    encontrados = {v for k, v in _recorrer(nodo) if k == clave and isinstance(v, str)}
    if base is not None:
        for nombre in {v for k, v in _recorrer(nodo) if k == "definicion" and isinstance(v, str)} - vistas:
            encontrados |= _atomos(base.definiciones.get(nombre, {}), clave, base, vistas | {nombre})
    return encontrados


def _cadena(resultado: Resultado, base: BaseConocimiento) -> list[Activacion]:
    """Encadenamiento hacia atrás sobre la traza: solo los disparos que importaron.

    Se parte de lo que la rama elegida consulta (solicitudes y hechos) y se añaden,
    recursivamente, los disparos que produjeron los hechos que sirvieron de soporte.
    """
    rama = next(r for r in base.resolucion if r.rama == resultado.rama_r30)
    solicitudes = {NOMBRE_SOLICITUD[s] for s in _atomos(rama.si, "solicitud")}
    buscados = _atomos(rama.si, "hecho", base) | _atomos(rama.si, "algun_hecho", base)
    por_hallazgo = {a.hallazgo: a for a in resultado.traza if a.hallazgo}

    por_solicitud: dict[str, list[Activacion]] = {}
    for activacion in resultado.traza:
        for solicitud in activacion.solicitudes:
            por_solicitud.setdefault(solicitud, []).append(activacion)

    elegidas: dict[int, Activacion] = {}
    pendientes = list(buscados | solicitudes)
    while pendientes:
        nombre = pendientes.pop()
        productores = list(por_solicitud.get(nombre, ()))
        if nombre in por_hallazgo:
            productores.append(por_hallazgo[nombre])
        for activacion in productores:
            if activacion.orden not in elegidas:
                elegidas[activacion.orden] = activacion
                pendientes.extend(activacion.soportes)
    return [elegidas[k] for k in sorted(elegidas)]


def _explicar_rama(rama: EvaluacionRama, elegida: str) -> RamaExplicada:
    return RamaExplicada(
        rama=rama.rama,
        decision=rama.decision,
        aplicada=rama.rama == elegida,
        valor=rama.valor,
        faltan=rama.fallidas,
    )


def explicar(resultado: Resultado, base: BaseConocimiento) -> Explicacion:
    antecedentes = _antecedentes(base)
    cadena = [_paso(a, antecedentes) for a in _cadena(resultado, base)]
    ramas = [_explicar_rama(r, resultado.rama_r30) for r in resultado.ramas]

    # ¿Por qué no? Solo interesa para las autorizaciones que no se concedieron:
    # todas si la decisión no autoriza; la ordinaria si se autorizó con monitoreo.
    autorizadas = base.decisiones_autorizadas
    indice_elegida = next(i for i, r in enumerate(ramas) if r.aplicada)
    por_que_no = [
        r for i, r in enumerate(ramas)
        if r.decision in autorizadas and not r.aplicada and r.decision != resultado.decision_final
        and (resultado.decision_final not in autorizadas or i > indice_elegida)
    ]
    if resultado.decision_final not in autorizadas:
        por_que_no = [r for r in ramas if r.decision in autorizadas]
    elif resultado.decision_final == "AUTORIZAR_CON_MONITOREO":
        por_que_no = [r for r in ramas if r.decision == "AUTORIZAR_ALMACENAMIENTO"]
    else:
        por_que_no = []

    superiores = [r.rama for r in ramas[:indice_elegida]]
    rama = next(r for r in base.resolucion if r.rama == resultado.rama_r30)
    cabecera = f"Se aplicó {resultado.rama_r30} ({ETIQUETA_DECISION[resultado.decision_final]})"
    pedidas = {NOMBRE_SOLICITUD[s] for s in _atomos(rama.si, "solicitud")}
    causantes = [p for p in cadena if pedidas & set(p.solicitudes)]
    if resultado.decision_final in autorizadas:
        condiciones = [c.get("descripcion") for c in rama.si.get("todos", []) if c.get("descripcion")]
        resumen = f"{cabecera} porque se cumplieron todas sus condiciones: {', '.join(condiciones)}."
    elif causantes:
        detalle = ", ".join(f"{p.regla} ({p.conclusion})" for p in causantes if p.conclusion)
        resumen = f"{cabecera} porque lo solicitaron {detalle}."
    elif resultado.rama_r30 == "R30.5":
        n = len({p.campo for p in resultado.datos_pendientes})
        resumen = f"{cabecera} porque {'falta 1 dato exigible' if n == 1 else f'faltan {n} datos exigibles'}."
    else:
        resumen = f"{cabecera}."
    if superiores:
        resumen += f" Las ramas de mayor prioridad ({', '.join(superiores)}) no se cumplían."

    return Explicacion(
        decision=resultado.decision_final,
        etiqueta=ETIQUETA_DECISION[resultado.decision_final],
        rama=resultado.rama_r30,
        resumen=resumen,
        cadena=tuple(cadena),
        traza_completa=tuple(_paso(a, antecedentes) for a in resultado.traza),
        ramas=tuple(ramas),
        por_que_no=tuple(por_que_no),
        hechos_iniciales=resultado.hechos_iniciales,
        hechos_inferidos=resultado.hechos_inferidos,
        no_aplicables=resultado.no_aplicables,
    )


@dataclass(frozen=True, slots=True)
class PorQueSePide:
    campo: str
    reglas: tuple[str, ...]
    texto: str


def por_que_se_pide(campo: str, base: BaseConocimiento) -> PorQueSePide:
    reglas = base.uso_de_campos.get(campo, ())
    if not reglas:
        texto = "Ninguna regla usa este dato para decidir; se registra como contexto del caso."
    else:
        antecedentes = _antecedentes(base)
        primeras = "; ".join(f"{r}: {antecedentes.get(r, '')}".strip(": ") for r in reglas[:3])
        extra = f" y {len(reglas) - 3} más" if len(reglas) > 3 else ""
        texto = f"Lo usan {', '.join(reglas)}. Por ejemplo, {primeras}{extra}."
    return PorQueSePide(campo=campo, reglas=reglas, texto=texto)
