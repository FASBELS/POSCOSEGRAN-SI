"""Tabla de tiempo de referencia y su selección determinista, sección 6.1.

Los guiones de la tabla no son cero ni vida infinita: son celdas sin duración
publicada. La selección avanza a una celda numérica más exigente en lugar de
inventar un valor, y si no hay fila o columna elegible el cálculo queda
NO_DISPONIBLE. No se extrapola ni se recorta una lectura fuera de rango.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

ID_TABLA = "NDSU_CEREALES_S08"

# Las temperaturas exactas son las conversiones de 50, 60, 70 y 80 °F.
COLUMNAS_F: tuple[Decimal, ...] = (Decimal("50"), Decimal("60"), Decimal("70"), Decimal("80"))
COLUMNAS_C: tuple[Decimal, ...] = (
    Decimal("10"),
    Decimal("15.56"),
    Decimal("21.11"),
    Decimal("26.67"),
)

# None representa una celda sin duración numérica publicada.
FILAS: tuple[tuple[Decimal, tuple[int | None, ...]], ...] = (
    (Decimal("14"), (None, None, 200, 140)),
    (Decimal("15"), (None, 240, 125, 70)),
    (Decimal("16"), (230, 120, 70, 40)),
    (Decimal("17"), (130, 75, 45, 20)),
    (Decimal("18"), (90, 50, 30, 15)),
    (Decimal("19"), (70, 35, 20, 10)),
    (Decimal("20"), (50, 25, 14, 7)),
)

HUMEDAD_MINIMA_TABLA = FILAS[0][0]
HUMEDAD_MAXIMA_TABLA = FILAS[-1][0]


@dataclass(frozen=True, slots=True)
class Celda:
    id_tabla: str
    humedad_fila: Decimal
    temperatura_columna_f: Decimal
    temperatura_columna_c: Decimal
    dias_referencia: int
    sustituida: bool
    motivo: str


def seleccionar(humedad: Decimal, temperatura_c: Decimal) -> Celda | None:
    """Devuelve la celda aplicable o None si el cálculo no está disponible.

    1. La menor fila cuya humedad sea mayor o igual que la observada; por debajo
       de 14 % se usa la fila de 14 %.
    2. En esa fila, la columna numérica de menor temperatura que sea mayor o
       igual que la observada, avanzando si la celda no tiene número.
    3. Sin fila o columna elegible, NO_DISPONIBLE.
    """
    if humedad > HUMEDAD_MAXIMA_TABLA:
        return None
    if temperatura_c > COLUMNAS_C[-1]:
        return None

    humedad_efectiva = max(humedad, HUMEDAD_MINIMA_TABLA)
    fila = next((f for f in FILAS if f[0] >= humedad_efectiva), None)
    if fila is None:
        return None

    humedad_fila, valores = fila
    motivos: list[str] = []
    if humedad < HUMEDAD_MINIMA_TABLA:
        motivos.append(f"humedad {humedad} % por debajo de la tabla; se usa la fila de 14 %")
    elif humedad_fila != humedad:
        motivos.append(f"humedad {humedad} % elevada a la fila de {humedad_fila} %")

    indice_base = next(
        (i for i, columna in enumerate(COLUMNAS_C) if columna >= temperatura_c), None
    )
    if indice_base is None:
        return None

    for indice in range(indice_base, len(COLUMNAS_C)):
        dias = valores[indice]
        if dias is None:
            continue
        if indice != indice_base:
            motivos.append(
                f"columna de {COLUMNAS_C[indice_base]} °C sin duración publicada; "
                f"se avanza a {COLUMNAS_C[indice]} °C"
            )
        elif COLUMNAS_C[indice] != temperatura_c:
            motivos.append(f"temperatura {temperatura_c} °C elevada a {COLUMNAS_C[indice]} °C")
        return Celda(
            id_tabla=ID_TABLA,
            humedad_fila=humedad_fila,
            temperatura_columna_f=COLUMNAS_F[indice],
            temperatura_columna_c=COLUMNAS_C[indice],
            dias_referencia=dias,
            sustituida=bool(motivos),
            motivo="; ".join(motivos) if motivos else "celda directa de la tabla",
        )
    return None
