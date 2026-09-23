"""Genera knowledge/casos_referencia.json: casos congelados de la base de conocimiento.

Contenido:
  * aceptacion  — las instantáneas que evalúan las pruebas C01–C40.
  * variaciones — casos derivados del caso base, estratificados por decisión.

Para cada caso se congela lo que decidió el sistema experto con la base vigente.
Los casos sirven para dos cosas:
  1. Regresión: tests/test_base_conocimiento.py comprueba que el motor y la base
     activa los reproducen exactamente.
  2. Adquisición: al proponer una versión nueva, el módulo de adquisición evalúa
     estos casos con la propuesta y muestra cuáles cambiarían de decisión.

Las variaciones se verificaron, antes de congelarse, contra el motor anterior con
reglas en código: 48 000 casos sin diferencias (ver docs/ARQUITECTURA_SE.md).

Uso:  python scripts/generar_casos_referencia.py  (requiere pytest instalado)
Regenerar solo cuando un cambio de la base sea intencional y esté revisado.
"""

from __future__ import annotations

import importlib
import json
import random
import sys
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "src"), str(RAIZ / "tests")]

from casos.base import AHORA, base, bul, con, desconocido, fec, num, txt  # noqa: E402
from casos.test_aceptacion import dictamen_vigente, hermetico, plan_reforzado  # noqa: E402

from poscosegran.dominio.hechos import (  # noqa: E402
    Controles, Episodio, Fase, Historial, Intervalo, Modalidad, Plan, ResultadoRevision,
)
from poscosegran.dominio.motor import evaluar  # noqa: E402
from poscosegran.dominio.valores import D, Dato, EstadoDato, F, V  # noqa: E402
from poscosegran.sistema_experto import base_conocimiento, serializacion  # noqa: E402

SUAVE_B, SUAVE_N = 8, 7
rnd = random.Random(20260923)

