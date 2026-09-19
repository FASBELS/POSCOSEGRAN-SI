import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { request, type Schema } from '../api/client'
import Panel, { ErrorMessage, Loading } from '../components/Shared'
import { Source } from './Resultado'
export default function Conocimiento() {
  const [q, setQ] = useState('')
  const data = useQuery({ queryKey: ['conocimiento'], queryFn: () => request<Schema['Catalogo']>('/conocimiento') })
  if (data.isLoading) return <Loading />
  return <div className="stack"><div><p className="eyebrow">Conocimiento documentado</p><h1>Base de conocimiento</h1><p>Versión {data.data?.version_base} · Reglas, decisiones y fuentes de consulta.</p></div><ErrorMessage error={data.error} />
    <label className="field"><span>Buscar regla o término</span><input type="search" value={q} onChange={e => setQ(e.target.value)} placeholder="Ej. R19, humedad, cuarentena" /></label>
    {data.data && <><Panel title="Reglas R01–R30">{[...data.data.reglas, ...data.data.ramas_r30].filter(r => JSON.stringify(r).toLowerCase().includes(q.toLowerCase())).map(r => <details className="reason" key={r.id}><summary><span className="badge">{r.id}</span> {r.consecuente}</summary><p><strong>Condición:</strong> {r.antecedente}</p><p><strong>Acción:</strong> {r.accion}</p><Source text={r.fundamento_markdown} /></details>)}</Panel><Panel title="Fuentes">{data.data.fuentes.map(f => <div className="reason" key={f.id}><strong>{f.id}</strong><Source text={f.referencia_markdown} /></div>)}</Panel></>}
  </div>
}
