import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { list, request, write, revisiones, fecha, nombre, decision, type Schema, type Unidad, type Resultado } from '../api/client'
import Panel, { Empty, ErrorMessage, Field, Loading } from '../components/Shared'
import Captura, { ahoraLocal, convertir, type CapturaDatos } from '../components/Captura'
import { useAppNavigate, useId } from '../App'

export default function Seguimiento() {
  const id = useId(), navigate = useAppNavigate()
  const unidades = useQuery({ queryKey: ['unidades'], queryFn: () => list<Unidad>('/unidades') })
  if (!id) return <Panel title="Seguimiento por unidad"><ErrorMessage error={unidades.error} /><Field label="Unidad"><select value="" onChange={e => navigate('seguimiento', e.target.value)}><option value="">Seleccionar</option>{unidades.data?.map(u => <option key={u.id} value={u.id}>{u.nombre_recipiente}</option>)}</select></Field></Panel>
  return <Detalle key={id} id={id} />
}
function Detalle({ id }: { id: string }) {
  const navigate = useAppNavigate(), qc = useQueryClient()
  const perfil = qc.getQueryData<Schema['Perfil']>(['perfil'])
  const [action, setAction] = useState(''), [error, setError] = useState<unknown>(null), [busy, setBusy] = useState(false), [message, setMessage] = useState('')
  const [datos, setDatos] = useState<CapturaDatos>({})
  const [form, setForm] = useState({ tipoControl: 'GRANO', tipoEvento: 'APERTURA', fecha: ahoraLocal(), evidencia: '', proximo: '', salida: '', intervalo: '', actividades: '', humedadMin: '', humedadMax: '', plazo: '', vence: '', condiciones: '', incidencia: '', resultado: 'PENDIENTE', disposicion: '', tipoAdmision: 'INGRESO' })
  const set = (k: keyof typeof form, v: string) => setForm(f => ({ ...f, [k]: v }))
  const storageKey = `seguimiento:${perfil?.id}:${id}`
  const [restored, setRestored] = useState(false)
  useEffect(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(storageKey) || 'null')
      if (saved) { setForm(saved.form); setDatos(saved.datos); setAction(saved.action) }
    } catch { /* Una captura local corrupta no impide consultar el historial. */ }
    setRestored(true)
  }, [storageKey])
  useEffect(() => { if (restored) sessionStorage.setItem(storageKey, JSON.stringify({ form, datos, action })) }, [storageKey, restored, form, datos, action])
  const data = useQuery({ queryKey: ['seguimiento', id], queryFn: async () => {
    const [u, historial, controles, planes, dictamenes, incidencias, eventos, vigencia] = await Promise.all([
      request<Unidad>(`/unidades/${id}`), list<Resultado>(`/unidades/${id}/historial`), list<Schema['Control']>(`/unidades/${id}/controles`), list<Schema['Plan']>(`/unidades/${id}/planes`), list<Schema['Dictamen']>(`/unidades/${id}/dictamenes`), list<Schema['Incidencia']>(`/unidades/${id}/incidencias`), list<{id: string; tipo: string; fecha: string; evidencia: string}>(`/unidades/${id}/eventos`), request<Schema['Vigencia']>(`/unidades/${id}/vigencia`),
    ])
    return { u, historial, controles, planes, dictamenes, incidencias, eventos, vigencia }
  } })
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError(null); setMessage('')
    try {
      if (!data.data) throw new Error('Espera a que cargue la unidad')
      const revisions = revisiones(data.data.u)
      let path = `/unidades/${id}/${action}`, body: unknown
      if (action === 'controles') body = { ...revisions, tipo: form.tipoControl, fecha: new Date(form.fecha).toISOString(), evidencia: form.evidencia, observaciones: convertir(datos) }
      else if (action === 'eventos') body = { ...revisions, tipo: form.tipoEvento, fecha: new Date(form.fecha).toISOString(), evidencia: form.evidencia }
      else if (action === 'planes') body = { ...revisions, fecha_proximo_control: new Date(form.proximo).toISOString(), fecha_salida_prevista: new Date(form.salida).toISOString(), intervalo_dias: Number(form.intervalo), actividades: form.actividades }
      else if (action === 'dictamenes') body = { ...revisions, humedad_min: Number(form.humedadMin.replace(',', '.')), humedad_max: Number(form.humedadMax.replace(',', '.')), plazo_maximo_dias: Number(form.plazo), vence_en: new Date(form.vence).toISOString(), condiciones: form.condiciones, evidencia: form.evidencia }
      else if (action === 'admisiones') body = { ...revisions, id_evaluacion: data.data.u.id_evaluacion_actual, tipo: form.tipoAdmision }
      else {
        const incidencia = data.data.incidencias.find(i => i.id === form.incidencia)
        if (!incidencia) throw new Error('Selecciona una incidencia')
        path = `/incidencias/${incidencia.id}/${action}`
        body = { ...revisions, revision_incidencia: incidencia.revision, evidencia: form.evidencia, ...(action === 'revisiones' ? { resultado: form.resultado } : { disposicion: form.disposicion }) }
      }
      const result = await write<{completo?: boolean; campos_pendientes?: string[]}>(path, body)
      setMessage(action === 'controles' ? (result.completo ? 'Control completo registrado. Reevalúa la unidad.' : `Control parcial registrado. Pendientes: ${result.campos_pendientes?.map(nombre).join(', ')}. Reevalúa para obtener la decisión.`) : action === 'admisiones' ? 'Admisión registrada con autorización vigente.' : 'Registro guardado. Reevalúa la unidad para conocer su nueva decisión.')
      await qc.invalidateQueries()
    } catch (err) { setError(err) } finally { setBusy(false) }
  }
  if (data.isLoading) return <Loading />
  if (!data.data) return <ErrorMessage error={data.error} />
  const d = data.data, tecnico = perfil?.roles.includes('TECNICO')
  return <div className="stack"><div className="page-heading"><div><p className="eyebrow">Historial y actuaciones</p><h1>Seguimiento</h1><p>{d.u.nombre_recipiente} · <span className="badge">{nombre(d.vigencia.estado)}</span></p></div><button className="primary" onClick={() => navigate('evaluacion', id)}>Reevaluar unidad</button></div>
    <ErrorMessage error={error || data.error} />{message && <p className="message" role="status">{message}</p>}
    <div className="actions">{[['controles','Registrar control'],['eventos','Registrar evento'],['planes','Plan de monitoreo'],...(tecnico ? [['dictamenes','Dictamen técnico'],['revisiones','Revisar incidencia'],['resoluciones','Resolver incidencia']] : []),['admisiones','Registrar admisión']].map(([k,label]) => <button key={k} className={action === k ? 'primary' : ''} onClick={() => setAction(action === k ? '' : k)}>{label}</button>)}<button onClick={() => void data.refetch()}>Actualizar datos</button></div>
    {action && <Panel title={nombre(action)}><form className="stack" onSubmit={e => void submit(e)}><div className="form-grid">
      {action === 'controles' && <Field label="Tipo de control"><select value={form.tipoControl} onChange={e => set('tipoControl',e.target.value)}>{['INGRESO','GRANO','EXTERIOR','ALMACEN'].map(t => <option key={t}>{t}</option>)}</select></Field>}
      {action === 'eventos' && <Field label="Tipo de evento"><select value={form.tipoEvento} onChange={e => set('tipoEvento',e.target.value)}>{['LIMPIEZA_GENERAL','APERTURA','RESELLADO','SECADO','ENFRIAMIENTO','EXPOSICION_AGUA','CARGA_DESCARGA'].map(t => <option key={t}>{t}</option>)}</select></Field>}
      {['controles','eventos'].includes(action) && <Field label="Fecha de la actuación"><input required type="datetime-local" value={form.fecha} onChange={e => set('fecha', e.target.value)} /></Field>}
      {['controles','eventos','dictamenes','revisiones','resoluciones'].includes(action) && <Field label="Evidencia de la actuación"><textarea required value={form.evidencia} onChange={e => set('evidencia',e.target.value)} /></Field>}
      {action === 'planes' && <><Field label="Fecha del próximo control"><input required type="datetime-local" value={form.proximo} onChange={e => set('proximo',e.target.value)} /></Field><Field label="Fecha de salida prevista"><input required type="datetime-local" value={form.salida} onChange={e => set('salida',e.target.value)} /></Field><Field label="Intervalo entre controles (días)"><input required type="number" min="1" max="365" value={form.intervalo} onChange={e => set('intervalo',e.target.value)} /></Field><Field label="Actividades de monitoreo"><textarea required value={form.actividades} onChange={e => set('actividades',e.target.value)} /></Field></>}
      {action === 'dictamenes' && <>{(['humedadMin','humedadMax','plazo','vence','condiciones'] as const).map((k,i) => <Field key={k} label={['Humedad mínima (%)','Humedad máxima (%)','Plazo máximo (días)','Vencimiento del dictamen','Condiciones del dictamen'][i]}><input required type={k === 'vence' ? 'datetime-local' : 'text'} value={form[k]} onChange={e => set(k,e.target.value)} /></Field>)}</>}
      {['revisiones','resoluciones'].includes(action) && <><Field label="Incidencia abierta"><select required value={form.incidencia} onChange={e => set('incidencia', e.target.value)}><option value="">Seleccionar</option>{d.incidencias.filter(i => i.estado === 'ABIERTA').map(i => <option key={i.id} value={i.id}>{nombre(i.tipo)} · {fecha(i.creada_en)}</option>)}</select></Field>{action === 'revisiones' ? <Field label="Resultado de la revisión"><select value={form.resultado} onChange={e => set('resultado',e.target.value)}>{['PENDIENTE','CONFIRMADA','DESCARTADA'].map(t => <option key={t}>{t}</option>)}</select></Field> : <Field label="Disposición y fundamento del cierre"><textarea required value={form.disposicion} onChange={e => set('disposicion',e.target.value)} /></Field>}</>}
      {action === 'admisiones' && <><Field label="Tipo de admisión"><select value={form.tipoAdmision} onChange={e => set('tipoAdmision',e.target.value)}><option>INGRESO</option><option>CONTINUIDAD</option></select></Field><p>El servidor comprobará nuevamente la vigencia antes de registrar la admisión.</p></>}
    </div>{action === 'controles' && <><p>Registra los campos inspeccionados. El servidor identifica si el control está completo. En hermético usa el control exterior sin abrir rutinariamente.</p><Captura datos={datos} onChange={setDatos} /></>}
    <button className="primary" disabled={busy || (action === 'admisiones' && d.vigencia.estado !== 'VIGENTE')}>{busy ? 'Guardando…' : 'Guardar actuación'}</button></form></Panel>}
    <Panel title="Incidencias">{d.incidencias.length ? d.incidencias.map(i => <div key={i.id} className="reason"><strong>{nombre(i.tipo)} · {nombre(i.estado)}</strong><p>{i.causas.join(', ')} · {fecha(i.creada_en)}</p><IncidenciaHistorial id={i.id} /></div>) : <Empty>No hay incidencias registradas.</Empty>}</Panel>
    <Panel title="Historial de evaluaciones">{d.historial.length ? d.historial.map(r => <div className="row" key={r.evaluacion.id}><div><strong>{decision(r.evaluacion.decision_final)}</strong><small>{fecha(r.evaluacion.fecha_evaluacion)} · {nombre(r.vigencia.estado)}</small></div><button onClick={() => navigate('resultado',r.evaluacion.id)}>Ver explicación</button></div>) : <Empty>No hay evaluaciones registradas.</Empty>}</Panel>
    <Panel title="Controles">{d.controles.length ? d.controles.map(c => <div className="row" key={c.id}><span>{nombre(c.tipo)} · {fecha(c.fecha)}<small>{c.completo ? 'Completo' : `Parcial: ${c.campos_pendientes.map(nombre).join(', ')}`}</small></span><p>{c.evidencia}</p></div>) : <Empty>No hay controles.</Empty>}</Panel>
    <Panel title="Planes de monitoreo">{d.planes.map(p => <div className="row" key={p.id}><p>{p.actividades}<small>{p.vigente ? 'Activo' : 'Sustituido'} · cada {p.intervalo_dias} días · control {fecha(p.fecha_proximo_control)}</small></p></div>)}{!d.planes.length && <Empty>No hay planes.</Empty>}</Panel>
    <Panel title="Dictámenes técnicos">{d.dictamenes.map(d => <div className="row" key={d.id}><p>{d.condiciones}<small>{d.humedad_min}–{d.humedad_max} % · plazo {d.plazo_maximo_dias} días · vence {fecha(d.vence_en)} · {d.vigente ? 'Vigente' : 'Vencido'}</small></p></div>)}{!d.dictamenes.length && <Empty>No hay dictámenes.</Empty>}</Panel>
    <Panel title="Eventos">{d.eventos.map(e => <div className="row" key={e.id}><span>{nombre(e.tipo)} · {fecha(e.fecha)}</span><p>{e.evidencia}</p></div>)}{!d.eventos.length && <Empty>No hay eventos.</Empty>}</Panel>
  </div>
}
function IncidenciaHistorial({ id }: { id: string }) {
  const [open,setOpen] = useState(false)
  const data = useQuery({ queryKey:['incidencia-historial',id], enabled:open, queryFn:async () => ({ revisiones:await list<Schema['Revision']>(`/incidencias/${id}/revisiones`), resoluciones:await list<Schema['Resolucion']>(`/incidencias/${id}/resoluciones`) }) })
  return <details onToggle={e => setOpen(e.currentTarget.open)}><summary>Revisiones y resoluciones</summary><ErrorMessage error={data.error}/>{data.data?.revisiones.map(r => <p key={r.id}>{fecha(r.fecha)} · {r.resultado} · {r.evidencia}</p>)}{data.data?.resoluciones.map(r => <p key={r.id}>{fecha(r.fecha)} · {r.disposicion} · {r.evidencia}</p>)}</details>
}