BOOL = ["insectos_vivos","granos_perforados","polvillo_inusual","exuvias_larvas","ruido_alimentacion","heces_roedores_aves_entorno","huellas","bolsa_roida","grano_derramado_por_plaga","moho_visible","olor_anormal","condensacion_interna","germinacion","heces_visibles","recipiente_limpio","recipiente_seco","material_grado_alimentario","recipiente_resistente","cierre_seguro","limpieza_diaria","limpieza_previa_nuevo_lote","limpieza_tras_operaciones","polvo_humo_gases_vapores","quimicos_combustibles_en_almacen","equipo_humedad_verificado","muestra_representativa","procedimiento_medicion_cumplido","aw_medida","lluvia_o_niebla","sello_integro","perforacion_barrera","bolsa_abierta_sin_resellar"]
NUM = {"humedad_grano":(10,17),"temperatura_grano":(5,32),"temperatura_almacen":(5,30),"hr_almacen":(40,75),"granos_defectuosos":(0,10),"granos_enfermos":(0,1),"granos_quebrados":(0,8),"materia_organica_extrana":(0,2),"materia_inorganica_extrana":(0,1),"suciedad_origen_animal":(0,0.3),"distancia_piso":(0.05,0.3),"distancia_pared":(0.3,0.8),"distancia_techo":(0.8,1.4),"actividad_agua":(0.5,0.8),"temperatura_muestra":(2,15),"humedad_equilibrio_maiz":(10,15),"hr_aire_exterior":(50,90),"temperatura_aire_exterior":(2,25),"temperatura_grano_previa":(5,30)}
def variar(i):
    inst = base()
    d = dict(inst.datos.datos)
    for campo in rnd.sample(BOOL, rnd.randint(0, SUAVE_B)):
        r = rnd.random()
        d[campo] = desconocido(campo) if r < 0.3 else bul(campo, r < 0.65)
    for campo in rnd.sample(list(NUM), rnd.randint(0, SUAVE_N)):
        lo, hi = NUM[campo]
        r = rnd.random()
        if r < 0.2:
            d[campo] = desconocido(campo)
        else:
            unidad = "CELSIUS" if "temperatura" in campo else "PCT_HR" if "hr_" in campo else "METROS" if "distancia" in campo else "PCT_BH"
            d[campo] = num(campo, str(round(rnd.uniform(lo, hi), 2)), unidad)
    if rnd.random() < 0.15:
        d["metodo_humedad"] = rnd.choice([txt("metodo_humedad","LABORATORIO"), txt("metodo_humedad","ESTIMACION_INDIRECTA"), desconocido("metodo_humedad")])
    if rnd.random() < 0.15:
        d["punto_medicion_previo"] = txt("punto_medicion_previo", rnd.choice(["CENTRO","BORDE"]))
        d["metodo_termico_previo"] = txt("metodo_termico_previo", "SONDA")
        pr = d.get("temperatura_grano_previa")
        if pr is None or not pr.utilizable:
            d["temperatura_grano_previa"] = num("temperatura_grano_previa", "8", "CELSIUS")
        tp = d["temperatura_grano_previa"]
        d["temperatura_grano_previa"] = replace(tp, fecha_observacion=AHORA - timedelta(hours=rnd.choice([12, 200, 800])))
    if rnd.random() < 0.15:
        d["tabla_equilibrio_id"] = txt("tabla_equilibrio_id", "EQ")
    if rnd.random() < 0.1:
        d["fecha_limpieza_general"] = fec("fecha_limpieza_general", AHORA - timedelta(days=rnd.choice([10, 40])))
    if rnd.random() < 0.08:
        d["granos_quebrados"] = Dato(campo="granos_quebrados", estado=EstadoDato.INVALIDO, valor=Decimal("-1"))
    from poscosegran.dominio.valores import Conjunto
    inst = replace(inst, datos=Conjunto(d))
    cambios = {}
    cambios["fase"] = rnd.choice([Fase.INGRESO, Fase.SEGUIMIENTO, Fase.SEGUIMIENTO, None])
    cambios["tipo_almacenamiento"] = rnd.choice([Modalidad.NO_HERMETICO, Modalidad.NO_HERMETICO, Modalidad.HERMETICO, None])
    cambios["clima_calido"] = rnd.choice([F, F, V, D])
    if rnd.random() < 0.3:
        cambios["historial"] = Historial(vida_previa_documentada=rnd.choice([None, Decimal("0.5"), Decimal("0.85"), Decimal("0.97"), Decimal("1.1")]))
    if rnd.random() < 0.15:
        cambios["historial"] = Historial(vida_previa_documentada=Decimal("0.1"), intervalos=(Intervalo(AHORA-timedelta(days=20), AHORA-timedelta(days=10), Decimal("13"), Decimal("12")), Intervalo(AHORA-timedelta(days=rnd.choice([10, 8, 12])), AHORA-timedelta(days=1), Decimal(rnd.choice(["14","16"])) if rnd.random()<0.8 else None, Decimal("15"))))
    if rnd.random() < 0.25:
        dias = rnd.choice([5, 20, 31, 60, None])
        cambios["dias_previstos_restantes"] = dias
        cambios["fecha_salida_prevista"] = (AHORA + timedelta(days=dias + rnd.choice([0,0,3]))) if dias else rnd.choice([None, AHORA+timedelta(days=10)])
    if rnd.random() < 0.3:
        cambios["dias_almacenados"] = rnd.choice([0, 50, 89, 90, 120, None])
    if rnd.random() < 0.3:
        cambios["plan"] = rnd.choice([plan_reforzado(), plan_reforzado(14), Plan(registrado=True, intervalo_dias=7, fecha_salida_prevista=None, vigente=True), Plan()])
    if rnd.random() < 0.25:
        cambios["dictamen"] = rnd.choice([dictamen_vigente(), dictamen_vigente(10), None])
    if rnd.random() < 0.2:
        cambios["episodios"] = (Episodio(id="e", tipo=rnd.choice(["CUARENTENA","REVISION_PLAGAS","REVISION_TERMICA","CORRECCION"])),)
    if rnd.random() < 0.2:
        cambios["resultado_revision_plagas"] = rnd.choice(list(ResultadoRevision))
        cambios["revision_plagas_cubre_indicios_actuales"] = rnd.random() < 0.5
    if rnd.random() < 0.3:
        cambios["controles"] = Controles(
            fecha_inspeccion_grano=rnd.choice([AHORA, AHORA-timedelta(days=10), AHORA-timedelta(days=20), None]),
            fecha_inspeccion_exterior=rnd.choice([AHORA, AHORA-timedelta(days=10), AHORA-timedelta(days=35), None]),
            fecha_control_almacen=rnd.choice([AHORA, AHORA-timedelta(days=10), AHORA-timedelta(days=20), None]),
            ingreso_inspeccionado=rnd.choice([V, F, D]),
            hay_evento_que_invalida_control=rnd.choice([F, F, V, D]),
        )
    if rnd.random() < 0.3:
        cambios["sensor_interno_hermetico"] = rnd.random() < 0.5
    if rnd.random() < 0.3:
        cambios["temperatura_ambiente_maxima_intervalo"] = rnd.choice([None, Decimal("12"), Decimal("27")])
    return replace(inst, **cambios)

