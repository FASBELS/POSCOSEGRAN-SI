"""Fuentes por regla y naturaleza de su fundamento.

Transcrito de la base 2.0. Distingue lo publicado de lo transferido a chulpi y
de lo que es política del prototipo, porque presentar una decisión de diseño
como respaldo bibliográfico sería atribuir a la fuente algo que no dice.
"""

from __future__ import annotations

from typing import Final

# regla -> (fuentes, fundamento)
FUENTES_POR_REGLA: Final[dict[str, tuple[tuple[str, ...], str]]] = {
    "R01": (("S01",), "MIXTO"),
    "R02": (("S01", "S03"), "MIXTO"),
    "R03": (("S01", "S03"), "MIXTO"),
    "R04": (("S04",), "MIXTO"),
    "R05": (("S07",), "MIXTO"),
    "R06": (("S01", "S06"), "MIXTO"),
    "R07": (("S01", "S05"), "PUBLICADO"),
    "R08": (("S01", "S04"), "MIXTO"),
    "R09": (("S04",), "MIXTO"),
    "R10": (("S05",), "MIXTO"),
    "R11": (("S05",), "MIXTO"),
    "R12": (("S06", "S01", "S03"), "MIXTO"),
    "R13": (("S06",), "MIXTO"),
    "R14": (("S09",), "MIXTO"),
    "R15": (("S05",), "MIXTO"),
    "R16": (("S03",), "MIXTO"),
    "R17": (("S02", "S05"), "PUBLICADO"),
    "R18": (("S04",), "PUBLICADO"),
    "R19": (("S02", "S04"), "MIXTO"),
    "R20": (("S09", "S01"), "MIXTO"),
    "R21": (("S09",), "TRANSFERIDO"),
    "R22": (("S09",), "TRANSFERIDO"),
    "R23": (("S09",), "MIXTO"),
    "R24": (("S02",), "PUBLICADO"),
    "R25": (("S02",), "MIXTO"),
    "R26": (("S02",), "PUBLICADO"),
    "R27": (("S05", "S06"), "MIXTO"),
    "R28": (("S08",), "MIXTO"),
    "R29": (("S01", "S08"), "MIXTO"),
    "R30": (("S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09"), "MIXTO"),
    "R30.1": (("S02", "S04"), "MIXTO"),
    "R30.2": (("S01", "S08", "S09"), "MIXTO"),
    "R30.3": (("S01", "S08", "S09"), "MIXTO"),
    "R30.4": ((), "POLITICA_PROTOTIPO"),
    "R30.5": ((), "POLITICA_PROTOTIPO"),
    "R30.6": (("S01", "S03", "S08"), "MIXTO"),
    "R30.7": (("S03", "S06", "S08"), "MIXTO"),
    "R30.8": ((), "POLITICA_PROTOTIPO"),
    "R30.9": ((), "POLITICA_PROTOTIPO"),
    "VALIDACION": ((), "POLITICA_PROTOTIPO"),
    "SECCION_6": (("S08",), "MIXTO"),
    "SECCION_5": (("S05", "S06"), "MIXTO"),
}

LOCALIZADORES: Final[dict[str, str]] = {
    "S01": "pp. 30–31",
    "S02": "secciones 3.1–3.6",
    "S03": "capítulo de almacenamiento",
    "S04": "párrs. 37–39",
    "S05": "secciones 5.2.4.2–5.2.4.3",
    "S06": "E-265-W",
    "S07": "recomendaciones de medición",
    "S08": "tabla de tiempo permisible",
    "S09": "CXS 153-1985",
}


def fuentes(regla: str) -> tuple[tuple[str, str | None], ...]:
    codigos, _ = FUENTES_POR_REGLA.get(regla, ((), "POLITICA_PROTOTIPO"))
    return tuple((codigo, LOCALIZADORES.get(codigo)) for codigo in codigos)


def fundamento(regla: str) -> str:
    _, tipo = FUENTES_POR_REGLA.get(regla, ((), "POLITICA_PROTOTIPO"))
    return tipo
