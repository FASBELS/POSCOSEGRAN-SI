"""Valores cerrados del dominio.

CONGELADO: las migraciones importan estas tuplas. No se edita un valor existente
ni se elimina; se añade uno nuevo junto con su migración correspondiente.
Los nombres reproducen literalmente el anexo A.2 del contrato.
"""

from __future__ import annotations

from typing import Final

# INGENIERO_CONOCIMIENTO se añadió en la migración 0003: opera el módulo de adquisición.
ROL: Final = ("PRODUCTOR", "TECNICO", "ADMINISTRADOR", "INGENIERO_CONOCIMIENTO")
# Ciclo de vida de una versión de la base de conocimiento (migración 0003).
ESTADO_VERSION: Final = ("PROPUESTA", "ACTIVADA", "DESCARTADA")
FASE: Final = ("INGRESO", "SEGUIMIENTO")
MODALIDAD: Final = ("HERMETICO", "NO_HERMETICO")
VARIEDAD: Final = ("MAIZ_CHULPI",)
USO_FINAL: Final = ("ALIMENTACION",)

DECISION: Final = (
    "CUARENTENA",
    "BLOQUEAR_INGRESO",
    "RETIRAR_LOTE",
    "CORREGIR_Y_REEVALUAR",
    "SIN_CONCLUSION_AUTOMATICA",
    "AUTORIZAR_CON_MONITOREO",
    "AUTORIZAR_ALMACENAMIENTO",
)
RAMA_R30: Final = (
    "R30.1",
    "R30.2",
    "R30.3",
    "R30.4",
    "R30.5",
    "R30.6",
    "R30.7",
    "R30.8",
    "R30.9",
)

UNIDAD_DATO: Final = (
    "PCT_BH",
    "PCT_HR",
    "PCT_MASA",
    "CELSIUS",
    "METROS",
    "DIAS",
    "FRACCION",
    "BOOLEANO",
    "TEXTO",
)
ESTADO_DATO: Final = ("VALIDO", "DESCONOCIDO", "INVALIDO", "VENCIDO")
ESTADO_VIGENCIA: Final = (
    "VIGENTE",
    "VENCIDA",
    "INVALIDADA",
    "NO_AUTORIZADO",
    "SIN_EVALUACION",
)

CAPTURA: Final = ("APORTADO", "DESCONOCIDO", "NO_APLICA")
APLICABILIDAD: Final = ("APLICA", "NO_APLICA")
PROCEDENCIA: Final = ("ACTUAL", "HISTORICA", "ESTIMADA")

FUNDAMENTO_MOTIVO: Final = ("PUBLICADO", "TRANSFERIDO", "POLITICA_PROTOTIPO", "MIXTO")
OPERADOR: Final = ("GT", "GTE", "LT", "LTE", "EQ", "NEQ", "PRESENCIA", "VIGENCIA")
RESPONSABLE_REQUERIDO: Final = ("PRODUCTOR", "TECNICO")
TIPO_ESTIMACION: Final = ("ESTIMACION_HERMETICA", "SUSTITUCION_TABLA")

TIPO_CONTROL: Final = ("INGRESO", "GRANO", "EXTERIOR", "ALMACEN")
TIPO_EVENTO: Final = (
    "LIMPIEZA_GENERAL",
    "APERTURA",
    "RESELLADO",
    "SECADO",
    "ENFRIAMIENTO",
    "EXPOSICION_AGUA",
    "CARGA_DESCARGA",
)
TIPO_INCIDENCIA: Final = (
    "CUARENTENA",
    "REVISION_PLAGAS",
    "REVISION_TERMICA",
    "CORRECCION",
)
ESTADO_INCIDENCIA: Final = ("ABIERTA", "CERRADA")
RESULTADO_REVISION: Final = ("PENDIENTE", "CONFIRMADA", "DESCARTADA")
TIPO_ADMISION: Final = ("INGRESO", "CONTINUIDAD")

TIPO_ASIGNACION: Final = ("ALMACEN", "LOTE")
