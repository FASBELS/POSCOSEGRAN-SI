"""Riesgo, control, R27–R29 y la resolución R30 de la sección 7.

R30 elige la primera fila aplicable de una tabla ordenada. Las filas inferiores
no emiten una segunda decisión, pero todos los motivos se conservan: la
prioridad determina la actuación principal, no borra las causas.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from . import comprobaciones as comp
from .hechos import Accion, Fase, Instantanea, Pendiente, Solicitud
from .reglas import Contexto, Memoria
from .tiempo import CalculosTiempo
from .valores import D, F, NA, Tri, V, menor, y

# Hallazgos adversos que hacen riesgo_activo VERDADERO (sección 5.1).
# R27 queda fuera a propósito: el atraso de inspección no debe acortar su propio plazo.
HALLAZGOS_DE_RIESGO = frozenset(
    {
        "HUMEDAD_NO_APTA",
        "HUMEDAD_CONDICIONAL",
        "RIESGO_FUNGICO_HIDRICO",
        "MEDICION_HUMEDAD_NO_CONFIRMADA",
        "RIESGO_REHUMEDECIMIENTO",
        "RIESGO_TERMICO",
        "PUNTO_CALIENTE_SOSPECHADO",
        "HERMETICIDAD_COMPROMETIDA",
        "INFESTACION_CONFIRMADA",
        "INFESTACION_SOSPECHADA",
        "AMBIENTE_FAVORABLE_A_INSECTOS",
        "CONTAMINACION_BIOLOGICA_SOSPECHADA",
        "DETERIORO_SOSPECHADO",
        "CONTAMINACION_ANIMAL_OBSERVADA",
        "LOTE_NO_CONFORME_POR_DEFECTOS",
        "LOTE_REQUIERE_LIMPIEZA_Y_CLASIFICACION",
        "RECIPIENTE_NO_APTO",
        "ESTIBA_NO_APTA",
        "ALMACEN_NO_HIGIENICO",
        "CALIDAD_AIRE_INADECUADA",
        "VIDA_ESTIMADA_PROXIMA_AL_LIMITE",
        "VIDA_O_PLAZO_AGOTADO",
    }
)

# Paso del formulario al que pertenece cada campo, para dirigir los datos pendientes.
PASO_POR_CAMPO: dict[str, int] = {
    "humedad_grano": 2, "metodo_humedad": 2, "temperatura_muestra": 2,
    "equipo_humedad_verificado": 2, "muestra_representativa": 2,
    "procedimiento_medicion_cumplido": 2, "aw_medida": 2, "actividad_agua": 2,
    "temperatura_grano": 2, "punto_medicion": 2, "metodo_termico": 2,
    "temperatura_almacen": 2, "hr_almacen": 2, "temperatura_aire_exterior": 2,
    "hr_aire_exterior": 2, "lluvia_o_niebla": 2,
    "insectos_vivos": 3, "granos_perforados": 3, "polvillo_inusual": 3, "exuvias_larvas": 3,
    "ruido_alimentacion": 3, "heces_roedores_aves_entorno": 3, "huellas": 3, "bolsa_roida": 3,
    "grano_derramado_por_plaga": 3, "moho_visible": 3, "olor_anormal": 3,
    "condensacion_interna": 3, "germinacion": 3, "suciedad_origen_animal": 3,
    "heces_visibles": 3, "granos_defectuosos": 3, "granos_enfermos": 3, "granos_quebrados": 3,
    "materia_organica_extrana": 3, "materia_inorganica_extrana": 3,
    "sello_integro": 4, "perforacion_barrera": 4, "bolsa_abierta_sin_resellar": 4,
    "cierre_seguro": 4, "recipiente_limpio": 4, "recipiente_seco": 4,
    "material_grado_alimentario": 4, "recipiente_resistente": 4, "distancia_piso": 4,
    "distancia_pared": 4, "distancia_techo": 4, "fecha_limpieza_general": 4,
    "limpieza_previa_nuevo_lote": 4, "limpieza_diaria": 4, "limpieza_tras_operaciones": 4,
    "polvo_humo_gases_vapores": 4, "quimicos_combustibles_en_almacen": 4,
    "fecha_inicio_historial": 5, "vida_previa_documentada": 5, "intervalos_historial": 5,
    "dias_previstos_restantes": 5, "fecha_salida_prevista": 5, "fecha_proximo_control": 5,
    "fecha_inspeccion_grano": 5, "fecha_inspeccion_exterior": 5, "fecha_control_almacen": 5,
    "tipo_almacenamiento": 1, "fase": 1, "clima_calido": 1,
}


def paso_de(campo: str) -> int:
    return PASO_POR_CAMPO.get(campo, 6)


@dataclass(frozen=True, slots=True)
class Comprobaciones:
    recipiente_apto: Tri
    estiba_apta: Tri
    almacen_higienico: Tri
    calidad_aire_adecuada: Tri
    calidad_fisica_conforme: Tri
    sin_evidencia_de_plagas: Tri
    sin_evidencia_de_deterioro: Tri
    aw_sin_alerta: Tri
    ambiente_base_apto: Tri
    control_vigente: Tri
    medicion_confirmada: Tri
    temperatura_bajo_alerta: Tri
    condiciones_comunes_aptas: Tri
    plazos: tuple[comp.PlazoControl, ...]


def campos_riesgo_aplicables(inst: Instantanea) -> tuple[str, ...]:
    """Campos que alimentan las reglas de riesgo, según la modalidad.

    No incluye las mediciones de aireación: son opcionales y su ausencia no debe
    volver desconocido el riesgo ni acortar los plazos de control.
    """
    campos: list[str] = [
        *comp.CAMPOS_MEDICION,
        "temperatura_grano",
        "temperatura_almacen",
        "aw_medida",
        *comp.CAMPOS_PLAGAS,
        *comp.INDICIOS_R15,
        *comp.CAMPOS_DETERIORO,
        *comp.CAMPOS_CALIDAD_FISICA,
        *comp.CAMPOS_RECIPIENTE,
        *comp.CAMPOS_ESTIBA,
        *comp.CAMPOS_CALIDAD_AIRE,
        "fecha_limpieza_general",
        "limpieza_diaria",
        "limpieza_tras_operaciones",
    ]
    if inst.fase is Fase.INGRESO:
        campos.append("limpieza_previa_nuevo_lote")
    if inst.es_no_hermetico:
        campos.append("hr_almacen")
    if inst.es_hermetico:
        campos.extend(comp.CAMPOS_HERMETICIDAD)
    if inst.datos.booleano("aw_medida") is V:
        campos.append("actividad_agua")
    return tuple(dict.fromkeys(campos))


def calcular_riesgo(inst: Instantanea, mem: Memoria) -> Tri:
    """VERDADERO con cualquier hallazgo adverso; DESCONOCIDO si faltan comprobaciones."""
    if mem.hallazgos & HALLAZGOS_DE_RIESGO:
        return V
    if inst.revisiones_abiertas or inst.cuarentenas_abiertas:
        return V
    if inst.datos.desconocidos(campos_riesgo_aplicables(inst)):
        return D
    return F


def construir_comprobaciones(
    inst: Instantanea, ctx: Contexto, riesgo: Tri, mem: Memoria
) -> Comprobaciones:
    plazos = comp.plazos_control(inst, riesgo)
    ambiente = V if mem.tiene("AMBIENTE_BASE_APTO") else (
        F if mem.tiene("RIESGO_REHUMEDECIMIENTO") or mem.tiene("RIESGO_TERMICO") else D
    )
    piezas = {
        "recipiente_apto": comp.recipiente_apto(inst),
        "estiba_apta": comp.estiba_apta(inst),
        "almacen_higienico": comp.almacen_higienico(inst),
        "calidad_aire_adecuada": comp.calidad_aire_adecuada(inst),
        "calidad_fisica_conforme": comp.calidad_fisica_conforme(inst),
        "sin_evidencia_de_plagas": comp.sin_evidencia_de_plagas(inst),
        "sin_evidencia_de_deterioro": comp.sin_evidencia_de_deterioro(inst),
        "aw_sin_alerta": comp.aw_sin_alerta(inst),
        "ambiente_base_apto": ambiente,
        "control_vigente": comp.control_vigente(inst, plazos),
        "medicion_confirmada": ctx.medicion_confirmada,
        "temperatura_bajo_alerta": menor(ctx.temperatura_grano, inst.parametros.temperatura_alerta),
    }
    contexto_valido = (
        V if inst.tipo_almacenamiento is not None else D
    )
    comunes = y(*piezas.values(), contexto_valido)
    return Comprobaciones(**piezas, condiciones_comunes_aptas=comunes, plazos=plazos)


def aplicar_r27(inst: Instantanea, mem: Memoria, chequeos: Comprobaciones) -> list[Pendiente]:
    """Un registro inexistente no genera atraso con fecha inventada: genera pendiente."""
    pendientes: list[Pendiente] = []
    vencidos = [plazo for plazo in chequeos.plazos if plazo.vencido is V]
    sin_registro = [plazo for plazo in chequeos.plazos if plazo.vencido is D]

    if vencidos:
        detalle = ", ".join(
            f"{plazo.etiqueta} (máximo {plazo.dias_maximos} días)" for plazo in vencidos
        )
        mem.registrar(
            "R27",
            "CONTROL_ATRASADO",
            f"Control fuera de plazo: {detalle}. Una inspección exterior no cuenta como "
            "muestreo interno.",
            solicitudes=(Solicitud.CORRECCION,),
            accion=Accion("INSPECCIONAR", "Completar la inspección requerida.", "PRODUCTOR"),
        )
    if inst.controles.hay_evento_que_invalida_control is V:
        mem.registrar(
            "R27",
            "CONTROL_INVALIDADO_POR_EVENTO",
            "Un evento posterior invalidó los controles: la lista favorable anterior ya no "
            "describe la situación.",
            solicitudes=(Solicitud.CORRECCION,),
        )
    for plazo in sin_registro:
        campo = f"fecha_{plazo.etiqueta}" if plazo.etiqueta != "ingreso" else "ingreso_inspeccionado"
        pendientes.append(
            Pendiente(campo, f"No hay registro del control {plazo.etiqueta}.", paso_de(campo))
        )
    return pendientes


def aplicar_r28_r29(inst: Instantanea, mem: Memoria, calculos: CalculosTiempo) -> None:
    p = inst.parametros
    vida = calculos.vida_consumida
    minima = calculos.vida_minima_documentada

    agotada = (
        (vida is not None and vida >= p.vida_limite)
        or (minima is not None and minima >= p.vida_limite)
        or (
            inst.clima_calido is V
            and inst.es_no_hermetico
            and inst.dias_almacenados is not None
            and inst.dias_almacenados >= p.limite_calido_no_hermetico_dias
        )
    )
    if agotada:
        mem.registrar(
            "R29",
            "VIDA_O_PLAZO_AGOTADO",
            "El tiempo de referencia del modelo está agotado o se superó el plazo máximo "
            "en clima cálido sin hermeticidad. Secar o enfriar no reinicia el acumulado.",
            solicitudes=(Solicitud.SUSPENSION,),
            accion=Accion(
                "EVALUAR_DISPOSICION",
                "Evaluar disposición técnica del lote; no se ordena consumo ni destrucción.",
                "TECNICO",
            ),
        )
        return

    if vida is not None and p.vida_alerta <= vida < p.vida_limite:
        mem.registrar(
            "R28",
            "VIDA_ESTIMADA_PROXIMA_AL_LIMITE",
            f"La fracción consumida del tiempo de referencia es {vida}, dentro del aviso "
            f"preventivo de {p.vida_alerta}.",
            solicitudes=(Solicitud.MONITOREO,),
        )


def rama_condicional_admisible(
    inst: Instantanea, mem: Memoria, chequeos: Comprobaciones, plazo: Tri
) -> tuple[Tri, list[str]]:
    """Sección 7.2. Las cuatro condiciones se exigen juntas."""
    if not mem.tiene("HUMEDAD_CONDICIONAL"):
        return NA, []

    faltas: list[str] = []
    if not inst.es_no_hermetico:
        faltas.append("la banda condicional solo se admite en almacenamiento no hermético")
    if inst.clima_calido is not F:
        faltas.append("se exige clima no cálido documentado")
    if inst.dias_previstos_restantes is None:
        faltas.append("falta el plazo restante previsto")
    elif inst.dias_previstos_restantes > inst.parametros.plazo_corto_max_dias:
        faltas.append(
            f"el plazo restante supera {inst.parametros.plazo_corto_max_dias} días"
        )

    if chequeos.condiciones_comunes_aptas is not V or plazo is not V:
        faltas.append("las condiciones comunes o el plazo no están comprobados")

    humedad = inst.datos["humedad_grano"].numero
    dias = inst.dias_previstos_restantes or 0
    if inst.dictamen is None or humedad is None or not inst.dictamen.cubre(
        humedad, dias, inst.fecha_evaluacion
    ):
        faltas.append("falta un dictamen técnico vigente para ese rango y plazo")

    if not inst.plan.registrado or not inst.plan.vigente:
        faltas.append("falta un plan de monitoreo registrado y vigente")
    elif inst.plan.intervalo_dias is None or inst.plan.intervalo_dias > 7:
        faltas.append("el plan debe fijar control como máximo cada 7 días")
    elif inst.plan.fecha_salida_prevista is None:
        faltas.append("el plan debe fijar fecha de salida")

    return (V if not faltas else F), faltas


def proximo_control(inst: Instantanea, riesgo: Tri, monitoreo: bool) -> datetime | None:
    p = inst.parametros
    if inst.es_hermetico:
        base = p.control_con_riesgo_dias if (riesgo in (V, D) or monitoreo) else (
            p.control_exterior_hermetico_normal_dias
        )
        ultima = inst.controles.fecha_inspeccion_exterior
    else:
        base = p.control_con_riesgo_dias if (riesgo in (V, D) or monitoreo) else (
            p.control_no_hermetico_normal_dias
        )
        ultima = inst.controles.fecha_inspeccion_grano
    if inst.plan.registrado and inst.plan.vigente and inst.plan.intervalo_dias:
        base = min(base, inst.plan.intervalo_dias)
    return (ultima or inst.fecha_evaluacion) + timedelta(days=base)
