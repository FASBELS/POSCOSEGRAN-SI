"""Evaluador del lenguaje de condiciones.

Interpreta los nodos de la base de conocimiento en lógica de tres estados. No hay
eval ni exec: cada operador tiene una implementación explícita y cerrada, y un
operador que no está en la lista de base_conocimiento.OPERADORES no se admite.

Además del valor de verdad, cada evaluación devuelve sus soportes: las
condiciones concretas que la hicieron verdadera. El módulo de explicación los
usa para responder "¿por qué?".
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from ..dominio.valores import D, Dato, F, NA, Tri, V, no, o, y
from .base_conocimiento import NOMBRE_SOLICITUD, BaseConocimiento
from .base_hechos import BaseHechos


@dataclass(frozen=True, slots=True)
class Juicio:
    valor: Tri
    soportes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "soportes", tuple(dict.fromkeys(self.soportes)))


def sumar_mes_calendario(fecha: datetime) -> datetime:
    """Conserva el día; si no existe en el mes siguiente, usa el último día."""
    anio, mes = (fecha.year + 1, 1) if fecha.month == 12 else (fecha.year, fecha.month + 1)
    for dia in range(fecha.day, 0, -1):
        try:
            return fecha.replace(year=anio, month=mes, day=dia)
        except ValueError:
            continue
    raise ValueError("fecha no representable")  # pragma: no cover


def _comparar(izquierda: Decimal, operador: str, derecha: Decimal) -> Tri:
    resultado = {
        "GT": izquierda > derecha,
        "GTE": izquierda >= derecha,
        "LT": izquierda < derecha,
        "LTE": izquierda <= derecha,
        "EQ": izquierda == derecha,
        "NEQ": izquierda != derecha,
    }[operador]
    return V if resultado else F


def _como_decimal(valor: Any) -> Decimal | None:
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, Decimal):
        return valor
    try:
        return Decimal(str(valor))
    except (ArithmeticError, ValueError):
        return None


class Evaluador:
    def __init__(self, base: BaseConocimiento, hechos: BaseHechos, calculadora: Any) -> None:
        self.base = base
        self.hechos = hechos
        self.calculadora = calculadora
        self._evaluando: set[str] = set()

    # --- Valores ---------------------------------------------------------------

    def valor(self, nodo: Any) -> Any:
        """Resuelve un valor: literal, parámetro, dato observado o elección."""
        if isinstance(nodo, Mapping):
            if "param" in nodo:
                return self.base.parametro(nodo["param"])
            if "dato" in nodo:
                return self.hechos.dato(nodo["dato"])
            if "elegir" in nodo:
                eleccion = nodo["elegir"]
                rama = "entonces" if self.evaluar(eleccion["si"]).valor is V else "sino"
                return self.valor(eleccion[rama])
        if isinstance(nodo, bool) or isinstance(nodo, str):
            return nodo
        return _como_decimal(nodo)

    # --- Condiciones -----------------------------------------------------------

    def evaluar(self, nodo: Mapping[str, Any]) -> Juicio:
        operador = next(k for k in nodo if k != "descripcion" and k not in {"op", "valor", "en", "igual", "definido", "dias", "meses"})
        metodo = getattr(self, f"_op_{operador}")
        juicio: Juicio = metodo(nodo)
        return juicio

    def definicion(self, nombre: str) -> Tri:
        return self._op_definicion({"definicion": nombre}).valor

    def descripcion(self, nodo: Mapping[str, Any]) -> str | None:
        texto = nodo.get("descripcion")
        return str(texto) if texto else None

    def _soportes(self, nodo: Mapping[str, Any], juicio: Juicio) -> tuple[str, ...]:
        """Un nodo descrito se resume en su descripción; si no, en sus propios soportes."""
        descripcion = self.descripcion(nodo)
        return (descripcion,) if descripcion else juicio.soportes

    # Conectivas -----------------------------------------------------------------

    def _op_todos(self, nodo: Mapping[str, Any]) -> Juicio:
        juicios = [(hijo, self.evaluar(hijo)) for hijo in nodo["todos"]]
        valor = y(*(j.valor for _, j in juicios))
        soportes: tuple[str, ...] = ()
        if valor is V:
            for hijo, juicio in juicios:
                if juicio.valor is V:
                    soportes += self._soportes(hijo, juicio)
        return Juicio(valor, soportes)

    def _op_alguno(self, nodo: Mapping[str, Any]) -> Juicio:
        juicios = [(hijo, self.evaluar(hijo)) for hijo in nodo["alguno"]]
        valor = o(*(j.valor for _, j in juicios))
        soportes: tuple[str, ...] = ()
        if valor is V:
            for hijo, juicio in juicios:
                if juicio.valor is V:
                    soportes += self._soportes(hijo, juicio)
        return Juicio(valor, soportes)

    def _op_negar(self, nodo: Mapping[str, Any]) -> Juicio:
        """Negar DESCONOCIDO produce DESCONOCIDO: la negación no crea información."""
        return Juicio(no(self.evaluar(nodo["negar"]).valor))

    def _op_implica(self, nodo: Mapping[str, Any]) -> Juicio:
        """Si el antecedente no es VERDADERO, la condición no aplica."""
        partes = nodo["implica"]
        if self.evaluar(partes["si"]).valor is not V:
            return Juicio(NA)
        return self.evaluar(partes["entonces"])

    def _op_guarda(self, nodo: Mapping[str, Any]) -> Juicio:
        """Sin el dato de guarda la condición completa es DESCONOCIDO, no FALSO."""
        partes = nodo["guarda"]
        dato = self.hechos.dato(partes["campo"])
        if dato.no_aplica:
            return Juicio(NA)
        if not dato.utilizable:
            return Juicio(D)
        return self.evaluar(partes["entonces"])

    def _op_es_verdadero(self, nodo: Mapping[str, Any]) -> Juicio:
        juicio = self.evaluar(nodo["es_verdadero"])
        return Juicio(V, juicio.soportes) if juicio.valor is V else Juicio(F)

    def _op_es_falso(self, nodo: Mapping[str, Any]) -> Juicio:
        return Juicio(V if self.evaluar(nodo["es_falso"]).valor is F else F)

    def _op_es_desconocido(self, nodo: Mapping[str, Any]) -> Juicio:
        return Juicio(V if self.evaluar(nodo["es_desconocido"]).valor is D else F)

    def _op_no_falso(self, nodo: Mapping[str, Any]) -> Juicio:
        return Juicio(V if self.evaluar(nodo["no_falso"]).valor in (V, D) else F)

    def _op_constante(self, nodo: Mapping[str, Any]) -> Juicio:
        return Juicio({"VERDADERO": V, "FALSO": F, "DESCONOCIDO": D}[nodo["constante"]])

    def _op_siempre(self, nodo: Mapping[str, Any]) -> Juicio:
        return Juicio(V)

    # Datos observados -----------------------------------------------------------

    def _op_dato(self, nodo: Mapping[str, Any]) -> Juicio:
        campo = nodo["dato"]
        dato = self.hechos.dato(campo)
        soporte = (campo,)

        if "en" in nodo:
            if dato.no_aplica:
                return Juicio(NA)
            texto = dato.texto
            if texto is None:
                return Juicio(D)
            return Juicio(V if texto in nodo["en"] else F, soporte)

        if "op" not in nodo:
            valor = dato.booleano
            return Juicio(valor, soporte if valor is V else ())

        operador = nodo["op"]
        derecha = self.valor(nodo["valor"])

        if isinstance(derecha, Dato):
            # Dato frente a dato: si falta cualquiera, DESCONOCIDO.
            if operador in {"EQ", "NEQ"} and (dato.texto is not None or derecha.texto is not None):
                if dato.texto is None or derecha.texto is None:
                    return Juicio(D)
                igual = dato.texto == derecha.texto
                return Juicio(V if igual == (operador == "EQ") else F, soporte)
            a, b = dato.numero, derecha.numero
            if a is None or b is None:
                return Juicio(D)
            resultado = _comparar(a, operador, b)
            return Juicio(resultado, soporte if resultado is V else ())

        if isinstance(derecha, bool):
            valor = dato.booleano
            if valor in (NA, D):
                return Juicio(valor)
            coincide = (valor is V) == derecha
            return Juicio(V if coincide == (operador == "EQ") else F, soporte)

        if isinstance(derecha, str):
            if dato.no_aplica:
                return Juicio(NA)
            texto = dato.texto
            if texto is None:
                return Juicio(D)
            igual = texto == derecha
            return Juicio(V if igual == (operador == "EQ") else F, soporte)

        numero = dato.numero
        if numero is None:
            return Juicio(NA if dato.no_aplica else D)
        if derecha is None:
            return Juicio(D)
        resultado = _comparar(numero, operador, derecha)
        return Juicio(resultado, soporte if resultado is V else ())

    def _op_aportado(self, nodo: Mapping[str, Any]) -> Juicio:
        return Juicio(V if self.hechos.dato(nodo["aportado"]).utilizable else F)

    def _op_presentes(self, nodo: Mapping[str, Any]) -> Juicio:
        return Juicio(V if all(self.hechos.dato(c).utilizable for c in nodo["presentes"]) else D)

    def _op_conocidos(self, nodo: Mapping[str, Any]) -> Juicio:
        faltan = [
            c for c in nodo["conocidos"]
            if not self.hechos.dato(c).utilizable and not self.hechos.dato(c).no_aplica
        ]
        return Juicio(V if not faltan else D)

    def _op_vigente_meses(self, nodo: Mapping[str, Any]) -> Juicio:
        dato = self.hechos.dato(nodo["vigente_meses"])
        if dato.no_aplica:
            return Juicio(NA)
        referencia = dato.fecha
        if referencia is None:
            return Juicio(D)
        limite = referencia
        for _ in range(int(nodo.get("meses", 1))):
            limite = sumar_mes_calendario(limite)
        return Juicio(V if self.hechos.instantanea.fecha_evaluacion <= limite else F)

    def _op_vencido_dias(self, nodo: Mapping[str, Any]) -> Juicio:
        """Un registro inexistente no es un atraso con fecha inventada: DESCONOCIDO."""
        from datetime import timedelta

        referencia = self.hechos.dato(nodo["vencido_dias"]).fecha
        if referencia is None:
            return Juicio(D)
        dias = self.valor(nodo["dias"])
        vence = referencia + timedelta(days=float(dias))
        return Juicio(V if self.hechos.instantanea.fecha_evaluacion > vence else F)

    def _op_horas_entre(self, nodo: Mapping[str, Any]) -> Juicio:
        a, b = (self.hechos.dato(c) for c in nodo["horas_entre"])
        if a.fecha_observacion is None or b.fecha_observacion is None:
            return Juicio(D)
        horas = Decimal(str((a.fecha_observacion - b.fecha_observacion).total_seconds() / 3600))
        derecha = self.valor(nodo["valor"])
        return Juicio(_comparar(horas, nodo["op"], derecha))

    def _op_diferencia(self, nodo: Mapping[str, Any]) -> Juicio:
        a, b = (self.hechos.dato(c).numero for c in nodo["diferencia"])
        if a is None or b is None:
            return Juicio(D)
        return Juicio(_comparar(a - b, nodo["op"], self.valor(nodo["valor"])))

    # Hechos inferidos y contexto -------------------------------------------------

    def _op_hecho(self, nodo: Mapping[str, Any]) -> Juicio:
        nombre = nodo["hecho"]
        return Juicio(V, (nombre,)) if self.hechos.tiene(nombre) else Juicio(F)

    def _op_algun_hecho(self, nodo: Mapping[str, Any]) -> Juicio:
        presentes = tuple(n for n in nodo["algun_hecho"] if self.hechos.tiene(n))
        return Juicio(V, presentes) if presentes else Juicio(F)

    def _op_solicitud(self, nodo: Mapping[str, Any]) -> Juicio:
        nombre = nodo["solicitud"]
        return Juicio(V, (NOMBRE_SOLICITUD[nombre],)) if self.hechos.pedida(nombre) else Juicio(F)

    def _op_episodio(self, nodo: Mapping[str, Any]) -> Juicio:
        abiertos = self.hechos.episodios_abiertos(list(nodo["episodio"]))
        if not abiertos:
            return Juicio(F)
        return Juicio(V, tuple(f"EPISODIO_{e.tipo}_ABIERTO" for e in abiertos))

    def _op_contexto(self, nodo: Mapping[str, Any]) -> Juicio:
        """Fase y modalidad son hechos del contexto: su igualdad es binaria."""
        inst = self.hechos.instantanea
        nombre = nodo["contexto"]
        if nombre == "clima_calido":
            return Juicio(inst.clima_calido)
        actual = inst.fase if nombre == "fase" else inst.tipo_almacenamiento
        if nodo.get("definido"):
            return Juicio(V if actual is not None else F)
        valor = actual.value if actual is not None else None
        return Juicio(V if valor == nodo.get("igual") else F)

    def _op_definicion(self, nodo: Mapping[str, Any]) -> Juicio:
        nombre = nodo["definicion"]
        if nombre in self._evaluando:  # pragma: no cover — el cargador rechaza ciclos
            raise RuntimeError(f"ciclo al evaluar la definición {nombre}")
        self._evaluando.add(nombre)
        try:
            definicion = self.base.definiciones[nombre]
            juicio = self.evaluar(definicion)
        finally:
            self._evaluando.discard(nombre)
        if juicio.valor is V:
            return Juicio(V, (definicion.get("descripcion") or nombre,))
        return Juicio(juicio.valor)

    def _op_calculo(self, nodo: Mapping[str, Any]) -> Juicio:
        valor = self.calculadora.valor(nodo["calculo"])
        if "op" not in nodo:
            if isinstance(valor, Tri):
                return Juicio(valor)
            if isinstance(valor, bool):
                return Juicio(V if valor else F)
            return Juicio(D if valor is None else V)
        izquierda = _como_decimal(valor)
        derecha = self.valor(nodo["valor"])
        if izquierda is None or derecha is None:
            return Juicio(D)
        return Juicio(_comparar(izquierda, nodo["op"], derecha))

    def _op_nulo(self, nodo: Mapping[str, Any]) -> Juicio:
        return Juicio(V if self.calculadora.valor(nodo["nulo"]) is None else F)

    def _op_hay_invalidos(self, nodo: Mapping[str, Any]) -> Juicio:
        return Juicio(V if self.hechos.invalidos() else F)

    def _op_inconsistencia(self, nodo: Mapping[str, Any]) -> Juicio:
        """Contradicciones detectadas fuera del motor, al consolidar el historial."""
        nombre = nodo["inconsistencia"]
        registradas = self.hechos.instantanea.datos_inconsistentes
        coincidentes = tuple(registradas) if nombre == "*" else tuple(r for r in registradas if r == nombre)
        return Juicio(V, coincidentes) if coincidentes else Juicio(F)

    def _op_pendientes(self, nodo: Mapping[str, Any]) -> Juicio:
        return Juicio(V if self.hechos.pendientes else F)

    def _estado(self, nodo: Mapping[str, Any], valor: Tri) -> str:
        """Los envoltorios aplanan NO_APLICA y DESCONOCIDO a FALSO; aquí se recupera."""
        interior = nodo
        for envoltura in ("es_verdadero", "no_falso"):
            if envoltura in nodo:
                interior = nodo[envoltura]
                valor = self.evaluar(interior).valor
        if valor is NA:
            return "no aplica"
        if valor is D:
            return "desconocido"
        return "no se cumple"

    @staticmethod
    def _sin_descripcion(nodo: Mapping[str, Any]) -> Mapping[str, Any]:
        return {k: v for k, v in nodo.items() if k != "descripcion"}

    # --- Diagnóstico: qué le faltó a una condición para ser VERDADERO ------------

    def fallidas(self, nodo: Mapping[str, Any]) -> list[str]:
        """Descripciones de las partes que impidieron que la condición fuera VERDADERO.

        Es la base del "¿por qué no?": recorre conjunciones, implicaciones y
        definiciones hasta encontrar las condiciones descritas que fallaron.
        """
        if self.evaluar(nodo).valor is V:
            return []
        if "todos" in nodo:
            salida: list[str] = []
            for hijo in nodo["todos"]:
                juicio = self.evaluar(hijo)
                if juicio.valor in (V, NA):
                    continue
                descripcion = self.descripcion(hijo)
                if descripcion:
                    estado = self._estado(hijo, juicio.valor)
                    detalle = [d for d in self.fallidas(self._sin_descripcion(hijo)) if d != descripcion]
                    texto = f"{descripcion} ({estado})"
                    if detalle and estado != "no aplica":
                        texto += ": " + "; ".join(detalle)
                    salida.append(texto)
                else:
                    salida.extend(self.fallidas(hijo))
            return salida
        if "implica" in nodo:
            return self.fallidas(nodo["implica"]["entonces"])
        if "guarda" in nodo:
            campo = nodo["guarda"]["campo"]
            if not self.hechos.dato(campo).utilizable:
                return [f"falta {campo}"]
            return self.fallidas(nodo["guarda"]["entonces"])
        if "definicion" in nodo:
            return self.fallidas(self._sin_descripcion(self.base.definiciones[nodo["definicion"]]))
        for envoltura in ("es_verdadero", "no_falso"):
            if envoltura in nodo:
                return self.fallidas(nodo[envoltura])
        descripcion = self.descripcion(nodo)
        return [descripcion] if descripcion else []
