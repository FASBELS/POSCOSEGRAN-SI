"""Base de hechos: la memoria de trabajo de una evaluación.

Separa dos clases de hechos, como en el diagrama de arquitectura:

    iniciales   lo que el usuario observó o el historial documenta: observaciones,
                contexto de la unidad, controles, episodios abiertos, plan y dictamen.
    inferidos   lo que el motor deduce aplicando reglas: hallazgos y solicitudes.

Los hechos inferidos pertenecen a esta evaluación y no se copian a la siguiente.
Los episodios abiertos sí persisten, porque son registros de seguimiento, no
inferencia.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from ..dominio.hechos import Accion, Episodio, Instantanea, Motivo, Pendiente
from ..dominio.valores import Conjunto, Dato, EstadoDato, Procedencia, Tri


@dataclass(frozen=True, slots=True)
class Activacion:
    """Un disparo de regla: lo que el módulo de explicación reconstruye como '¿cómo?'."""

    orden: int
    etapa: str
    pasada: int
    produccion: str
    regla: str
    hallazgo: str | None
    soportes: tuple[str, ...]
    solicitudes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EvaluacionRama:
    """Resultado de comprobar una rama de R30, con lo que le faltó si no aplicó."""

    rama: str
    decision: str
    valor: str
    fallidas: tuple[str, ...]


def _dato_de_tri(campo: str, valor: Tri, fecha: datetime) -> Dato:
    if valor is Tri.VERDADERO or valor is Tri.FALSO:
        return Dato(
            campo=campo,
            estado=EstadoDato.VALIDO,
            valor=valor is Tri.VERDADERO,
            unidad="BOOLEANO",
            fecha_observacion=fecha,
            metodo="REGISTRO",
        )
    return Dato(campo=campo)


def _dato_de_fecha(campo: str, valor: datetime | None, fecha: datetime) -> Dato:
    if valor is None:
        return Dato(campo=campo)
    return Dato(
        campo=campo,
        estado=EstadoDato.VALIDO,
        valor=valor,
        unidad="TEXTO",
        fecha_observacion=fecha,
        metodo="REGISTRO",
    )


def _registro(campo: str, valor: bool | str, fecha: datetime) -> Dato:
    return Dato(
        campo=campo,
        estado=EstadoDato.VALIDO,
        valor=valor,
        unidad="BOOLEANO" if isinstance(valor, bool) else "TEXTO",
        fecha_observacion=fecha,
        metodo="REGISTRO",
    )


@dataclass
class BaseHechos:
    instantanea: Instantanea
    datos: dict[str, Dato] = field(default_factory=dict)

    hallazgos: list[str] = field(default_factory=list)
    solicitudes: dict[str, list[str]] = field(default_factory=dict)
    motivos: list[Motivo] = field(default_factory=list)
    acciones: list[Accion] = field(default_factory=list)
    reglas_activadas: list[str] = field(default_factory=list)
    traza: list[Activacion] = field(default_factory=list)
    disparadas: set[str] = field(default_factory=set)
    no_aplicables: list[str] = field(default_factory=list)
    pendientes: list[Pendiente] | None = None
    ramas: list[EvaluacionRama] = field(default_factory=list)

    @classmethod
    def desde(cls, inst: Instantanea) -> "BaseHechos":
        """Construye los hechos iniciales a partir de la instantánea de entrada.

        Los registros de control, revisión y sensor se incorporan como datos, de
        modo que las reglas los consultan con el mismo lenguaje que las
        observaciones.
        """
        ahora = inst.fecha_evaluacion
        datos = dict(inst.datos.datos)
        controles = inst.controles
        datos["fecha_inspeccion_grano"] = _dato_de_fecha(
            "fecha_inspeccion_grano", controles.fecha_inspeccion_grano, ahora
        )
        datos["fecha_inspeccion_exterior"] = _dato_de_fecha(
            "fecha_inspeccion_exterior", controles.fecha_inspeccion_exterior, ahora
        )
        datos["fecha_control_almacen"] = _dato_de_fecha(
            "fecha_control_almacen", controles.fecha_control_almacen, ahora
        )
        datos["ingreso_inspeccionado"] = _dato_de_tri(
            "ingreso_inspeccionado", controles.ingreso_inspeccionado, ahora
        )
        datos["hay_evento_que_invalida_control"] = _dato_de_tri(
            "hay_evento_que_invalida_control", controles.hay_evento_que_invalida_control, ahora
        )
        # La revisión técnica de plagas es un registro cerrado: si no existe, no hay
        # descarte ni confirmación, nunca un valor desconocido que se pudiera leer
        # como favorable.
        datos["resultado_revision_plagas"] = _registro(
            "resultado_revision_plagas",
            inst.resultado_revision_plagas.value if inst.resultado_revision_plagas else "NINGUNA",
            ahora,
        )
        datos["revision_plagas_cubre_indicios_actuales"] = _registro(
            "revision_plagas_cubre_indicios_actuales",
            bool(inst.revision_plagas_cubre_indicios_actuales),
            ahora,
        )
        datos["sensor_interno_hermetico"] = _registro(
            "sensor_interno_hermetico", bool(inst.sensor_interno_hermetico), ahora
        )
        return cls(instantanea=inst, datos=datos)

    # --- Consulta -------------------------------------------------------------

    def dato(self, campo: str) -> Dato:
        return self.datos.get(campo) or Dato(campo=campo)

    @property
    def conjunto(self) -> Conjunto:
        return Conjunto(self.datos)

    def tiene(self, hallazgo: str) -> bool:
        return hallazgo in self.hallazgos

    def pedida(self, solicitud: str) -> bool:
        return bool(self.solicitudes.get(solicitud))

    def episodio_abierto(self, tipos: list[str]) -> bool:
        return any(e.abierta and e.tipo in tipos for e in self.instantanea.episodios)

    def episodios_abiertos(self, tipos: list[str]) -> tuple[Episodio, ...]:
        return tuple(e for e in self.instantanea.episodios if e.abierta and e.tipo in tipos)

    def invalidos(self) -> list[str]:
        return sorted(
            campo
            for campo, dato in self.instantanea.datos.datos.items()
            if dato.estado in (EstadoDato.INVALIDO, EstadoDato.VENCIDO)
        )

    # --- Hechos iniciales, para la explicación -------------------------------

    def iniciales(self) -> list[tuple[str, object, str]]:
        """Observaciones utilizables con su procedencia: el punto de partida del caso."""
        salida = []
        for campo, dato in sorted(self.instantanea.datos.datos.items()):
            if dato.utilizable:
                valor = dato.valor
                if isinstance(valor, Decimal):
                    valor = float(valor)
                salida.append((campo, valor, dato.procedencia.value))
        return salida

    # --- Afirmación -----------------------------------------------------------

    def afirmar_calculado(self, dato: Dato) -> None:
        """Hecho derivado por un procedimiento de cálculo, marcado como tal."""
        self.datos[dato.campo] = dato

    def solicitar(self, solicitud: str, causa: str) -> bool:
        causas = self.solicitudes.setdefault(solicitud, [])
        if causa in causas:
            return False
        causas.append(causa)
        return True


__all__ = ["Activacion", "BaseHechos", "EvaluacionRama", "Procedencia"]
