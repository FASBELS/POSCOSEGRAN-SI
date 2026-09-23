import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { list, request, write, nombre, fecha, NOTA_PROTOTIPO, type Schema, type Unidad } from '../api/client'
import Panel, { Empty, ErrorMessage, Field, Loading } from '../components/Shared'
import { useAppNavigate } from '../App'

export default function Dashboard() {
  const navigate = useAppNavigate(), qc = useQueryClient()
  const [error, setError] = useState<unknown>(null), [busy, setBusy] = useState(false), [show, setShow] = useState(false)
  const data = useQuery({ queryKey: ['inicio'], queryFn: async () => {
    const [inicio, almacenes, lotes, unidades, perfil] = await Promise.all([
      request<Schema['Inicio']>('/inicio'), list<Schema['Almacen']>('/almacenes'), list<Schema['Lote']>('/lotes'), list<Unidad>('/unidades'), request<Schema['Perfil']>('/me'),
    ])
    const vigencias = await Promise.all(unidades.map(u => request<Schema['Vigencia']>(`/unidades/${u.id}/vigencia`)))
    return { inicio, almacenes, lotes, unidades, perfil, vigencias }
  } })
  const [form, setForm] = useState({ nombre: '', ubicacion: '', clima: '', fundamento: '', codigo: '', almacen: '', lote: '', recipiente: '', modalidad: '' })
  const set = (k: keyof typeof form, v: string) => setForm(f => ({ ...f, [k]: v }))
  async function save(e: React.FormEvent, kind: 'almacenes' | 'lotes' | 'unidades') {
    e.preventDefault(); setBusy(true); setError(null)
    try {
      const body = kind === 'almacenes' ? { nombre: form.nombre, ubicacion: form.ubicacion, clima_calido: form.clima === '' ? null : form.clima === 'si', fundamento_clima: form.fundamento || null }
        : kind === 'lotes' ? { codigo: form.codigo, variedad: 'MAIZ_CHULPI', uso_final: 'ALIMENTACION' }
        : { id_lote: form.lote, id_almacen: form.almacen, nombre_recipiente: form.recipiente, tipo_almacenamiento: form.modalidad || null }
      const created = await write<{ id: string }>(`/${kind}`, body)
      if (kind === 'almacenes') set('almacen', created.id)
      if (kind === 'lotes') set('lote', created.id)
      await qc.invalidateQueries()
      if (kind === 'unidades') navigate('evaluacion', created.id)
    } catch (err) { setError(err) } finally { setBusy(false) }
  }
  if (data.isLoading) return <Loading />
  if (!data.data) return <ErrorMessage error={data.error} />
  const d = data.data
  return <div className="stack"><div className="page-heading"><div><p className="eyebrow">Control del almacenamiento</p><h1>Inicio</h1><p className="muted">Tus unidades, sus condiciones y el próximo paso.</p><p className="nota-prototipo">{NOTA_PROTOTIPO}</p></div>
    <button className="primary" onClick={() => setShow(!show)}>{show ? 'Cerrar registro' : 'Registrar unidad'}</button></div>
    <div className="metrics"><Panel><span>Unidades registradas</span><strong>{d.inicio.unidades_total}</strong></Panel><Panel><span>Cuarentenas abiertas</span><strong>{d.inicio.cuarentenas_abiertas}</strong></Panel><Panel><span>Correcciones pendientes</span><strong>{d.inicio.correcciones_pendientes}</strong></Panel></div>
    <ErrorMessage error={error || data.error} />
    {show && <Panel title="Registrar almacén, lote y unidad"><p className="muted">Cada unidad representa condiciones homogéneas. Puedes usar un almacén o lote ya registrado.</p>
      <div className="form-grid">
        <form className="stack" onSubmit={e => void save(e, 'almacenes')}><h3>1. Almacén</h3>
          <Field label="Nombre del almacén"><input required value={form.nombre} onChange={e => set('nombre', e.target.value)} /></Field>
          <Field label="Ubicación"><input required value={form.ubicacion} onChange={e => set('ubicacion', e.target.value)} /></Field>
          <Field label="Clima cálido documentado"><select value={form.clima} onChange={e => set('clima', e.target.value)}><option value="">No se sabe</option><option value="si">Sí</option><option value="no">No</option></select></Field>
          <Field label="Fundamento del clima"><input required={form.clima !== ''} value={form.fundamento} onChange={e => set('fundamento', e.target.value)} /></Field>
          <button disabled={busy}>Guardar almacén</button></form>
        {d.perfil.roles.includes('PRODUCTOR') && <form className="stack" onSubmit={e => void save(e, 'lotes')}><h3>2. Lote de maíz chulpi</h3>
          <Field label="Código del lote"><input required value={form.codigo} onChange={e => set('codigo', e.target.value)} /></Field><p>Uso final: alimentación.</p><button disabled={busy}>Guardar lote</button></form>}
        <form className="stack" onSubmit={e => void save(e, 'unidades')}><h3>3. Unidad de almacenamiento</h3>
          <Field label="Almacén"><select required value={form.almacen} onChange={e => set('almacen', e.target.value)}><option value="">Seleccionar</option>{d.almacenes.map(a => <option key={a.id} value={a.id}>{a.nombre}</option>)}</select></Field>
          <Field label="Lote"><select required value={form.lote} onChange={e => set('lote', e.target.value)}><option value="">Seleccionar</option>{d.lotes.map(a => <option key={a.id} value={a.id}>{a.codigo}</option>)}</select></Field>
          <Field label="Nombre del recipiente"><input required value={form.recipiente} onChange={e => set('recipiente', e.target.value)} /></Field>
          <Field label="Modalidad"><select value={form.modalidad} onChange={e => set('modalidad', e.target.value)}><option value="">No se sabe</option><option value="HERMETICO">Hermético</option><option value="NO_HERMETICO">No hermético</option></select></Field>
          <button className="primary" disabled={busy}>Crear unidad y capturar</button></form>
      </div></Panel>}
    <Panel title="Unidades de almacenamiento">{!d.unidades.length ? <Empty>Aún no tienes unidades. Registra la primera para comenzar.</Empty> : <div className="table-scroll"><table><thead><tr><th>Recipiente</th><th>Modalidad</th><th>Autorización actual</th><th>Próximo control</th><th>Acciones</th></tr></thead><tbody>{d.unidades.map((u, i) => <tr key={u.id}><td><strong>{u.nombre_recipiente}</strong><small>{d.lotes.find(l => l.id === u.id_lote)?.codigo}</small></td><td>{u.tipo_almacenamiento ? nombre(u.tipo_almacenamiento) : 'Sin definir'}</td><td><span className={`badge ${d.vigencias[i].estado === 'VIGENTE' ? 'good' : ''}`}>{nombre(d.vigencias[i].estado)}</span></td><td>{fecha(d.vigencias[i].fecha_proximo_control)}</td><td><div className="actions"><button onClick={() => navigate('evaluacion', u.id)}>Evaluar</button><button onClick={() => navigate('seguimiento', u.id)}>Seguimiento</button>{u.id_evaluacion_actual && <button onClick={() => navigate('resultado', u.id_evaluacion_actual!)}>Resultado</button>}</div></td></tr>)}</tbody></table></div>}</Panel>
    <Panel title="Controles próximos">{d.inicio.controles_proximos.length ? d.inicio.controles_proximos.map(c => <div key={c.id_unidad} className="row"><span>{c.nombre} · {fecha(c.fecha)} · {nombre(c.estado)}</span><button onClick={() => navigate('seguimiento', c.id_unidad)}>Registrar control</button></div>) : <Empty>No hay controles programados.</Empty>}</Panel>
  </div>
}
