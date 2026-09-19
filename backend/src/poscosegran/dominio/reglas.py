"""Reglas R01–R29 declarativas.

Cada regla recibe la instantánea y el contexto calculado, y añade hallazgos,
motivos y solicitudes. Nunca borra un hallazgo anterior: que varias causas
generen la misma solicitud no elimina ninguna causa.

No hay eval ni exec: cada antecedente es código Python explícito que se puede
leer junto a la fila correspondiente de la sección 4 de la base 2.0.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal

from . import catalogo
from .comprobaciones import (
    CAMPOS_DETERIORO,
    CAMPOS_RECIPIENTE,
    INDICIOS_R15,
    indicio_r15_residual,
    limpieza_general_vigente,
)
from .hechos import Accion, Fase, Instantanea, Motivo, ResultadoRevision, Solicitud
from .valores import (
    Dato,
    D,
    Evidencia,
    F,
    NA,
    Tri,
    V,
    comparar,
    entre,
    evidencia,
    mayor,
    mayor_igual,
    menor,
    menor_igual,
    no,
    o,
    y,
)


@dataclass
class Memoria:
    """Hechos derivados de una evaluación. No se copian a la siguiente."""

    hallazgos: set[str] = field(default_factory=set)
    motivos: list[Motivo] = field(default_factory=list)
    solicitudes: dict[Solicitud, list[str]] = field(default_factory=dict)
    reglas_activadas: list[str] = field(default_factory=list)
    acciones: list[Accion] = field(default_factory=list)
    no_aplica: set[str] = field(default_factory=set)

    def tiene(self, hallazgo: str) -> bool:
        return hallazgo in self.hallazgos

    def registrar(
        self,
        regla: str,
        hallazgo: str,
        mensaje: str,
        *,
        evidencias: tuple[Evidencia, ...] = (),
        solicitudes: tuple[Solicitud, ...] = (),
        accion: Accion | None = None,
    ) -> bool:
        """Añade un hallazgo. Devuelve True solo la primera vez (refracción)."""
        nuevo = hallazgo not in self.hallazgos
        if nuevo:
            self.hallazgos.add(hallazgo)
            self.motivos.append(
                Motivo(
                    id=f"{regla}:{hallazgo}",
                    regla=regla,
                    mensaje=mensaje,
                    evidencias=evidencias,
                    fuentes=catalogo.fuentes(regla),
                    fundamento=catalogo.fundamento(regla),
                )
            )
            if regla not in self.reglas_activadas:
                self.reglas_activadas.append(regla)
            if accion is not None and accion not in self.acciones:
                self.acciones.append(accion)
        for solicitud in solicitudes:
            causas = self.solicitudes.setdefault(solicitud, [])
            if regla not in causas:
                causas.append(regla)
        return nuevo

    def solicitar(self, solicitud: Solicitud, causa: str) -> None:
        causas = self.solicitudes.setdefault(solicitud, [])
        if causa not in causas:
            causas.append(causa)

    def pedida(self, solicitud: Solicitud) -> bool:
        return bool(self.solicitudes.get(solicitud))


Regla = Callable[[Instantanea, Memoria, "Contexto"], None]
_REGISTRO: dict[str, Regla] = {}


def regla(codigo: str) -> Callable[[Regla], Regla]:
    def envolver(funcion: Regla) -> Regla:
        _REGISTRO[codigo] = funcion
        return funcion

    return envolver


@dataclass(frozen=True, slots=True)
class Contexto:
    """Valores calculados que las reglas comparten dentro de una evaluación."""

    medicion_confirmada: Tri
    integridad_hermetica: Tri
    temperatura_grano: Dato  # Dato aplicable, medido o estimado
    lecturas_termicas_comparables: Tri
    horas_entre_lecturas: Decimal | None
    datos_aireacion_completos: Tri


def _corregir(descripcion: str) -> Accion:
    return Accion("CORREGIR", descripcion, "PRODUCTOR")


def _tecnico(descripcion: str) -> Accion:
    return Accion("REVISION_TECNICA", descripcion, "TECNICO")


# --- A. Humedad y aptitud inicial -------------------------------------------------

@regla("R01")
def r01(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    humedad = inst.datos["humedad_grano"]
    if y(ctx.medicion_confirmada, mayor(humedad, inst.parametros.humedad_admision_max)) is V:
        destino = "admisión" if inst.fase is Fase.INGRESO else "permanencia normal"
        mem.registrar(
            "R01",
            "HUMEDAD_NO_APTA",
            f"Humedad confirmada {humedad.valor} % b.h. supera el máximo de admisión "
            f"de {inst.parametros.humedad_admision_max} %: no procede la {destino}.",
            evidencias=(evidencia(humedad, "GT", inst.parametros.humedad_admision_max),),
            solicitudes=(Solicitud.SUSPENSION,),
            accion=_corregir("Secar el lote, medir de nuevo y volver a evaluar."),
        )


@regla("R02")
def r02(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    humedad = inst.datos["humedad_grano"]
    p = inst.parametros
    en_banda = y(
        ctx.medicion_confirmada,
        mayor(humedad, p.humedad_base_max),
        menor_igual(humedad, p.humedad_admision_max),
    )
    if en_banda is not V:
        return
    mem.registrar(
        "R02",
        "HUMEDAD_CONDICIONAL",
        f"Humedad confirmada {humedad.valor} % b.h. está en la banda condicional "
        f"(> {p.humedad_base_max} % y <= {p.humedad_admision_max} %).",
        evidencias=(evidencia(humedad, "GT", p.humedad_base_max),),
    )
    plazo = inst.dias_previstos_restantes
    obliga_secado = (
        inst.es_hermetico
        or inst.clima_calido is V
        or (plazo is not None and plazo > p.plazo_corto_max_dias)
    )
    if obliga_secado:
        mem.registrar(
            "R02",
            "SECADO_REQUERIDO_BANDA_CONDICIONAL",
            "La banda condicional no es admisible con almacenamiento hermético, clima "
            f"cálido o plazo mayor de {p.plazo_corto_max_dias} días: secar hasta "
            f"<= {p.humedad_base_max} %.",
            evidencias=(evidencia(humedad, "GT", p.humedad_base_max),),
            solicitudes=(Solicitud.CORRECCION,),
            accion=_corregir(f"Secar hasta {p.humedad_base_max} % b.h. y reevaluar."),
        )


@regla("R03")
def r03(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    humedad = inst.datos["humedad_grano"]
    if y(ctx.medicion_confirmada, menor_igual(humedad, inst.parametros.humedad_base_max)) is V:
        mem.registrar(
            "R03",
            "HUMEDAD_APTA_BASE",
            f"Humedad confirmada {humedad.valor} % b.h. dentro de la condición base. "
            "Este hecho no autoriza por sí solo.",
            evidencias=(evidencia(humedad, "LTE", inst.parametros.humedad_base_max),),
        )


@regla("R04")
def r04(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    aw = inst.datos["actividad_agua"]
    if y(inst.datos.booleano("aw_medida"), mayor_igual(aw, inst.parametros.aw_alerta)) is V:
        mem.registrar(
            "R04",
            "RIESGO_FUNGICO_HIDRICO",
            f"Actividad de agua medida {aw.valor} alcanza o supera {inst.parametros.aw_alerta}.",
            evidencias=(evidencia(aw, "GTE", inst.parametros.aw_alerta),),
            solicitudes=(Solicitud.CORRECCION,),
            accion=_tecnico("Secado o evaluación técnica y nueva medición."),
        )


@regla("R05")
def r05(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    humedad = inst.datos["humedad_grano"]
    hay_medicion = humedad.utilizable or inst.datos["metodo_humedad"].texto is not None
    if hay_medicion and ctx.medicion_confirmada is F:
        mem.registrar(
            "R05",
            "MEDICION_HUMEDAD_NO_CONFIRMADA",
            "La medición de humedad no está confirmada: corregir método, equipo, "
            "representatividad o acondicionamiento. Una estimación indirecta no sustenta "
            "R01–R03.",
            evidencias=(evidencia(inst.datos["metodo_humedad"], "EQ", "INSTRUMENTAL"),),
            solicitudes=(Solicitud.CORRECCION,),
            accion=_corregir("Repetir la medición con procedimiento y equipo verificados."),
        )


# --- B. Ambiente, aireación y hermeticidad ----------------------------------------

@regla("R06")
def r06(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    p = inst.parametros
    temperatura = inst.datos["temperatura_almacen"]
    if inst.es_no_hermetico:
        rama = menor(inst.datos["hr_almacen"], p.hr_almacen_no_hermetico_max_exclusiva)
    elif inst.es_hermetico:
        rama = ctx.integridad_hermetica
    else:
        return
    if y(menor(temperatura, p.temperatura_alerta), rama) is V:
        mem.registrar(
            "R06",
            "AMBIENTE_BASE_APTO",
            "Ambiente del almacén dentro de la condición base.",
            evidencias=(
                evidencia(temperatura, "LT", p.temperatura_alerta),
                evidencia(inst.datos["hr_almacen"], "LT", p.hr_almacen_no_hermetico_max_exclusiva),
            ),
        )


@regla("R07")
def r07(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    if not inst.es_no_hermetico:
        return
    hr = inst.datos["hr_almacen"]
    if mayor_igual(hr, inst.parametros.hr_almacen_no_hermetico_max_exclusiva) is V:
        mem.registrar(
            "R07",
            "RIESGO_REHUMEDECIMIENTO",
            f"Humedad relativa del almacén {hr.valor} % alcanza o supera "
            f"{inst.parametros.hr_almacen_no_hermetico_max_exclusiva} % en almacenamiento "
            "no hermético.",
            evidencias=(
                evidencia(hr, "GTE", inst.parametros.hr_almacen_no_hermetico_max_exclusiva),
            ),
            solicitudes=(Solicitud.CORRECCION,),
            accion=_corregir("Corregir la exposición a humedad del almacén."),
        )


@regla("R08")
def r08(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    p = inst.parametros
    almacen = inst.datos["temperatura_almacen"]
    grano = ctx.temperatura_grano
    if o(mayor_igual(almacen, p.temperatura_alerta), mayor_igual(grano, p.temperatura_alerta)) is V:
        mem.registrar(
            "R08",
            "RIESGO_TERMICO",
            f"Temperatura de {p.temperatura_alerta} °C o más en el almacén o en el grano.",
            evidencias=(
                evidencia(almacen, "GTE", p.temperatura_alerta),
                evidencia(grano, "GTE", p.temperatura_alerta),
            ),
            solicitudes=(Solicitud.CORRECCION,),
            accion=_corregir("Evaluar enfriamiento, revisar el grano y recalcular el tiempo."),
        )


@regla("R09")
def r09(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    if ctx.lecturas_termicas_comparables is NA:
        mem.no_aplica.add("R09")
        return
    actual, previa = inst.datos["temperatura_grano"], inst.datos["temperatura_grano_previa"]
    if ctx.lecturas_termicas_comparables is not V:
        return
    a, b = actual.numero, previa.numero
    if a is None or b is None:
        return
    if (a - b) >= inst.parametros.aumento_termico_alerta:
        horas = ctx.horas_entre_lecturas
        mem.registrar(
            "R09",
            "PUNTO_CALIENTE_SOSPECHADO",
            f"La temperatura del grano aumentó {a - b} °C en {horas} horas. El aumento no "
            "confirma infestación ni actividad microbiana: exige inspección.",
            evidencias=(
                evidencia(actual, "GTE", b + inst.parametros.aumento_termico_alerta),
                evidencia(previa),
            ),
            solicitudes=(Solicitud.CORRECCION,),
            accion=_tecnico("Inspeccionar varios puntos y buscar la causa del aumento."),
        )


@regla("R10")
def r10(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    if not inst.es_no_hermetico:
        mem.no_aplica.add("R10")
        return
    if ctx.datos_aireacion_completos is not V:
        return
    humedad = inst.datos["humedad_grano"]
    equilibrio = inst.datos["humedad_equilibrio_maiz"]
    hr_exterior = inst.datos["hr_aire_exterior"]
    aire = inst.datos["temperatura_aire_exterior"]
    condiciones = y(
        comparar(humedad, "GT", equilibrio),
        menor(hr_exterior, inst.parametros.hr_aireacion_max_exclusiva),
        no(inst.datos.booleano("lluvia_o_niebla")),
        comparar(aire, "LTE", inst.datos["temperatura_grano"]),
    )
    if condiciones is V:
        mem.registrar(
            "R10",
            "AIREACION_FAVORABLE",
            "El aire exterior puede secar el grano sin aumentar su temperatura. La "
            "recomendación queda subordinada a la decisión final.",
            evidencias=(
                evidencia(humedad, "GT", equilibrio.valor),
                evidencia(hr_exterior, "LT", inst.parametros.hr_aireacion_max_exclusiva),
                evidencia(aire, "LTE", inst.datos["temperatura_grano"].valor),
            ),
        )


@regla("R11")
def r11(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    if not inst.es_no_hermetico:
        mem.no_aplica.add("R11")
        return
    humedad = inst.datos["humedad_grano"]
    equilibrio = inst.datos["humedad_equilibrio_maiz"]
    hr_exterior = inst.datos["hr_aire_exterior"]
    aire = inst.datos["temperatura_aire_exterior"]
    # Basta una contraindicación comprobada, aunque falten otros datos exteriores.
    contraindicacion = o(
        comparar(humedad, "LTE", equilibrio),
        mayor_igual(hr_exterior, inst.parametros.hr_aireacion_max_exclusiva),
        inst.datos.booleano("lluvia_o_niebla"),
        comparar(aire, "GT", inst.datos["temperatura_grano"]),
    )
    if contraindicacion is V:
        mem.registrar(
            "R11",
            "AIREACION_DESFAVORABLE",
            "El aire exterior no permite airear sin riesgo de rehumedecer o calentar el "
            "grano. Con igualdad de humedad se adopta el criterio conservador.",
            evidencias=(
                evidencia(humedad, "LTE", equilibrio.valor),
                evidencia(hr_exterior, "GTE", inst.parametros.hr_aireacion_max_exclusiva),
                evidencia(aire, "GT", inst.datos["temperatura_grano"].valor),
            ),
        )


@regla("R12")
def r12(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    if not inst.es_hermetico:
        mem.no_aplica.add("R12")
        return
    if y(
        V if mem.tiene("HUMEDAD_APTA_BASE") else D,
        ctx.integridad_hermetica,
    ) is V:
        mem.registrar(
            "R12",
            "PROTECCION_HERMETICA_ACTIVA",
            "Barrera comprobada con humedad en condición base: mantener sellado y usar "
            "control exterior. No demuestra eliminación de insectos.",
            evidencias=(evidencia(inst.datos["sello_integro"], "EQ", True),),
        )


@regla("R13")
def r13(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    if not inst.es_hermetico:
        mem.no_aplica.add("R13")
        return
    comprometida = o(
        no(inst.datos.booleano("sello_integro")),
        inst.datos.booleano("perforacion_barrera"),
        inst.datos.booleano("bolsa_abierta_sin_resellar"),
        no(inst.datos.booleano("cierre_seguro")),
    )
    if comprometida is V:
        mem.registrar(
            "R13",
            "HERMETICIDAD_COMPROMETIDA",
            "La barrera hermética no está íntegra: se invalidan la protección y los "
            "controles internos heredados del sellado.",
            evidencias=(
                evidencia(inst.datos["sello_integro"], "EQ", False),
                evidencia(inst.datos["perforacion_barrera"], "EQ", True),
                evidencia(inst.datos["bolsa_abierta_sin_resellar"], "EQ", True),
            ),
            solicitudes=(Solicitud.CORRECCION,),
            accion=_corregir("Reparar o sustituir el recipiente y documentar el nuevo cierre."),
        )


# --- C. Plagas, deterioro y separación --------------------------------------------

@regla("R14")
def r14(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    insectos = inst.datos["insectos_vivos"]
    revision_confirmada = (
        inst.resultado_revision_plagas is ResultadoRevision.CONFIRMADA
        and inst.revision_plagas_cubre_indicios_actuales
    )
    if o(insectos.booleano, V if revision_confirmada else F) is V:
        mem.registrar(
            "R14",
            "INFESTACION_CONFIRMADA",
            "Infestación confirmada por observación de insectos vivos o revisión técnica.",
            evidencias=(evidencia(insectos, "PRESENCIA", True),),
            accion=_tecnico("Derivar a personal autorizado; no aplicar plaguicidas por cuenta propia."),
        )


@regla("R15")
def r15(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    if indicio_r15_residual(inst) is V:
        mem.registrar(
            "R15",
            "INFESTACION_SOSPECHADA",
            "Hay indicios de insectos sin revisión que los descarte. La sospecha no se "
            "convierte por sí sola en confirmación.",
            evidencias=tuple(
                evidencia(inst.datos[campo], "PRESENCIA", True) for campo in INDICIOS_R15
            ),
            solicitudes=(Solicitud.CORRECCION,),
            accion=_tecnico("Registrar la revisión del episodio con su resultado."),
        )


@regla("R16")
def r16(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    if not inst.es_no_hermetico:
        mem.no_aplica.add("R16")
        return
    p = inst.parametros
    if entre(ctx.temperatura_grano, p.insectos_temperatura_min, p.insectos_temperatura_max) is V:
        mem.registrar(
            "R16",
            "AMBIENTE_FAVORABLE_A_INSECTOS",
            f"Temperatura del grano entre {p.insectos_temperatura_min} y "
            f"{p.insectos_temperatura_max} °C: riesgo ambiental, no infestación.",
            evidencias=(evidencia(ctx.temperatura_grano, "GTE", p.insectos_temperatura_min),),
            solicitudes=(Solicitud.MONITOREO,),
        )


@regla("R17")
def r17(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    campos = ("heces_roedores_aves_entorno", "huellas", "bolsa_roida", "grano_derramado_por_plaga")
    if o(*(inst.datos.booleano(campo) for campo in campos)) is V:
        mem.registrar(
            "R17",
            "CONTAMINACION_BIOLOGICA_SOSPECHADA",
            "Signos de roedores o aves en el ámbito evaluado.",
            evidencias=tuple(evidencia(inst.datos[campo], "PRESENCIA", True) for campo in campos),
        )


@regla("R18")
def r18(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    if o(*(inst.datos.booleano(campo) for campo in CAMPOS_DETERIORO)) is V:
        mem.registrar(
            "R18",
            "DETERIORO_SOSPECHADO",
            "Indicio de deterioro del grano o del interior del envase.",
            evidencias=tuple(
                evidencia(inst.datos[campo], "PRESENCIA", True) for campo in CAMPOS_DETERIORO
            ),
        )


@regla("R19")
def r19(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    disparadores = (
        "INFESTACION_CONFIRMADA",
        "CONTAMINACION_BIOLOGICA_SOSPECHADA",
        "CONTAMINACION_ANIMAL_OBSERVADA",
        "DETERIORO_SOSPECHADO",
    )
    causas = [nombre for nombre in disparadores if mem.tiene(nombre)]
    if inst.cuarentenas_abiertas:
        causas.append("EPISODIO_CUARENTENA_ABIERTO")
    if not causas:
        return
    mem.registrar(
        "R19",
        "CUARENTENA_SOLICITADA",
        "Separar el lote y remitir a evaluación competente: " + ", ".join(causas) + ". "
        "Prohibida la mezcla y la salida para consumo sin evaluación.",
        solicitudes=(Solicitud.CUARENTENA,),
        accion=_tecnico("Separar físicamente el lote y abrir o mantener el episodio de cuarentena."),
    )


# --- D. Calidad física, recipiente, estiba e higiene -------------------------------

@regla("R20")
def r20(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    suciedad = inst.datos["suciedad_origen_animal"]
    if o(
        mayor(suciedad, inst.parametros.suciedad_animal_max),
        inst.datos.booleano("heces_visibles"),
    ) is V:
        mem.registrar(
            "R20",
            "CONTAMINACION_ANIMAL_OBSERVADA",
            "Material de origen animal observado o por encima del criterio de calidad. "
            "No afirma confirmación microbiológica de laboratorio.",
            evidencias=(
                evidencia(suciedad, "GT", inst.parametros.suciedad_animal_max),
                evidencia(inst.datos["heces_visibles"], "PRESENCIA", True),
            ),
        )


@regla("R21")
def r21(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    p = inst.parametros
    defectuosos, enfermos = inst.datos["granos_defectuosos"], inst.datos["granos_enfermos"]
    if o(mayor(defectuosos, p.defectuosos_max), mayor(enfermos, p.enfermos_max)) is V:
        mem.registrar(
            "R21",
            "LOTE_NO_CONFORME_POR_DEFECTOS",
            "Defectuosos o enfermos por encima del cribado comercial provisional.",
            evidencias=(
                evidencia(defectuosos, "GT", p.defectuosos_max),
                evidencia(enfermos, "GT", p.enfermos_max),
            ),
            solicitudes=(Solicitud.CORRECCION,),
            accion=_corregir("Separar para revisión y clasificación."),
        )


@regla("R22")
def r22(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    p = inst.parametros
    quebrados = inst.datos["granos_quebrados"]
    organica = inst.datos["materia_organica_extrana"]
    inorganica = inst.datos["materia_inorganica_extrana"]
    if o(
        mayor(quebrados, p.quebrados_max),
        mayor(organica, p.materia_organica_max),
        mayor(inorganica, p.materia_inorganica_max),
    ) is V:
        mem.registrar(
            "R22",
            "LOTE_REQUIERE_LIMPIEZA_Y_CLASIFICACION",
            "Quebrados o materias extrañas por encima del cribado comercial provisional.",
            evidencias=(
                evidencia(quebrados, "GT", p.quebrados_max),
                evidencia(organica, "GT", p.materia_organica_max),
                evidencia(inorganica, "GT", p.materia_inorganica_max),
            ),
            solicitudes=(Solicitud.CORRECCION,),
            accion=_corregir("Limpiar o clasificar, tomar nueva muestra y reevaluar."),
        )


@regla("R23")
def r23(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    if o(*(no(inst.datos.booleano(campo)) for campo in CAMPOS_RECIPIENTE)) is V:
        destino = "admisión" if inst.fase is Fase.INGRESO else "permanencia en el recipiente actual"
        mem.registrar(
            "R23",
            "RECIPIENTE_NO_APTO",
            f"El recipiente incumple un requisito comprobado: no procede la {destino}.",
            evidencias=tuple(
                evidencia(inst.datos[campo], "EQ", False) for campo in CAMPOS_RECIPIENTE
            ),
            solicitudes=(Solicitud.SUSPENSION,),
            accion=_corregir("Reemplazar o acondicionar el recipiente."),
        )


@regla("R24")
def r24(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    p = inst.parametros
    piso, pared, techo = (
        inst.datos["distancia_piso"],
        inst.datos["distancia_pared"],
        inst.datos["distancia_techo"],
    )
    if o(
        menor(piso, p.estiba_piso_min),
        menor(pared, p.estiba_pared_min),
        menor(techo, p.estiba_techo_min),
    ) is V:
        mem.registrar(
            "R24",
            "ESTIBA_NO_APTA",
            "La estiba no conserva las separaciones mínimas a piso, pared o techo.",
            evidencias=(
                evidencia(piso, "LT", p.estiba_piso_min),
                evidencia(pared, "LT", p.estiba_pared_min),
                evidencia(techo, "LT", p.estiba_techo_min),
            ),
            solicitudes=(Solicitud.CORRECCION,),
            accion=_corregir("Reubicar la estiba y medir de nuevo."),
        )


@regla("R25")
def r25(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    causas = [
        no(limpieza_general_vigente(inst)),
        no(inst.datos.booleano("limpieza_diaria")),
        no(inst.datos.booleano("limpieza_tras_operaciones")),
    ]
    if inst.fase is Fase.INGRESO:
        causas.append(no(inst.datos.booleano("limpieza_previa_nuevo_lote")))
    if o(*causas) is V:
        mem.registrar(
            "R25",
            "ALMACEN_NO_HIGIENICO",
            "La limpieza exigible no está vigente o no se comprobó.",
            evidencias=(evidencia(inst.datos["fecha_limpieza_general"], "VIGENCIA", None),),
            solicitudes=(Solicitud.CORRECCION,),
            accion=_corregir("Limpiar y registrar la verificación antes de autorizar."),
        )


@regla("R26")
def r26(inst: Instantanea, mem: Memoria, ctx: Contexto) -> None:
    campos = ("polvo_humo_gases_vapores", "quimicos_combustibles_en_almacen")
    if o(*(inst.datos.booleano(campo) for campo in campos)) is V:
        mem.registrar(
            "R26",
            "CALIDAD_AIRE_INADECUADA",
            "Hay contaminantes o productos incompatibles en el almacén de alimentos.",
            evidencias=tuple(evidencia(inst.datos[campo], "PRESENCIA", True) for campo in campos),
            solicitudes=(Solicitud.CORRECCION,),
            accion=_corregir("Retirar la fuente del área de alimentos y reevaluar."),
        )


REGLAS_ENCADENADAS: tuple[str, ...] = tuple(f"R{n:02d}" for n in range(1, 27))


def ejecutar_encadenamiento(inst: Instantanea, mem: Memoria, ctx: Contexto, *, maximo: int = 12) -> int:
    """Ejecuta R01–R26 hasta punto fijo.

    El recorrido se repite completo para que un hecho tardío active una regla ya
    evaluada, como R20 sobre R19. Si en una pasada no aparece ningún hallazgo
    nuevo, el punto fijo está alcanzado.
    """
    for pasada in range(1, maximo + 1):
        antes = len(mem.hallazgos)
        for codigo in REGLAS_ENCADENADAS:
            _REGISTRO[codigo](inst, mem, ctx)
        if len(mem.hallazgos) == antes:
            return pasada
    raise RuntimeError(
        "el encadenamiento no alcanzó un punto fijo: revise una dependencia circular"
    )
