"""Procedimientos de cálculo que las reglas invocan por nombre.

Son adjuntos procedimentales: lo que no se expresa bien como regla —acumular la
vida consumida a lo largo de un historial o buscar una celda en una tabla— se
calcula aquí. Ningún umbral vive en este módulo: la tabla, los límites y la
condición de estimación se leen de la base de conocimiento.

vida_consumida es una fracción acumulada del tiempo de referencia del modelo, no
una medida de inocuidad ni una fecha de caducidad. Un tramo sin cobertura deja el
total desconocido, y secar, enfriar o resellar no reinicia el acumulado.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from ..dominio.hechos import Estimacion
from ..dominio.valores import D, Dato, EstadoDato, F, Procedencia, Tri, V
from .base_conocimiento import BaseConocimiento, Celda
from .base_hechos import BaseHechos


@dataclass(frozen=True, slots=True)
class CalculosTiempo:
    vida_consumida: Decimal | None = None
    vida_minima_documentada: Decimal | None = None
    vida_proyectada: Decimal | None = None
    tiempo_referencia_actual: int | None = None
    celda: Celda | None = None
    motivos_no_disponible: tuple[str, ...] = ()
    estimaciones: tuple[Estimacion, ...] = ()


def _fraccion(dias: Decimal, referencia: int) -> Decimal:
    return dias / Decimal(referencia)


class Calculadora:
    """Calcula y memoriza los valores que dependen solo de los hechos iniciales."""

    def __init__(
        self,
        base: BaseConocimiento,
        hechos: BaseHechos,
        evaluar_definicion: Callable[[str], Tri],
    ) -> None:
        self._base = base
        self._hechos = hechos
        self._definicion = evaluar_definicion
        self._memoria: dict[str, Any] = {}
        self.estimacion_hermetica: Estimacion | None = None

    # --- Temperatura aplicable, sección 6.2 ----------------------------------

    def preparar(self) -> None:
        """Afirma los hechos calculados antes de la inferencia."""
        self._hechos.afirmar_calculado(self._temperatura_aplicable())

    def _temperatura_aplicable(self) -> Dato:
        medida = self._hechos.dato("temperatura_grano")
        config = self._base.calculos.get("temperatura_grano_aplicable", {})
        condicion = config.get("aplica_estimacion")
        aplica = self._definicion(condicion) if condicion else F

        base_dato = Dato(
            campo="temperatura_grano",
            estado=medida.estado,
            valor=medida.valor,
            unidad=medida.unidad,
            fecha_observacion=medida.fecha_observacion,
            metodo=medida.metodo,
            procedencia=medida.procedencia,
            no_aplica=medida.no_aplica,
        )
        if aplica is not V:
            return self._como_aplicable(base_dato)

        candidatas = [
            valor
            for valor in (medida.numero, self._hechos.instantanea.temperatura_ambiente_maxima_intervalo)
            if valor is not None
        ]
        if not candidatas:
            return self._como_aplicable(base_dato)

        self.estimacion_hermetica = Estimacion(
            tipo="ESTIMACION_HERMETICA",
            descripcion=str(config.get("descripcion", "")).strip()
            or "Escenario de planificación sin apertura del recipiente.",
            campos=("temperatura_grano",),
        )
        estimada = Dato(
            campo="temperatura_grano",
            estado=EstadoDato.VALIDO,
            valor=max(candidatas),
            unidad="CELSIUS",
            fecha_observacion=medida.fecha_observacion,
            metodo="ESTIMACION_HERMETICA",
            procedencia=Procedencia.ESTIMADA,
        )
        return self._como_aplicable(estimada)

    @staticmethod
    def _como_aplicable(dato: Dato) -> Dato:
        """Se guarda bajo su propio nombre pero conserva el campo de origen en la evidencia."""
        return Dato(
            campo="temperatura_grano_aplicable",
            estado=dato.estado,
            valor=dato.valor,
            unidad=dato.unidad,
            fecha_observacion=dato.fecha_observacion,
            metodo=dato.metodo,
            procedencia=dato.procedencia,
            no_aplica=dato.no_aplica,
        )

    # --- Tiempo de almacenamiento, sección 6 ---------------------------------

    @property
    def tiempo(self) -> CalculosTiempo:
        if "tiempo" not in self._memoria:
            self._memoria["tiempo"] = self._calcular_tiempo()
        return self._memoria["tiempo"]

    def _calcular_tiempo(self) -> CalculosTiempo:
        inst = self._hechos.instantanea
        tabla = self._base.tabla_tiempo
        humedad = self._hechos.dato("humedad_grano").numero
        temperatura = self._hechos.dato("temperatura_grano_aplicable").numero

        celda = None
        motivos: list[str] = []
        estimaciones: list[Estimacion] = []
        if humedad is None or temperatura is None:
            motivos.append("faltan humedad o temperatura para seleccionar la celda de referencia")
        else:
            celda = tabla.seleccionar(humedad, temperatura)
            if celda is None:
                motivos.append(
                    f"la tabla {tabla.id} no cubre {humedad} % b.h. a {temperatura} °C; "
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
        referencia = celda.dias_referencia if celda else None

        conocido = Decimal("0")
        completo = True
        previa = inst.historial.vida_previa_documentada
        if previa is None:
            completo = False
            motivos.append("no hay vida previa documentada ni constancia de inicio del historial")
        else:
            conocido += previa

        anterior: datetime | None = None
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
            celda_tramo = tabla.seleccionar(
                intervalo.humedad_grano,  # type: ignore[arg-type]
                intervalo.temperatura_grano,  # type: ignore[arg-type]
            )
            if celda_tramo is None:
                completo = False
                motivos.append(
                    f"intervalo {intervalo.inicio.date()}–{intervalo.fin.date()} fuera de la tabla"
                )
                continue
            conocido += _fraccion(intervalo.dias, celda_tramo.dias_referencia)

        vida = conocido if completo else None
        proyectada = None
        if vida is not None and referencia and inst.dias_previstos_restantes is not None:
            proyectada = vida + _fraccion(Decimal(inst.dias_previstos_restantes), referencia)

        return CalculosTiempo(
            vida_consumida=vida,
            vida_minima_documentada=conocido,
            vida_proyectada=proyectada,
            tiempo_referencia_actual=referencia,
            celda=celda,
            motivos_no_disponible=tuple(motivos),
            estimaciones=tuple(estimaciones),
        )

    def plazo_compatible(self) -> Tri:
        """Sección 6.3. No se memoriza: depende del hecho HUMEDAD_CONDICIONAL."""
        inst = self._hechos.instantanea
        config = self._base.calculos.get("plazo_compatible", {})
        limite = self._base.parametro(config.get("parametro_limite", "vida_limite"))
        calculo = self.tiempo
        if calculo.vida_consumida is None or not calculo.tiempo_referencia_actual:
            return D
        if inst.dias_previstos_restantes is None or calculo.vida_proyectada is None:
            return D
        if calculo.vida_proyectada >= limite:
            return F
        if inst.fecha_salida_prevista is None:
            return D
        esperada = inst.fecha_evaluacion + timedelta(days=inst.dias_previstos_restantes)
        if abs((inst.fecha_salida_prevista - esperada).days) > 1:
            return F
        if inst.clima_calido is V and inst.es_no_hermetico:
            if inst.dias_almacenados is None:
                return D
            limite_calido = self._base.parametro(config.get("parametro_limite_calido", "limite_calido_dias"))
            if inst.dias_almacenados + inst.dias_previstos_restantes >= limite_calido:
                return F
        condicional = self._hechos.tiene(config.get("hecho_condicional", "HUMEDAD_CONDICIONAL"))
        plazo_corto = self._base.parametro(config.get("parametro_plazo_condicional", "plazo_corto_max_dias"))
        if condicional and inst.dias_previstos_restantes > plazo_corto:
            return F
        return V

    # --- Acceso por nombre desde el lenguaje de condiciones -------------------

    def valor(self, nombre: str) -> Any:
        inst = self._hechos.instantanea
        tiempo = self.tiempo
        match nombre:
            case "vida_consumida":
                return tiempo.vida_consumida
            case "vida_minima_documentada":
                return tiempo.vida_minima_documentada
            case "vida_proyectada":
                return tiempo.vida_proyectada
            case "tiempo_referencia_actual":
                return tiempo.tiempo_referencia_actual
            case "plazo_compatible":
                return self.plazo_compatible()
            case "estimacion_hermetica":
                return V if self.estimacion_hermetica is not None else F
            case "dias_previstos_restantes":
                return inst.dias_previstos_restantes
            case "dias_almacenados":
                return inst.dias_almacenados
            case "fecha_salida_prevista":
                return inst.fecha_salida_prevista
            case "plan_vigente":
                return V if inst.plan.registrado and inst.plan.vigente else F
            case "plan_intervalo_dias":
                return inst.plan.intervalo_dias if inst.plan.registrado and inst.plan.vigente else None
            case "plan_salida_definida":
                return V if inst.plan.fecha_salida_prevista is not None else F
            case "dictamen_cubre":
                humedad = self._hechos.dato("humedad_grano").numero
                dictamen = inst.dictamen
                if dictamen is None or humedad is None:
                    return F
                cubre = dictamen.cubre(humedad, inst.dias_previstos_restantes or 0, inst.fecha_evaluacion)
                return V if cubre else F
        raise KeyError(f"cálculo desconocido: {nombre}")

    # --- Fechas del resultado ------------------------------------------------

    def proximo_control(self, riesgo: Tri, monitoreo: bool) -> datetime:
        inst = self._hechos.instantanea
        config = self._base.calculos.get("proximo_control", {})
        con_riesgo = self._base.parametro(config.get("parametro_riesgo", "control_con_riesgo_dias"))
        if inst.es_hermetico:
            normal = self._base.parametro(config.get("parametro_hermetico", "control_exterior_dias"))
            ultima = inst.controles.fecha_inspeccion_exterior
        else:
            normal = self._base.parametro(config.get("parametro_no_hermetico", "control_no_hermetico_dias"))
            ultima = inst.controles.fecha_inspeccion_grano
        dias = con_riesgo if (riesgo in (V, D) or monitoreo) else normal
        if inst.plan.registrado and inst.plan.vigente and inst.plan.intervalo_dias:
            dias = min(dias, Decimal(inst.plan.intervalo_dias))
        return (ultima or inst.fecha_evaluacion) + timedelta(days=float(dias))

    def vencimiento_autorizacion(self, proximo: datetime | None) -> datetime | None:
        """La menor fecha entre control, salida, dictamen y cruce del límite de vida."""
        inst = self._hechos.instantanea
        limite = self._base.parametro("vida_limite")
        candidatas: list[datetime] = []
        if proximo is not None:
            candidatas.append(proximo)
        if inst.fecha_salida_prevista is not None:
            candidatas.append(inst.fecha_salida_prevista)
        if inst.dictamen is not None and inst.dictamen.vigente:
            candidatas.append(inst.dictamen.vence_en)
        tiempo = self.tiempo
        if tiempo.vida_consumida is not None and tiempo.tiempo_referencia_actual and tiempo.vida_consumida < limite:
            restante = (limite - tiempo.vida_consumida) * Decimal(tiempo.tiempo_referencia_actual)
            candidatas.append(inst.fecha_evaluacion + timedelta(days=float(restante)))
        return min(candidatas) if candidatas else None