def dirigido(i):
    """Casos cerca de las ramas R30.6 y R30.7: todo conforme salvo el motivo de monitoreo."""
    inst = replace(base(), plan=rnd.choice([plan_reforzado(), plan_reforzado(), Plan()]))
    eleccion = rnd.choice(["r16", "r28", "hermetico", "condicional"])
    if eleccion == "r16":
        inst = con(inst, temperatura_grano=num("temperatura_grano", str(rnd.choice([14, 15, 20, 24, 25])), "CELSIUS"))
    elif eleccion == "r28":
        vida = Decimal(rnd.choice(["0.75", "0.80", "0.85", "0.93", "1.0"]))
        dias = rnd.choice([5, 10, 20])
        inst = replace(inst, historial=Historial(vida_previa_documentada=vida), dias_previstos_restantes=dias, fecha_salida_prevista=AHORA + timedelta(days=dias))
    elif eleccion == "hermetico":
        inst = replace(hermetico(base()), fase=Fase.SEGUIMIENTO, dias_almacenados=20, plan=inst.plan,
                       sensor_interno_hermetico=rnd.random() < 0.4,
                       temperatura_ambiente_maxima_intervalo=rnd.choice([None, Decimal("12"), Decimal("26")]))
    else:
        inst = replace(inst, dictamen=rnd.choice([dictamen_vigente(), dictamen_vigente(10), None]),
                       clima_calido=rnd.choice([F, F, V, D]))
        dias = rnd.choice([10, 20, 30, 31])
        inst = replace(inst, dias_previstos_restantes=dias, fecha_salida_prevista=AHORA + timedelta(days=dias))
        inst = con(inst, humedad_grano=num("humedad_grano", rnd.choice(["13.2", "13.5", "14", "14.01"])))
    return inst


def esperado(inst) -> dict:
    r = evaluar(inst)
    return {
        "decision": r.decision_final,
        "rama": r.rama_r30,
        "reglas": sorted(r.reglas_activadas),
        "motivos": sorted(m.id for m in r.motivos),
        "pendientes": sorted({p.campo for p in r.datos_pendientes}),
    }


def capturar_aceptacion() -> list[tuple[str, object]]:
    capturas: list[tuple[str, object]] = []
    modulo = importlib.import_module("casos.test_aceptacion")
    original = modulo.evaluar
    actual = {"nombre": ""}

    def espia(inst, *args, **kwargs):
        capturas.append((actual["nombre"], inst))
        return original(inst, *args, **kwargs)

    modulo.evaluar = espia
    try:
        for nombre in sorted(dir(modulo)):
            funcion = getattr(modulo, nombre)
            if not nombre.startswith("test_") or not callable(funcion):
                continue
            marcas = getattr(funcion, "pytestmark", [])
            juegos = list(getattr(funcion, "_params", [()]))
            for marca in marcas:
                if marca.name == "parametrize":
                    juegos = [a if isinstance(a, tuple) else (a,) for a in marca.args[1]]
            for argumentos in juegos:
                actual["nombre"] = nombre + (f"[{argumentos}]" if argumentos else "")
                funcion(*argumentos)
    finally:
        modulo.evaluar = original
    return capturas


def generar_variaciones(por_decision: int = 25) -> list[tuple[str, object]]:
    global SUAVE_B, SUAVE_N
    cuotas: dict[str, int] = {}
    salida: list[tuple[str, object]] = []
    for modo, generador, intentos in (("dirigido", dirigido, 3000), ("suave", variar, 4000), ("intenso", variar, 3000)):
        SUAVE_B, SUAVE_N = (1, 2) if modo == "suave" else (8, 7)
        for i in range(intentos):
            inst = generador(i)
            decision = evaluar(inst).decision_final
            if cuotas.get(decision, 0) >= por_decision:
                continue
            cuotas[decision] = cuotas.get(decision, 0) + 1
            salida.append((f"{modo}-{i}", inst))
    return salida


def main() -> None:
    base_activa = base_conocimiento.cargar()
    plantilla = serializacion.a_json(base())["datos"]
    casos = []
    for origen, lista in (("aceptacion", capturar_aceptacion()), ("variacion", generar_variaciones())):
        for nombre, inst in lista:
            casos.append({
                "id": f"{origen}:{nombre}",
                "origen": origen,
                "hechos": serializacion.comprimir(serializacion.a_json(inst), plantilla),
                "esperado": esperado(inst),
            })
    destino = base_conocimiento.ruta_por_defecto() / "casos_referencia.json"
    destino.write_text(
        json.dumps(
            {
                "version_base": base_activa.version_base,
                "version_parametros": base_activa.version_parametros,
                "hash_base": base_activa.hash,
                "plantilla_datos": plantilla,
                "casos": casos,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    por_decision: dict[str, int] = {}
    for caso in casos:
        por_decision[caso["esperado"]["decision"]] = por_decision.get(caso["esperado"]["decision"], 0) + 1
    print(f"{len(casos)} casos → {destino}")
    print(por_decision)


if __name__ == "__main__":
    main()
