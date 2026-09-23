import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { request, fecha, nombre, decision, tieneRol, type Schema } from '../api/client'
import Panel, { Empty, ErrorMessage, Field, Loading } from '../components/Shared'

type Resultado = Schema['PropuestaResultado']
type Version = Schema['VersionConocimientoResumen']

const post = <T,>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) })

/**
 * Módulo de adquisición del conocimiento.
 * El ingeniero del conocimiento modifica la base sin tocar el motor: propone,
 * el sistema valida y mide el impacto sobre casos de referencia y evaluaciones
 * reales, y solo entonces se registra y activa la nueva versión.
 */
export default function Adquisicion() {
  const qc = useQueryClient()
  const perfil = qc.getQueryData<Schema['Perfil']>(['perfil'])
  const permitido = tieneRol(perfil, 'INGENIERO_CONOCIMIENTO')
  const catalogo = useQuery({ queryKey: ['conocimiento'], queryFn: () => request<Schema['Catalogo']>('/conocimiento') })
  const versiones = useQuery({ queryKey: ['versiones'], queryFn: () => request<Version[]>('/adquisicion/versiones'), enabled: permitido })
  const activa = versiones.data?.find(v => v.activa)
  const detalle = useQuery({ queryKey: ['version', activa?.id], queryFn: () => request<Schema['DetalleVersion']>(`/adquisicion/versiones/${activa!.id}`), enabled: !!activa })

  const [valores, setValores] = useState<Record<string, string>>({})
  const [motivo, setMotivo] = useState(''), [versionParametros, setVersionParametros] = useState(''), [versionBase, setVersionBase] = useState('')
  const [reglaId, setReglaId] = useState(''), [reglaTexto, setReglaTexto] = useState(''), [avanzado, setAvanzado] = useState(false)
  const [resultado, setResultado] = useState<Resultado | null>(null), [error, setError] = useState<unknown>(null), [busy, setBusy] = useState(false)
  const [motivoActivacion, setMotivoActivacion] = useState<Record<string, string>>({})

  if (!permitido) return <Panel title="Adquisición del conocimiento"><p>Esta función corresponde al rol de ingeniería del conocimiento. Los umbrales y las reglas no se modifican desde la captura ni desde el seguimiento.</p></Panel>
  if (catalogo.isLoading || versiones.isLoading) return <Loading />
  const parametros = catalogo.data?.parametros || []

  function cuerpo(guardar: boolean) {
    const cambios: Record<string, number> = {}
    for (const [k, v] of Object.entries(valores)) {
      if (v.trim() === '') continue
      const n = Number(v.replace(',', '.'))
      if (!Number.isFinite(n)) throw new Error(`El valor de ${k} no es un número`)
      cambios[k] = n
    }
    const reglas: Record<string, Record<string, unknown> | null> = {}
    if (avanzado && reglaId) {
      try { reglas[reglaId] = reglaTexto.trim() === '' ? null : JSON.parse(reglaTexto) }
      catch { throw new Error('La definición de la regla no es JSON válido') }
    }
    return { motivo, parametros: cambios, reglas, version_parametros: versionParametros || null, version_base: versionBase || null, guardar }
  }
  async function enviar(guardar: boolean) {
    setBusy(true); setError(null)
    try {
      const r = await post<Resultado>('/adquisicion/propuestas', cuerpo(guardar))
      setResultado(r)
      if (r.version) await qc.invalidateQueries({ queryKey: ['versiones'] })
    } catch (err) { setError(err) } finally { setBusy(false) }
  }
  async function activar(v: Version) {
    setBusy(true); setError(null)
    try {
      await post<Version>(`/adquisicion/versiones/${v.id}/activar`, { motivo: motivoActivacion[v.id] || '' })
      setResultado(null); setValores({})
      await qc.invalidateQueries()
    } catch (err) { setError(err) } finally { setBusy(false) }
  }
  function cargarRegla(id: string) {
    setReglaId(id)
    const regla = detalle.data?.reglas.find(r => r.id === id)
    setReglaTexto(regla ? JSON.stringify(regla, null, 2) : '')
  }

  return <div className="stack">
    <div className="page-heading"><div><p className="eyebrow">Módulo de adquisición del conocimiento</p><h1>Mantener la base de conocimiento</h1>
      <p className="muted">Activa: base {activa?.version_base} · parámetros {activa?.version_parametros} · huella {activa?.hash_base.slice(0, 12)}</p></div></div>
    <p className="message">Un cambio aquí altera lo que el sistema decide para las evaluaciones futuras. Las evaluaciones ya emitidas conservan la versión con que se resolvieron.</p>
    <ErrorMessage error={error || catalogo.error || versiones.error} />

    <Panel title="1. Proponer cambios de parámetros">
      <div className="table-scroll"><table className="parametros"><thead><tr><th>Parámetro</th><th>Descripción</th><th>Fundamento</th><th>Actual</th><th>Propuesto</th></tr></thead><tbody>
        {parametros.map(p => <tr key={p.nombre} className={valores[p.nombre] ? 'modificado' : ''}><td><code>{p.nombre}</code></td><td>{p.descripcion}<small>{nombre(p.unidad)}</small></td><td>{nombre(p.fundamento)}{p.fuentes.length > 0 && <small>{p.fuentes.join(', ')}</small>}</td><td>{p.valor}</td>
          <td><input aria-label={`Nuevo valor de ${p.nombre}`} inputMode="decimal" value={valores[p.nombre] || ''} placeholder="Sin cambio" onChange={e => setValores(v => ({ ...v, [p.nombre]: e.target.value }))} /></td></tr>)}
      </tbody></table></div>
      <label className="check"><input type="checkbox" checked={avanzado} onChange={e => setAvanzado(e.target.checked)} />Modificar también una regla de producción (avanzado)</label>
      {avanzado && <div className="stack">
        <Field label="Regla de producción"><select value={reglaId} onChange={e => cargarRegla(e.target.value)}><option value="">Seleccionar</option>{detalle.data?.reglas.map(r => <option key={String(r.id)} value={String(r.id)}>{String(r.id)}</option>)}</select></Field>
        <Field label="Definición (JSON). Vacío retira la regla."><textarea rows={14} spellCheck={false} value={reglaTexto} onChange={e => setReglaTexto(e.target.value)} style={{ fontFamily: 'monospace', fontSize: 12 }} /></Field>
        <p className="muted">Un cambio de reglas exige una nueva versión de la base. El validador rechaza operadores, parámetros o definiciones que no existan.</p>
      </div>}
      <div className="form-grid">
        <Field label="Motivo del cambio (obligatorio)"><textarea required minLength={15} value={motivo} onChange={e => setMotivo(e.target.value)} placeholder="Fuente, revisión técnica o evidencia que justifica el cambio" /></Field>
        <Field label="Nueva versión de parámetros"><input value={versionParametros} onChange={e => setVersionParametros(e.target.value)} placeholder={`Actual ${activa?.version_parametros}`} /></Field>
        {avanzado && <Field label="Nueva versión de la base"><input value={versionBase} onChange={e => setVersionBase(e.target.value)} placeholder={`Actual ${activa?.version_base}`} /></Field>}
      </div>
      <div className="actions"><button disabled={busy} onClick={() => void enviar(false)}>{busy ? 'Evaluando casos…' : 'Simular impacto'}</button><button className="primary" disabled={busy || !resultado?.valida} onClick={() => void enviar(true)}>Registrar propuesta</button></div>
      <p className="muted">La simulación evalúa los casos de referencia y las últimas evaluaciones emitidas con la versión activa y con la propuesta. Puede tardar unos segundos.</p>
    </Panel>

    {resultado && <Panel title="2. Validación e impacto">
      {resultado.valida ? <p className="message">Propuesta válida · versión {resultado.version_base}/{resultado.version_parametros}{resultado.version ? ' · registrada como propuesta' : ''}</p>
        : <div className="aviso"><strong>La propuesta no es válida:</strong><ul>{resultado.errores.map((e, i) => <li key={i}>{e}</li>)}</ul></div>}
      {resultado.advertencias.map((a, i) => <p className="aviso" key={i}>⚠ {a}</p>)}
      {resultado.cambios_parametros.length > 0 && <div className="chips">{resultado.cambios_parametros.map(c => <span className="chip cambio" key={c.nombre}>{c.nombre}: {c.anterior} → {c.nuevo}</span>)}</div>}
      {resultado.cambios_reglas.length > 0 && <div className="chips">{resultado.cambios_reglas.map(c => <span className="chip cambio" key={c.produccion}>{nombre(c.tipo)}: {c.produccion}</span>)}</div>}
      {resultado.impacto && <>
        <div className="metrics"><div><span>Casos evaluados</span><strong>{resultado.impacto.evaluados}</strong></div><div><span>Cambian de decisión</span><strong>{resultado.impacto.cambian}</strong></div><div><span>Nuevas autorizaciones</span><strong>{resultado.impacto.nuevas_autorizaciones}</strong></div></div>
        {Object.entries(resultado.impacto.transiciones).map(([t, n]) => <p className="row" key={t}><span>{t.split(' → ').map(decision).join(' → ')}</span><strong>{n}</strong></p>)}
        {resultado.impacto.casos.length > 0 && <details><summary>Casos afectados ({resultado.impacto.casos.length})</summary><div className="table-scroll"><table><thead><tr><th>Caso</th><th>Antes</th><th>Después</th><th>Reglas</th></tr></thead><tbody>
          {resultado.impacto.casos.map(c => <tr key={c.id}><td><small>{c.origen}</small>{c.id.split(':').slice(1).join(':')}</td><td>{decision(c.decision_antes)}<small>{c.rama_antes}</small></td><td>{decision(c.decision_despues)}<small>{c.rama_despues}</small></td><td>{c.reglas_nuevas.map(r => '+' + r).concat(c.reglas_retiradas.map(r => '−' + r)).join(' ')}</td></tr>)}
        </tbody></table></div></details>}
        {resultado.impacto.cambian === 0 && <p className="muted">Ningún caso cambia de decisión. Revisa si el cambio tiene efecto en la práctica.</p>}
      </>}
    </Panel>}

    <Panel title="3. Versiones">{versiones.data?.length ? versiones.data.map(v => <div className="reason" key={v.id}>
      <p><strong>Base {v.version_base} · parámetros {v.version_parametros}</strong> <span className={`badge ${v.activa ? 'good' : ''}`}>{v.activa ? 'Activa' : nombre(v.estado)}</span></p>
      <p className="muted">{v.motivo || 'Sin motivo registrado'} · cargada {fecha(v.cargada_en)}{v.activada_en ? ` · activada ${fecha(v.activada_en)}` : ''} · motor {v.version_motor} · {v.hash_base.slice(0, 12)}</p>
      {!v.activa && v.estado === 'PROPUESTA' && <div className="form-grid"><Field label="Motivo de la activación"><input value={motivoActivacion[v.id] || ''} onChange={e => setMotivoActivacion(m => ({ ...m, [v.id]: e.target.value }))} placeholder="Revisión y aprobación de la propuesta" /></Field>
        <div className="actions"><button className="primary" disabled={busy || (motivoActivacion[v.id] || '').length < 15} onClick={() => void activar(v)}>Activar esta versión</button></div></div>}
    </div>) : <Empty>No hay versiones registradas.</Empty>}</Panel>
  </div>
}
