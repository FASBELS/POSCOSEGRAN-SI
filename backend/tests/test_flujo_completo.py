import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from poscosegran.db.modelos import AsignacionLote, Usuario
from test_integracion_api import entrada, post, unidad

pytestmark = pytest.mark.bd


def actual(c, u):
    return c.get('/api/v1/unidades/' + u['id']).json()


def rev(u):
    return {'revision_unidad': u['revision'], 'revision_almacen': u['revision_almacen']}


def test_borrador_reintento_y_conflicto(api_real):
    c, h, _ = api_real
    u = unidad(c)
    body = entrada(u, {'moho_visible': True})
    headers = {**h(), 'If-None-Match': '*'}
    url = f'/api/v1/unidades/{u["id"]}/borrador'
    a = c.put(url, json=body, headers=headers)
    assert a.status_code == 201, a.text
    b = c.put(url, json=body, headers=headers)
    assert b.status_code == 201 and b.json() == a.json()
    assert c.get(url).headers['etag'] == '"1"'
    assert c.put(url, json=body, headers={**h(), 'If-Match': '"99"'}).status_code == 409
    assert c.put(url, json=body, headers={**h(), 'If-Match': '"1"'}).json()['revision'] == 2
    post(c, f'/unidades/{u["id"]}/evaluaciones', body)
    assert c.get(url).status_code == 404


def test_control_evento_y_admision(api_real):
    c, h, _ = api_real
    u = unidad(c)
    result = post(c, f'/unidades/{u["id"]}/evaluaciones', entrada(u))
    u = actual(c, u)
    admision = {**rev(u), 'id_evaluacion': result['evaluacion']['id'], 'tipo': 'INGRESO'}
    post(c, f'/unidades/{u["id"]}/admisiones', admision)
    evento = post(c, f'/unidades/{u["id"]}/eventos', {**rev(u), 'tipo':'APERTURA',
        'fecha': (datetime.now(UTC)-timedelta(minutes=1)).isoformat(), 'evidencia':'Se abrió para muestrear'})
    assert evento['tipo'] == 'APERTURA'
    assert c.get(f'/api/v1/unidades/{u["id"]}/vigencia').json()['estado'] == 'INVALIDADA'
    assert c.post(f'/api/v1/unidades/{u["id"]}/admisiones',json=admision,headers=h()).status_code == 409
    u = actual(c,u)
    obs = entrada(u, {'moho_visible': True})['observaciones']
    control = post(c,f'/unidades/{u["id"]}/controles',{**rev(u),'tipo':'GRANO',
        'fecha':datetime.now(UTC).isoformat(),'observaciones':obs,'evidencia':'Moho observado'})
    assert not control['completo']
    u = actual(c,u)
    result = post(c,f'/unidades/{u["id"]}/evaluaciones',entrada(u,{}))
    assert result['evaluacion']['decision_final'] == 'CUARENTENA'


def test_revision_y_resolucion_tecnica(api_real, url_bd):
    c, h, usuarios = api_real
    u = unidad(c)
    post(c,f'/unidades/{u["id"]}/evaluaciones',entrada(u,{'moho_visible':True}))
    u = actual(c,u)
    incidencia = c.get(f'/api/v1/unidades/{u["id"]}/incidencias').json()['items'][0]
    with Session(create_engine(url_bd)) as db, db.begin():
        db.add(AsignacionLote(id_tecnico=usuarios['TECNICO'],id_lote=uuid.UUID(u['id_lote']),creada_por=usuarios['ADMINISTRADOR']))
    revision = {**rev(u),'revision_incidencia':incidencia['revision'],'resultado':'CONFIRMADA','evidencia':'Inspección técnica'}
    url = f'/incidencias/{incidencia["id"]}/revisiones'
    assert c.post('/api/v1'+url,json=revision,headers=h('PRODUCTOR')).status_code == 403
    post(c,url,revision,h('TECNICO'))
    assert c.get(f'/api/v1/incidencias/{incidencia["id"]}').json()['estado'] == 'ABIERTA'
    u = actual(c,u)
    post(c,f'/incidencias/{incidencia["id"]}/resoluciones',{**rev(u),'revision_incidencia':2,
        'evidencia':'Acta de tratamiento y comprobación','disposicion':'Cierre documentado; exige reevaluación'},h('TECNICO'))
    assert c.get(f'/api/v1/incidencias/{incidencia["id"]}').json()['estado'] == 'CERRADA'
    assert c.get(f'/api/v1/unidades/{u["id"]}/vigencia').json()['estado'] != 'VIGENTE'


def test_plan_dictamen_historia_y_vencimiento(api_real, monkeypatch):
    c, h, _ = api_real
    u = unidad(c)
    r1 = post(c,f'/unidades/{u["id"]}/evaluaciones',entrada(u))
    u = actual(c,u)
    post(c,f'/unidades/{u["id"]}/planes',{**rev(u),'fecha_proximo_control':(datetime.now(UTC)+timedelta(days=5)).isoformat(),
        'fecha_salida_prevista':(datetime.now(UTC)+timedelta(days=20)).isoformat(),'intervalo_dias':5,'actividades':'Control exterior'})
    u = actual(c,u)
    r2 = post(c,f'/unidades/{u["id"]}/evaluaciones',entrada(u))
    assert c.get('/api/v1/evaluaciones/'+r1['evaluacion']['id']).json()['vigencia']['estado']=='INVALIDADA'
    from poscosegran.servicios import vigencia
    futuro = datetime.fromisoformat(r2['vigencia']['fecha_vencimiento_autorizacion'].replace('Z','+00:00')) + timedelta(seconds=1)
    class Reloj(datetime):
        @classmethod
        def now(cls,tz=None): return futuro
    monkeypatch.setattr(vigencia,'datetime',Reloj)
    assert c.get(f'/api/v1/unidades/{u["id"]}/vigencia').json()['estado']=='VENCIDA'
    u = actual(c,u)
    assert c.post(f'/api/v1/unidades/{u["id"]}/admisiones',headers=h(),json={**rev(u),'tipo':'INGRESO','id_evaluacion':r2['evaluacion']['id']}).status_code==409


def test_usuario_inactivo_y_traslado_ajeno(api_real,url_bd):
    c,h,usuarios=api_real
    u=unidad(c)
    c.headers.update(h('AJENO'))
    ajena=unidad(c)
    c.headers.update(h())
    body={k:u[k] for k in ('id_lote','id_almacen','nombre_recipiente','tipo_almacenamiento')}
    body['id_almacen']=ajena['id_almacen']
    assert c.patch('/api/v1/unidades/'+u['id'],json=body,headers={'If-Match':'"1"'}).status_code==404
    with Session(create_engine(url_bd)) as db,db.begin():
        db.get(Usuario,usuarios['AJENO']).activo=False
    assert c.get('/api/v1/me',headers=h('AJENO')).status_code==403


def test_valores_estrictos_y_fecha_sin_zona(api_real):
    c,h,_=api_real
    u=unidad(c)
    body=entrada(u,{'moho_visible':True})
    body['observaciones'][0]['valor']='true'
    assert c.post(f'/api/v1/unidades/{u["id"]}/evaluaciones',json=body,headers=h()).status_code==422
    body['observaciones'][0]['valor']=True
    body['observaciones'][0]['fecha_observacion']='2026-01-01T10:00:00'
    assert c.post(f'/api/v1/unidades/{u["id"]}/evaluaciones',json=body,headers=h()).status_code==422
