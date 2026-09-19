import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, list, request, write, revisiones, type Unidad, type EvaluacionEntrada, type Resultado, type Schema } from '../api/client'
import Panel, { ErrorMessage, Field, Loading } from '../components/Shared'
import Captura, { convertir, desdeObservaciones, fechaLocal, type CapturaDatos } from '../components/Captura'
import { useAppNavigate, useId } from '../App'
import EditarUnidad from '../components/EditarUnidad'

const steps = ['Identificación', 'Mediciones', 'Inspección biológica', 'Recipiente y almacén', 'Historial y plan', 'Revisión final']
const blank = () => ({ datos: {} as CapturaDatos, fase: '' as '' | 'INGRESO' | 'SEGUIMIENTO', dias: '', salida: '', inicio: '', vida: '', evidencia: '', intervalos: [] as { inicio: string; fin: string; humedad: string; temperatura: string; metodo: string; evidencia: string }[] })
export default function Evaluacion() {
  const id = useId(), navigate = useAppNavigate()
  const unidades = useQuery({ queryKey: ['unidades'], queryFn: () => list<Unidad>('/unidades') })
  if (!id) return <Panel title="Selecciona una unidad para evaluar"><ErrorMessage error={unidades.error} /><Field label="Unidad"><select value="" onChange={e => navigate('evaluacion', e.target.value)}><option value="">Seleccionar</option>{unidades.data?.map(u => <option key={u.id} value={u.id}>{u.nombre_recipiente}</option>)}</select></Field></Panel>
  return <Formulario key={id} id={id} />
}
function Formulario({ id }: { id: string }) {
  const navigate = useAppNavigate(), qc = useQueryClient()
  const perfil = qc.getQueryData<Schema['Perfil']>(['perfil'])
  const key = `captura:${perfil?.id}:${id}`
  const habiaCapturaLocal = useRef(!!sessionStorage.getItem(key))
  const [form, setForm] = useState(() => { try { return JSON.parse(sessionStorage.getItem(key) || 'null') as ReturnType<typeof blank> || blank() } catch { return blank() } })
  const [step, setStep] = useState(1), [busy, setBusy] = useState(false), [error, setError] = useState<unknown>(null), [message, setMessage] = useState('')
  const [draftRevision, setDraftRevision] = useState<number | null>(null)
  const [draftLoaded, setDraftLoaded] = useState(false)
  const unidad = useQuery({ queryKey: ['unidad', id], queryFn: () => request<Unidad>(`/unidades/${id}`) })
  useEffect(() => { sessionStorage.setItem(key, JSON.stringify(form)) }, [key, form])
  useEffect(() => {
    let active = true
    request<Schema['Borrador']>(`/unidades/${id}/borrador`).then(b => {
      if (!active) return
      setDraftRevision(b.revision)
      if (!habiaCapturaLocal.current) restore(b.contenido)
      else setMessage('Hay una captura local y un borrador en el servidor. Puedes recuperar el borrador guardado.')
    }).catch(err => { if (active && (!(err instanceof ApiError) || err.status !== 404)) setError(err) }).finally(() => { if (active) setDraftLoaded(true) })
    return () => { active = false }
  }, [id, key])
  function restore(b: EvaluacionEntrada) {
    setForm({ datos: desdeObservaciones(b.observaciones), fase: b.fase || '', dias: b.dias_previstos_restantes?.toString() || '', salida: b.fecha_salida_prevista ? fechaLocal(b.fecha_salida_prevista) : '', inicio: b.historial.fecha_inicio_historial ? fechaLocal(b.historial.fecha_inicio_historial) : '', vida: b.historial.vida_previa_documentada?.toString() || '', evidencia: b.historial.evidencia_vida_previa || '', intervalos: b.historial.intervalos_historial.map(i => ({ inicio: fechaLocal(i.inicio), fin: fechaLocal(i.fin), humedad: i.humedad_grano?.toString() || '', temperatura: i.temperatura_grano?.toString() || '', metodo: i.metodo || '', evidencia: i.evidencia || '' })) })
    setMessage('Borrador recuperado.')
  }
  function body(): EvaluacionEntrada {
    if (!unidad.data) throw new Error('Espera a que cargue la unidad')
    const numero = (v: string) => { if (!v) return null; const n = Number(v.replace(',', '.')); if (!Number.isFinite(n)) throw new Error('Revisa los valores numéricos'); return n }
    return { ...revisiones(unidad.data), fase: form.fase || null, observaciones: convertir(form.datos), dias_previstos_restantes: numero(form.dias), fecha_salida_prevista: form.salida ? new Date(form.salida).toISOString() : null,
      historial: { fecha_inicio_historial: form.inicio ? new Date(form.inicio).toISOString() : null, vida_previa_documentada: numero(form.vida), evidencia_vida_previa: form.evidencia || null, intervalos_historial: form.intervalos.map(i => ({ inicio: new Date(i.inicio).toISOString(), fin: new Date(i.fin).toISOString(), humedad_grano: numero(i.humedad), temperatura_grano: numero(i.temperatura), metodo: i.metodo || null, evidencia: i.evidencia || null })) } }
  }
  async function submit(draft: boolean) {
    setBusy(true); setError(null); setMessage('')
    try {
      if (draft) {
        const b = await write<Schema['Borrador']>(`/unidades/${id}/borrador`, body(), 'PUT', draftRevision ? { 'If-Match': `"${draftRevision}"` } : { 'If-None-Match': '*' })
        setDraftRevision(b.revision); setMessage('Borrador guardado en el servidor. No constituye una evaluación.')
      } else {
        const result = await write<Resultado>(`/unidades/${id}/evaluaciones`, body())
        sessionStorage.removeItem(key); await qc.invalidateQueries(); navigate('resultado', result.evaluacion.id)
      }
    } catch (err) { setError(err) } finally { setBusy(false) }
  }
  const set = (k: keyof typeof form, v: string) => setForm(f => ({ ...f, [k]: v }))
  if (unidad.isLoading || !draftLoaded) return <Loading />
  return <div className="stack"><div className="page-heading"><div><p className="eyebrow">Captura guiada · P{step}</p><h1>Evaluar unidad</h1><p>{unidad.data?.nombre_recipiente}</p></div><button disabled={busy} onClick={() => void submit(true)}>Guardar borrador</button></div>
    <div className="steps">{steps.map((s, i) => <button key={s} className={step === i + 1 ? 'active' : ''} aria-current={step === i + 1 ? 'step' : undefined} onClick={() => setStep(i + 1)}><b>P{i + 1}</b><span>{s}</span></button>)}</div>
    <ErrorMessage error={error || unidad.error} />{message && <p role="status" className="message">{message}</p>}
    <div className="actions"><button onClick={() => { void unidad.refetch(); setMessage('Revisiones actualizadas; comprueba los datos antes de reenviar.') }}>Actualizar revisiones</button>{draftRevision && <button onClick={() => void request<Schema['Borrador']>(`/unidades/${id}/borrador`).then(b => { setDraftRevision(b.revision); restore(b.contenido) }).catch(setError)}>Recuperar borrador guardado</button>}</div>
    <Panel title={steps[step - 1]}><p className="muted">No se sabe es diferente de No. Puedes enviar información parcial: un hallazgo de moho no necesita esperar las otras mediciones.</p>
      {step === 1 && <div className="form-grid"><Field label="Fase"><select value={form.fase} onChange={e => set('fase', e.target.value)}><option value="">Sin definir</option><option value="INGRESO">Ingreso</option><option value="SEGUIMIENTO">Seguimiento</option></select></Field><div><p>Modalidad: {unidad.data?.tipo_almacenamiento || 'Sin definir'}</p><p>Maíz chulpi · Alimentación</p><p>Responsable: {perfil?.nombre}</p></div></div>}
      {step === 1 && unidad.data && <EditarUnidad unidad={unidad.data} />}
      {step >= 2 && step <= 5 && <Captura paso={step} datos={form.datos} onChange={datos => setForm(f => ({ ...f, datos }))} />}
      {step === 5 && <div className="stack"><h3>Tiempo documentado</h3><p>La vida previa es una fracción del tiempo de referencia, nunca un porcentaje de seguridad. El cero requiere constancia de origen.</p><div className="form-grid">
        <Field label="Inicio del historial"><input type="datetime-local" value={form.inicio.slice(0,16)} onChange={e => set('inicio', e.target.value)} /></Field><Field label="Vida previa documentada (fracción)"><input inputMode="decimal" value={form.vida} onChange={e => set('vida', e.target.value)} /></Field><Field label="Evidencia de la vida previa"><input value={form.evidencia} onChange={e => set('evidencia', e.target.value)} /></Field><Field label="Días previstos restantes"><input inputMode="numeric" value={form.dias} onChange={e => set('dias', e.target.value)} /></Field><Field label="Salida prevista"><input type="datetime-local" value={form.salida.slice(0,16)} onChange={e => set('salida', e.target.value)} /></Field></div>
        <h3>Intervalos del historial</h3>{form.intervalos.map((item, i) => <div className="panel form-grid" key={i}>{Object.entries(item).map(([k, v]) => <Field key={k} label={`${k} · intervalo ${i + 1}`}><input type={k === 'inicio' || k === 'fin' ? 'datetime-local' : 'text'} value={v} onChange={e => setForm(f => ({ ...f, intervalos: f.intervalos.map((it, n) => n === i ? { ...it, [k]: e.target.value } : it) }))} /></Field>)}<button onClick={() => setForm(f => ({ ...f, intervalos: f.intervalos.filter((_, n) => n !== i) }))}>Quitar intervalo</button></div>)}
        <button onClick={() => setForm(f => ({ ...f, intervalos: [...f.intervalos, { inicio: '', fin: '', humedad: '', temperatura: '', metodo: '', evidencia: '' }] }))}>Añadir intervalo</button><p>Los planes de monitoreo y dictámenes se registran desde Seguimiento.</p></div>}
      {step === 6 && <><p>{Object.values(form.datos).filter(d => d.captura === 'APORTADO').length} observaciones aportadas. Los campos omitidos permanecen desconocidos o conservan su dato histórico identificado por el servidor.</p><div className="review-list">{Object.entries(form.datos).map(([k,v]) => <p key={k}><strong>{k.replaceAll('_', ' ')}:</strong> {v.captura === 'APORTADO' ? v.valor : v.captura}</p>)}</div><p>La decisión y su vigencia se calcularán en el servidor.</p></>}
    </Panel><div className="actions sticky-actions"><button disabled={step === 1} onClick={() => setStep(s => s - 1)}>Anterior</button>{step < 6 && <button onClick={() => setStep(s => s + 1)}>Siguiente</button>}<button className="primary" disabled={busy || !unidad.data} onClick={() => void submit(false)}>{busy ? 'Guardando…' : 'Enviar y evaluar'}</button></div>
  </div>
}
