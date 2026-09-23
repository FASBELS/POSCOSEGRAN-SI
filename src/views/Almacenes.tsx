import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { list, request, fecha, nombre, type Schema, type Unidad } from '../api/client'
import Panel, { Empty, ErrorMessage, Field, Loading } from '../components/Shared'
import { useAppNavigate } from '../App'

/** Almacenes y lotes: listado, búsqueda, filtros y detalle (Prompt 1). */
export default function Almacenes() {
  const navigate = useAppNavigate()
  const [q, setQ] = useState(''), [estado, setEstado] = useState(''), [modalidad, setModalidad] = useState(''), [seleccion, setSeleccion] = useState<string | null>(null)
  const data = useQuery({ queryKey: ['almacenes-lotes'], queryFn: async () => {
    const [almacenes, lotes, unidades] = await Promise.all([list<Schema['Almacen']>('/almacenes'), list<Schema['Lote']>('/lotes'), list<Unidad>('/unidades')])
    const vigencias = await Promise.all(unidades.map(u => request<Schema['Vigencia']>(`/unidades/${u.id}/vigencia`)))
    return { almacenes, lotes, unidades, vigencias: Object.fromEntries(unidades.map((u, i) => [u.id, vigencias[i]])) }
  } })
  const filas = useMemo(() => {
    if (!data.data) return []
    const d = data.data, texto = q.trim().toLowerCase()
    return d.unidades.map(u => ({ u, almacen: d.almacenes.find(a => a.id === u.id_almacen), lote: d.lotes.find(l => l.id === u.id_lote), vigencia: d.vigencias[u.id] }))
      .filter(f => !texto || [f.u.nombre_recipiente, f.almacen?.nombre, f.almacen?.ubicacion, f.lote?.codigo].some(v => v?.toLowerCase().includes(texto)))
      .filter(f => !estado || f.vigencia?.estado === estado)
      .filter(f => !modalidad || (modalidad === 'SIN' ? !f.u.tipo_almacenamiento : f.u.tipo_almacenamiento === modalidad))
  }, [data.data, q, estado, modalidad])
  if (data.isLoading) return <Loading />
  if (!data.data) return <ErrorMessage error={data.error} />
  const d = data.data
  const almacen = seleccion ? d.almacenes.find(a => a.id === seleccion) : null
  const estados = [...new Set(Object.values(d.vigencias).map(v => v.estado))]

  return <div className="stack">
    <div className="page-heading"><div><p className="eyebrow">Inventario</p><h1>Almacenes y lotes</h1><p className="muted">{d.almacenes.length} almacenes · {d.lotes.length} lotes · {d.unidades.length} unidades</p></div><button className="primary" onClick={() => navigate('dashboard')}>Registrar unidad</button></div>
    <ErrorMessage error={data.error} />
    <div className="filtros">
      <Field label="Buscar"><input type="search" value={q} onChange={e => setQ(e.target.value)} placeholder="Recipiente, almacén, ubicación o lote" /></Field>
      <Field label="Autorización"><select value={estado} onChange={e => setEstado(e.target.value)}><option value="">Todas</option>{estados.map(s => <option key={s} value={s}>{nombre(s)}</option>)}</select></Field>
      <Field label="Modalidad"><select value={modalidad} onChange={e => setModalidad(e.target.value)}><option value="">Todas</option><option value="HERMETICO">Hermético</option><option value="NO_HERMETICO">No hermético</option><option value="SIN">Sin definir</option></select></Field>
    </div>

    <Panel title="Almacenes">{d.almacenes.length ? <div className="table-scroll"><table><thead><tr><th>Almacén</th><th>Ubicación</th><th>Clima cálido</th><th>Unidades</th><th></th></tr></thead><tbody>
      {d.almacenes.map(a => <tr key={a.id}><td><strong>{a.nombre}</strong></td><td>{a.ubicacion}</td><td>{a.clima_calido === null ? 'No se sabe' : a.clima_calido ? 'Sí' : 'No'}</td><td>{d.unidades.filter(u => u.id_almacen === a.id).length}</td><td><button onClick={() => setSeleccion(seleccion === a.id ? null : a.id)}>{seleccion === a.id ? 'Ocultar detalle' : 'Ver detalle'}</button></td></tr>)}
    </tbody></table></div> : <Empty>No hay almacenes registrados.</Empty>}</Panel>

    {almacen && <Panel title={`Detalle · ${almacen.nombre}`}>
      <p>{almacen.ubicacion} · registrado {fecha(almacen.creado_en)}</p>
      <p>Clima cálido: {almacen.clima_calido === null ? 'no se sabe (la banda condicional de humedad queda pendiente)' : almacen.clima_calido ? 'sí' : 'no'}{almacen.fundamento_clima ? ` · Fundamento: ${almacen.fundamento_clima}` : ''}</p>
      {d.unidades.filter(u => u.id_almacen === almacen.id).map(u => <div className="row" key={u.id}><span><strong>{u.nombre_recipiente}</strong><small>Lote {d.lotes.find(l => l.id === u.id_lote)?.codigo} · {u.tipo_almacenamiento ? nombre(u.tipo_almacenamiento) : 'Modalidad sin definir'}</small></span><span className={`badge ${d.vigencias[u.id]?.estado === 'VIGENTE' ? 'good' : ''}`}>{nombre(d.vigencias[u.id]?.estado || 'SIN_EVALUACION')}</span></div>)}
    </Panel>}

    <Panel title="Unidades por lote">{filas.length ? <div className="table-scroll"><table><thead><tr><th>Lote</th><th>Recipiente</th><th>Almacén</th><th>Modalidad</th><th>Autorización</th><th>Próximo control</th><th>Acciones</th></tr></thead><tbody>
      {filas.map(({ u, almacen, lote, vigencia }) => <tr key={u.id}><td><strong>{lote?.codigo}</strong><small>Maíz chulpi · alimentación</small></td><td>{u.nombre_recipiente}</td><td>{almacen?.nombre}</td><td>{u.tipo_almacenamiento ? nombre(u.tipo_almacenamiento) : 'Sin definir'}</td><td><span className={`badge ${vigencia?.estado === 'VIGENTE' ? 'good' : ''}`}>{nombre(vigencia?.estado || 'SIN_EVALUACION')}</span></td><td>{fecha(vigencia?.fecha_proximo_control ?? null)}</td>
        <td><div className="actions"><button onClick={() => navigate('evaluacion', u.id)}>Evaluar</button><button onClick={() => navigate('seguimiento', u.id)}>Seguimiento</button>{u.id_evaluacion_actual && <button onClick={() => navigate('resultado', u.id_evaluacion_actual!)}>Resultado</button>}</div></td></tr>)}
    </tbody></table></div> : <Empty>Ninguna unidad coincide con los filtros.</Empty>}</Panel>

    <Panel title="Lotes">{d.lotes.length ? d.lotes.map(l => <div className="row" key={l.id}><span><strong>{l.codigo}</strong><small>Registrado {fecha(l.creado_en)}</small></span><span>{d.unidades.filter(u => u.id_lote === l.id).length} unidades</span></div>) : <Empty>No hay lotes registrados.</Empty>}</Panel>
  </div>
}
