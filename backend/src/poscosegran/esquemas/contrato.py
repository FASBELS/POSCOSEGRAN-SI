"""Esquemas del anexo A.2.

Todas las propiedades están presentes en la salida; `| null` es ausencia
explícita y las listas vacías son `[]`. No se permiten propiedades adicionales:
un campo desconocido es un error de estructura, no un valor por omisión.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, Literal, TypeVar

from pydantic import AwareDatetime, StrictBool, StrictFloat, StrictInt, StrictStr, BaseModel, ConfigDict, Field, field_validator, model_validator

from ..dominio.campos import CAMPOS

T = TypeVar("T")

Rol = Literal["PRODUCTOR", "TECNICO", "ADMINISTRADOR", "INGENIERO_CONOCIMIENTO"]
Fase = Literal["INGRESO", "SEGUIMIENTO"]
Modalidad = Literal["HERMETICO", "NO_HERMETICO"]
Decision = Literal[
    "CUARENTENA",
    "BLOQUEAR_INGRESO",
    "RETIRAR_LOTE",
    "CORREGIR_Y_REEVALUAR",
    "SIN_CONCLUSION_AUTOMATICA",
    "AUTORIZAR_CON_MONITOREO",
    "AUTORIZAR_ALMACENAMIENTO",
]
Rama = Literal["R30.1", "R30.2", "R30.3", "R30.4", "R30.5", "R30.6", "R30.7", "R30.8", "R30.9"]
UnidadDato = Literal[
    "PCT_BH", "PCT_HR", "PCT_MASA", "CELSIUS", "METROS", "DIAS", "FRACCION", "BOOLEANO", "TEXTO"
]
EstadoDato = Literal["VALIDO", "DESCONOCIDO", "INVALIDO", "VENCIDO"]
EstadoVigencia = Literal["VIGENTE", "VENCIDA", "INVALIDADA", "NO_AUTORIZADO", "SIN_EVALUACION"]
Captura = Literal["APORTADO", "DESCONOCIDO", "NO_APLICA"]
Operador = Literal["GT", "GTE", "LT", "LTE", "EQ", "NEQ", "PRESENCIA", "VIGENCIA"]
Fundamento = Literal["PUBLICADO", "TRANSFERIDO", "POLITICA_PROTOTIPO", "MIXTO"]
TipoControl = Literal["INGRESO", "GRANO", "EXTERIOR", "ALMACEN"]


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class Pagina(Base, Generic[T]):
    items: list[T]
    siguiente_cursor: str | None


class CampoError(Base):
    ruta: str
    codigo: str
    mensaje: str


class ErrorAPI(Base):
    codigo: str
    mensaje: str
    campos: list[CampoError]
    id_solicitud: uuid.UUID


class Revisiones(Base):
    revision_unidad: int = Field(ge=1)
    revision_almacen: int = Field(ge=1)


class Perfil(Base):
    id: uuid.UUID
    nombre: str
    roles: list[Rol]


class AlmacenEntrada(Base):
    nombre: str = Field(min_length=1, max_length=200)
    ubicacion: str = Field(min_length=1, max_length=300)
    clima_calido: StrictBool | None
    fundamento_clima: str | None

    @model_validator(mode="after")
    def _clima_con_fundamento(self) -> "AlmacenEntrada":
        if self.clima_calido is not None and not (self.fundamento_clima or "").strip():
            raise ValueError(
                "clima_calido es una clasificación territorial documentada: exige fundamento"
            )
        return self


class Almacen(AlmacenEntrada):
    id: uuid.UUID
    revision: int
    creado_en: AwareDatetime


class LoteEntrada(Base):
    codigo: str = Field(min_length=1, max_length=80)
    variedad: Literal["MAIZ_CHULPI"]
    uso_final: Literal["ALIMENTACION"]


class Lote(LoteEntrada):
    id: uuid.UUID
    id_propietario: uuid.UUID
    revision: int
    creado_en: AwareDatetime


class UnidadEntrada(Base):
    id_lote: uuid.UUID
    id_almacen: uuid.UUID
    nombre_recipiente: str = Field(min_length=1, max_length=120)
    tipo_almacenamiento: Modalidad | None


class Unidad(UnidadEntrada):
    id: uuid.UUID
    id_recipiente: uuid.UUID
    revision: int
    revision_almacen: int
    id_evaluacion_actual: uuid.UUID | None
    creado_en: AwareDatetime


class ObservacionEntrada(Base):
    """Una omisión significa desconocido: no implica falso, cero ni no aplicable."""

    campo: str
    captura: Captura
    valor: StrictFloat | StrictInt | StrictBool | StrictStr | None
    unidad: UnidadDato
    valor_original: str | None
    fecha_observacion: AwareDatetime | None
    metodo: str | None
    evidencia: str | None
    motivo_no_aplica: str | None

    @field_validator("campo")
    @classmethod
    def _campo_conocido(cls, valor: str) -> str:
        if valor not in CAMPOS:
            raise ValueError(f"campo no capturable: {valor}")
        return valor

    @model_validator(mode="after")
    def _coherencia(self) -> "ObservacionEntrada":
        definicion = CAMPOS[self.campo]
        if self.unidad != definicion.unidad:
            raise ValueError(
                f"{self.campo} se expresa en {definicion.unidad}, no en {self.unidad}"
            )

        if self.captura == "APORTADO":
            if self.valor is None:
                raise ValueError("una observación aportada necesita valor")
            if self.fecha_observacion is None or not (self.metodo or "").strip():
                raise ValueError("una observación aportada necesita fecha y método")
            esperado = {"N": (int, float), "B": (bool,), "X": (str,), "F": (str,)}[definicion.tipo]
            if definicion.tipo == "N" and isinstance(self.valor, bool):
                raise ValueError(f"{self.campo} es numérico: un booleano no se convierte")
            if not isinstance(self.valor, esperado):
                raise ValueError(f"{self.campo} espera un valor de tipo {definicion.tipo}")
        elif self.valor is not None:
            raise ValueError("solo una observación aportada lleva valor")

        if self.captura == "NO_APLICA":
            if not definicion.admite_no_aplica:
                raise ValueError(f"{self.campo} no admite NO_APLICA")
            if not (self.motivo_no_aplica or "").strip():
                raise ValueError("NO_APLICA exige causa")
        return self


class ObservacionValidada(Base):
    id: uuid.UUID
    entrada: ObservacionEntrada
    aplicabilidad: Literal["APLICA", "NO_APLICA"]
    estado_dato: EstadoDato | None
    id_responsable: uuid.UUID
    procedencia: Literal["ACTUAL", "HISTORICA", "ESTIMADA"]
    incidencias_validacion: list[str]


class IntervaloEntrada(Base):
    inicio: AwareDatetime
    fin: AwareDatetime
    humedad_grano: float | None
    temperatura_grano: float | None
    metodo: str | None
    evidencia: str | None

    @model_validator(mode="after")
    def _orden(self) -> "IntervaloEntrada":
        if self.fin <= self.inicio:
            raise ValueError("el intervalo termina antes de empezar")
        return self


class HistorialEntrada(Base):
    fecha_inicio_historial: AwareDatetime | None
    vida_previa_documentada: float | None
    evidencia_vida_previa: str | None
    intervalos_historial: list[IntervaloEntrada]

    @model_validator(mode="after")
    def _vida_documentada(self) -> "HistorialEntrada":
        if self.vida_previa_documentada is not None:
            if self.vida_previa_documentada < 0:
                raise ValueError("la vida previa no puede ser negativa")
            if not (self.evidencia_vida_previa or "").strip():
                raise ValueError(
                    "el valor cero o cualquier vida previa exige constancia del origen "
                    "del historial"
                )
        return self


class EvaluacionEntrada(Revisiones):
    fase: Fase | None
    observaciones: list[ObservacionEntrada]
    historial: HistorialEntrada
    dias_previstos_restantes: int | None
    fecha_salida_prevista: AwareDatetime | None

    @field_validator("observaciones")
    @classmethod
    def _sin_repetidos(cls, valores: list[ObservacionEntrada]) -> list[ObservacionEntrada]:
        vistos = {observacion.campo for observacion in valores}
        if len(vistos) != len(valores):
            raise ValueError("un mismo campo no puede enviarse dos veces en una evaluación")
        return valores

    @field_validator("dias_previstos_restantes")
    @classmethod
    def _plazo_positivo(cls, valor: int | None) -> int | None:
        if valor is not None and valor <= 0:
            raise ValueError("los días restantes previstos deben ser mayores que cero")
        return valor


class Borrador(Base):
    id: uuid.UUID
    id_unidad: uuid.UUID
    revision: int
    contenido: EvaluacionEntrada
    actualizado_en: AwareDatetime


class FuenteRef(Base):
    id_fuente: str
    localizador: str | None


class EvidenciaMotivo(Base):
    campo: str
    valor_observado: StrictFloat | StrictInt | StrictBool | StrictStr | None
    unidad: UnidadDato | None
    fecha_observacion: AwareDatetime | None
    operador: Operador | None
    umbral: StrictFloat | StrictInt | StrictBool | StrictStr | None


class Motivo(Base):
    id: str
    regla: str
    mensaje: str
    evidencias: list[EvidenciaMotivo]
    fuentes: list[FuenteRef]
    fundamento: Fundamento


class Accion(Base):
    codigo: str
    descripcion: str
    responsable_requerido: Literal["PRODUCTOR", "TECNICO"]
    id_incidencia: uuid.UUID | None


class DatoPendiente(Base):
    campo: str
    motivo: str
    paso: Literal[1, 2, 3, 4, 5, 6]


class Estimacion(Base):
    tipo: Literal["ESTIMACION_HERMETICA", "SUSTITUCION_TABLA"]
    descripcion: str
    campos: list[str]
    id_tabla: str | None


class CeldaTabla(Base):
    id_tabla: str
    humedad_fila: float
    temperatura_columna_f: float
    dias_referencia: int


class CalculosTiempo(Base):
    vida_consumida: float | None
    vida_minima_documentada: float | None
    vida_proyectada: float | None
    tiempo_referencia_actual: int | None
    celda_tabla: CeldaTabla | None


class Vigencia(Base):
    id_unidad: uuid.UUID
    id_evaluacion: uuid.UUID | None
    estado: EstadoVigencia
    consultada_en: AwareDatetime
    fecha_proximo_control: AwareDatetime | None
    fecha_vencimiento_autorizacion: AwareDatetime | None
    causas: list[str]


class Evaluacion(Base):
    id: uuid.UUID
    id_unidad: uuid.UUID
    id_lote: uuid.UUID
    id_recipiente: uuid.UUID
    id_almacen: uuid.UUID
    fecha_evaluacion: AwareDatetime
    fase: Fase | None
    decision_final: Decision
    rama_r30: Rama
    motivos: list[Motivo]
    acciones_requeridas: list[Accion]
    datos_pendientes: list[DatoPendiente]
    estimaciones_y_sustituciones: list[Estimacion]
    reglas_activadas: list[str]
    observaciones_aplicadas: list[ObservacionValidada]
    calculos_tiempo: CalculosTiempo
    fecha_proximo_control: AwareDatetime | None
    fecha_vencimiento_autorizacion: AwareDatetime | None
    version_base: str
    version_parametros: str
    version_motor: str


class ResultadoEvaluacion(Base):
    evaluacion: Evaluacion
    vigencia: Vigencia


class ControlEntrada(Revisiones):
    tipo: TipoControl
    fecha: AwareDatetime
    observaciones: list[ObservacionEntrada]
    evidencia: str = Field(min_length=1)


class Control(Base):
    id: uuid.UUID
    id_unidad: uuid.UUID
    tipo: TipoControl
    fecha: AwareDatetime
    completo: bool
    campos_pendientes: list[str]
    id_responsable: uuid.UUID
    evidencia: str


class PlanEntrada(Revisiones):
    fecha_proximo_control: AwareDatetime
    intervalo_dias: int = Field(gt=0, le=365)
    fecha_salida_prevista: AwareDatetime
    actividades: str = Field(min_length=1)


class Plan(Base):
    id: uuid.UUID
    id_unidad: uuid.UUID
    fecha_proximo_control: AwareDatetime
    intervalo_dias: int
    fecha_salida_prevista: AwareDatetime
    actividades: str
    vigente: bool
    id_responsable: uuid.UUID


class DictamenEntrada(Revisiones):
    humedad_min: float
    humedad_max: float
    plazo_maximo_dias: int = Field(gt=0, le=365)
    vence_en: AwareDatetime
    condiciones: str = Field(min_length=1)
    evidencia: str = Field(min_length=1)

    @model_validator(mode="after")
    def _banda(self) -> "DictamenEntrada":
        if self.humedad_min > self.humedad_max:
            raise ValueError("la banda de humedad está invertida")
        return self


class Dictamen(Base):
    id: uuid.UUID
    id_unidad: uuid.UUID
    humedad_min: float
    humedad_max: float
    plazo_maximo_dias: int
    emitido_en: AwareDatetime
    vence_en: AwareDatetime
    condiciones: str
    evidencia: str
    id_tecnico: uuid.UUID
    vigente: bool


class Incidencia(Base):
    id: uuid.UUID
    id_unidad: uuid.UUID
    revision: int
    tipo: Literal["CUARENTENA", "REVISION_PLAGAS", "REVISION_TERMICA", "CORRECCION"]
    estado: Literal["ABIERTA", "CERRADA"]
    causas: list[str]
    creada_en: AwareDatetime
    cerrada_en: AwareDatetime | None


class RevisionEntrada(Revisiones):
    revision_incidencia: int = Field(ge=1)
    resultado: Literal["PENDIENTE", "CONFIRMADA", "DESCARTADA"]
    evidencia: str = Field(min_length=1)


class Revision(Base):
    id: uuid.UUID
    id_incidencia: uuid.UUID
    resultado: Literal["PENDIENTE", "CONFIRMADA", "DESCARTADA"]
    evidencia: str
    id_tecnico: uuid.UUID
    fecha: AwareDatetime


class ResolucionEntrada(Revisiones):
    revision_incidencia: int = Field(ge=1)
    evidencia: str = Field(min_length=1)
    disposicion: str = Field(min_length=1)


class Resolucion(Base):
    id: uuid.UUID
    id_incidencia: uuid.UUID
    evidencia: str
    disposicion: str
    id_tecnico: uuid.UUID
    fecha: AwareDatetime


class AdmisionEntrada(Revisiones):
    id_evaluacion: uuid.UUID
    tipo: Literal["INGRESO", "CONTINUIDAD"]


class Admision(Base):
    id: uuid.UUID
    id_unidad: uuid.UUID
    id_evaluacion: uuid.UUID
    tipo: Literal["INGRESO", "CONTINUIDAD"]
    registrado_en: AwareDatetime
    id_responsable: uuid.UUID


class Fuente(Base):
    id: str
    referencia_markdown: str


class Regla(Base):
    id: str
    antecedente: str
    consecuente: str
    accion: str
    fundamento_markdown: str


class Parametro(Base):
    nombre: str
    valor: float
    unidad: str
    fundamento: Literal["PUBLICADO", "TRANSFERIDO", "POLITICA_PROTOTIPO", "MIXTO"]
    fuentes: list[str]
    descripcion: str


class Catalogo(Base):
    version_base: str
    reglas: list[Regla]
    ramas_r30: list[Regla]
    fuentes: list[Fuente]
    # Extensión del contrato (docs/DECISIONES.md, D-SE-3): la base como datos.
    version_parametros: str | None = None
    hash_base: str | None = None
    parametros: list[Parametro] = Field(default_factory=list)
    uso_campos: dict[str, list[str]] = Field(
        default_factory=dict, description="Para cada campo, las reglas que lo usan: «¿por qué se pide este dato?»"
    )


# --- Módulo de explicación ----------------------------------------------------------


class HechoInicial(Base):
    campo: str
    valor: str | float | bool | None
    procedencia: str


class PasoExplicacion(Base):
    orden: int
    regla: str
    etapa: str
    pasada: int
    conclusion: str | None
    solicitudes: list[str]
    porque: list[str]
    antecedente: str | None


class RamaExplicada(Base):
    rama: str
    decision: str
    aplicada: bool
    valor: Literal["VERDADERO", "FALSO", "DESCONOCIDO", "NO_APLICA"]
    faltan: list[str]


class Explicacion(Base):
    id_evaluacion: uuid.UUID
    decision: str
    etiqueta: str
    rama: str
    resumen: str
    cadena: list[PasoExplicacion] = Field(description="¿Cómo? Reglas que llevaron a la decisión.")
    traza_completa: list[PasoExplicacion]
    ramas: list[RamaExplicada]
    por_que_no: list[RamaExplicada] = Field(description="Qué le faltó a cada autorización no concedida.")
    hechos_iniciales: list[HechoInicial]
    hechos_inferidos: list[str]
    no_aplicables: list[str]
    version_base: str
    version_parametros: str
    hash_base: str


# --- Módulo de adquisición ------------------------------------------------------------


class VersionConocimientoResumen(Base):
    id: uuid.UUID
    version_base: str
    version_parametros: str
    version_motor: str
    hash_base: str
    estado: Literal["PROPUESTA", "ACTIVADA", "DESCARTADA", "SUPERADA"]
    activa: bool
    motivo: str | None
    id_version_origen: uuid.UUID | None
    cargada_en: AwareDatetime
    activada_en: AwareDatetime | None


class CambioParametro(Base):
    nombre: str
    anterior: float
    nuevo: float
    unidad: str


class CambioRegla(Base):
    produccion: str
    regla: str
    tipo: Literal["MODIFICADA", "NUEVA", "RETIRADA"]


class CasoAfectado(Base):
    id: str = Field(
        description="Identificador del caso dentro de la simulación. Los casos de "
        "referencia usan su nombre; las evaluaciones reales usan un índice opaco, "
        "porque el ingeniero del conocimiento no accede a unidades concretas."
    )
    origen: str
    decision_antes: str
    decision_despues: str
    rama_antes: str
    rama_despues: str
    reglas_nuevas: list[str]
    reglas_retiradas: list[str]


class Impacto(Base):
    evaluados: int
    cambian: int
    transiciones: dict[str, int]
    casos: list[CasoAfectado]
    nuevas_autorizaciones: int


class PropuestaEntrada(Base):
    motivo: str = Field(min_length=15, max_length=2000)
    version_parametros: str | None = Field(default=None, max_length=40)
    version_base: str | None = Field(default=None, max_length=40)
    parametros: dict[str, StrictFloat | StrictInt] = Field(default_factory=dict)
    reglas: dict[str, dict[str, Any] | None] = Field(
        default_factory=dict, description="Id de regla de producción → nueva definición completa; null la retira."
    )
    guardar: bool = Field(default=False, description="false: solo simular; true: registrar como PROPUESTA si es válida.")


class PropuestaResultado(Base):
    valida: bool
    errores: list[str]
    advertencias: list[str]
    version_base: str
    version_parametros: str
    cambios_parametros: list[CambioParametro]
    cambios_reglas: list[CambioRegla]
    impacto: Impacto | None
    version: VersionConocimientoResumen | None = None


class ActivacionEntrada(Base):
    motivo: str = Field(min_length=15, max_length=2000)


class DescarteEntrada(Base):
    motivo: str = Field(min_length=15, max_length=2000)


class DetalleVersion(Base):
    version: VersionConocimientoResumen
    parametros: list[Parametro]
    reglas: list[dict[str, Any]] = Field(description="Reglas de producción tal como las ejecuta el motor.")
    cambios_respecto_origen: list[CambioParametro]


class ValidarReglaEntrada(Base):
    definicion: dict[str, Any] = Field(description="Definición completa de la regla de producción a validar.")


class ValidarReglaResultado(Base):
    valida: bool
    errores: list[str]

class ControlProximo(Base):
    id_unidad: uuid.UUID
    nombre: str
    fecha: AwareDatetime
    estado: Literal["PENDIENTE", "ATRASADO"]


class Inicio(Base):
    unidades_total: int
    cuarentenas_abiertas: int
    correcciones_pendientes: int
    controles_proximos: list[ControlProximo]


class EventoEntrada(Revisiones):
    tipo: Literal["LIMPIEZA_GENERAL", "APERTURA", "RESELLADO", "SECADO", "ENFRIAMIENTO", "EXPOSICION_AGUA", "CARGA_DESCARGA"]
    fecha: AwareDatetime
    evidencia: str = Field(min_length=1)


class Evento(Base):
    id: uuid.UUID
    id_unidad: uuid.UUID
    tipo: Literal["LIMPIEZA_GENERAL", "APERTURA", "RESELLADO", "SECADO", "ENFRIAMIENTO", "EXPOSICION_AGUA", "CARGA_DESCARGA"]
    fecha: AwareDatetime
    evidencia: str
    id_responsable: uuid.UUID
