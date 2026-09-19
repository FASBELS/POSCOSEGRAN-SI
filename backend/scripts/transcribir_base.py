"""Transcribe la base 2.0 en Markdown al catálogo YAML que carga el backend.

Lee las tablas de la sección 4 (R01–R30), de la 7.3 (R30.1–R30.9) y la lista de
fuentes de la sección 11. No interpreta ni resume: copia el texto de cada celda,
de modo que el catálogo que consulta la pantalla de conocimiento sea el mismo que
el documento revisado.

Uso: python scripts/transcribir_base.py knowledge/POSCOSEGRAN_..._actualizado.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

FILA_REGLA = re.compile(r"^\|\s*(?:\*\*)?(R\d{2})(?:\*\*)?\s*\|")
FILA_RAMA = re.compile(r"^\|\s*(R30\.\d)\s*\|")
FILA_FUENTE = re.compile(r"^-\s+\*\*(S\d{2})\.\*\*\s+(.+)$")
CITA_FUENTE = re.compile(r"\b(S\d{2})\b")

FUNDAMENTOS_TRANSFERIDOS = {"R21", "R22"}
FUNDAMENTOS_PUBLICADOS = {"R07", "R17", "R18", "R24", "R26"}


def celdas(linea: str) -> list[str]:
    partes = [parte.strip() for parte in linea.strip().strip("|").split("|")]
    return [re.sub(r"\s+", " ", parte) for parte in partes]


def fundamento_de(codigo: str, fuentes: list[str], texto: str) -> str:
    if not fuentes:
        return "POLITICA_PROTOTIPO"
    if codigo in FUNDAMENTOS_TRANSFERIDOS:
        return "TRANSFERIDO"
    if codigo in FUNDAMENTOS_PUBLICADOS and "Base de diseño" not in texto:
        return "PUBLICADO"
    return "MIXTO"


def escapar(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace('"', '\\"')


def bloque(valor: str, sangria: str = "      ") -> str:
    limpio = valor.replace("<br>", " ").strip()
    return f'"{escapar(limpio)}"'


def transcribir(ruta: Path) -> str:
    lineas = ruta.read_text(encoding="utf-8").replace("\r", "").splitlines()

    reglas: list[dict[str, object]] = []
    ramas: list[dict[str, object]] = []
    fuentes: list[tuple[str, str]] = []

    for linea in lineas:
        coincidencia = FILA_REGLA.match(linea)
        if coincidencia:
            partes = celdas(linea)
            if len(partes) < 5:
                continue
            codigo = coincidencia.group(1)
            citadas = sorted(set(CITA_FUENTE.findall(partes[4])))
            reglas.append(
                {
                    "id": codigo,
                    "antecedente": partes[1],
                    "consecuente": partes[2],
                    "accion": partes[3],
                    "fundamento_markdown": partes[4],
                    "fundamento": fundamento_de(codigo, citadas, partes[4]),
                    "fuentes": citadas,
                }
            )
            continue

        coincidencia = FILA_RAMA.match(linea)
        if coincidencia:
            partes = celdas(linea)
            if len(partes) < 4:
                continue
            codigo = coincidencia.group(1)
            citadas = sorted(set(CITA_FUENTE.findall(partes[3])))
            ramas.append(
                {
                    "id": codigo,
                    "antecedente": partes[1],
                    "consecuente": partes[2],
                    "accion": (
                        "Resolver una única decisión final; conservar todos los motivos."
                    ),
                    "fundamento_markdown": partes[3],
                    "fundamento": "MIXTO" if citadas else "POLITICA_PROTOTIPO",
                    "fuentes": citadas,
                }
            )
            continue

        coincidencia = FILA_FUENTE.match(linea.strip())
        if coincidencia and coincidencia.group(1) not in {f[0] for f in fuentes}:
            fuentes.append((coincidencia.group(1), coincidencia.group(2)))

    reglas = list({regla["id"]: regla for regla in reglas}.values())
    reglas.sort(key=lambda regla: str(regla["id"]))
    ramas = list({rama["id"]: rama for rama in ramas}.values())
    ramas.sort(key=lambda rama: str(rama["id"]))

    faltan = [f"R{n:02d}" for n in range(1, 31) if f"R{n:02d}" not in {r["id"] for r in reglas}]
    if faltan:
        raise SystemExit(f"no se encontraron las reglas: {faltan}")
    if len(ramas) != 9:
        raise SystemExit(f"se esperaban 9 ramas de R30 y se encontraron {len(ramas)}")
    if len(fuentes) != 9:
        raise SystemExit(f"se esperaban 9 fuentes S01–S09 y se encontraron {len(fuentes)}")

    salida: list[str] = [
        "# Catálogo transcrito de POSCOSEGRAN_30_reglas_base_conocimiento_actualizado.md",
        "# Generado por scripts/transcribir_base.py. No editar a mano: regenerar.",
        'version_base: "2.0"',
        'version_parametros: "1.0"',
        'version_motor: "0.7.0"',
        "",
        "fuentes:",
    ]
    for codigo, referencia in fuentes:
        salida.append(f'  - id: "{codigo}"')
        salida.append(f"    referencia_markdown: {bloque(referencia)}")

    for nombre, coleccion in (("reglas", reglas), ("ramas_r30", ramas)):
        salida.append("")
        salida.append(f"{nombre}:")
        for elemento in coleccion:
            salida.append(f'  - id: "{elemento["id"]}"')
            salida.append(f"    antecedente: {bloque(str(elemento['antecedente']))}")
            salida.append(f"    consecuente: {bloque(str(elemento['consecuente']))}")
            salida.append(f"    accion: {bloque(str(elemento['accion']))}")
            salida.append(
                f"    fundamento_markdown: {bloque(str(elemento['fundamento_markdown']))}"
            )
            salida.append(f'    fundamento: "{elemento["fundamento"]}"')
            citadas = elemento["fuentes"]
            if citadas:
                lista = ", ".join(f'"{codigo}"' for codigo in citadas)  # type: ignore[union-attr]
                salida.append(f"    fuentes: [{lista}]")
            else:
                salida.append("    fuentes: []")

    return "\n".join(salida) + "\n"


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    origen = Path(sys.argv[1])
    destino = origen.parent / "catalogo.yaml"
    destino.write_text(transcribir(origen), encoding="utf-8")
    print(f"escrito {destino}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
