"""Construcción de la instantánea, ejecución del motor y persistencia."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from dataclasses import replace
from fastapi.encoders import jsonable_encoder
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Session

from ..db.modelos import (
    AccionRequerida,
    Control,
    Evento,
    RevisionIncidencia,
    Almacen,
    DatoPendiente,
    Dictamen as DictamenBD,
    Estimacion as EstimacionBD,
    Evaluacion as EvaluacionBD,
    Incidencia,
    Motivo as MotivoBD,
    MotivoEvidencia,
    MotivoFuente,
    Observacion as ObservacionBD,
    ObservacionAplicada,
    Plan as PlanBD,
    Unidad,
    VersionConocimiento,
)
from ..dominio import motor
from ..sistema_experto import serializacion
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
from ..dominio.valores import Conjunto, D, F, Tri, V, Procedencia
from ..esquemas import contrato as api
from . import observaciones as obs
from .aplicabilidad import comprobar

CAMPOS_CONTROL = {
    "fecha_inspeccion_grano",
    "fecha_inspeccion_exterior",
    "fecha_control_almacen",
    "ingreso_inspeccionado",
    "hay_evento_que_invalida_control",
    "sensor_interno_hermetico",
    "temperatura_ambiente_maxima_intervalo",
    "clima_calido",
}


def _tri(valor: bool | None) -> Tri:
    if valor is None:
        return D
    return V if valor else F


def construir_instantanea(
    sesion: Session,
    *,
    unidad: Unidad,
    almacen: Almacen,
    entrada: api.EvaluacionEntrada,
    filas_actuales: list[ObservacionBD],
    ahora: datetime,
) -> tuple[Instantanea, list[ObservacionBD]]:
    """Mezcla las observaciones enviadas con las recuperadas del historial."""
    enviados = {fila.campo for fila in filas_actuales}
    reutilizadas = obs.historicas(sesion, unidad.id, excluir=enviados)

    aplicadas = [*filas_actuales, *reutilizadas]
    datos = {fila.campo: replace(obs.a_dato(fila), procedencia=Procedencia.HISTORICA)
             for fila in reutilizadas}
    datos.update({fila.campo: obs.a_dato(fila) for fila in filas_actuales})

    datos = comprobar(datos, unidad.tipo_almacenamiento, entrada.fase)

    episodios = tuple(
        Episodio(id=str(fila.id), tipo=fila.tipo, causas=tuple(fila.causas), abierta=True)
        for fila in sesion.scalars(
            sa.select(Incidencia).where(
                Incidencia.id_unidad == unidad.id, Incidencia.estado == "ABIERTA"
            )
        )
    )

    plan_bd = sesion.scalar(
        sa.select(PlanBD).where(PlanBD.id_unidad == unidad.id, PlanBD.vigente.is_(True))
    )
    plan = (
        Plan(
            registrado=True,
            intervalo_dias=plan_bd.intervalo_dias,
            fecha_salida_prevista=plan_bd.fecha_salida_prevista,
            vigente=True,
        )
        if plan_bd
        else Plan()
    )

    dictamen_bd = sesion.scalar(
        sa.select(DictamenBD)
        .where(
            DictamenBD.id_unidad == unidad.id,
            DictamenBD.anulado_en.is_(None),
            DictamenBD.vence_en > ahora,
        )
        .order_by(DictamenBD.vence_en.desc())
        .limit(1)
    )
    dictamen = (
        Dictamen(
            humedad_min=dictamen_bd.humedad_min,
            humedad_max=dictamen_bd.humedad_max,
            plazo_maximo_dias=dictamen_bd.plazo_maximo_dias,
            vence_en=dictamen_bd.vence_en,
            vigente=True,
        )
        if dictamen_bd
        else None
    )

    # Los controles completos aportan fechas verificadas; los parciales no renuevan vigencia.
    from ..dominio.valores import Dato, EstadoDato
    fechas_control = {"GRANO": "fecha_inspeccion_grano", "EXTERIOR": "fecha_inspeccion_exterior",
                      "ALMACEN": "fecha_control_almacen"}
    for tipo, campo in fechas_control.items():
        control = sesion.scalar(sa.select(Control).where(Control.id_unidad == unidad.id,
            Control.tipo == tipo, Control.completo.is_(True)).order_by(Control.fecha.desc()).limit(1))
        previa = datos.get(campo)
        if control and (previa is None or previa.fecha is None or control.fecha > previa.fecha):
            datos[campo] = Dato(campo=campo, estado=EstadoDato.VALIDO, valor=control.fecha)
    evento = sesion.scalar(sa.select(Evento).where(Evento.id_unidad == unidad.id)
                          .order_by(Evento.creado_en.desc()).limit(1))
    if evento and evento.tipo in {"APERTURA", "RESELLADO", "SECADO", "ENFRIAMIENTO", "EXPOSICION_AGUA", "CARGA_DESCARGA"}:
        # Una comprobación anterior al evento no demuestra las condiciones posteriores.
        for campo in ("cierre_seguro", "sello_integro", "temperatura_grano_previa",
                      "fecha_inspeccion_grano", "fecha_inspeccion_exterior", "ingreso_inspeccionado"):
            dato = datos.get(campo)
            if dato and (dato.fecha_observacion is None or dato.fecha_observacion <= evento.fecha):
                datos[campo] = replace(dato, estado=EstadoDato.VENCIDO)

    controles = Controles(
        fecha_inspeccion_grano=datos["fecha_inspeccion_grano"].fecha
        if "fecha_inspeccion_grano" in datos
        else None,
        fecha_inspeccion_exterior=datos["fecha_inspeccion_exterior"].fecha
        if "fecha_inspeccion_exterior" in datos
        else None,
        fecha_control_almacen=datos["fecha_control_almacen"].fecha
        if "fecha_control_almacen" in datos
        else None,
        ingreso_inspeccionado=datos["ingreso_inspeccionado"].booleano
        if "ingreso_inspeccionado" in datos
        else D,
        hay_evento_que_invalida_control=datos["hay_evento_que_invalida_control"].booleano
        if "hay_evento_que_invalida_control" in datos
        else F,
    )

    historial = Historial(
        fecha_inicio_historial=entrada.historial.fecha_inicio_historial,
        vida_previa_documentada=(
            Decimal(str(entrada.historial.vida_previa_documentada))
            if entrada.historial.vida_previa_documentada is not None
            else None
        ),
        evidencia_vida_previa=entrada.historial.evidencia_vida_previa,
        intervalos=tuple(
            Intervalo(
                inicio=tramo.inicio,
                fin=tramo.fin,
                humedad_grano=(
                    Decimal(str(tramo.humedad_grano)) if tramo.humedad_grano is not None else None
                ),
                temperatura_grano=(
                    Decimal(str(tramo.temperatura_grano))
                    if tramo.temperatura_grano is not None
                    else None
                ),
                metodo=tramo.metodo,
                evidencia=tramo.evidencia,
            )
            for tramo in entrada.historial.intervalos_historial
        ),
    )

    dias_almacenados = (
        (ahora - entrada.historial.fecha_inicio_historial).days
        if entrada.historial.fecha_inicio_historial
        else None
    )

    revision = sesion.scalar(
        sa.select(Incidencia)
        .where(Incidencia.id_unidad == unidad.id, Incidencia.tipo == "REVISION_PLAGAS")
        .order_by(Incidencia.creada_en.desc())
        .limit(1)
    )

    revision_plagas = None
    if revision and revision.estado == "ABIERTA":
        ultima = sesion.scalar(sa.select(RevisionIncidencia).where(
            RevisionIncidencia.id_incidencia == revision.id).order_by(
            RevisionIncidencia.fecha.desc(), RevisionIncidencia.id.desc()).limit(1))
        revision_plagas = ResultadoRevision(ultima.resultado) if ultima else ResultadoRevision.PENDIENTE

    instantanea = Instantanea(
        fecha_evaluacion=ahora,
        fase=Fase(entrada.fase) if entrada.fase else None,
        tipo_almacenamiento=(
            Modalidad(unidad.tipo_almacenamiento) if unidad.tipo_almacenamiento else None
        ),
        clima_calido=_tri(almacen.clima_calido),
        datos=Conjunto(datos),
        historial=historial,
        dias_almacenados=dias_almacenados,
        dias_previstos_restantes=entrada.dias_previstos_restantes,
        fecha_salida_prevista=entrada.fecha_salida_prevista,
        controles=controles,
        plan=plan,
        dictamen=dictamen,
        episodios=episodios,
        resultado_revision_plagas=(
            revision_plagas
        ),
        sensor_interno_hermetico=(
            datos["sensor_interno_hermetico"].booleano is V
            if "sensor_interno_hermetico" in datos
            else False
        ),
        temperatura_ambiente_maxima_intervalo=(
            datos["temperatura_ambiente_maxima_intervalo"].numero
            if "temperatura_ambiente_maxima_intervalo" in datos
            else None
        ),
    )
    return instantanea, aplicadas


TIPO_INCIDENCIA_POR_HALLAZGO = {
    "CUARENTENA_SOLICITADA": ("CUARENTENA", ("R19",)),
    "INFESTACION_SOSPECHADA": ("REVISION_PLAGAS", ("R15",)),
    "PUNTO_CALIENTE_SOSPECHADO": ("REVISION_TERMICA", ("R09",)),
}


def sincronizar_incidencias(
    sesion: Session, id_unidad: uuid.UUID, resultado: motor.Resultado, id_evaluacion: uuid.UUID | None
) -> list[Incidencia]:
    """Abre los episodios que el motor solicita. Cerrarlos exige resolución registrada."""
    hallazgos = {motivo.id.split(":", 1)[1] for motivo in resultado.motivos}
    abiertas = {
        fila.tipo: fila
        for fila in sesion.scalars(
            sa.select(Incidencia).where(
                Incidencia.id_unidad == id_unidad, Incidencia.estado == "ABIERTA"
            )
        )
    }
    creadas: list[Incidencia] = []
    for hallazgo, (tipo, reglas) in TIPO_INCIDENCIA_POR_HALLAZGO.items():
        if hallazgo not in hallazgos or tipo in abiertas:
            continue
        incidencia = Incidencia(
            id_unidad=id_unidad,
            tipo=tipo,
            estado="ABIERTA",
            causas=list(reglas),
            id_evaluacion_origen=id_evaluacion,
        )
        sesion.add(incidencia)
        creadas.append(incidencia)
    return creadas


def persistir(
    sesion: Session,
    *,
    unidad: Unidad,
    almacen: Almacen,
    instantanea: Instantanea,
    entrada: api.EvaluacionEntrada,
    resultado: motor.Resultado,
    aplicadas: list[ObservacionBD],
    id_responsable: uuid.UUID,
    version: VersionConocimiento,
) -> EvaluacionBD:
    calculos = resultado.calculos
    efectiva = entrada.model_dump(mode="json")
    efectiva["_instantanea"] = jsonable_encoder(instantanea, custom_encoder={Decimal: str})
    # Base de hechos iniciales en forma reproducible y huella de la base usada:
    # permiten explicar y volver a evaluar esta decisión con la misma versión.
    efectiva["_hechos_iniciales"] = serializacion.a_json(instantanea)
    efectiva["_hash_base"] = resultado.hash_base
    efectiva["_observaciones_aplicadas"] = [
        obs.a_validada(fila).model_copy(update={"procedencia":
            "ACTUAL" if sa.inspect(fila).transient else "HISTORICA"}).model_dump(mode="json")
        for fila in aplicadas
    ]
    for aplicada in efectiva["_observaciones_aplicadas"]:
        dato = instantanea.datos[aplicada["entrada"]["campo"]]
        aplicada["aplicabilidad"] = "NO_APLICA" if dato.no_aplica else "APLICA"
        aplicada["estado_dato"] = None if dato.no_aplica else dato.estado.value
        if dato.estado.value == "INVALIDO" and aplicada["entrada"]["captura"] == "NO_APLICA":
            aplicada["incidencias_validacion"] = ["El contexto no justifica NO_APLICA"]
    evaluacion = EvaluacionBD(
        id_unidad=unidad.id,
        id_lote=unidad.id_lote,
        id_recipiente=unidad.id_recipiente,
        id_almacen=unidad.id_almacen,
        fecha_evaluacion=instantanea.fecha_evaluacion,
        fase=entrada.fase,
        decision_final=resultado.decision_final,
        rama_r30=resultado.rama_r30,
        entrada_efectiva=efectiva,
        revision_unidad_usada=unidad.revision,
        revision_almacen_usada=almacen.revision,
        reglas_activadas=list(resultado.reglas_activadas),
        vida_consumida=calculos.vida_consumida,
        vida_minima_documentada=calculos.vida_minima_documentada,
        vida_proyectada=calculos.vida_proyectada,
        tiempo_referencia_actual=calculos.tiempo_referencia_actual,
        celda_tabla_id=calculos.celda.id_tabla if calculos.celda else None,
        celda_humedad_fila=calculos.celda.humedad_fila if calculos.celda else None,
        celda_temperatura_columna_f=(
            calculos.celda.temperatura_columna_f if calculos.celda else None
        ),
        celda_dias_referencia=calculos.celda.dias_referencia if calculos.celda else None,
        fecha_proximo_control=resultado.fecha_proximo_control,
        fecha_vencimiento_autorizacion=resultado.fecha_vencimiento_autorizacion,
        version_base=resultado.version_base,
        version_parametros=resultado.version_parametros,
        version_motor=resultado.version_motor,
        id_version_conocimiento=version.id,
        id_responsable=id_responsable,
    )
    sesion.add(evaluacion)
    sesion.flush()

    for orden, motivo in enumerate(resultado.motivos, start=1):
        fila = MotivoBD(
            id_evaluacion=evaluacion.id,
            orden=orden,
            codigo=motivo.id,
            regla=motivo.regla,
            mensaje=motivo.mensaje,
            fundamento=motivo.fundamento,
        )
        sesion.add(fila)
        sesion.flush()
        for indice, prueba in enumerate(motivo.evidencias, start=1):
            evidencia = MotivoEvidencia(
                id_motivo=fila.id,
                orden=indice,
                campo=prueba.campo,
                unidad_dato=prueba.unidad,
                fecha_observacion=prueba.fecha_observacion,
                operador=prueba.operador,
            )
            _asignar_valor(evidencia, "valor", prueba.valor_observado)
            _asignar_valor(evidencia, "umbral", prueba.umbral)
            sesion.add(evidencia)
        for id_fuente, localizador in motivo.fuentes:
            sesion.add(
                MotivoFuente(id_motivo=fila.id, id_fuente=id_fuente, localizador=localizador)
            )

    for orden, accion in enumerate(resultado.acciones_requeridas, start=1):
        sesion.add(
            AccionRequerida(
                id_evaluacion=evaluacion.id,
                orden=orden,
                codigo=accion.codigo,
                descripcion=accion.descripcion,
                responsable_requerido=accion.responsable_requerido,
            )
        )
    for orden, pendiente in enumerate(resultado.datos_pendientes, start=1):
        sesion.add(
            DatoPendiente(
                id_evaluacion=evaluacion.id,
                orden=orden,
                campo=pendiente.campo,
                motivo=pendiente.motivo,
                paso=pendiente.paso,
            )
        )
    for orden, estimacion in enumerate(resultado.estimaciones, start=1):
        sesion.add(
            EstimacionBD(
                id_evaluacion=evaluacion.id,
                orden=orden,
                tipo=estimacion.tipo,
                descripcion=estimacion.descripcion,
                campos=list(estimacion.campos),
                id_tabla=estimacion.id_tabla,
            )
        )
    for orden, fila_obs in enumerate(aplicadas, start=1):
        if sa.inspect(fila_obs).transient:
            fila_obs.id_evaluacion_origen = evaluacion.id
            sesion.add(fila_obs)
            sesion.flush()
        sesion.add(
            ObservacionAplicada(
                id_evaluacion=evaluacion.id, id_observacion=fila_obs.id, orden=orden
            )
        )

    unidad.id_evaluacion_actual = evaluacion.id
    unidad.actualizado_en = datetime.now(UTC)
    return evaluacion


def _asignar_valor(destino: MotivoEvidencia, prefijo: str, valor: object) -> None:
    if valor is None:
        return
    if isinstance(valor, bool):
        setattr(destino, f"{prefijo}_booleano", valor)
    elif isinstance(valor, (int, float, Decimal)):
        setattr(destino, f"{prefijo}_numero", Decimal(str(valor)))
    else:
        setattr(destino, f"{prefijo}_texto", str(valor))
