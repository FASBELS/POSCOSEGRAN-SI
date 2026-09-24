"""Validación de observaciones y reconstrucción del historial.

El servidor decide aplicabilidad, estado y procedencia: el cliente no los impone.
Un valor fuera de dominio se conserva como INVALIDO —produce corrección— pero no
participa en comparaciones. Un dato reutilizado del historial conserva su fecha y
se marca HISTORICA; nunca se presenta como una observación recién realizada.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation

import sqlalchemy as sa
from sqlalchemy.orm import Session

from ..db.modelos import Observacion as ObservacionBD
from ..dominio.campos import CAMPOS, DOMINIOS, METODOS_HUMEDAD
from ..dominio.valores import Dato, EstadoDato, Procedencia
from ..esquemas.contrato import ObservacionEntrada, ObservacionValidada

CAMPOS_FECHA = {campo for campo, definicion in CAMPOS.items() if definicion.tipo == "F"}


def _a_decimal(valor: object) -> Decimal | None:
    try:
        return Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        return None


def validar(entrada: ObservacionEntrada) -> tuple[str | None, list[str]]:
    """Devuelve el estado del dato y sus incidencias de validación."""
    incidencias: list[str] = []
    if entrada.captura == "NO_APLICA":
        return None, incidencias
    if entrada.captura == "DESCONOCIDO":
        return "DESCONOCIDO", incidencias

    definicion = CAMPOS[entrada.campo]
    if definicion.tipo == "N":
        numero = _a_decimal(entrada.valor)
        if numero is None:
            incidencias.append("valor no numérico")
            return "INVALIDO", incidencias
        rango = DOMINIOS.get(entrada.campo)
        if rango and not (Decimal(str(rango[0])) <= numero <= Decimal(str(rango[1]))):
            incidencias.append(f"fuera del dominio {rango[0]}–{rango[1]}")
            return "INVALIDO", incidencias
    if entrada.campo == "metodo_humedad" and entrada.valor not in METODOS_HUMEDAD:
        incidencias.append("método de humedad no reconocido")
        return "INVALIDO", incidencias
    if entrada.campo in CAMPOS_FECHA:
        try:
            fecha = datetime.fromisoformat(str(entrada.valor))
            if fecha.tzinfo is None or fecha > datetime.now(fecha.tzinfo):
                raise ValueError("fecha sin zona o futura")
        except ValueError:
            incidencias.append("fecha no interpretable")
            return "INVALIDO", incidencias
    if entrada.fecha_observacion is not None and entrada.fecha_observacion > datetime.now(
        entrada.fecha_observacion.tzinfo
    ):
        incidencias.append("fecha de observación en el futuro")
        return "INVALIDO", incidencias
    return "VALIDO", incidencias


def a_fila(
    entrada: ObservacionEntrada,
    *,
    id_unidad: uuid.UUID,
    id_responsable: uuid.UUID,
    id_control: uuid.UUID | None = None,
) -> ObservacionBD:
    estado, incidencias = validar(entrada)
    definicion = CAMPOS[entrada.campo]
    fila = ObservacionBD(
        id=uuid.uuid4(),
        id_unidad=id_unidad,
        id_control=id_control,
        campo=entrada.campo,
        captura=entrada.captura,
        unidad_dato=entrada.unidad,
        valor_original=entrada.valor_original,
        fecha_observacion=entrada.fecha_observacion,
        metodo=entrada.metodo,
        evidencia=entrada.evidencia,
        motivo_no_aplica=entrada.motivo_no_aplica,
        aplicabilidad="NO_APLICA" if entrada.captura == "NO_APLICA" else "APLICA",
        estado_dato=estado,
        procedencia="ACTUAL",
        incidencias_validacion=incidencias,
        id_responsable=id_responsable,
    )
    if entrada.captura == "APORTADO":
        if definicion.tipo == "N":
            fila.valor_numero = _a_decimal(entrada.valor)
        elif definicion.tipo == "B":
            fila.valor_booleano = bool(entrada.valor)
        else:
            fila.valor_texto = str(entrada.valor)
    return fila


def a_dato(fila: ObservacionBD) -> Dato:
    """Convierte una fila persistida en el dato que consume el motor."""
    definicion = CAMPOS.get(fila.campo)
    valor: object | None
    if fila.valor_numero is not None:
        valor = fila.valor_numero
    elif fila.valor_booleano is not None:
        valor = fila.valor_booleano
    elif fila.valor_texto is not None:
        valor = fila.valor_texto
        if definicion is not None and definicion.tipo == "F":
            try:
                valor = datetime.fromisoformat(fila.valor_texto)
            except ValueError:
                valor = fila.valor_texto
    else:
        valor = None

    return Dato(
        campo=fila.campo,
        estado=EstadoDato(fila.estado_dato) if fila.estado_dato else EstadoDato.DESCONOCIDO,
        valor=valor,
        unidad=fila.unidad_dato,
        fecha_observacion=fila.fecha_observacion,
        metodo=fila.metodo,
        procedencia=Procedencia(fila.procedencia),
        no_aplica=fila.aplicabilidad == "NO_APLICA",
        motivo_no_aplica=fila.motivo_no_aplica,
    )


def historicas(
    sesion: Session, id_unidad: uuid.UUID, excluir: set[str], desde: datetime | None = None
) -> list[ObservacionBD]:
    """Última observación válida por campo, de evaluaciones o controles anteriores.

    Se reutiliza para no exigir abrir un recipiente hermético solo para repetir un
    dato que ya consta. Conserva su fecha y pasa a procedencia HISTORICA.
    """
    filas = sesion.scalars(
        sa.select(ObservacionBD).where(
            ObservacionBD.id_unidad == id_unidad,
            ObservacionBD.campo.notin_(excluir) if excluir else sa.true(),
            ObservacionBD.fecha_observacion >= desde if desde else sa.true(),
        ).order_by(ObservacionBD.creada_en.desc(), ObservacionBD.id.desc())
    ).all()
    vistas: dict[str, ObservacionBD] = {}
    for fila in filas:
        vistas.setdefault(fila.campo, fila)
    return list(vistas.values())



def a_validada(fila: ObservacionBD) -> ObservacionValidada:
    if fila.valor_numero is not None:
        valor: float | bool | str | None = float(fila.valor_numero)
    elif fila.valor_booleano is not None:
        valor = fila.valor_booleano
    else:
        valor = fila.valor_texto
    return ObservacionValidada(
        id=fila.id,
        entrada=ObservacionEntrada(
            campo=fila.campo,
            captura=fila.captura,
            valor=valor,
            unidad=fila.unidad_dato,
            valor_original=fila.valor_original,
            fecha_observacion=fila.fecha_observacion,
            metodo=fila.metodo,
            evidencia=fila.evidencia,
            motivo_no_aplica=fila.motivo_no_aplica,
        ),
        aplicabilidad=fila.aplicabilidad,
        estado_dato=fila.estado_dato,
        id_responsable=fila.id_responsable,
        procedencia=fila.procedencia,
        incidencias_validacion=list(fila.incidencias_validacion),
    )
