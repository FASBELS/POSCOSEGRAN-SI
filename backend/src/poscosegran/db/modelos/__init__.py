"""Modelos ORM. Importar este módulo registra todas las tablas en Base.metadata."""

from .captura import Borrador, Control, Evento, Observacion
from .conocimiento import Fuente, Regla, VersionConocimiento
from .dominio import Almacen, Lote, Recipiente, Unidad
from .evaluacion import (
    AccionRequerida,
    DatoPendiente,
    Estimacion,
    Evaluacion,
    Motivo,
    MotivoEvidencia,
    MotivoFuente,
    ObservacionAplicada,
)
from .identidad import AsignacionAlmacen, AsignacionLote, Usuario, UsuarioRol
from .operacion import ClaveIdempotencia, RegistroAuditoria
from .seguimiento import (
    Admision,
    Dictamen,
    Incidencia,
    Plan,
    Resolucion,
    RevisionIncidencia,
)

__all__ = [
    "AccionRequerida", "Admision", "Almacen", "AsignacionAlmacen", "AsignacionLote",
    "Borrador", "ClaveIdempotencia", "Control", "DatoPendiente", "Dictamen",
    "Estimacion", "Evaluacion", "Evento", "Fuente", "Incidencia", "Lote", "Motivo",
    "MotivoEvidencia", "MotivoFuente", "Observacion", "ObservacionAplicada", "Plan",
    "Recipiente", "RegistroAuditoria", "Regla", "Resolucion", "RevisionIncidencia",
    "Unidad", "Usuario", "UsuarioRol", "VersionConocimiento",
]
