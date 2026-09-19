from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

from casos.base import AHORA, base
from poscosegran.dominio.hechos import Historial, Intervalo
from poscosegran.dominio.motor import evaluar
from test_integracion_api import entrada, unidad, post
import pytest
from concurrent.futures import ThreadPoolExecutor


@pytest.mark.bd
@pytest.mark.parametrize('misma_clave', [True, False])
def test_evaluaciones_concurrentes_no_duplican_efectos(api_real, misma_clave):
    c, h, _ = api_real
    u = unidad(c)
    body = entrada(u, {'moho_visible': True})
    primero = h()
    headers = [primero, primero if misma_clave else h()]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda cabeceras: c.post(
            f'/api/v1/unidades/{u["id"]}/evaluaciones', json=body, headers=cabeceras
        ), headers))
    assert sorted(r.status_code for r in responses) == ([201, 201] if misma_clave else [201, 409])
    if misma_clave:
        assert responses[0].json() == responses[1].json()
    historial = c.get(f'/api/v1/unidades/{u["id"]}/historial').json()['items']
    incidencias = c.get(f'/api/v1/unidades/{u["id"]}/incidencias').json()['items']
    assert len(historial) == 1
    assert len([i for i in incidencias if i['tipo'] == 'CUARENTENA']) == 1


def test_historial_no_duplica_intervalos_y_detecta_laguna():
    tramo = Intervalo(AHORA-timedelta(days=10), AHORA, Decimal('12.5'), Decimal('10'))
    inst = replace(base(), historial=Historial(vida_previa_documentada=Decimal('0'), intervalos=(tramo,tramo)))
    r = evaluar(inst)
    assert r.calculos.vida_consumida is None
    assert r.calculos.vida_minima_documentada == Decimal('0.05')
    segundo = replace(tramo, inicio=AHORA-timedelta(days=4))
    primero = replace(tramo, fin=AHORA-timedelta(days=5))
    r = evaluar(replace(inst,historial=replace(inst.historial,intervalos=(primero,segundo))))
    assert r.calculos.vida_consumida is None


@pytest.mark.bd
def test_no_aplica_no_sustituye_condicion_obligatoria(api_real):
    c,_,_=api_real
    u=unidad(c)
    body=entrada(u)
    obs=next(o for o in body['observaciones'] if o['campo']=='temperatura_muestra')
    obs.update(captura='NO_APLICA',valor=None,motivo_no_aplica='No lo medí')
    r=post(c,f'/unidades/{u["id"]}/evaluaciones',body)
    assert not r['evaluacion']['decision_final'].startswith('AUTORIZAR')
    aplicada=next(o for o in r['evaluacion']['observaciones_aplicadas'] if o['entrada']['campo']=='temperatura_muestra')
    assert aplicada['estado_dato']=='INVALIDO'


@pytest.mark.bd
def test_control_adverso_abre_episodio_sin_evaluacion(api_real):
    c,_,_=api_real
    u=unidad(c)
    body=entrada(u,{'moho_visible':True})
    post(c,f'/unidades/{u["id"]}/controles',{'revision_unidad':u['revision'],'revision_almacen':u['revision_almacen'],
        'tipo':'GRANO','fecha':body['observaciones'][0]['fecha_observacion'],
        'observaciones':body['observaciones'],'evidencia':'Moho observado'})
    items=c.get(f'/api/v1/unidades/{u["id"]}/incidencias').json()['items']
    assert any(i['tipo']=='CUARENTENA' and i['estado']=='ABIERTA' for i in items)
