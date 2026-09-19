"""Comprobaciones favorables explícitas, sección 3.2.

Ninguna se deduce de la ausencia de alertas: si falta un requisito devuelven
DESCONOCIDO, y solo devuelven FALSO cuando un requisito conocido falla. Esa
distinción es lo que impide que la falta de datos se lea como seguridad.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .hechos import Fase, Instantanea, ResultadoRevision
from .valores import D, F, NA, Tri, V, mayor_igual, menor, menor_igual, no, o, y

CAMPOS_MEDICION = (
    "humedad_grano",
    "metodo_humedad",
    "equipo_humedad_verificado",
    "muestra_representativa",
    "procedimiento_medicion_cumplido",
)
CAMPOS_RECIPIENTE = (
    "recipiente_limpio",
    "recipiente_seco",
    "material_grado_alimentario",
    "recipiente_resistente",
    "cierre_seguro",
)
CAMPOS_ESTIBA = ("distancia_piso", "distancia_pared", "distancia_techo")
CAMPOS_CALIDAD_AIRE = ("polvo_humo_gases_vapores", "quimicos_combustibles_en_almacen")
CAMPOS_CALIDAD_FISICA = (
    "suciedad_origen_animal",
    "heces_visibles",
    "granos_defectuosos",
    "granos_enfermos",
    "granos_quebrados",
    "materia_organica_extrana",
    "materia_inorganica_extrana",
)
CAMPOS_PLAGAS = (
    "insectos_vivos",
    "heces_roedores_aves_entorno",
    "huellas",
    "bolsa_roida",
    "grano_derramado_por_plaga",
)
INDICIOS_R15 = ("granos_perforados", "polvillo_inusual", "exuvias_larvas", "ruido_alimentacion")
CAMPOS_DETERIORO = ("moho_visible", "olor_anormal", "condensacion_interna", "germinacion")
CAMPOS_HERMETICIDAD = (
    "sello_integro",
    "cierre_seguro",
    "perforacion_barrera",
    "bolsa_abierta_sin_resellar",
)


def sumar_mes_calendario(fecha: datetime) -> datetime:
    """Conserva el día del mes; si no existe en el mes siguiente, usa el último día."""
    if fecha.month == 12:
        anio, mes = fecha.year + 1, 1
    else:
        anio, mes = fecha.year, fecha.month + 1
    dia = fecha.day
    while dia > 0:
        try:
            return fecha.replace(year=anio, month=mes, day=dia)
        except ValueError:
            dia -= 1
    raise ValueError("fecha no representable")  # pragma: no cover


def medicion_confirmada(inst: Instantanea) -> Tri:
    """Método válido, equipo verificado, muestra representativa y procedimiento cumplido."""
    metodo = inst.datos["metodo_humedad"].texto
    if metodo is None:
        return D
    if metodo == "ESTIMACION_INDIRECTA":
        return F
    if metodo not in {"INSTRUMENTAL", "LABORATORIO"}:
        return F

    comprobaciones = [
        inst.datos.booleano("equipo_humedad_verificado"),
        inst.datos.booleano("muestra_representativa"),
        inst.datos.booleano("procedimiento_medicion_cumplido"),
    ]
    if metodo == "INSTRUMENTAL":
        comprobaciones.append(
            mayor_igual(inst.datos["temperatura_muestra"], inst.parametros.muestra_fria_umbral)
        )
    return y(*comprobaciones)


def integridad_hermetica_verificada(inst: Instantanea) -> Tri:
    if not inst.es_hermetico:
        return NA
    if "hermeticidad" in inst.datos_inconsistentes:
        return F
    return y(
        inst.datos.booleano("sello_integro"),
        inst.datos.booleano("cierre_seguro"),
        no(inst.datos.booleano("perforacion_barrera")),
        no(inst.datos.booleano("bolsa_abierta_sin_resellar")),
    )


def recipiente_apto(inst: Instantanea) -> Tri:
    return y(*(inst.datos.booleano(campo) for campo in CAMPOS_RECIPIENTE))


def estiba_apta(inst: Instantanea) -> Tri:
    p = inst.parametros
    return y(
        mayor_igual(inst.datos["distancia_piso"], p.estiba_piso_min),
        mayor_igual(inst.datos["distancia_pared"], p.estiba_pared_min),
        mayor_igual(inst.datos["distancia_techo"], p.estiba_techo_min),
    )


def limpieza_general_vigente(inst: Instantanea) -> Tri:
    """Vence al cumplirse un mes calendario desde la última limpieza general.

    Sin fecha registrada devuelve DESCONOCIDO, no vencido: una ausencia genera
    dato pendiente, no un atraso con fecha inventada.
    """
    referencia = inst.datos["fecha_limpieza_general"].fecha
    if referencia is None:
        return D
    return V if inst.fecha_evaluacion <= sumar_mes_calendario(referencia) else F


def almacen_higienico(inst: Instantanea) -> Tri:
    comprobaciones = [
        limpieza_general_vigente(inst),
        inst.datos.booleano("limpieza_diaria"),
        o(inst.datos.booleano("limpieza_tras_operaciones"),
          V if inst.datos["limpieza_tras_operaciones"].no_aplica else F),
    ]
    if inst.fase is Fase.INGRESO:
        comprobaciones.append(inst.datos.booleano("limpieza_previa_nuevo_lote"))
    return y(*comprobaciones)


def calidad_aire_adecuada(inst: Instantanea) -> Tri:
    return y(*(no(inst.datos.booleano(campo)) for campo in CAMPOS_CALIDAD_AIRE))


def calidad_fisica_conforme(inst: Instantanea) -> Tri:
    p = inst.parametros
    return y(
        menor_igual(inst.datos["suciedad_origen_animal"], p.suciedad_animal_max),
        no(inst.datos.booleano("heces_visibles")),
        menor_igual(inst.datos["granos_defectuosos"], p.defectuosos_max),
        menor_igual(inst.datos["granos_enfermos"], p.enfermos_max),
        menor_igual(inst.datos["granos_quebrados"], p.quebrados_max),
        menor_igual(inst.datos["materia_organica_extrana"], p.materia_organica_max),
        menor_igual(inst.datos["materia_inorganica_extrana"], p.materia_inorganica_max),
    )


def indicio_r15_residual(inst: Instantanea) -> Tri:
    """Indicios de R15 que no estén explicados por una revisión DESCARTADA válida."""
    presentes = o(*(inst.datos.booleano(campo) for campo in INDICIOS_R15))
    if presentes is not V:
        return presentes
    descartado = (
        inst.resultado_revision_plagas is ResultadoRevision.DESCARTADA
        and inst.revision_plagas_cubre_indicios_actuales
    )
    return F if descartado else V


def sin_evidencia_de_plagas(inst: Instantanea) -> Tri:
    episodios = tuple(e for e in inst.revisiones_abiertas if e.tipo == "REVISION_PLAGAS")
    return y(
        *(no(inst.datos.booleano(campo)) for campo in CAMPOS_PLAGAS),
        no(indicio_r15_residual(inst)),
        F if episodios else V,
    )


def sin_evidencia_de_deterioro(inst: Instantanea) -> Tri:
    abiertos = any(e.tipo == "CUARENTENA" for e in inst.cuarentenas_abiertas)
    return y(
        *(no(inst.datos.booleano(campo)) for campo in CAMPOS_DETERIORO),
        F if abiertos else V,
    )


def aw_sin_alerta(inst: Instantanea) -> Tri:
    """No medir aw no prueba ausencia de hongos, pero permite el cribado por humedad."""
    medida = inst.datos.booleano("aw_medida")
    if medida is F:
        return V
    if medida is D:
        return D
    return menor(inst.datos["actividad_agua"], inst.parametros.aw_alerta)


@dataclass(frozen=True, slots=True)
class PlazoControl:
    etiqueta: str
    fecha_ultima: datetime | None
    dias_maximos: int | None
    vencido: Tri


def _vencimiento(fecha: datetime | None, dias: int, ahora: datetime) -> Tri:
    if fecha is None:
        return D
    return V if ahora > fecha + timedelta(days=dias) else F


def plazos_control(inst: Instantanea, riesgo: Tri) -> tuple[PlazoControl, ...]:
    """Sección 5.2. Un registro inexistente no se trata como fecha conocida."""
    p = inst.parametros
    ahora = inst.fecha_evaluacion
    con_riesgo = riesgo in (V, D)
    plazos: list[PlazoControl] = []

    if inst.fase is Fase.INGRESO:
        plazos.append(
            PlazoControl("ingreso", None, None, no(inst.controles.ingreso_inspeccionado))
        )
    elif inst.es_no_hermetico:
        dias = p.control_con_riesgo_dias if con_riesgo else p.control_no_hermetico_normal_dias
        plazos.append(
            PlazoControl(
                "inspeccion_grano",
                inst.controles.fecha_inspeccion_grano,
                dias,
                _vencimiento(inst.controles.fecha_inspeccion_grano, dias, ahora),
            )
        )
    elif inst.es_hermetico:
        dias = (
            p.control_con_riesgo_dias if con_riesgo else p.control_exterior_hermetico_normal_dias
        )
        plazos.append(
            PlazoControl(
                "inspeccion_exterior",
                inst.controles.fecha_inspeccion_exterior,
                dias,
                _vencimiento(inst.controles.fecha_inspeccion_exterior, dias, ahora),
            )
        )

    dias_almacen = p.control_con_riesgo_dias if con_riesgo else p.control_almacen_sin_riesgo_dias
    plazos.append(
        PlazoControl(
            "control_almacen",
            inst.controles.fecha_control_almacen,
            dias_almacen,
            _vencimiento(inst.controles.fecha_control_almacen, dias_almacen, ahora),
        )
    )
    return tuple(plazos)


def control_vigente(inst: Instantanea, plazos: tuple[PlazoControl, ...]) -> Tri:
    if inst.controles.hay_evento_que_invalida_control is V:
        return F
    return y(*(no(plazo.vencido) for plazo in plazos))
