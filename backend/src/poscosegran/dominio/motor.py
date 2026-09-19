"""Ciclo del motor y resolución R30, sección 8.

Encadenamiento hacia adelante determinista: validar, construir comprobaciones,
ejecutar R01–R26 hasta punto fijo, calcular tiempo y R28–R29, calcular control y
R27, consolidar solicitudes y resolver R30 una sola vez.

Los hechos derivados pertenecen a esta evaluación y no se copian a la siguiente.
Los episodios abiertos sí persisten: son registros de seguimiento, no inferencia.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal

from . import comprobaciones as comp
from . import resolucion as res
from . import tiempo as tmp
from .catalogo import fuentes, fundamento
from .hechos import (
    Accion,
    Estimacion,
    Fase,
    Instantanea,
    Motivo,
    Pendiente,
    Solicitud,
)
from .parametros import VERSION_MOTOR, VERSION_PARAMETROS
from .reglas import Contexto, Memoria, ejecutar_encadenamiento
from .valores import D, F, NA, Tri, V, o, y

DECISIONES_AUTORIZADAS = frozenset({"AUTORIZAR_ALMACENAMIENTO", "AUTORIZAR_CON_MONITOREO"})


@dataclass(frozen=True, slots=True)
class Resultado:
    decision_final: str
    rama_r30: str
    motivos: tuple[Motivo, ...]
    acciones_requeridas: tuple[Accion, ...]
    datos_pendientes: tuple[Pendiente, ...]
    estimaciones: tuple[Estimacion, ...]
    reglas_activadas: tuple[str, ...]
    calculos: tmp.CalculosTiempo
    fecha_proximo_control: datetime | None
    fecha_vencimiento_autorizacion: datetime | None
    solicitudes: dict[str, tuple[str, ...]]
    riesgo_activo: Tri
    version_base: str
    version_parametros: str = VERSION_PARAMETROS
    version_motor: str = VERSION_MOTOR


def _inconsistencias(inst: Instantanea) -> tuple[str, ...]:
    """Sección 2.3. Se conserva el indicio adverso y se impide declarar protección."""
    marcas: list[str] = list(inst.datos_inconsistentes)
    if inst.datos.booleano("sello_integro") is V and o(
        inst.datos.booleano("perforacion_barrera"),
        inst.datos.booleano("bolsa_abierta_sin_resellar"),
    ) is V:
        marcas.append("hermeticidad")
    if inst.datos.booleano("insectos_vivos") is V and (
        inst.resultado_revision_plagas is not None
        and inst.resultado_revision_plagas.value == "DESCARTADA"
    ):
        marcas.append("revision_plagas_contradictoria")
    defectuosos = inst.datos["granos_defectuosos"].numero
    enfermos = inst.datos["granos_enfermos"].numero
    if defectuosos is not None and enfermos is not None and enfermos > defectuosos:
        marcas.append("granos_enfermos_supera_defectuosos")
    return tuple(dict.fromkeys(marcas))


def _lecturas_comparables(inst: Instantanea) -> tuple[Tri, Decimal | None]:
    actual, previa = inst.datos["temperatura_grano"], inst.datos["temperatura_grano_previa"]
    if not previa.utilizable:
        return NA, None
    punto = inst.datos["punto_medicion"].texto
    punto_previo = inst.datos["punto_medicion_previo"].texto
    metodo = inst.datos["metodo_termico"].texto
    metodo_previo = inst.datos["metodo_termico_previo"].texto
    if None in (punto, punto_previo, metodo, metodo_previo):
        return D, None
    if punto != punto_previo or metodo != metodo_previo:
        return F, None
    if actual.fecha_observacion is None or previa.fecha_observacion is None:
        return D, None

    horas = Decimal(
        str((actual.fecha_observacion - previa.fecha_observacion).total_seconds() / 3600)
    )
    if horas <= 0 or horas > inst.parametros.intervalo_termico_max_horas:
        return F, horas
    return V, horas


def _datos_aireacion(inst: Instantanea, medicion: Tri) -> Tri:
    if not inst.es_no_hermetico:
        return NA
    campos = (
        "temperatura_grano",
        "hr_aire_exterior",
        "temperatura_aire_exterior",
        "lluvia_o_niebla",
        "humedad_equilibrio_maiz",
        "tabla_equilibrio_id",
    )
    return y(medicion, inst.datos.presentes(campos))


def _pendientes(
    inst: Instantanea,
    chequeos: res.Comprobaciones,
    calculos: tmp.CalculosTiempo,
    plazo: Tri,
) -> list[Pendiente]:
    """Datos exigibles desconocidos. Un dato ausente no es un incumplimiento."""
    pendientes: list[Pendiente] = []
    grupos: tuple[tuple[Tri, tuple[str, ...], str], ...] = (
        (chequeos.medicion_confirmada, comp.CAMPOS_MEDICION, "confirmar la medición de humedad"),
        (chequeos.recipiente_apto, comp.CAMPOS_RECIPIENTE, "comprobar el recipiente"),
        (chequeos.estiba_apta, comp.CAMPOS_ESTIBA, "comprobar la estiba"),
        (chequeos.calidad_aire_adecuada, comp.CAMPOS_CALIDAD_AIRE, "comprobar la calidad del aire"),
        (chequeos.calidad_fisica_conforme, comp.CAMPOS_CALIDAD_FISICA, "comprobar la calidad física"),
        (chequeos.sin_evidencia_de_plagas, comp.CAMPOS_PLAGAS + comp.INDICIOS_R15, "descartar plagas"),
        (chequeos.sin_evidencia_de_deterioro, comp.CAMPOS_DETERIORO, "descartar deterioro"),
        (chequeos.almacen_higienico, ("fecha_limpieza_general", "limpieza_diaria",
                                      "limpieza_tras_operaciones", "limpieza_previa_nuevo_lote"),
         "comprobar la higiene del almacén"),
        (chequeos.ambiente_base_apto, ("temperatura_almacen", "hr_almacen"),
         "comprobar el ambiente del almacén"),
        (chequeos.aw_sin_alerta, ("aw_medida", "actividad_agua"), "resolver la actividad de agua"),
        (chequeos.temperatura_bajo_alerta, ("temperatura_grano",),
         "comprobar la temperatura del grano"),
    )
    for estado, campos, motivo in grupos:
        if estado is not D:
            continue
        for campo in inst.datos.desconocidos(campos):
            pendientes.append(Pendiente(campo, f"Falta para {motivo}.", res.paso_de(campo)))

    if inst.es_hermetico:
        for campo in inst.datos.desconocidos(comp.CAMPOS_HERMETICIDAD):
            pendientes.append(
                Pendiente(campo, "Falta para comprobar la barrera hermética.", res.paso_de(campo))
            )

    if calculos.vida_consumida is None:
        for motivo in calculos.motivos_no_disponible:
            pendientes.append(Pendiente("vida_consumida", motivo, 5))
    if calculos.tiempo_referencia_actual is None:
        pendientes.append(
            Pendiente(
                "tiempo_referencia_actual",
                "No hay celda de referencia aplicable: el cálculo no está disponible.",
                5,
            )
        )
    if inst.dias_previstos_restantes is None:
        pendientes.append(Pendiente("dias_previstos_restantes", "Falta el plazo previsto.", 5))
    if inst.fecha_salida_prevista is None and inst.dias_previstos_restantes is not None:
        pendientes.append(Pendiente("fecha_salida_prevista", "Falta la fecha de salida.", 5))
    if inst.tipo_almacenamiento is None:
        pendientes.append(Pendiente("tipo_almacenamiento", "Falta la modalidad.", 1))
    if inst.fase is None:
        pendientes.append(Pendiente("fase", "Falta la fase de la evaluación.", 1))
    if inst.clima_calido is D:
        pendientes.append(
            Pendiente("clima_calido", "Falta la clasificación territorial de clima.", 1)
        )

    unicos: dict[tuple[str, str], Pendiente] = {}
    for pendiente in pendientes:
        unicos.setdefault((pendiente.campo, pendiente.motivo), pendiente)
    return list(unicos.values())


def _motivo_simple(regla: str, codigo: str, mensaje: str) -> Motivo:
    return Motivo(
        id=f"{regla}:{codigo}",
        regla=regla,
        mensaje=mensaje,
        fuentes=fuentes(regla),
        fundamento=fundamento(regla),
    )


def evaluar(inst: Instantanea) -> Resultado:
    mem = Memoria()

    # 2. Validación y comprobaciones auxiliares
    inconsistencias = _inconsistencias(inst)
    inst = replace(inst, datos_inconsistentes=inconsistencias)

    medicion = comp.medicion_confirmada(inst)
    integridad = comp.integridad_hermetica_verificada(inst)
    temperatura, estimacion_hermetica = tmp.temperatura_aplicable(inst, integridad)
    comparables, horas = _lecturas_comparables(inst)
    ctx = Contexto(
        medicion_confirmada=medicion,
        integridad_hermetica=integridad,
        temperatura_grano=temperatura,
        lecturas_termicas_comparables=comparables,
        horas_entre_lecturas=horas,
        datos_aireacion_completos=_datos_aireacion(inst, medicion),
    )

    if inconsistencias:
        mem.registrar(
            "VALIDACION",
            "DATOS_INCONSISTENTES",
            "Hay registros contradictorios: " + ", ".join(inconsistencias) + ". Se conserva "
            "el indicio adverso y se solicita revisión.",
            solicitudes=(Solicitud.CORRECCION,),
        )
    invalidos = inst.datos.invalidos()
    if invalidos:
        mem.registrar(
            "VALIDACION",
            "DATOS_INVALIDOS",
            "Datos inválidos o vencidos que no participan en comparaciones: "
            + ", ".join(invalidos),
            solicitudes=(Solicitud.CORRECCION,),
        )

    # 3. Encadenamiento R01–R26 hasta punto fijo
    ejecutar_encadenamiento(inst, mem, ctx)

    # 4. Tiempo, R28–R29 y riesgo
    calculos = tmp.calcular(inst, temperatura)
    res.aplicar_r28_r29(inst, mem, calculos)
    riesgo = res.calcular_riesgo(inst, mem)

    # 5. Control y R27
    chequeos = res.construir_comprobaciones(inst, ctx, riesgo, mem)
    pendientes_control = res.aplicar_r27(inst, mem, chequeos)

    # 6. Consolidación de la sección 7.1
    condicional = mem.tiene("HUMEDAD_CONDICIONAL")
    plazo = tmp.plazo_compatible(inst, calculos, condicional)
    admisible, faltas_condicional = res.rama_condicional_admisible(inst, mem, chequeos, plazo)

    if plazo is F:
        mem.registrar(
            "SECCION_6",
            "PLAZO_INCOMPATIBLE",
            "El plazo previsto no es compatible con el tiempo de referencia restante. "
            "Reducir el plazo o reevaluar; no significa que la vida actual esté agotada.",
            solicitudes=(Solicitud.CORRECCION,),
        )
    if estimacion_hermetica is not None:
        mem.registrar(
            "SECCION_6",
            "ESTIMACION_HERMETICA_APLICADA",
            "Temperatura estimada sin apertura del recipiente: exige monitoreo y no es una "
            "medición interna.",
            solicitudes=(Solicitud.MONITOREO,),
        )
    if condicional and admisible is V:
        mem.solicitar(Solicitud.MONITOREO, "R02")
    if condicional and admisible is F:
        mem.registrar(
            "R30.4",
            "BANDA_CONDICIONAL_NO_ADMISIBLE",
            "La banda condicional no es admisible: " + "; ".join(faltas_condicional) + ".",
            solicitudes=(Solicitud.CORRECCION,),
        )

    if inst.cuarentenas_abiertas:
        mem.solicitar(Solicitud.CUARENTENA, "EPISODIO_ABIERTO")
    for episodio in inst.revisiones_abiertas:
        mem.solicitar(Solicitud.CORRECCION, f"INCIDENCIA_{episodio.tipo}")

    # Un monitoreo solicitado sin plan registrado es una corrección, no una autorización.
    if mem.pedida(Solicitud.MONITOREO) and not (inst.plan.registrado and inst.plan.vigente):
        mem.registrar(
            "SECCION_5",
            "PLAN_DE_MONITOREO_AUSENTE",
            "Se requiere monitoreo reforzado y no hay un plan registrado y vigente.",
            solicitudes=(Solicitud.CORRECCION,),
        )

    if mem.pedida(Solicitud.SUSPENSION) and inst.fase is None:
        mem.registrar(
            "R30.4",
            "FASE_DESCONOCIDA_CON_SUSPENSION",
            "Almacenamiento normal no permitido hasta definir la fase y la actuación.",
            solicitudes=(Solicitud.CORRECCION,),
        )

    pendientes = _pendientes(inst, chequeos, calculos, plazo) + pendientes_control
    if plazo is D:
        pendientes.append(
            Pendiente("plazo_compatible", "No hay datos suficientes para comprobar el plazo.", 5)
        )
    requisitos_completos = V if not pendientes else F

    # 7. R30, una sola vez
    decision, rama = _resolver(
        inst, mem, chequeos, plazo, admisible, requisitos_completos, bool(pendientes)
    )

    monitoreo = mem.pedida(Solicitud.MONITOREO)
    fecha_control = res.proximo_control(inst, riesgo, monitoreo)
    if decision == "CUARENTENA":
        fecha_control = None
    vencimiento = (
        tmp.vencimiento_autorizacion(inst, calculos, fecha_control)
        if decision in DECISIONES_AUTORIZADAS
        else None
    )

    estimaciones = tuple(
        dict.fromkeys(
            ([estimacion_hermetica] if estimacion_hermetica else []) + list(calculos.estimaciones)
        )
    )

    return Resultado(
        decision_final=decision,
        rama_r30=rama,
        motivos=tuple(mem.motivos),
        acciones_requeridas=tuple(mem.acciones),
        datos_pendientes=tuple(pendientes),
        estimaciones=estimaciones,
        reglas_activadas=tuple(mem.reglas_activadas),
        calculos=calculos,
        fecha_proximo_control=fecha_control,
        fecha_vencimiento_autorizacion=vencimiento,
        solicitudes={
            solicitud.value: tuple(causas) for solicitud, causas in mem.solicitudes.items()
        },
        riesgo_activo=riesgo,
        version_base=inst.version_base,
    )


def _resolver(
    inst: Instantanea,
    mem: Memoria,
    chequeos: res.Comprobaciones,
    plazo: Tri,
    admisible: Tri,
    requisitos_completos: Tri,
    hay_pendientes: bool,
) -> tuple[str, str]:
    """Tabla de decisión ordenada de la sección 7.3: la primera fila aplicable gana."""
    if mem.pedida(Solicitud.CUARENTENA):
        return "CUARENTENA", "R30.1"
    if mem.pedida(Solicitud.SUSPENSION) and inst.fase is Fase.INGRESO:
        return "BLOQUEAR_INGRESO", "R30.2"
    if mem.pedida(Solicitud.SUSPENSION) and inst.fase is Fase.SEGUIMIENTO:
        return "RETIRAR_LOTE", "R30.3"
    if mem.pedida(Solicitud.CORRECCION):
        return "CORREGIR_Y_REEVALUAR", "R30.4"
    if hay_pendientes or requisitos_completos is not V:
        return "SIN_CONCLUSION_AUTOMATICA", "R30.5"

    comunes_y_plazo = chequeos.condiciones_comunes_aptas is V and plazo is V
    if comunes_y_plazo and admisible is V:
        return "AUTORIZAR_CON_MONITOREO", "R30.6"

    proteccion = (
        V if inst.es_no_hermetico else (V if mem.tiene("PROTECCION_HERMETICA_ACTIVA") else D)
    )
    base = comunes_y_plazo and mem.tiene("HUMEDAD_APTA_BASE") and proteccion is V
    if base and mem.pedida(Solicitud.MONITOREO) and inst.plan.registrado and inst.plan.vigente:
        return "AUTORIZAR_CON_MONITOREO", "R30.7"
    if base and not mem.pedida(Solicitud.MONITOREO):
        return "AUTORIZAR_ALMACENAMIENTO", "R30.8"

    mem.motivos.append(
        _motivo_simple(
            "R30.9",
            "SIN_CONCLUSION",
            "No hay una fila aplicable: se informa la condición que impide resolver y se "
            "deriva a revisión.",
        )
    )
    return "SIN_CONCLUSION_AUTOMATICA", "R30.9"
