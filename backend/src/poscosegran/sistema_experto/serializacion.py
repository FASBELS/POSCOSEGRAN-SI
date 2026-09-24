"""Conversión de la base de hechos iniciales a JSON y de vuelta.

Permite guardar con cada evaluación los hechos exactos con que se resolvió, y
reproducirla después con otra versión de la base de conocimiento: es lo que usa
el módulo de adquisición para medir el impacto de un cambio.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from ..dominio.hechos import (
    Controles,
    Dictamen,
    Episodio,
    Fase,
    Historial,
    Instantanea,
    Intervalo,
    Modalidad,
    Plan,
    ResultadoRevision,
)
from ..dominio.valores import Conjunto, Dato, EstadoDato, Procedencia, Tri


def _f(valor: datetime | None) -> str | None:
    return valor.isoformat() if valor is not None else None


def _p(valor: str | None) -> datetime | None:
    return datetime.fromisoformat(valor) if valor else None


def _d(valor: Decimal | None) -> str | None:
    return str(valor) if valor is not None else None


def _n(valor: str | None) -> Decimal | None:
    return Decimal(valor) if valor is not None else None


def _valor(dato: Dato) -> dict[str, Any] | None:
    valor = dato.valor
    if valor is None:
        return None
    if isinstance(valor, bool):
        return {"tipo": "B", "v": valor}
    if isinstance(valor, Decimal):
        return {"tipo": "N", "v": str(valor)}
    if isinstance(valor, datetime):
        return {"tipo": "F", "v": valor.isoformat()}
    return {"tipo": "X", "v": str(valor)}


def _desde_valor(codificado: dict[str, Any] | None) -> Any:
    if codificado is None:
        return None
    tipo, v = codificado["tipo"], codificado["v"]
    if tipo == "B":
        return bool(v)
    if tipo == "N":
        return Decimal(v)
    if tipo == "F":
        return datetime.fromisoformat(v)
    return v


def a_json(inst: Instantanea) -> dict[str, Any]:
    return {
        "fecha_evaluacion": _f(inst.fecha_evaluacion),
        "fase": inst.fase.value if inst.fase else None,
        "tipo_almacenamiento": inst.tipo_almacenamiento.value if inst.tipo_almacenamiento else None,
        "clima_calido": inst.clima_calido.value,
        "datos": {
            campo: {
                "estado": dato.estado.value,
                "valor": _valor(dato),
                "unidad": dato.unidad,
                "fecha_observacion": _f(dato.fecha_observacion),
                "metodo": dato.metodo,
                "procedencia": dato.procedencia.value,
                "no_aplica": dato.no_aplica,
                "motivo_no_aplica": dato.motivo_no_aplica,
            }
            for campo, dato in sorted(inst.datos.datos.items())
        },
        "historial": {
            "fecha_inicio_historial": _f(inst.historial.fecha_inicio_historial),
            "vida_previa_documentada": _d(inst.historial.vida_previa_documentada),
            "evidencia_vida_previa": inst.historial.evidencia_vida_previa,
            "intervalos": [
                {
                    "inicio": _f(i.inicio),
                    "fin": _f(i.fin),
                    "humedad_grano": _d(i.humedad_grano),
                    "temperatura_grano": _d(i.temperatura_grano),
                    "metodo": i.metodo,
                    "evidencia": i.evidencia,
                }
                for i in inst.historial.intervalos
            ],
        },
        "dias_almacenados": inst.dias_almacenados,
        "dias_previstos_restantes": inst.dias_previstos_restantes,
        "fecha_salida_prevista": _f(inst.fecha_salida_prevista),
        "controles": {
            "fecha_inspeccion_grano": _f(inst.controles.fecha_inspeccion_grano),
            "fecha_inspeccion_exterior": _f(inst.controles.fecha_inspeccion_exterior),
            "fecha_control_almacen": _f(inst.controles.fecha_control_almacen),
            "ingreso_inspeccionado": inst.controles.ingreso_inspeccionado.value,
            "hay_evento_que_invalida_control": inst.controles.hay_evento_que_invalida_control.value,
        },
        "plan": {
            "registrado": inst.plan.registrado,
            "intervalo_dias": inst.plan.intervalo_dias,
            "fecha_salida_prevista": _f(inst.plan.fecha_salida_prevista),
            "vigente": inst.plan.vigente,
        },
        "dictamen": None if inst.dictamen is None else {
            "humedad_min": _d(inst.dictamen.humedad_min),
            "humedad_max": _d(inst.dictamen.humedad_max),
            "plazo_maximo_dias": inst.dictamen.plazo_maximo_dias,
            "vence_en": _f(inst.dictamen.vence_en),
            "vigente": inst.dictamen.vigente,
        },
        "episodios": [
            {"id": e.id, "tipo": e.tipo, "causas": list(e.causas), "abierta": e.abierta}
            for e in inst.episodios
        ],
        "resultado_revision_plagas": inst.resultado_revision_plagas.value if inst.resultado_revision_plagas else None,
        "revision_plagas_id": inst.revision_plagas_id,
        "revision_plagas_cubre_indicios_actuales": inst.revision_plagas_cubre_indicios_actuales,
        "sensor_interno_hermetico": inst.sensor_interno_hermetico,
        "temperatura_ambiente_maxima_intervalo": _d(inst.temperatura_ambiente_maxima_intervalo),
        "datos_inconsistentes": list(inst.datos_inconsistentes),
    }


def desde_json(datos: dict[str, Any]) -> Instantanea:
    controles = datos["controles"]
    plan = datos["plan"]
    dictamen = datos.get("dictamen")
    return Instantanea(
        fecha_evaluacion=_p(datos["fecha_evaluacion"]),  
        fase=Fase(datos["fase"]) if datos.get("fase") else None,
        tipo_almacenamiento=Modalidad(datos["tipo_almacenamiento"]) if datos.get("tipo_almacenamiento") else None,
        clima_calido=Tri(datos["clima_calido"]),
        datos=Conjunto(
            {
                campo: Dato(
                    campo=campo,
                    estado=EstadoDato(d["estado"]),
                    valor=_desde_valor(d["valor"]),
                    unidad=d.get("unidad"),
                    fecha_observacion=_p(d.get("fecha_observacion")),
                    metodo=d.get("metodo"),
                    procedencia=Procedencia(d.get("procedencia", "ACTUAL")),
                    no_aplica=bool(d.get("no_aplica")),
                    motivo_no_aplica=d.get("motivo_no_aplica"),
                )
                for campo, d in datos["datos"].items()
            }
        ),
        historial=Historial(
            fecha_inicio_historial=_p(datos["historial"].get("fecha_inicio_historial")),
            vida_previa_documentada=_n(datos["historial"].get("vida_previa_documentada")),
            evidencia_vida_previa=datos["historial"].get("evidencia_vida_previa"),
            intervalos=tuple(
                Intervalo(
                    inicio=_p(i["inicio"]),  
                    fin=_p(i["fin"]),  
                    humedad_grano=_n(i.get("humedad_grano")),
                    temperatura_grano=_n(i.get("temperatura_grano")),
                    metodo=i.get("metodo"),
                    evidencia=i.get("evidencia"),
                )
                for i in datos["historial"].get("intervalos", [])
            ),
        ),
        dias_almacenados=datos.get("dias_almacenados"),
        dias_previstos_restantes=datos.get("dias_previstos_restantes"),
        fecha_salida_prevista=_p(datos.get("fecha_salida_prevista")),
        controles=Controles(
            fecha_inspeccion_grano=_p(controles.get("fecha_inspeccion_grano")),
            fecha_inspeccion_exterior=_p(controles.get("fecha_inspeccion_exterior")),
            fecha_control_almacen=_p(controles.get("fecha_control_almacen")),
            ingreso_inspeccionado=Tri(controles["ingreso_inspeccionado"]),
            hay_evento_que_invalida_control=Tri(controles["hay_evento_que_invalida_control"]),
        ),
        plan=Plan(
            registrado=bool(plan["registrado"]),
            intervalo_dias=plan.get("intervalo_dias"),
            fecha_salida_prevista=_p(plan.get("fecha_salida_prevista")),
            vigente=bool(plan["vigente"]),
        ),
        dictamen=None if not dictamen else Dictamen(
            humedad_min=Decimal(dictamen["humedad_min"]),
            humedad_max=Decimal(dictamen["humedad_max"]),
            plazo_maximo_dias=int(dictamen["plazo_maximo_dias"]),
            vence_en=_p(dictamen["vence_en"]),  
            vigente=bool(dictamen["vigente"]),
        ),
        episodios=tuple(
            Episodio(id=e["id"], tipo=e["tipo"], causas=tuple(e.get("causas", ())), abierta=bool(e.get("abierta", True)))
            for e in datos.get("episodios", [])
        ),
        resultado_revision_plagas=(
            ResultadoRevision(datos["resultado_revision_plagas"]) if datos.get("resultado_revision_plagas") else None
        ),
        revision_plagas_id=datos.get("revision_plagas_id"),
        revision_plagas_cubre_indicios_actuales=bool(datos.get("revision_plagas_cubre_indicios_actuales")),
        sensor_interno_hermetico=bool(datos.get("sensor_interno_hermetico")),
        temperatura_ambiente_maxima_intervalo=_n(datos.get("temperatura_ambiente_maxima_intervalo")),
        datos_inconsistentes=tuple(datos.get("datos_inconsistentes", ())),
    )



def comprimir(hechos: dict[str, Any], plantilla: dict[str, Any]) -> dict[str, Any]:
    datos = hechos["datos"]
    salida = {k: v for k, v in hechos.items() if k != "datos"}
    salida["datos_distintos"] = {c: d for c, d in datos.items() if plantilla.get(c) != d}
    salida["datos_ausentes"] = sorted(c for c in plantilla if c not in datos)
    return salida


def expandir(compacto: dict[str, Any], plantilla: dict[str, Any]) -> dict[str, Any]:
    datos = {c: d for c, d in plantilla.items() if c not in set(compacto.get("datos_ausentes", ()))}
    datos.update(compacto.get("datos_distintos", {}))
    salida = {k: v for k, v in compacto.items() if k not in {"datos_distintos", "datos_ausentes"}}
    salida["datos"] = datos
    return salida


def cargar_casos(contenido: dict[str, Any]) -> list[tuple[str, Instantanea, dict[str, Any]]]:
    """(id, instantánea, esperado) de un archivo de casos de referencia."""
    plantilla = contenido.get("plantilla_datos", {})
    return [
        (caso["id"], desde_json(expandir(caso["hechos"], plantilla)), caso["esperado"])
        for caso in contenido["casos"]
    ]
