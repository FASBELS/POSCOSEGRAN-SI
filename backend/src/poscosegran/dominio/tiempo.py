"""Modelo de tiempo de almacenamiento, sección 6.

vida_consumida es una fracción acumulada del tiempo de referencia del modelo, no
una medida de inocuidad ni una fecha de caducidad. Un tramo sin cobertura deja el
total DESCONOCIDO: la parte desconocida no se registra como un cero observado.
Secar, enfriar, trasvasar o resellar no reinicia el acumulado.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from . import tablas
from .hechos import Estimacion, Instantanea
from .valores import D, Dato, EstadoDato, F, Procedencia, Tri, V


@dataclass(frozen=True, slots=True)
class CalculosTiempo:
    vida_consumida: Decimal | None = None
    vida_minima_documentada: Decimal | None = None
    vida_proyectada: Decimal | None = None
    tiempo_referencia_actual: int | None = None
    celda: tablas.Celda | None = None
    motivos_no_disponible: tuple[str, ...] = ()
    estimaciones: tuple[Estimacion, ...] = ()


def temperatura_aplicable(inst: Instantanea, integridad: Tri) -> tuple[Dato, Estimacion | None]:
    """Temperatura del grano utilizable, medida o estimada.

    En hermético sin sensor interno se permite un escenario de planificación con
    la mayor entre la última temperatura interna válida y las máximas ambientales
    documentadas. Se etiqueta ESTIMACION_HERMETICA y no se presenta como una
    medición interna: exige barrera íntegra, control exterior vigente y ausencia
    de sospecha interna.
    """
    medida = inst.datos["temperatura_grano"]
    if not inst.es_hermetico or inst.sensor_interno_hermetico:
        return medida, None
    if integridad is not V:
        return medida, None

    candidatas = [
        valor
        for valor in (medida.numero, inst.temperatura_ambiente_maxima_intervalo)
        if valor is not None
    ]
    if not candidatas:
        return medida, None

    estimada = max(candidatas)
    dato = Dato(
        campo="temperatura_grano",
        estado=EstadoDato.VALIDO,
        valor=estimada,
        unidad="CELSIUS",
        fecha_observacion=medida.fecha_observacion,
        metodo="ESTIMACION_HERMETICA",
        procedencia=Procedencia.ESTIMADA,
    )
    return dato, Estimacion(
        tipo="ESTIMACION_HERMETICA",
        descripcion=(
            "Escenario de planificación sin apertura: se toma la mayor entre la última "
            "temperatura interna válida y la máxima ambiental documentada del intervalo."
        ),
        campos=("temperatura_grano",),
    )


def _fraccion(dias: Decimal, referencia: int) -> Decimal:
    return dias / Decimal(referencia)


def calcular(inst: Instantanea, temperatura: Dato) -> CalculosTiempo:
    humedad = inst.datos["humedad_grano"].numero
    temperatura_actual = temperatura.numero

    celda = None
    motivos: list[str] = []
    estimaciones: list[Estimacion] = []
    if humedad is None or temperatura_actual is None:
        motivos.append("faltan humedad o temperatura para seleccionar la celda de referencia")
    else:
        celda = tablas.seleccionar(humedad, temperatura_actual)
        if celda is None:
            motivos.append(
                f"la tabla {tablas.ID_TABLA} no cubre {humedad} % b.h. a {temperatura_actual} °C; "
                "no se extrapola"
            )
        elif celda.sustituida:
            estimaciones.append(
                Estimacion(
                    tipo="SUSTITUCION_TABLA",
                    descripcion=celda.motivo,
                    campos=("humedad_grano", "temperatura_grano"),
                    id_tabla=celda.id_tabla,
                )
            )

    referencia_actual = celda.dias_referencia if celda else None

    # Acumulado histórico
    conocido = Decimal("0")
    completo = True
    previa = inst.historial.vida_previa_documentada
    if previa is None:
        completo = False
        motivos.append("no hay vida previa documentada ni constancia de inicio del historial")
    else:
        conocido += previa

    anterior = None
    for intervalo in sorted(inst.historial.intervalos, key=lambda i: i.inicio):
        if intervalo.fin <= intervalo.inicio or intervalo.fin > inst.fecha_evaluacion:
            completo = False
            motivos.append("intervalo invertido o posterior a la evaluación")
            continue
        if anterior is not None and intervalo.inicio < anterior:
            completo = False
            motivos.append("intervalos solapados: no se duplica el consumo documentado")
            continue
        if anterior is not None and intervalo.inicio > anterior:
            completo = False
            motivos.append("laguna entre intervalos del historial")
        anterior = intervalo.fin
        if not intervalo.documentado:
            completo = False
            motivos.append(
                f"intervalo {intervalo.inicio.date()}–{intervalo.fin.date()} sin condiciones "
                "representativas documentadas"
            )
            continue
        celda_intervalo = tablas.seleccionar(
            intervalo.humedad_grano,  # type: ignore[arg-type]
            intervalo.temperatura_grano,  # type: ignore[arg-type]
        )
        if celda_intervalo is None:
            completo = False
            motivos.append(
                f"intervalo {intervalo.inicio.date()}–{intervalo.fin.date()} fuera de la tabla"
            )
            continue
        conocido += _fraccion(intervalo.dias, celda_intervalo.dias_referencia)

    vida_minima = conocido
    vida_consumida = conocido if completo else None

    vida_proyectada: Decimal | None = None
    if (
        vida_consumida is not None
        and referencia_actual
        and inst.dias_previstos_restantes is not None
    ):
        vida_proyectada = vida_consumida + _fraccion(
            Decimal(inst.dias_previstos_restantes), referencia_actual
        )

    return CalculosTiempo(
        vida_consumida=vida_consumida,
        vida_minima_documentada=vida_minima,
        vida_proyectada=vida_proyectada,
        tiempo_referencia_actual=referencia_actual,
        celda=celda,
        motivos_no_disponible=tuple(motivos),
        estimaciones=tuple(estimaciones),
    )


def plazo_compatible(inst: Instantanea, calculos: CalculosTiempo, humedad_condicional: bool) -> Tri:
    """Sección 6.3. El dictamen y el resto de la rama condicional se comprueban en R30."""
    if calculos.vida_consumida is None or not calculos.tiempo_referencia_actual:
        return D
    if inst.dias_previstos_restantes is None or calculos.vida_proyectada is None:
        return D
    if calculos.vida_proyectada >= inst.parametros.vida_limite:
        return F
    if inst.fecha_salida_prevista is None:
        return D

    esperada = inst.fecha_evaluacion + timedelta(days=inst.dias_previstos_restantes)
    if abs((inst.fecha_salida_prevista - esperada).days) > 1:
        return F

    if inst.clima_calido is V and inst.es_no_hermetico:
        if inst.dias_almacenados is None:
            return D
        limite = inst.parametros.limite_calido_no_hermetico_dias
        if inst.dias_almacenados + inst.dias_previstos_restantes >= limite:
            return F

    if humedad_condicional and inst.dias_previstos_restantes > inst.parametros.plazo_corto_max_dias:
        return F

    return V


def vencimiento_autorizacion(
    inst: Instantanea,
    calculos: CalculosTiempo,
    fecha_proximo_control: datetime | None,
) -> datetime | None:
    """La menor fecha entre control, salida prevista, dictamen y cruce del límite de vida."""
    candidatas: list[datetime] = []
    if fecha_proximo_control is not None:
        candidatas.append(fecha_proximo_control)
    if inst.fecha_salida_prevista is not None:
        candidatas.append(inst.fecha_salida_prevista)
    if inst.dictamen is not None and inst.dictamen.vigente:
        candidatas.append(inst.dictamen.vence_en)

    if (
        calculos.vida_consumida is not None
        and calculos.tiempo_referencia_actual
        and calculos.vida_consumida < inst.parametros.vida_limite
    ):
        restante = (inst.parametros.vida_limite - calculos.vida_consumida) * Decimal(
            calculos.tiempo_referencia_actual
        )
        candidatas.append(inst.fecha_evaluacion + timedelta(days=float(restante)))

    return min(candidatas) if candidatas else None
