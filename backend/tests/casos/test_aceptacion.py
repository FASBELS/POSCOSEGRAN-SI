"""Casos de aceptación C01–C40 de la sección 9 de la base 2.0.

Son expectativas de aceptación del motor, no ensayos de campo. Cada caso parte
del caso base B y modifica lo que indica la especificación.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from poscosegran.dominio import tablas
from poscosegran.dominio.hechos import (
    Controles,
    Dictamen,
    Episodio,
    Fase,
    Historial,
    Instantanea,
    Modalidad,
    Plan,
    ResultadoRevision,
)
from poscosegran.dominio.motor import evaluar
from poscosegran.dominio.valores import EstadoDato, Dato, F, V

from .base import AHORA, base, bul, con, num, sin, txt


def plan_reforzado(dias: int = 7) -> Plan:
    return Plan(
        registrado=True,
        intervalo_dias=dias,
        fecha_salida_prevista=AHORA + timedelta(days=20),
        vigente=True,
    )


def dictamen_vigente(plazo: int = 30) -> Dictamen:
    return Dictamen(
        humedad_min=Decimal("13"),
        humedad_max=Decimal("14"),
        plazo_maximo_dias=plazo,
        vence_en=AHORA + timedelta(days=25),
        vigente=True,
    )


def hermetico(inst: Instantanea, **estado: bool) -> Instantanea:
    """Convierte la instantánea a hermética con su barrera declarada."""
    valores = {
        "sello_integro": True,
        "cierre_seguro": True,
        "perforacion_barrera": False,
        "bolsa_abierta_sin_resellar": False,
    }
    valores.update(estado)
    inst = replace(
        inst,
        tipo_almacenamiento=Modalidad.HERMETICO,
        controles=replace(inst.controles, fecha_inspeccion_exterior=AHORA),
    )
    return con(inst, **{campo: bul(campo, valor) for campo, valor in valores.items()})



def test_c01_caso_base_autoriza() -> None:
    resultado = evaluar(base())
    assert resultado.decision_final == "AUTORIZAR_ALMACENAMIENTO"
    assert resultado.rama_r30 == "R30.8"
    assert resultado.calculos.vida_consumida == Decimal("0.10")
    assert resultado.calculos.vida_proyectada == Decimal("0.20")


def test_c02_humedad_trece_es_condicion_base() -> None:
    resultado = evaluar(con(base(), humedad_grano=num("humedad_grano", "13")))
    assert "HUMEDAD_APTA_BASE" in {motivo.id.split(":")[1] for motivo in resultado.motivos}
    assert resultado.decision_final == "AUTORIZAR_ALMACENAMIENTO"


def test_c03_banda_condicional_con_dictamen_y_plan() -> None:
    inst = replace(base(), dictamen=dictamen_vigente(), plan=plan_reforzado())
    resultado = evaluar(con(inst, humedad_grano=num("humedad_grano", "13.5")))
    assert resultado.decision_final == "AUTORIZAR_CON_MONITOREO"
    assert resultado.rama_r30 == "R30.6"


def test_c04_humedad_catorce_no_activa_r01() -> None:
    inst = replace(base(), dictamen=dictamen_vigente(), plan=plan_reforzado())
    resultado = evaluar(con(inst, humedad_grano=num("humedad_grano", "14")))
    assert resultado.decision_final == "AUTORIZAR_CON_MONITOREO"
    assert "R01" not in resultado.reglas_activadas


def test_c05_humedad_sobre_catorce_bloquea_ingreso() -> None:
    resultado = evaluar(con(base(), humedad_grano=num("humedad_grano", "14.01")))
    assert resultado.decision_final == "BLOQUEAR_INGRESO"
    assert resultado.rama_r30 == "R30.2"


def test_c06_misma_humedad_en_seguimiento_retira_lote() -> None:
    inst = replace(base(), fase=Fase.SEGUIMIENTO)
    resultado = evaluar(con(inst, humedad_grano=num("humedad_grano", "14.01")))
    assert resultado.decision_final == "RETIRAR_LOTE"
    assert resultado.rama_r30 == "R30.3"


def test_c07_temperatura_del_grano_alta_exige_correccion() -> None:
    resultado = evaluar(
        con(
            base(),
            temperatura_grano=num("temperatura_grano", "26", "CELSIUS"),
            temperatura_almacen=num("temperatura_almacen", "20", "CELSIUS"),
        )
    )
    assert resultado.decision_final == "CORREGIR_Y_REEVALUAR"
    assert "R08" in resultado.reglas_activadas


def test_c08_estimacion_indirecta_no_confirma_medicion() -> None:
    resultado = evaluar(
        con(base(), metodo_humedad=txt("metodo_humedad", "ESTIMACION_INDIRECTA"))
    )
    assert resultado.decision_final == "CORREGIR_Y_REEVALUAR"
    assert "R03" not in resultado.reglas_activadas
    assert "R05" in resultado.reglas_activadas


def test_c09_falta_verificacion_del_equipo_no_concluye() -> None:
    resultado = evaluar(sin(base(), "equipo_humedad_verificado"))
    assert resultado.decision_final == "SIN_CONCLUSION_AUTOMATICA"
    assert resultado.rama_r30 == "R30.5"
    assert "R05" not in resultado.reglas_activadas



def test_c10_sello_con_perforacion_es_inconsistente() -> None:
    resultado = evaluar(hermetico(base(), perforacion_barrera=True))
    assert resultado.decision_final == "CORREGIR_Y_REEVALUAR"
    assert "PROTECCION_HERMETICA_ACTIVA" not in {m.id.split(":")[1] for m in resultado.motivos}
    assert "R13" in resultado.reglas_activadas


def test_c11_hermetico_con_sensor_no_exige_inspeccion_interna() -> None:
    inst = hermetico(base())
    inst = replace(
        inst,
        fase=Fase.SEGUIMIENTO,
        sensor_interno_hermetico=True,
        dias_almacenados=20,
        controles=Controles(
            fecha_inspeccion_exterior=AHORA - timedelta(days=15),
            fecha_control_almacen=AHORA - timedelta(days=5),
            ingreso_inspeccionado=V,
            hay_evento_que_invalida_control=F,
        ),
    )
    resultado = evaluar(inst)
    assert "R27" not in resultado.reglas_activadas


def test_c12_inspeccion_exterior_vencida_exige_correccion() -> None:
    inst = hermetico(base())
    inst = replace(
        inst,
        fase=Fase.SEGUIMIENTO,
        sensor_interno_hermetico=True,
        dias_almacenados=40,
        controles=Controles(
            fecha_inspeccion_exterior=AHORA - timedelta(days=31),
            fecha_control_almacen=AHORA - timedelta(days=5),
            ingreso_inspeccionado=V,
            hay_evento_que_invalida_control=F,
        ),
    )
    resultado = evaluar(inst)
    assert resultado.decision_final == "CORREGIR_Y_REEVALUAR"
    assert "R27" in resultado.reglas_activadas



def test_c13_moho_visible_produce_cuarentena() -> None:
    resultado = evaluar(con(base(), moho_visible=bul("moho_visible", True)))
    assert resultado.decision_final == "CUARENTENA"
    assert resultado.rama_r30 == "R30.1"


def test_c14_sospecha_sin_revision_no_confirma_infestacion() -> None:
    inst = replace(base(), resultado_revision_plagas=ResultadoRevision.PENDIENTE)
    resultado = evaluar(con(inst, polvillo_inusual=bul("polvillo_inusual", True)))
    assert resultado.decision_final == "CORREGIR_Y_REEVALUAR"
    assert "R15" in resultado.reglas_activadas
    assert "R14" not in resultado.reglas_activadas


def test_c15_revision_confirmada_encadena_hasta_cuarentena() -> None:
    inst = replace(
        base(),
        resultado_revision_plagas=ResultadoRevision.CONFIRMADA,
        revision_plagas_cubre_indicios_actuales=True,
    )
    resultado = evaluar(con(inst, polvillo_inusual=bul("polvillo_inusual", True)))
    assert resultado.decision_final == "CUARENTENA"
    assert "R14" in resultado.reglas_activadas
    assert "R19" in resultado.reglas_activadas



def test_c16_vida_en_aviso_autoriza_con_monitoreo() -> None:
    inst = replace(
        base(),
        historial=Historial(vida_previa_documentada=Decimal("0.80")),
        dias_previstos_restantes=10,
        fecha_salida_prevista=AHORA + timedelta(days=10),
        plan=plan_reforzado(),
    )
    resultado = evaluar(inst)
    assert resultado.decision_final == "AUTORIZAR_CON_MONITOREO"
    assert "R28" in resultado.reglas_activadas


@pytest.mark.parametrize(
    ("vida", "fase", "esperado"),
    [
        (Decimal("1.00"), Fase.INGRESO, "BLOQUEAR_INGRESO"),
        (Decimal("1.20"), Fase.INGRESO, "BLOQUEAR_INGRESO"),
        (Decimal("1.20"), Fase.SEGUIMIENTO, "RETIRAR_LOTE"),
    ],
)
def test_c17_vida_agotada_suspende(vida: Decimal, fase: Fase, esperado: str) -> None:
    inst = replace(
        base(), fase=fase, historial=Historial(vida_previa_documentada=vida)
    )
    resultado = evaluar(inst)
    assert resultado.decision_final == esperado
    assert "R29" in resultado.reglas_activadas


def test_c18_seleccion_de_celda_sube_fila_y_columna() -> None:
    celda = tablas.seleccionar(Decimal("12.5"), Decimal("10"))
    assert celda is not None
    assert (celda.humedad_fila, celda.temperatura_columna_c) == (Decimal("14"), Decimal("21.11"))
    assert celda.dias_referencia == 200


def test_c19_temperatura_fuera_de_tabla_no_se_extrapola() -> None:
    resultado = evaluar(con(base(), temperatura_grano=num("temperatura_grano", "30", "CELSIUS")))
    assert tablas.seleccionar(Decimal("12.5"), Decimal("30")) is None
    assert resultado.calculos.tiempo_referencia_actual is None
    assert "R08" in resultado.reglas_activadas
    assert resultado.decision_final == "CORREGIR_Y_REEVALUAR"



def aireacion(inst: Instantanea, equilibrio: str, hr: str, aire: str) -> Instantanea:
    return con(
        inst,
        humedad_equilibrio_maiz=num("humedad_equilibrio_maiz", equilibrio),
        tabla_equilibrio_id=txt("tabla_equilibrio_id", "EQUILIBRIO_MAIZ_ALTOANDINO"),
        hr_aire_exterior=num("hr_aire_exterior", hr, "PCT_HR"),
        temperatura_aire_exterior=num("temperatura_aire_exterior", aire, "CELSIUS"),
        lluvia_o_niebla=bul("lluvia_o_niebla", False),
    )


def test_c20_aire_seco_y_frio_permite_airear() -> None:
    resultado = evaluar(aireacion(base(), "11", "55", "8"))
    assert "R10" in resultado.reglas_activadas
    assert "R11" not in resultado.reglas_activadas


def test_c21_equilibrio_igual_no_permite_airear() -> None:
    resultado = evaluar(aireacion(base(), "12.5", "55", "8"))
    assert "R11" in resultado.reglas_activadas
    assert "R10" not in resultado.reglas_activadas


def test_c22_aire_mas_caliente_no_se_recomienda() -> None:
    resultado = evaluar(aireacion(base(), "11", "55", "15"))
    assert "R11" in resultado.reglas_activadas
    assert "R10" not in resultado.reglas_activadas


def test_c23_aireacion_no_aplica_a_hermetico() -> None:
    resultado = evaluar(aireacion(hermetico(base()), "11", "55", "8"))
    assert "R10" not in resultado.reglas_activadas
    assert "R11" not in resultado.reglas_activadas



def test_c24_nueva_medicion_desfavorable_no_conserva_autorizacion() -> None:
    primera = evaluar(base())
    assert primera.decision_final == "AUTORIZAR_ALMACENAMIENTO"
    segunda = evaluar(con(base(), humedad_grano=num("humedad_grano", "15")))
    assert segunda.decision_final == "BLOQUEAR_INGRESO"


def test_c25_cuarentena_abierta_no_se_levanta_sin_cierre() -> None:
    inst = replace(
        base(),
        fase=Fase.SEGUIMIENTO,
        episodios=(Episodio(id="e1", tipo="CUARENTENA", causas=("moho",)),),
    )
    resultado = evaluar(inst)
    assert resultado.decision_final == "CUARENTENA"


def test_c26_cuarentena_conserva_la_causa_de_suspension() -> None:
    inst = con(
        base(),
        moho_visible=bul("moho_visible", True),
        humedad_grano=num("humedad_grano", "15"),
    )
    resultado = evaluar(sin(inst, "granos_quebrados"))
    hallazgos = {motivo.id.split(":")[1] for motivo in resultado.motivos}
    assert resultado.decision_final == "CUARENTENA"
    assert "HUMEDAD_NO_APTA" in hallazgos
    assert resultado.datos_pendientes



def test_c27_ambiente_favorable_a_insectos_con_plan_autoriza_con_monitoreo() -> None:
    inst = replace(base(), plan=plan_reforzado())
    resultado = evaluar(con(inst, temperatura_grano=num("temperatura_grano", "20", "CELSIUS")))
    assert resultado.decision_final == "AUTORIZAR_CON_MONITOREO"
    assert "R16" in resultado.reglas_activadas


def test_c28_monitoreo_sin_plan_exige_correccion() -> None:
    resultado = evaluar(con(base(), temperatura_grano=num("temperatura_grano", "20", "CELSIUS")))
    assert resultado.decision_final == "CORREGIR_Y_REEVALUAR"


@pytest.mark.parametrize("cambio", ["plazo", "clima"])
def test_c29_banda_condicional_inadmisible_exige_secado(cambio: str) -> None:
    inst = replace(base(), dictamen=dictamen_vigente(), plan=plan_reforzado())
    if cambio == "plazo":
        inst = replace(
            inst, dias_previstos_restantes=31, fecha_salida_prevista=AHORA + timedelta(days=31)
        )
    else:
        inst = replace(inst, clima_calido=V)
    resultado = evaluar(con(inst, humedad_grano=num("humedad_grano", "13.5")))
    assert resultado.decision_final == "CORREGIR_Y_REEVALUAR"


def test_c30_proyeccion_sobre_el_limite_revisa_plazo_sin_declarar_vida_agotada() -> None:
    inst = replace(base(), historial=Historial(vida_previa_documentada=Decimal("0.95")))
    resultado = evaluar(inst)
    assert resultado.calculos.vida_proyectada == Decimal("1.05")
    assert resultado.decision_final == "CORREGIR_Y_REEVALUAR"
    assert "R29" not in resultado.reglas_activadas


def test_c31_clima_calido_no_hermetico_a_los_noventa_dias_retira() -> None:
    inst = replace(
        base(),
        fase=Fase.SEGUIMIENTO,
        clima_calido=V,
        dias_almacenados=90,
    )
    resultado = evaluar(inst)
    assert resultado.decision_final == "RETIRAR_LOTE"
    assert "R29" in resultado.reglas_activadas


def test_c32_historia_previa_desconocida_no_se_inicializa_en_cero() -> None:
    inst = replace(base(), historial=Historial())
    resultado = evaluar(inst)
    assert resultado.calculos.vida_consumida is None
    assert resultado.decision_final == "SIN_CONCLUSION_AUTOMATICA"


def test_c33_escenario_hermetico_se_declara_como_estimacion() -> None:
    inst = hermetico(base())
    inst = replace(
        inst,
        fase=Fase.SEGUIMIENTO,
        dias_almacenados=20,
        sensor_interno_hermetico=False,
        temperatura_ambiente_maxima_intervalo=Decimal("12"),
        plan=plan_reforzado(30),
    )
    resultado = evaluar(inst)
    assert resultado.decision_final == "AUTORIZAR_CON_MONITOREO"
    assert any(e.tipo == "ESTIMACION_HERMETICA" for e in resultado.estimaciones)



@pytest.mark.parametrize(
    ("campo", "valor", "unidad"),
    [("temperatura_almacen", "25", "CELSIUS"), ("hr_almacen", "60", "PCT_HR")],
)
def test_c34_umbrales_ambientales_exigen_correccion(campo: str, valor: str, unidad: str) -> None:
    resultado = evaluar(con(base(), **{campo: num(campo, valor, unidad)}))
    assert resultado.decision_final == "CORREGIR_Y_REEVALUAR"


def test_c35_hr_externa_no_bloquea_hermetico_integro() -> None:
    inst = replace(hermetico(base()), sensor_interno_hermetico=True)
    resultado = evaluar(con(inst, hr_almacen=num("hr_almacen", "65", "PCT_HR")))
    assert "R07" not in resultado.reglas_activadas
    assert "R06" in resultado.reglas_activadas
    assert resultado.decision_final in {"AUTORIZAR_ALMACENAMIENTO", "AUTORIZAR_CON_MONITOREO"}


def test_c36_material_animal_encadena_hasta_cuarentena() -> None:
    resultado = evaluar(con(base(), heces_visibles=bul("heces_visibles", True)))
    assert resultado.decision_final == "CUARENTENA"
    assert "R20" in resultado.reglas_activadas
    assert "R19" in resultado.reglas_activadas


def test_c37_suspension_con_fase_desconocida_corrige() -> None:
    inst = replace(base(), fase=None)
    resultado = evaluar(
        con(inst, material_grado_alimentario=bul("material_grado_alimentario", False))
    )
    assert resultado.decision_final == "CORREGIR_Y_REEVALUAR"
    assert "R23" in resultado.reglas_activadas


def test_c38_el_secado_no_reinicia_el_historial() -> None:
    inst = replace(
        base(),
        fase=Fase.SEGUIMIENTO,
        historial=Historial(vida_previa_documentada=Decimal("1.10")),
    )
    resultado = evaluar(con(inst, humedad_grano=num("humedad_grano", "12")))
    assert resultado.decision_final == "RETIRAR_LOTE"
    assert "R29" in resultado.reglas_activadas


def test_c39_dato_invalido_exige_correccion() -> None:
    invalido = Dato(
        campo="granos_quebrados",
        estado=EstadoDato.INVALIDO,
        valor=Decimal("-3"),
        unidad="PCT_MASA",
        fecha_observacion=AHORA,
        metodo="MUESTREO",
    )
    resultado = evaluar(con(base(), granos_quebrados=invalido))
    assert resultado.decision_final == "CORREGIR_Y_REEVALUAR"


def test_c40_un_descarte_anterior_no_cubre_insectos_nuevos() -> None:
    inst = replace(
        base(),
        resultado_revision_plagas=ResultadoRevision.DESCARTADA,
        revision_plagas_cubre_indicios_actuales=False,
    )
    resultado = evaluar(con(inst, insectos_vivos=bul("insectos_vivos", True)))
    assert resultado.decision_final == "CUARENTENA"
    assert "R14" in resultado.reglas_activadas



CASOS_VARIADOS = (
    "base", "moho", "humedad_alta", "sin_equipo", "temperatura_alta", "insectos",
)


def _instantanea(nombre: str) -> Instantanea:
    match nombre:
        case "moho":
            return con(base(), moho_visible=bul("moho_visible", True))
        case "humedad_alta":
            return con(base(), humedad_grano=num("humedad_grano", "16"))
        case "sin_equipo":
            return sin(base(), "equipo_humedad_verificado")
        case "temperatura_alta":
            return con(base(), temperatura_grano=num("temperatura_grano", "26", "CELSIUS"))
        case "insectos":
            return con(base(), insectos_vivos=bul("insectos_vivos", True))
        case _:
            return base()


@pytest.mark.parametrize("nombre", CASOS_VARIADOS)
def test_invariante_una_sola_decision(nombre: str) -> None:
    resultado = evaluar(_instantanea(nombre))
    assert resultado.decision_final
    assert resultado.rama_r30.startswith("R30.")


@pytest.mark.parametrize("nombre", CASOS_VARIADOS)
def test_invariante_ninguna_solicitud_adversa_termina_en_autorizacion(nombre: str) -> None:
    resultado = evaluar(_instantanea(nombre))
    adversas = {"CUARENTENA_SOLICITADA", "SUSPENSION_SOLICITADA", "CORRECCION_SOLICITADA"}
    if adversas & set(resultado.solicitudes):
        assert resultado.decision_final not in {
            "AUTORIZAR_ALMACENAMIENTO",
            "AUTORIZAR_CON_MONITOREO",
        }


@pytest.mark.parametrize("nombre", CASOS_VARIADOS)
def test_invariante_ninguna_autorizacion_con_datos_pendientes(nombre: str) -> None:
    resultado = evaluar(_instantanea(nombre))
    if resultado.datos_pendientes:
        assert resultado.decision_final not in {
            "AUTORIZAR_ALMACENAMIENTO",
            "AUTORIZAR_CON_MONITOREO",
        }


def test_invariante_r12_y_r13_no_coexisten() -> None:
    for perforada in (True, False):
        resultado = evaluar(hermetico(base(), perforacion_barrera=perforada))
        activadas = set(resultado.reglas_activadas)
        assert not ({"R12", "R13"} <= activadas)


def test_invariante_el_orden_de_insercion_no_altera_el_resultado() -> None:
    inst = con(base(), moho_visible=bul("moho_visible", True))
    invertida = replace(
        inst,
        datos=type(inst.datos)(dict(reversed(list(inst.datos.datos.items())))),
    )
    assert evaluar(inst).decision_final == evaluar(invertida).decision_final


def test_invariante_repetir_la_evaluacion_no_duplica_motivos() -> None:
    resultado = evaluar(con(base(), moho_visible=bul("moho_visible", True)))
    identificadores = [motivo.id for motivo in resultado.motivos]
    assert len(identificadores) == len(set(identificadores))
