"""Instantánea de entrada del motor y estructuras de salida intermedias.

El motor no toca la base de datos: recibe una instantánea coherente y devuelve
una decisión. Eso permite ejecutar los casos de aceptación sin PostgreSQL y
garantiza que el resultado dependa solo de los hechos declarados.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from .valores import Conjunto, Evidencia, Tri


class Fase(enum.Enum):
    INGRESO = "INGRESO"
    SEGUIMIENTO = "SEGUIMIENTO"


class Modalidad(enum.Enum):
    HERMETICO = "HERMETICO"
    NO_HERMETICO = "NO_HERMETICO"


class ResultadoRevision(enum.Enum):
    PENDIENTE = "PENDIENTE"
    CONFIRMADA = "CONFIRMADA"
    DESCARTADA = "DESCARTADA"


@dataclass(frozen=True, slots=True)
class Intervalo:
    """Tramo del historial con sus condiciones representativas documentadas."""

    inicio: datetime
    fin: datetime
    humedad_grano: Decimal | None
    temperatura_grano: Decimal | None
    metodo: str | None = None
    evidencia: str | None = None

    @property
    def dias(self) -> Decimal:
        return Decimal(str((self.fin - self.inicio).total_seconds() / 86400))

    @property
    def documentado(self) -> bool:
        return self.humedad_grano is not None and self.temperatura_grano is not None


@dataclass(frozen=True, slots=True)
class Historial:
    fecha_inicio_historial: datetime | None = None
    vida_previa_documentada: Decimal | None = None
    evidencia_vida_previa: str | None = None
    intervalos: tuple[Intervalo, ...] = ()


@dataclass(frozen=True, slots=True)
class Dictamen:
    """Dictamen técnico para la banda condicional de humedad."""

    humedad_min: Decimal
    humedad_max: Decimal
    plazo_maximo_dias: int
    vence_en: datetime
    vigente: bool

    def cubre(self, humedad: Decimal, dias_solicitados: int, ahora: datetime) -> bool:
        return (
            self.vigente
            and self.vence_en > ahora
            and self.humedad_min <= humedad <= self.humedad_max
            and self.plazo_maximo_dias >= dias_solicitados
        )


@dataclass(frozen=True, slots=True)
class Plan:
    registrado: bool = False
    intervalo_dias: int | None = None
    fecha_salida_prevista: datetime | None = None
    vigente: bool = False


@dataclass(frozen=True, slots=True)
class Episodio:
    """Cuarentena o revisión abierta. Persiste aunque cambien las mediciones."""

    id: str
    tipo: str
    causas: tuple[str, ...] = ()
    abierta: bool = True


@dataclass(frozen=True, slots=True)
class Controles:
    fecha_inspeccion_grano: datetime | None = None
    fecha_inspeccion_exterior: datetime | None = None
    fecha_control_almacen: datetime | None = None
    ingreso_inspeccionado: Tri = Tri.DESCONOCIDO
    hay_evento_que_invalida_control: Tri = Tri.FALSO


@dataclass(frozen=True, slots=True)
class Instantanea:
    """Todo lo que el motor necesita para resolver una evaluación."""

    fecha_evaluacion: datetime
    fase: Fase | None = None
    tipo_almacenamiento: Modalidad | None = None
    clima_calido: Tri = Tri.DESCONOCIDO
    datos: Conjunto = field(default_factory=Conjunto)

    historial: Historial = field(default_factory=Historial)
    dias_almacenados: int | None = None
    dias_previstos_restantes: int | None = None
    fecha_salida_prevista: datetime | None = None

    controles: Controles = field(default_factory=Controles)
    plan: Plan = field(default_factory=Plan)
    dictamen: Dictamen | None = None
    episodios: tuple[Episodio, ...] = ()

    resultado_revision_plagas: ResultadoRevision | None = None
    revision_plagas_id: str | None = None
    revision_plagas_cubre_indicios_actuales: bool = False

    sensor_interno_hermetico: bool = False
    temperatura_ambiente_maxima_intervalo: Decimal | None = None
    datos_inconsistentes: tuple[str, ...] = ()

    version_base: str = "2.0"

    @property
    def es_hermetico(self) -> bool:
        return self.tipo_almacenamiento is Modalidad.HERMETICO

    @property
    def es_no_hermetico(self) -> bool:
        return self.tipo_almacenamiento is Modalidad.NO_HERMETICO

    @property
    def cuarentenas_abiertas(self) -> tuple[Episodio, ...]:
        return tuple(e for e in self.episodios if e.abierta and e.tipo == "CUARENTENA")

    @property
    def revisiones_abiertas(self) -> tuple[Episodio, ...]:
        return tuple(
            e for e in self.episodios
            if e.abierta and e.tipo in {"REVISION_PLAGAS", "REVISION_TERMICA", "CORRECCION"}
        )


class Solicitud(enum.Enum):
    """Sección 7.1. Varias causas pueden generar la misma solicitud sin anularse."""

    CUARENTENA = "CUARENTENA_SOLICITADA"
    SUSPENSION = "SUSPENSION_SOLICITADA"
    CORRECCION = "CORRECCION_SOLICITADA"
    MONITOREO = "MONITOREO_SOLICITADO"


@dataclass(frozen=True, slots=True)
class Motivo:
    """Una causa conservada en el resultado, con su regla, evidencia y fuentes."""

    id: str
    regla: str
    mensaje: str
    evidencias: tuple[Evidencia, ...] = ()
    fuentes: tuple[tuple[str, str | None], ...] = ()
    fundamento: str = "POLITICA_PROTOTIPO"


@dataclass(frozen=True, slots=True)
class Pendiente:
    campo: str
    motivo: str
    paso: int


@dataclass(frozen=True, slots=True)
class Estimacion:
    tipo: str
    descripcion: str
    campos: tuple[str, ...]
    id_tabla: str | None = None


@dataclass(frozen=True, slots=True)
class Accion:
    codigo: str
    descripcion: str
    responsable_requerido: str
