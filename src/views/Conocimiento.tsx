import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { request, type Schema } from '../api/client'
import Panel, { ErrorMessage, Loading } from '../components/Shared'
import { Source } from './Resultado'
export default function Conocimiento() {
  const [q, setQ] = useState('')
  const data = useQuery({ queryKey: ['conocimiento'], queryFn: () => request<Schema['Catalogo']>('/conocimiento') })
  if (data.isLoading) return <Loading />
  return <div className="stack"><div><p className="eyebrow">Conocimiento documentado</p><h1>Base de conocimiento</h1><p>Base {data.data?.version_base} · parámetros {data.data?.version_parametros ?? '—'} · Reglas, parámetros, decisiones y fuentes.</p><p className="muted">El motor de inferencia no contiene umbrales ni reglas: los lee de esta base. Lo que se ve aquí es exactamente lo que se aplica.</p></div><ErrorMessage error={data.error} />
    <label className="field"><span>Buscar regla o término</span><input type="search" value={q} onChange={e => setQ(e.target.value)} placeholder="Ej. R19, humedad, cuarentena" /></label>
    {data.data && <><Panel title="Reglas R01–R30">{[...data.data.reglas, ...data.data.ramas_r30].filter(r => JSON.stringify(r).toLowerCase().includes(q.toLowerCase())).map(r => <details className="reason" key={r.id}><summary><span className="badge">{r.id}</span> {r.consecuente}</summary><p><strong>Condición:</strong> {r.antecedente}</p><p><strong>Acción:</strong> {r.accion}</p><Source text={r.fundamento_markdown} /></details>)}</Panel><Panel title="Parámetros vigentes">{data.data.parametros?.length ? <div className="table-scroll"><table><thead><tr><th>Parámetro</th><th>Valor</th><th>Fundamento</th><th>Fuentes</th></tr></thead><tbody>{data.data.parametros.filter(p => JSON.stringify(p).toLowerCase().includes(q.toLowerCase())).map(p => <tr key={p.nombre}><td>{p.descripcion}<small>{p.nombre}</small></td><td>{p.valor} {p.unidad}</td><td>{p.fundamento}</td><td>{p.fuentes.join(', ') || '—'}</td></tr>)}</tbody></table></div> : <p className="muted">La versión activa no expone parámetros.</p>}</Panel><Panel title="Fuentes">{data.data.fuentes.map(f => <div className="reason" key={f.id}><strong>{f.id}</strong><Source text={f.referencia_markdown} /></div>)}</Panel></>}
  </div>
}
