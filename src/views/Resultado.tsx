import { useQuery } from '@tanstack/react-query'
import { request, fecha, nombre, type Resultado as ResultadoAPI, type Schema } from '../api/client'
import Panel, { ErrorMessage, Loading } from '../components/Shared'
import { useAppNavigate, useId } from '../App'

export default function Resultado() {
  const id = useId(), navigate = useAppNavigate()
  const result = useQuery({ queryKey: ['resultado', id], queryFn: () => request<ResultadoAPI>(`/evaluaciones/${id}`), enabled: !!id, refetchInterval: 30000 })
  const catalogo = useQuery({ queryKey: ['conocimiento'], queryFn: () => request<Schema['Catalogo']>('/conocimiento') })
  if (!id) return <Panel title="Resultado"><p>Selecciona una evaluación desde Inicio o Seguimiento.</p></Panel>
  if (result.isLoading) return <Loading />
  if (!result.data) return <ErrorMessage error={result.error} />
  const { evaluacion: e, vigencia: v } = result.data
  return <div className="stack"><div className="page-heading"><div><p className="eyebrow">Decisión explicable · {e.rama_r30}</p><h1>Resultado de evaluación</h1><p className="muted">{fecha(e.fecha_evaluacion)}</p></div><button onClick={() => navigate('seguimiento', e.id_unidad)}>Ver seguimiento</button></div>
    <ErrorMessage error={result.error} />
    <section className={`decision ${e.decision_final === 'CUARENTENA' ? 'danger' : v.estado === 'VIGENTE' ? 'authorized' : ''}`}><p>Decisión histórica</p><h2>{nombre(e.decision_final)}</h2><p><strong>Autorización actual: {nombre(v.estado)}</strong></p>{v.causas.map(c => <p key={c}>{c}</p>)}<div className="actions"><button onClick={() => navigate('evaluacion', e.id_unidad)}>Reevaluar unidad</button><button onClick={() => void result.refetch()}>Consultar vigencia</button></div></section>
    <div className="form-grid"><Panel title="Próximas acciones">{e.acciones_requeridas.length ? e.acciones_requeridas.map((a,i) => <div className="row" key={i}><p>{a.descripcion}<small>Responsable: {nombre(a.responsable_requerido)}</small></p></div>) : <p>No se requieren acciones correctivas adicionales.</p>}<p>Próximo control: {fecha(e.fecha_proximo_control)}</p><p>Vencimiento: {fecha(e.fecha_vencimiento_autorizacion)}</p></Panel>
    <Panel title="Datos pendientes"><details><summary>{e.datos_pendientes.length} datos por completar · ver detalle</summary>{e.datos_pendientes.length ? e.datos_pendientes.map((p,i) => <p className="row" key={i}><strong>P{p.paso} · {nombre(p.campo)}</strong><span>{p.motivo}</span></p>) : <p>No hay datos pendientes.</p>}</details></Panel></div>
    <Panel title="Por qué se tomó esta decisión">{e.motivos.map(m => <details key={m.id} className="reason"><summary><span className="badge">{m.regla}</span> {m.mensaje}</summary><p>Fundamento: {nombre(m.fundamento)}</p>{m.evidencias.map((ev,i) => <p key={i}>{nombre(ev.campo)}: {String(ev.valor_observado ?? 'Desconocido')} {ev.unidad} {ev.operador && `· ${ev.operador} ${ev.umbral ?? ''}`} · {fecha(ev.fecha_observacion)}</p>)}{m.fuentes.map((f,i) => <div key={i}><strong>{f.id_fuente}</strong> {f.localizador}<Source text={catalogo.data?.fuentes.find(s => s.id === f.id_fuente)?.referencia_markdown || 'Fuente disponible en la base de conocimiento'} /></div>)}</details>)}<p>Reglas activadas: {e.reglas_activadas.join(', ') || 'Sin activaciones diagnósticas'}</p></Panel>
    <Panel title="Tiempo de almacenamiento"><div className="metrics">{[['Vida consumida', e.calculos_tiempo.vida_consumida], ['Vida proyectada', e.calculos_tiempo.vida_proyectada], ['Referencia actual (días)', e.calculos_tiempo.tiempo_referencia_actual]].map(([label,value]) => <div key={String(label)}><span>{label}</span><strong>{value === null ? 'No disponible' : value}</strong></div>)}</div><p>Las fracciones expresan consumo del tiempo de referencia del modelo. No representan porcentajes de seguridad.</p>{e.calculos_tiempo.vida_consumida === null && <p>Mínimo documentado: {e.calculos_tiempo.vida_minima_documentada ?? 'No disponible'}. No sustituye el total desconocido.</p>}{e.estimaciones_y_sustituciones.map((s,i) => <p className="message" key={i}>{nombre(s.tipo)}: {s.descripcion}</p>)}</Panel>
    <Panel title="Observaciones utilizadas"><div className="table-scroll"><table><thead><tr><th>Campo</th><th>Valor</th><th>Estado</th><th>Procedencia</th><th>Fecha</th></tr></thead><tbody>{e.observaciones_aplicadas.map(o => <tr key={o.id}><td>{nombre(o.entrada.campo)}</td><td>{o.entrada.valor === null ? 'Sin dato' : String(o.entrada.valor)}</td><td>{o.estado_dato || 'No aplica'}</td><td>{o.procedencia}</td><td>{fecha(o.entrada.fecha_observacion)}</td></tr>)}</tbody></table></div></Panel>
    <p className="muted">Base {e.version_base} · Parámetros {e.version_parametros} · Motor {e.version_motor} · {e.id}</p>
  </div>
}
export function Source({ text }: { text: string }) {
  const chunks = text.split(/(\[[^\]]+\]\(https?:\/\/[^)]+\))/g)
  return <p className="source">{chunks.map((part,i) => { const m = part.match(/^\[([^\]]+)\]\((https?:\/\/[^)]+)\)$/); return m ? <a key={i} href={m[2]} target="_blank" rel="noreferrer">{m[1]}</a> : <span key={i}>{part.replaceAll('<br>', ' ')}</span> })}</p>
}
