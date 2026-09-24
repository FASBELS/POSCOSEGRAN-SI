"""Motor de inferencia genérico.

No contiene conocimiento del dominio. Aplica cualquier base de conocimiento
válida siguiendo el ciclo reconocer–actuar:

    1. Afirmar los hechos iniciales y los calculados.
    2. Para cada etapa de la agenda, en orden:
         reconocer  evaluar la condición de cada regla aún no disparada;
         actuar     disparar las que resulten VERDADERO, añadiendo hechos
                    inferidos y solicitudes;
       repetir hasta que una pasada no dispare ninguna regla (punto fijo).
    3. Determinar los datos exigibles que siguen desconocidos.
    4. Resolver el conjunto conflicto con la tabla de prioridades: gana la primera
       rama VERDADERO. Las demás no emiten decisión, pero todos los motivos se
       conservan.

Refracción: una regla dispara una sola vez por evaluación. Como cada pasada que
no alcanza el punto fijo dispara al menos una regla nueva, el ciclo termina
siempre en, como mucho, tantas pasadas como reglas tenga la etapa.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from ..dominio.campos import CAMPOS
from ..dominio.hechos import Accion, Estimacion, Instantanea, Motivo, Pendiente
from ..dominio.valores import D, Dato, Evidencia, Tri, V
from .base_conocimiento import NOMBRE_SOLICITUD, BaseConocimiento, ReglaProduccion
from .base_hechos import Activacion, BaseHechos, EvaluacionRama
from .calculos import Calculadora, CalculosTiempo
from .lenguaje import Evaluador

VERSION_MOTOR = "0.8.0"



@dataclass(frozen=True, slots=True)
class Resultado:
    decision_final: str
    rama_r30: str
    motivos: tuple[Motivo, ...]
    acciones_requeridas: tuple[Accion, ...]
    datos_pendientes: tuple[Pendiente, ...]
    estimaciones: tuple[Estimacion, ...]
    reglas_activadas: tuple[str, ...]
    calculos: CalculosTiempo
    fecha_proximo_control: datetime | None
    fecha_vencimiento_autorizacion: datetime | None
    solicitudes: dict[str, tuple[str, ...]]
    riesgo_activo: Tri
    version_base: str
    version_parametros: str
    version_motor: str
    hash_base: str
    traza: tuple[Activacion, ...]
    ramas: tuple[EvaluacionRama, ...]
    hechos_inferidos: tuple[str, ...]
    hechos_iniciales: tuple[tuple[str, object, str], ...]
    no_aplicables: tuple[str, ...]


class Motor:
    def __init__(self, base: BaseConocimiento) -> None:
        self.base = base

    def evaluar(self, instantanea: Instantanea) -> Resultado:
        hechos = BaseHechos.desde(instantanea)
        evaluador = Evaluador(self.base, hechos, calculadora=None)
        calculadora = Calculadora(self.base, hechos, evaluador.definicion)
        evaluador.calculadora = calculadora
        calculadora.preparar()

        orden = 0
        for etapa in self.base.etapas:
            reglas = [r for r in self.base.reglas if r.etapa == etapa]
            for pasada in range(1, len(reglas) + 2):
                disparos = 0
                for regla in reglas:
                    if regla.id in hechos.disparadas:
                        continue
                    if regla.aplica_si is not None and evaluador.evaluar(regla.aplica_si).valor is not V:
                        if regla.regla not in hechos.no_aplicables:
                            hechos.no_aplicables.append(regla.regla)
                        continue
                    juicio = evaluador.evaluar(regla.si)
                    if juicio.valor is not V:
                        continue
                    orden += 1
                    self._disparar(regla, juicio.soportes, hechos, evaluador, etapa, pasada, orden)
                    disparos += 1
                if disparos == 0:
                    break
            else:  
                raise RuntimeError(f"la etapa {etapa} no alcanzó un punto fijo")

        hechos.pendientes = self._pendientes(hechos, evaluador, calculadora)

        decision, rama = self._resolver(hechos, evaluador)

        riesgo = evaluador.definicion("riesgo_activo") if "riesgo_activo" in self.base.definiciones else D
        monitoreo = hechos.pedida("MONITOREO")
        proximo = None if decision == "CUARENTENA" else calculadora.proximo_control(riesgo, monitoreo)
        vencimiento = (
            calculadora.vencimiento_autorizacion(proximo)
            if decision in self.base.decisiones_autorizadas
            else None
        )

        estimaciones: list[Estimacion] = []
        if calculadora.estimacion_hermetica is not None:
            estimaciones.append(calculadora.estimacion_hermetica)
        estimaciones.extend(calculadora.tiempo.estimaciones)

        return Resultado(
            decision_final=decision,
            rama_r30=rama,
            motivos=tuple(hechos.motivos),
            acciones_requeridas=tuple(hechos.acciones),
            datos_pendientes=tuple(hechos.pendientes),
            estimaciones=tuple(dict.fromkeys(estimaciones)),
            reglas_activadas=tuple(hechos.reglas_activadas),
            calculos=calculadora.tiempo,
            fecha_proximo_control=proximo,
            fecha_vencimiento_autorizacion=vencimiento,
            solicitudes={
                NOMBRE_SOLICITUD[s]: tuple(c) for s, c in hechos.solicitudes.items() if c
            },
            riesgo_activo=riesgo,
            version_base=self.base.version_base,
            version_parametros=self.base.version_parametros,
            version_motor=VERSION_MOTOR,
            hash_base=self.base.hash,
            traza=tuple(hechos.traza),
            ramas=tuple(hechos.ramas),
            hechos_inferidos=tuple(hechos.hallazgos),
            hechos_iniciales=tuple(hechos.iniciales()),
            no_aplicables=tuple(hechos.no_aplicables),
        )


    def _disparar(
        self,
        regla: ReglaProduccion,
        soportes: tuple[str, ...],
        hechos: BaseHechos,
        evaluador: Evaluador,
        etapa: str,
        pasada: int,
        orden: int,
    ) -> None:
        hechos.disparadas.add(regla.id)
        consecuente = regla.entonces
        hallazgo = consecuente.hallazgo

        if hallazgo and not hechos.tiene(hallazgo):
            hechos.hallazgos.append(hallazgo)
            if regla.registrar_motivo:
                hechos.motivos.append(
                    Motivo(
                        id=f"{regla.regla}:{hallazgo}",
                        regla=regla.regla,
                        mensaje=self._redactar(consecuente.mensaje or "", soportes, hechos, evaluador),
                        evidencias=tuple(self._evidencia(e, hechos, evaluador) for e in regla.evidencias),
                        fuentes=self.base.fuentes_de(regla.regla),
                        fundamento=self.base.fundamento_de(regla.regla),
                    )
                )
                if regla.regla not in hechos.reglas_activadas:
                    hechos.reglas_activadas.append(regla.regla)
            if consecuente.accion:
                accion = Accion(
                    codigo=consecuente.accion["codigo"],
                    descripcion=self._redactar(consecuente.accion["descripcion"], soportes, hechos, evaluador),
                    responsable_requerido=consecuente.accion["responsable"],
                )
                if accion not in hechos.acciones:
                    hechos.acciones.append(accion)

        for solicitud in consecuente.solicitudes:
            hechos.solicitar(solicitud, regla.regla)

        hechos.traza.append(
            Activacion(
                orden=orden,
                etapa=etapa,
                pasada=pasada,
                produccion=regla.id,
                regla=regla.regla,
                hallazgo=hallazgo,
                soportes=soportes,
                solicitudes=tuple(NOMBRE_SOLICITUD[s] for s in consecuente.solicitudes),
            )
        )

    def _evidencia(self, especificacion: Mapping[str, Any], hechos: BaseHechos, evaluador: Evaluador) -> Evidencia:
        dato = hechos.dato(especificacion["dato"])
        umbral: Any = None
        if "valor" in especificacion:
            umbral = evaluador.valor(especificacion["valor"])
            if isinstance(umbral, Dato):
                umbral = umbral.valor
        campo = "temperatura_grano" if dato.campo == "temperatura_grano_aplicable" else dato.campo
        return Evidencia(
            campo=campo,
            valor_observado=dato.valor,
            unidad=dato.unidad,
            fecha_observacion=dato.fecha_observacion,
            operador=especificacion.get("op"),
            umbral=umbral,
        )

    _MARCADOR = re.compile(r"\{([^{}]+)\}")

    def _redactar(
        self, plantilla: str, soportes: tuple[str, ...], hechos: BaseHechos, evaluador: Evaluador
    ) -> str:
        """Rellena el mensaje de la regla con los valores de este caso."""

        def formato(valor: Any) -> str:
            if valor is None:
                return "desconocido"
            if isinstance(valor, Decimal):
                return format(valor.normalize(), "f") if valor == valor.to_integral() else str(valor)
            return str(valor)

        def sustituir(coincidencia: re.Match[str]) -> str:
            marcador = coincidencia.group(1)
            if marcador == "soportes":
                return ", ".join(dict.fromkeys(soportes)) or "sin detalle"
            if marcador == "invalidos":
                return ", ".join(hechos.invalidos())
            if "?" in marcador:
                condicion, opciones = marcador.split("?", 1)
                si, _, sino = opciones.partition("|")
                es_ingreso = hechos.instantanea.fase is not None and hechos.instantanea.fase.value == "INGRESO"
                return si if condicion == "ingreso" and es_ingreso else sino
            tipo, _, argumento = marcador.partition(":")
            if tipo == "dato":
                return formato(hechos.dato(argumento).valor)
            if tipo == "param":
                return formato(self.base.parametro(argumento))
            if tipo == "calculo":
                return formato(evaluador.calculadora.valor(argumento))
            if tipo == "fallidas":
                return "; ".join(evaluador.fallidas({"definicion": argumento})) or "sin detalle"
            if tipo in {"diferencia", "horas"}:
                a, b = (hechos.dato(c.strip()) for c in argumento.split(","))
                if tipo == "diferencia":
                    if a.numero is None or b.numero is None:
                        return "desconocido"
                    return formato(a.numero - b.numero)
                if a.fecha_observacion is None or b.fecha_observacion is None:
                    return "desconocido"
                horas = (a.fecha_observacion - b.fecha_observacion).total_seconds() / 3600
                return formato(Decimal(str(round(horas, 1))))
            return coincidencia.group(0)

        return self._MARCADOR.sub(sustituir, plantilla)


    def _pendientes(self, hechos: BaseHechos, evaluador: Evaluador, calculadora: Calculadora) -> list[Pendiente]:
        salida: list[Pendiente] = []
        for exigible in self.base.datos_exigibles:
            if "cuando_desconocido" in exigible:
                activo = evaluador.evaluar(exigible["cuando_desconocido"]).valor is D
            else:
                activo = evaluador.evaluar(exigible["cuando"]).valor is V
            if not activo:
                continue
            if "campos" in exigible:
                for campo in hechos.conjunto.desconocidos(exigible["campos"]):
                    paso = CAMPOS[campo].paso if campo in CAMPOS else 6
                    salida.append(Pendiente(campo, exigible["motivo"], paso))
            if "pendiente" in exigible:
                p = exigible["pendiente"]
                salida.append(Pendiente(p["campo"], p["motivo"], int(p.get("paso", 6))))
            if "pendientes_del_calculo" in exigible:
                campo = exigible["pendientes_del_calculo"]
                for motivo in calculadora.tiempo.motivos_no_disponible:
                    salida.append(Pendiente(campo, motivo, 5))
        unicos: dict[tuple[str, str], Pendiente] = {}
        for pendiente in salida:
            unicos.setdefault((pendiente.campo, pendiente.motivo), pendiente)
        return list(unicos.values())


    def _resolver(self, hechos: BaseHechos, evaluador: Evaluador) -> tuple[str, str]:
        """Prioridad fija: gana la primera rama VERDADERO.

        Se evalúan todas las ramas para que la explicación pueda decir qué le
        faltó a cada autorización, aunque solo una emita la decisión.
        """
        elegida = None
        for rama in self.base.resolucion:
            juicio = evaluador.evaluar(rama.si)
            fallidas = () if juicio.valor is V else tuple(evaluador.fallidas(rama.si))
            hechos.ramas.append(
                EvaluacionRama(rama=rama.rama, decision=rama.decision, valor=juicio.valor.value, fallidas=fallidas)
            )
            if elegida is None and juicio.valor is V:
                elegida = rama
        assert elegida is not None, "la última rama se aplica siempre"
        if elegida.mensaje:
            hechos.motivos.append(
                Motivo(
                    id=f"{elegida.rama}:SIN_CONCLUSION",
                    regla=elegida.rama,
                    mensaje=elegida.mensaje,
                    fuentes=self.base.fuentes_de(elegida.rama),
                    fundamento=self.base.fundamento_de(elegida.rama),
                )
            )
        return elegida.decision, elegida.rama
