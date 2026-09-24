"""Base de conocimiento: carga, validación y consulta.

La base se compone de dos documentos versionados juntos:

    operativa   knowledge/base_conocimiento.yaml — lo que el motor ejecuta.
    documental  knowledge/catalogo.yaml — el texto de cada regla transcrito
                del documento 2.0, que se muestra al usuario.

El cargador exige que ambos describan exactamente las mismas reglas, de modo
que la pantalla de conocimiento nunca muestre una regla distinta de la que se
aplicó.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from functools import cached_property
from pathlib import Path
from typing import Any

import yaml

SOLICITUDES = ("CUARENTENA", "SUSPENSION", "CORRECCION", "MONITOREO")
NOMBRE_SOLICITUD = {
    "CUARENTENA": "CUARENTENA_SOLICITADA",
    "SUSPENSION": "SUSPENSION_SOLICITADA",
    "CORRECCION": "CORRECCION_SOLICITADA",
    "MONITOREO": "MONITOREO_SOLICITADO",
}
DECISIONES = (
    "CUARENTENA",
    "BLOQUEAR_INGRESO",
    "RETIRAR_LOTE",
    "CORREGIR_Y_REEVALUAR",
    "SIN_CONCLUSION_AUTOMATICA",
    "AUTORIZAR_CON_MONITOREO",
    "AUTORIZAR_ALMACENAMIENTO",
)
FUNDAMENTOS = ("PUBLICADO", "TRANSFERIDO", "POLITICA_PROTOTIPO", "MIXTO")
OPERADORES_COMPARACION = ("GT", "GTE", "LT", "LTE", "EQ", "NEQ")

# Operadores del lenguaje de condiciones y los campos que admite cada uno.
OPERADORES: dict[str, frozenset[str]] = {
    "todos": frozenset(),
    "alguno": frozenset(),
    "negar": frozenset(),
    "implica": frozenset(),
    "guarda": frozenset(),
    "dato": frozenset({"op", "valor", "en"}),
    "aportado": frozenset(),
    "presentes": frozenset(),
    "conocidos": frozenset(),
    "hecho": frozenset(),
    "algun_hecho": frozenset(),
    "definicion": frozenset(),
    "solicitud": frozenset(),
    "episodio": frozenset(),
    "contexto": frozenset({"igual", "definido"}),
    "calculo": frozenset({"op", "valor"}),
    "nulo": frozenset(),
    "es_verdadero": frozenset(),
    "es_falso": frozenset(),
    "es_desconocido": frozenset(),
    "no_falso": frozenset(),
    "vigente_meses": frozenset({"meses"}),
    "vencido_dias": frozenset({"dias"}),
    "horas_entre": frozenset({"op", "valor"}),
    "diferencia": frozenset({"op", "valor"}),
    "hay_invalidos": frozenset(),
    "inconsistencia": frozenset(),
    "pendientes": frozenset(),
    "constante": frozenset(),
    "siempre": frozenset(),
}

# Operadores que invierten la polaridad de lo que contienen. Un hecho leído bajo
# uno de ellos se consume *negado*: la producción concluye porque el hecho no está.
# El motor no retracta disparos, así que una negación solo es fiable si el hecho
# ya alcanzó su valor definitivo; de ahí la estratificación por etapas de _grafo().
OPERADORES_NEGATIVOS = frozenset({"negar", "es_falso", "es_desconocido"})

CALCULOS_DISPONIBLES = frozenset(
    {
        "vida_consumida",
        "vida_minima_documentada",
        "vida_proyectada",
        "tiempo_referencia_actual",
        "plazo_compatible",
        "estimacion_hermetica",
        "dias_previstos_restantes",
        "dias_almacenados",
        "fecha_salida_prevista",
        "plan_vigente",
        "plan_intervalo_dias",
        "plan_salida_definida",
        "dictamen_cubre",
    }
)
DATOS_CALCULADOS = frozenset({"temperatura_grano_aplicable"})
CONTEXTOS = frozenset({"fase", "tipo_almacenamiento", "clima_calido"})


class BaseInvalida(ValueError):
    """La base no se puede usar: el motor se niega a evaluar con ella."""

    def __init__(self, errores: list[str]) -> None:
        super().__init__("; ".join(errores))
        self.errores = errores


@dataclass(frozen=True, slots=True)
class Parametro:
    nombre: str
    valor: Decimal
    unidad: str
    fundamento: str
    fuentes: tuple[str, ...]
    descripcion: str


@dataclass(frozen=True, slots=True)
class Consecuente:
    hallazgo: str | None
    solicitudes: tuple[str, ...]
    mensaje: str | None
    accion: Mapping[str, str] | None


@dataclass(frozen=True, slots=True)
class ReglaProduccion:
    """Una regla SI–ENTONCES. `regla` es el código del catálogo al que pertenece."""

    id: str
    regla: str
    etapa: str
    si: Mapping[str, Any]
    entonces: Consecuente
    aplica_si: Mapping[str, Any] | None = None
    evidencias: tuple[Mapping[str, Any], ...] = ()
    registrar_motivo: bool = True


@dataclass(frozen=True, slots=True)
class Rama:
    rama: str
    decision: str
    si: Mapping[str, Any]
    mensaje: str | None = None


@dataclass(frozen=True, slots=True)
class Dependencias:
    """Lo que una producción consume y produce, y su lugar en la agenda.

    `posicion` es el índice de la etapa; las ramas de resolución usan una etapa
    virtual posterior a todas, porque se evalúan una vez alcanzado el punto fijo.
    """

    id: str
    etapa: str
    posicion: int
    hechos: frozenset[str]
    hechos_negados: frozenset[str]
    solicitudes: frozenset[str]
    solicitudes_negadas: frozenset[str]
    hallazgo: str | None
    produce_solicitudes: frozenset[str]


@dataclass(frozen=True, slots=True)
class Celda:
    id_tabla: str
    humedad_fila: Decimal
    temperatura_columna_f: Decimal
    temperatura_columna_c: Decimal
    dias_referencia: int
    sustituida: bool
    motivo: str


@dataclass(frozen=True, slots=True)
class TablaTiempo:
    """Tabla de tiempo de referencia con la selección determinista de la sección 6.1."""

    id: str
    columnas_f: tuple[Decimal, ...]
    columnas_c: tuple[Decimal, ...]
    filas: tuple[tuple[Decimal, tuple[int | None, ...]], ...]

    def seleccionar(self, humedad: Decimal, temperatura_c: Decimal) -> Celda | None:
        """La menor fila y columna mayores o iguales; sin celda elegible, None.

        Una celda sin duración publicada hace avanzar a una columna más cálida.
        Fuera de la tabla no se extrapola ni se recorta la lectura.
        """
        humedad_minima, humedad_maxima = self.filas[0][0], self.filas[-1][0]
        if humedad > humedad_maxima or temperatura_c > self.columnas_c[-1]:
            return None

        efectiva = max(humedad, humedad_minima)
        fila = next((f for f in self.filas if f[0] >= efectiva), None)
        if fila is None:
            return None
        humedad_fila, valores = fila

        motivos: list[str] = []
        if humedad < humedad_minima:
            motivos.append(
                f"humedad {humedad} % por debajo de la tabla; se usa la fila de {humedad_minima} %"
            )
        elif humedad_fila != humedad:
            motivos.append(f"humedad {humedad} % elevada a la fila de {humedad_fila} %")

        base = next((i for i, c in enumerate(self.columnas_c) if c >= temperatura_c), None)
        if base is None:
            return None
        for indice in range(base, len(self.columnas_c)):
            dias = valores[indice]
            if dias is None:
                continue
            if indice != base:
                motivos.append(
                    f"columna de {self.columnas_c[base]} °C sin duración publicada; "
                    f"se avanza a {self.columnas_c[indice]} °C"
                )
            elif self.columnas_c[indice] != temperatura_c:
                motivos.append(
                    f"temperatura {temperatura_c} °C elevada a {self.columnas_c[indice]} °C"
                )
            return Celda(
                id_tabla=self.id,
                humedad_fila=humedad_fila,
                temperatura_columna_f=self.columnas_f[indice],
                temperatura_columna_c=self.columnas_c[indice],
                dias_referencia=dias,
                sustituida=bool(motivos),
                motivo="; ".join(motivos) if motivos else "celda directa de la tabla",
            )
        return None


@dataclass(frozen=True)
class BaseConocimiento:
    version_base: str
    version_parametros: str
    parametros: Mapping[str, Parametro]
    definiciones: Mapping[str, Mapping[str, Any]]
    reglas: tuple[ReglaProduccion, ...]
    etapas: tuple[str, ...]
    datos_exigibles: tuple[Mapping[str, Any], ...]
    resolucion: tuple[Rama, ...]
    decisiones_autorizadas: frozenset[str]
    tabla_tiempo: TablaTiempo
    calculos: Mapping[str, Mapping[str, Any]]
    fundamentos: Mapping[str, tuple[tuple[str, ...], str]]
    localizadores: Mapping[str, str]
    documental: Mapping[str, Any]
    dependencias: tuple[Dependencias, ...]
    contenido: Mapping[str, Any] = field(repr=False)

    # --- Consulta -----------------------------------------------------------

    def parametro(self, nombre: str) -> Decimal:
        return self.parametros[nombre].valor

    def fuentes_de(self, regla: str) -> tuple[tuple[str, str | None], ...]:
        codigos, _ = self.fundamentos.get(regla, ((), "POLITICA_PROTOTIPO"))
        return tuple((codigo, self.localizadores.get(codigo)) for codigo in codigos)

    def fundamento_de(self, regla: str) -> str:
        return self.fundamentos.get(regla, ((), "POLITICA_PROTOTIPO"))[1]

    @cached_property
    def hash(self) -> str:
        """Huella estable del contenido completo: identifica la versión."""
        normalizado = json.dumps(self.contenido, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(normalizado.encode("utf-8")).hexdigest()

    @cached_property
    def uso_de_campos(self) -> dict[str, tuple[str, ...]]:
        """Para cada campo, las reglas del catálogo cuya decisión depende de él.

        Se sigue la dependencia a través de las definiciones, de modo que un campo
        usado en `medicion_confirmada` aparece en R01, R02, R03 y R05. Es lo que
        permite responder "¿por qué se pregunta este dato?".
        """
        por_definicion: dict[str, set[str]] = {}

        def campos_de(nodo: Any, visitadas: frozenset[str]) -> set[str]:
            encontrados: set[str] = set()
            for clave, valor in _recorrer(nodo):
                if clave in {"dato", "aportado", "vigente_meses", "vencido_dias"} and isinstance(valor, str):
                    encontrados.add(valor)
                elif clave in {"presentes", "conocidos", "horas_entre", "diferencia"} and isinstance(valor, list):
                    encontrados.update(v for v in valor if isinstance(v, str))
                elif clave == "definicion" and isinstance(valor, str) and valor not in visitadas:
                    if valor not in por_definicion:
                        por_definicion[valor] = campos_de(
                            self.definiciones.get(valor, {}), visitadas | {valor}
                        )
                    encontrados |= por_definicion[valor]
            return encontrados

        uso: dict[str, set[str]] = {}
        for regla in self.reglas:
            if not regla.regla.startswith("R"):
                continue
            nodos = [regla.si, regla.aplica_si or {}]
            for campo in set().union(*(campos_de(n, frozenset()) for n in nodos)):
                uso.setdefault(campo.replace("_aplicable", ""), set()).add(regla.regla)
        for rama in self.resolucion:
            for campo in campos_de(rama.si, frozenset()):
                uso.setdefault(campo.replace("_aplicable", ""), set()).add(rama.rama)
        return {campo: tuple(sorted(reglas)) for campo, reglas in sorted(uso.items())}


def _recorrer(nodo: Any) -> Iterator[tuple[str, Any]]:
    if isinstance(nodo, Mapping):
        for clave, valor in nodo.items():
            yield clave, valor
            yield from _recorrer(valor)
    elif isinstance(nodo, list):
        for elemento in nodo:
            yield from _recorrer(elemento)


# --- Validación -------------------------------------------------------------------


def _validar_nodo(
    nodo: Any, ruta: str, definiciones: Mapping[str, Any], parametros: Mapping[str, Any],
    errores: list[str],
) -> None:
    if not isinstance(nodo, Mapping):
        errores.append(f"{ruta}: se esperaba un nodo de condición")
        return
    operadores = [clave for clave in nodo if clave in OPERADORES]
    if len(operadores) != 1:
        errores.append(f"{ruta}: debe tener exactamente un operador, tiene {operadores or 'ninguno'}")
        return
    operador = operadores[0]
    admitidas = OPERADORES[operador] | {operador, "descripcion"}
    sobrantes = set(nodo) - admitidas
    if sobrantes:
        errores.append(f"{ruta}: claves no reconocidas para '{operador}': {sorted(sobrantes)}")
    valor = nodo[operador]

    if operador in {"todos", "alguno"}:
        if not isinstance(valor, list) or not valor:
            errores.append(f"{ruta}.{operador}: debe ser una lista no vacía")
            return
        for i, hijo in enumerate(valor):
            _validar_nodo(hijo, f"{ruta}.{operador}[{i}]", definiciones, parametros, errores)
    elif operador in {"negar", "es_verdadero", "es_falso", "es_desconocido", "no_falso"}:
        _validar_nodo(valor, f"{ruta}.{operador}", definiciones, parametros, errores)
    elif operador == "implica":
        if not isinstance(valor, Mapping) or set(valor) != {"si", "entonces"}:
            errores.append(f"{ruta}.implica: requiere exactamente 'si' y 'entonces'")
            return
        _validar_nodo(valor["si"], f"{ruta}.implica.si", definiciones, parametros, errores)
        _validar_nodo(valor["entonces"], f"{ruta}.implica.entonces", definiciones, parametros, errores)
    elif operador == "guarda":
        if not isinstance(valor, Mapping) or set(valor) != {"campo", "entonces"}:
            errores.append(f"{ruta}.guarda: requiere exactamente 'campo' y 'entonces'")
            return
        _validar_nodo(valor["entonces"], f"{ruta}.guarda.entonces", definiciones, parametros, errores)
    elif operador == "definicion":
        if valor not in definiciones:
            errores.append(f"{ruta}: definición desconocida '{valor}'")
    elif operador == "solicitud":
        if valor not in SOLICITUDES:
            errores.append(f"{ruta}: solicitud desconocida '{valor}'")
    elif operador == "contexto":
        if valor not in CONTEXTOS:
            errores.append(f"{ruta}: contexto desconocido '{valor}'")
    elif operador in {"calculo", "nulo"}:
        if valor not in CALCULOS_DISPONIBLES:
            errores.append(f"{ruta}: cálculo desconocido '{valor}'")
    elif operador == "constante":
        if valor not in {"VERDADERO", "FALSO", "DESCONOCIDO"}:
            errores.append(f"{ruta}: constante no admitida '{valor}'")

    if "op" in nodo:
        if nodo["op"] not in OPERADORES_COMPARACION:
            errores.append(f"{ruta}: operador de comparación desconocido '{nodo['op']}'")
        if "valor" not in nodo:
            errores.append(f"{ruta}: una comparación necesita 'valor'")
    for clave in ("valor", "dias", "meses"):
        if clave in nodo:
            _validar_valor(nodo[clave], f"{ruta}.{clave}", definiciones, parametros, errores)


def _validar_valor(
    valor: Any, ruta: str, definiciones: Mapping[str, Any], parametros: Mapping[str, Any],
    errores: list[str],
) -> None:
    if isinstance(valor, Mapping):
        if "param" in valor:
            if valor["param"] not in parametros:
                errores.append(f"{ruta}: parámetro desconocido '{valor['param']}'")
        elif "elegir" in valor:
            eleccion = valor["elegir"]
            if not isinstance(eleccion, Mapping) or set(eleccion) != {"si", "entonces", "sino"}:
                errores.append(f"{ruta}.elegir: requiere 'si', 'entonces' y 'sino'")
                return
            _validar_nodo(eleccion["si"], f"{ruta}.elegir.si", definiciones, parametros, errores)
            _validar_valor(eleccion["entonces"], f"{ruta}.elegir.entonces", definiciones, parametros, errores)
            _validar_valor(eleccion["sino"], f"{ruta}.elegir.sino", definiciones, parametros, errores)
        elif "dato" not in valor:
            errores.append(f"{ruta}: valor no reconocido {dict(valor)}")


def _ciclos(definiciones: Mapping[str, Any]) -> list[str]:
    """Una definición que dependa de sí misma no termina de evaluarse."""
    dependencias = {
        nombre: {v for k, v in _recorrer(nodo) if k == "definicion" and isinstance(v, str)}
        for nombre, nodo in definiciones.items()
    }
    errores: list[str] = []
    estado: dict[str, int] = {}

    def visitar(nombre: str, camino: list[str]) -> None:
        if estado.get(nombre) == 1:
            errores.append("ciclo entre definiciones: " + " → ".join([*camino, nombre]))
            return
        if estado.get(nombre) == 2:
            return
        estado[nombre] = 1
        for siguiente in dependencias.get(nombre, ()):
            visitar(siguiente, [*camino, nombre])
        estado[nombre] = 2

    for nombre in dependencias:
        visitar(nombre, [])
    return errores


def _consumos(
    nodo: Any, definiciones: Mapping[str, Any]
) -> tuple[frozenset[str], frozenset[str], frozenset[str], frozenset[str]]:
    """Hechos y solicitudes que consume una condición, separados por polaridad.

    Se recorre el árbol completo, entrando en las definiciones reutilizables. Un
    operador negativo invierte la polaridad de todo lo que contiene, y el
    antecedente de `implica` también es una posición negativa, porque
    `implica{si: A, entonces: B}` equivale a `alguno[negar A, B]`.
    """
    positivos: set[str] = set()
    negados: set[str] = set()
    solicitudes: set[str] = set()
    solicitudes_negadas: set[str] = set()

    def recorrer(nodo: Any, negativo: bool, visitadas: frozenset[str]) -> None:
        if isinstance(nodo, Mapping):
            for clave, valor in nodo.items():
                if clave in OPERADORES_NEGATIVOS:
                    recorrer(valor, not negativo, visitadas)
                    continue
                if clave == "implica" and isinstance(valor, Mapping):
                    recorrer(valor.get("si"), not negativo, visitadas)
                    recorrer(valor.get("entonces"), negativo, visitadas)
                    continue
                if clave in {"hecho", "algun_hecho"}:
                    nombres = [valor] if isinstance(valor, str) else valor
                    if isinstance(nombres, list):
                        destino = negados if negativo else positivos
                        destino.update(n for n in nombres if isinstance(n, str))
                elif clave == "solicitud" and isinstance(valor, str):
                    (solicitudes_negadas if negativo else solicitudes).add(valor)
                elif clave == "definicion" and isinstance(valor, str) and valor not in visitadas:
                    recorrer(definiciones.get(valor, {}), negativo, visitadas | {valor})
                if isinstance(valor, Mapping | list):
                    recorrer(valor, negativo, visitadas)
        elif isinstance(nodo, list):
            for hijo in nodo:
                recorrer(hijo, negativo, visitadas)

    recorrer(nodo, False, frozenset())
    return (
        frozenset(positivos),
        frozenset(negados),
        frozenset(solicitudes),
        frozenset(solicitudes_negadas),
    )


def _grafo(
    reglas: Sequence[ReglaProduccion],
    resolucion: Sequence[Rama],
    definiciones: Mapping[str, Any],
    etapas: Sequence[str],
) -> tuple[tuple[Dependencias, ...], list[str]]:
    """Grafo productor→consumidor de la base, con las reglas de orden seguro.

    El motor recorre las etapas en orden y no retracta lo ya afirmado, así que la
    corrección de una negación no puede depender de en qué línea del YAML esté
    escrita cada producción. Se exige que todo hecho negado se haya decidido en una
    etapa *estrictamente anterior*; con eso, reordenar el archivo no altera ninguna
    decisión y la propiedad queda comprobada en la carga, no confiada al autor.
    """
    posicion = {etapa: i for i, etapa in enumerate(etapas)}
    errores: list[str] = []

    grafo: list[Dependencias] = []
    for regla in reglas:
        if regla.etapa not in posicion:
            continue  # la etapa desconocida ya se reportó al construir la regla
        hechos, negados, solicitudes, sol_negadas = _consumos(regla.si, definiciones)
        if regla.aplica_si is not None:
            extra = _consumos(regla.aplica_si, definiciones)
            hechos |= extra[0]
            negados |= extra[1]
            solicitudes |= extra[2]
            sol_negadas |= extra[3]
        grafo.append(
            Dependencias(
                id=regla.id,
                etapa=regla.etapa,
                posicion=posicion[regla.etapa],
                hechos=hechos,
                hechos_negados=negados,
                solicitudes=solicitudes,
                solicitudes_negadas=sol_negadas,
                hallazgo=regla.entonces.hallazgo,
                produce_solicitudes=frozenset(regla.entonces.solicitudes),
            )
        )
    for rama in resolucion:
        hechos, negados, solicitudes, sol_negadas = _consumos(rama.si, definiciones)
        grafo.append(
            Dependencias(
                id=rama.rama,
                etapa="resolucion",
                posicion=len(etapas),  # después del punto fijo de todas las etapas
                hechos=hechos,
                hechos_negados=negados,
                solicitudes=solicitudes,
                solicitudes_negadas=sol_negadas,
                hallazgo=None,
                produce_solicitudes=frozenset(),
            )
        )

    # Un hecho con dos productores hace ambigua la etapa en que queda decidido y
    # permitiría que una negación válida hoy dejara de serlo al añadir el segundo.
    productor: dict[str, Dependencias] = {}
    for nodo in grafo:
        if nodo.hallazgo is None:
            continue
        previo = productor.get(nodo.hallazgo)
        if previo is not None:
            errores.append(
                f"dependencias: el hallazgo '{nodo.hallazgo}' lo producen '{previo.id}' y "
                f"'{nodo.id}'; cada hecho debe tener un único productor (use 'alguno' dentro "
                f"de una sola producción)"
            )
            continue
        productor[nodo.hallazgo] = nodo
    productores_solicitud: dict[str, list[Dependencias]] = {}
    for nodo in grafo:
        for solicitud in nodo.produce_solicitudes:
            productores_solicitud.setdefault(solicitud, []).append(nodo)

    for nodo in grafo:
        for hecho in sorted(nodo.hechos | nodo.hechos_negados):
            if hecho not in productor:
                errores.append(
                    f"dependencias: '{nodo.id}' consume el hecho '{hecho}', que ninguna "
                    f"producción afirma"
                )
        for hecho in sorted(nodo.hechos):
            origen = productor.get(hecho)
            if origen is not None and origen.posicion > nodo.posicion:
                errores.append(
                    f"dependencias: '{nodo.id}' (etapa {nodo.etapa}) exige el hecho '{hecho}', "
                    f"que solo se afirma en la etapa posterior '{origen.etapa}' ('{origen.id}'): "
                    f"nunca se dispararía"
                )
        for hecho in sorted(nodo.hechos_negados):
            origen = productor.get(hecho)
            if origen is None or origen.posicion < nodo.posicion:
                continue
            relacion = (
                f"la misma etapa '{origen.etapa}'"
                if origen.posicion == nodo.posicion
                else f"la etapa posterior '{origen.etapa}'"
            )
            errores.append(
                f"dependencias: '{nodo.id}' (etapa {nodo.etapa}) niega el hecho '{hecho}', que "
                f"'{origen.id}' afirma en {relacion}: el resultado dependería del orden de "
                f"escritura. Mueva la producción que niega a una etapa posterior a su productor"
            )
        for solicitud in sorted(nodo.solicitudes_negadas):
            tardios = [
                origen
                for origen in productores_solicitud.get(solicitud, [])
                if origen.posicion >= nodo.posicion
            ]
            if tardios:
                errores.append(
                    f"dependencias: '{nodo.id}' (etapa {nodo.etapa}) niega la solicitud "
                    f"'{solicitud}', que {', '.join(sorted(o.id for o in tardios))} puede pedir "
                    f"en esa etapa o después: el resultado dependería del orden de escritura"
                )

    return tuple(grafo), errores


def construir(operativa: Mapping[str, Any], documental: Mapping[str, Any]) -> BaseConocimiento:
    """Valida y construye la base. Cualquier error invalida la base entera."""
    errores: list[str] = []

    for clave in (
        "version_base", "version_parametros", "parametros", "definiciones", "etapas",
        "reglas", "datos_exigibles", "resolucion", "decisiones_autorizadas", "tablas",
        "fundamentos", "localizadores",
    ):
        if clave not in operativa:
            errores.append(f"falta la sección '{clave}'")
    if errores:
        raise BaseInvalida(errores)

    parametros: dict[str, Parametro] = {}
    for nombre, datos in operativa["parametros"].items():
        try:
            parametros[nombre] = Parametro(
                nombre=nombre,
                valor=Decimal(str(datos["valor"])),
                unidad=str(datos.get("unidad", "")),
                fundamento=str(datos.get("fundamento", "POLITICA_PROTOTIPO")),
                fuentes=tuple(datos.get("fuentes", ())),
                descripcion=str(datos.get("descripcion", "")),
            )
        except (KeyError, ArithmeticError, TypeError, ValueError):
            errores.append(f"parámetro '{nombre}': valor numérico ausente o inválido")
            continue
        if parametros[nombre].fundamento not in FUNDAMENTOS:
            errores.append(f"parámetro '{nombre}': fundamento desconocido")

    for i, restriccion in enumerate(operativa.get("restricciones", [])):
        motivo = restriccion.get("motivo", "restricción de integridad")
        if "menor" in restriccion:
            a, b = restriccion["menor"], restriccion["que"]
            if a not in parametros or b not in parametros:
                errores.append(f"restricciones[{i}]: parámetro desconocido")
                continue
            va, vb = parametros[a].valor, parametros[b].valor
            if va > vb or (va == vb and not restriccion.get("igual")):
                simbolo = "<=" if restriccion.get("igual") else "<"
                errores.append(f"restricción incumplida: {a} ({va}) {simbolo} {b} ({vb}) — {motivo}")
        elif "entre" in restriccion:
            nombre = restriccion["entre"]
            if nombre not in parametros:
                errores.append(f"restricciones[{i}]: parámetro desconocido")
                continue
            valor = parametros[nombre].valor
            if not Decimal(str(restriccion["minimo"])) <= valor <= Decimal(str(restriccion["maximo"])):
                errores.append(
                    f"restricción incumplida: {nombre} ({valor}) fuera de "
                    f"[{restriccion['minimo']}, {restriccion['maximo']}] — {motivo}"
                )
    for nombre, parametro in parametros.items():
        if parametro.valor < 0:
            errores.append(f"parámetro '{nombre}': no admite valores negativos")

    definiciones = dict(operativa["definiciones"])
    for nombre, nodo in definiciones.items():
        _validar_nodo(nodo, f"definicion.{nombre}", definiciones, parametros, errores)
    errores.extend(_ciclos(definiciones))

    etapas = tuple(operativa["etapas"])
    reglas: list[ReglaProduccion] = []
    identificadores: set[str] = set()
    for i, datos in enumerate(operativa["reglas"]):
        ident = datos.get("id")
        ruta = f"reglas[{i}]({ident})"
        if not ident or ident in identificadores:
            errores.append(f"{ruta}: identificador ausente o repetido")
            continue
        identificadores.add(ident)
        etapa = datos.get("etapa", "encadenamiento")
        if etapa not in etapas:
            errores.append(f"{ruta}: etapa desconocida '{etapa}'")
        if "si" not in datos or "entonces" not in datos:
            errores.append(f"{ruta}: requiere 'si' y 'entonces'")
            continue
        _validar_nodo(datos["si"], f"{ruta}.si", definiciones, parametros, errores)
        if datos.get("aplica_si") is not None:
            _validar_nodo(datos["aplica_si"], f"{ruta}.aplica_si", definiciones, parametros, errores)
        entonces = datos["entonces"]
        solicitudes = tuple(entonces.get("solicitudes", ()))
        for solicitud in solicitudes:
            if solicitud not in SOLICITUDES:
                errores.append(f"{ruta}: solicitud desconocida '{solicitud}'")
        registrar = bool(datos.get("registrar_motivo", True))
        if registrar and not entonces.get("hallazgo"):
            errores.append(f"{ruta}: una regla que registra motivo necesita 'hallazgo'")
        if registrar and not entonces.get("mensaje"):
            errores.append(f"{ruta}: una regla que registra motivo necesita 'mensaje'")
        if not entonces.get("hallazgo") and not solicitudes:
            errores.append(f"{ruta}: el consecuente no produce ningún hecho ni solicitud")
        for j, prueba in enumerate(datos.get("evidencias", ())):
            if "dato" not in prueba:
                errores.append(f"{ruta}.evidencias[{j}]: requiere 'dato'")
            elif "valor" in prueba:
                _validar_valor(prueba["valor"], f"{ruta}.evidencias[{j}].valor", definiciones, parametros, errores)
        reglas.append(
            ReglaProduccion(
                id=ident,
                regla=datos.get("regla", ident),
                etapa=etapa,
                si=datos["si"],
                aplica_si=datos.get("aplica_si"),
                entonces=Consecuente(
                    hallazgo=entonces.get("hallazgo"),
                    solicitudes=solicitudes,
                    mensaje=entonces.get("mensaje"),
                    accion=entonces.get("accion"),
                ),
                evidencias=tuple(datos.get("evidencias", ())),
                registrar_motivo=registrar,
            )
        )

    for i, exigible in enumerate(operativa["datos_exigibles"]):
        condicion = exigible.get("cuando_desconocido") or exigible.get("cuando")
        if condicion is None:
            errores.append(f"datos_exigibles[{i}]: requiere 'cuando' o 'cuando_desconocido'")
            continue
        _validar_nodo(condicion, f"datos_exigibles[{i}]", definiciones, parametros, errores)
        if not ({"campos", "pendiente", "pendientes_del_calculo"} & set(exigible)):
            errores.append(f"datos_exigibles[{i}]: no indica qué dato queda pendiente")

    resolucion: list[Rama] = []
    for i, datos in enumerate(operativa["resolucion"]):
        if datos.get("decision") not in DECISIONES:
            errores.append(f"resolucion[{i}]: decisión desconocida '{datos.get('decision')}'")
        _validar_nodo(datos.get("si"), f"resolucion[{i}]", definiciones, parametros, errores)
        resolucion.append(
            Rama(rama=datos["rama"], decision=datos["decision"], si=datos["si"], mensaje=datos.get("mensaje"))
        )
    if resolucion and "siempre" not in resolucion[-1].si:
        errores.append("resolucion: la última rama debe aplicarse siempre, para que toda evaluación concluya")
    decididas = {rama.decision for rama in resolucion}
    faltan = sorted(set(DECISIONES) - decididas)
    if faltan:
        errores.append(f"resolucion: ninguna rama produce {faltan}")

    datos_tabla = operativa["tablas"].get("tiempo_referencia")
    tabla = None
    if not datos_tabla:
        errores.append("tablas: falta 'tiempo_referencia'")
    else:
        columnas_c = tuple(Decimal(str(c)) for c in datos_tabla["columnas_c"])
        columnas_f = tuple(Decimal(str(c)) for c in datos_tabla["columnas_f"])
        filas = tuple(
            (Decimal(str(f["humedad"])), tuple(f["dias"])) for f in datos_tabla["filas"]
        )
        if len(columnas_c) != len(columnas_f) or any(len(f[1]) != len(columnas_c) for f in filas):
            errores.append("tablas.tiempo_referencia: filas y columnas no coinciden")
        if list(columnas_c) != sorted(columnas_c) or [f[0] for f in filas] != sorted(f[0] for f in filas):
            errores.append("tablas.tiempo_referencia: filas y columnas deben estar ordenadas")
        tabla = TablaTiempo(
            id=str(datos_tabla["id"]), columnas_f=columnas_f, columnas_c=columnas_c, filas=filas
        )

    fundamentos: dict[str, tuple[tuple[str, ...], str]] = {}
    for regla, datos in operativa["fundamentos"].items():
        tipo = datos.get("tipo", "POLITICA_PROTOTIPO")
        if tipo not in FUNDAMENTOS:
            errores.append(f"fundamentos.{regla}: tipo desconocido '{tipo}'")
        fuentes = tuple(datos.get("fuentes", ()))
        if tipo in {"PUBLICADO", "TRANSFERIDO", "MIXTO"} and not fuentes:
            errores.append(f"fundamentos.{regla}: {tipo} exige al menos una fuente")
        fundamentos[regla] = (fuentes, tipo)

    # Coherencia con el documento: mismas reglas, mismas fuentes.
    codigos_documento = {r["id"] for r in documental.get("reglas", [])}
    codigos_operativos = {r.regla for r in reglas if r.regla.startswith("R") and "." not in r.regla}
    nucleo = {f"R{n:02d}" for n in range(1, 31)}
    faltan_nucleo_doc = sorted(nucleo - codigos_documento)
    if faltan_nucleo_doc:
        errores.append(f"catálogo documental: faltan las reglas base {faltan_nucleo_doc}")
    faltan_operativas = sorted((nucleo - {"R30"}) - codigos_operativos)
    if faltan_operativas:
        errores.append(f"la base operativa no implementa {faltan_operativas}")
    # Reglas adicionales (R31+): cada operativa debe tener ficha documental y viceversa.
    adicionales_operativas = codigos_operativos - nucleo
    adicionales_documento = codigos_documento - nucleo
    sin_ficha = sorted(adicionales_operativas - adicionales_documento)
    sin_operativa = sorted(adicionales_documento - adicionales_operativas)
    if sin_ficha:
        errores.append(f"reglas operativas sin ficha en el catálogo documental: {sin_ficha}")
    if sin_operativa:
        errores.append(f"fichas documentales sin regla operativa: {sin_operativa}")
    ramas_documento = [r["id"] for r in documental.get("ramas_r30", [])]
    ramas_operativas = [r.rama for r in resolucion]
    if ramas_documento != ramas_operativas:
        errores.append(
            f"las ramas R30 del documento {ramas_documento} no coinciden con las operativas "
            f"{ramas_operativas}"
        )
    # Orden seguro de dependencias: ninguna negación puede depender del orden del YAML.
    dependencias, errores_grafo = _grafo(reglas, resolucion, definiciones, etapas)
    errores.extend(errores_grafo)

    fuentes_documento = {f["id"] for f in documental.get("fuentes", [])}
    citadas = {f for fuentes, _ in fundamentos.values() for f in fuentes}
    citadas |= {f for p in parametros.values() for f in p.fuentes}
    if citadas - fuentes_documento:
        errores.append(f"fuentes citadas sin referencia documental: {sorted(citadas - fuentes_documento)}")

    if errores:
        raise BaseInvalida(errores)

    assert tabla is not None
    return BaseConocimiento(
        version_base=str(operativa["version_base"]),
        version_parametros=str(operativa["version_parametros"]),
        parametros=parametros,
        definiciones=definiciones,
        reglas=tuple(reglas),
        etapas=etapas,
        datos_exigibles=tuple(operativa["datos_exigibles"]),
        resolucion=tuple(resolucion),
        decisiones_autorizadas=frozenset(operativa["decisiones_autorizadas"]),
        tabla_tiempo=tabla,
        calculos=dict(operativa.get("calculos", {})),
        fundamentos=fundamentos,
        localizadores=dict(operativa["localizadores"]),
        documental=documental,
        dependencias=dependencias,
        contenido={"operativa": operativa, "documental": documental},
    )


def desde_contenido(contenido: Mapping[str, Any]) -> BaseConocimiento:
    return construir(contenido["operativa"], contenido["documental"])


def validar_sintaxis_regla(
    definicion: Mapping[str, Any],
    base: BaseConocimiento,
) -> list[str]:
    """Comprueba la sintaxis y la semántica de una regla aislada contra la base activa.

    Devuelve una lista de errores; lista vacía si la definición es correcta.
    No reconstruye la base: solo valida la estructura, los operadores,
    los parámetros referenciados y los consecuentes.
    """
    errores: list[str] = []
    ident = definicion.get("id")
    ruta = f"regla({ident or '?'})"

    if not ident:
        errores.append(f"{ruta}: identificador ausente")

    etapa = definicion.get("etapa", "encadenamiento")
    if etapa not in base.etapas:
        errores.append(f"{ruta}: etapa desconocida '{etapa}'")

    if "si" not in definicion:
        errores.append(f"{ruta}: falta la condición 'si'")
    else:
        _validar_nodo(
            definicion["si"], f"{ruta}.si",
            dict(base.definiciones), dict(base.parametros), errores,
        )

    if definicion.get("aplica_si") is not None:
        _validar_nodo(
            definicion["aplica_si"], f"{ruta}.aplica_si",
            dict(base.definiciones), dict(base.parametros), errores,
        )

    if "entonces" not in definicion:
        errores.append(f"{ruta}: falta el consecuente 'entonces'")
    else:
        entonces = definicion["entonces"]
        solicitudes = tuple(entonces.get("solicitudes", ()))
        for solicitud in solicitudes:
            if solicitud not in SOLICITUDES:
                errores.append(f"{ruta}: solicitud desconocida '{solicitud}'")
        registrar = bool(definicion.get("registrar_motivo", True))
        if registrar and not entonces.get("hallazgo"):
            errores.append(f"{ruta}: una regla que registra motivo necesita 'hallazgo'")
        if registrar and not entonces.get("mensaje"):
            errores.append(f"{ruta}: una regla que registra motivo necesita 'mensaje'")
        if not entonces.get("hallazgo") and not solicitudes:
            errores.append(f"{ruta}: el consecuente no produce ningún hecho ni solicitud")

    for j, prueba in enumerate(definicion.get("evidencias", ())):
        if "dato" not in prueba:
            errores.append(f"{ruta}.evidencias[{j}]: requiere 'dato'")
        elif "valor" in prueba:
            _validar_valor(
                prueba["valor"], f"{ruta}.evidencias[{j}].valor",
                dict(base.definiciones), dict(base.parametros), errores,
            )

    return errores

def ruta_por_defecto() -> Path:
    """Carpeta knowledge/ del repositorio, o la indicada en POSCOSEGRAN_KNOWLEDGE."""
    import os

    configurada = os.environ.get("POSCOSEGRAN_KNOWLEDGE")
    if configurada:
        return Path(configurada)
    for candidata in Path(__file__).resolve().parents:
        if (candidata / "knowledge" / "base_conocimiento.yaml").exists():
            return candidata / "knowledge"
    return Path("knowledge")


def leer_archivos(carpeta: Path | None = None) -> dict[str, Any]:
    carpeta = carpeta or ruta_por_defecto()
    operativa = yaml.safe_load((carpeta / "base_conocimiento.yaml").read_text(encoding="utf-8"))
    documental = yaml.safe_load((carpeta / "catalogo.yaml").read_text(encoding="utf-8"))
    return {"operativa": operativa, "documental": documental}


_cache: dict[str, BaseConocimiento] = {}


def cargar(carpeta: Path | None = None) -> BaseConocimiento:
    """Base de los archivos del repositorio. Se usa en pruebas y como semilla."""
    clave = str((carpeta or ruta_por_defecto()).resolve())
    if clave not in _cache:
        _cache[clave] = desde_contenido(leer_archivos(carpeta))
    return _cache[clave]
