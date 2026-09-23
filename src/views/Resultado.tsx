import { useQuery } from '@tanstack/react-query'
import { ApiError, request, fecha, nombre, decision, tonoDecision, NOTA_PROTOTIPO, type Resultado as ResultadoAPI, type Schema } from '../api/client'
import Panel, { ErrorMessage, Loading } from '../components/Shared'
import { etiqueta } from '../components/Captura'
import { useAppNavigate, useId } from '../App'

type Explicacion = Schema['Explicacion']

export default function Resultado() {
  const id = useId(), navigate = useAppNavigate()
  const result = useQuery({ queryKey: ['resultado', id], queryFn: () => request<ResultadoAPI>(`/evaluaciones/${id}`), enabled: !!id, refetchInterval: 30000 })
  const explicacion = useQuery({ queryKey: ['explicacion', id], queryFn: () => request<Explicacion>(`/evaluaciones/${id}/explicacion`), enabled: !!id, staleTime: Infinity })
  const catalogo = useQuery({ queryKey: ['conocimiento'], queryFn: () => request<Schema['Catalogo']>('/conocimiento') })
  if (!id) return <Panel title="Resultado"><p>Selecciona una evaluación desde Inicio o Seguimiento.</p></Panel>
  if (result.isLoading) return <Loading />
  if (!result.data) return <ErrorMessage error={result.error} />
  const { evaluacion: e, vigencia: v } = result.data
  const x = explicacion.data
  const pendientesPorPaso = [...e.datos_pendientes].sort((a, b) => a.paso - b.paso)

  return <div className="stack">
    <div className="page-heading"><div><p className="eyebrow">Decisión explicable · {e.rama_r30}</p><h1>Resultado de evaluación</h1><p className="muted">{fecha(e.fecha_evaluacion)}</p></div><button onClick={() => navigate('seguimiento', e.id_unidad)}>Ver seguimiento</button></div>
    <p className="nota-prototipo">{NOTA_PROTOTIPO}</p>
    <ErrorMessage error={result.error} />

    {/* 1. Qué hacer */}
    <section className={`decision ${tonoDecision(e.decision_final)}`} aria-labelledby="que-hacer">
      <p id="que-hacer">Qué hacer</p>
      <h2>{decision(e.decision_final)}</h2>
      <p className="codigo">{e.decision_final} · {e.rama_r30}</p>
      <p><strong>Autorización actual: {nombre(v.estado)}</strong></p>{v.causas.map(c => <p key={c}>{c}</p>)}
      <div className="actions"><button onClick={() => navigate('evaluacion', e.id_unidad)}>Reevaluar unidad</button><button onClick={() => void result.refetch()}>Consultar vigencia</button></div>
    </section>

    {/* 2. Por qué */}
    <Panel title="Por qué">
      {x ? <p>{x.resumen}</p> : explicacion.isLoading ? <p className="muted">Preparando la explicación…</p> : null}
      {explicacion.error instanceof ApiError && explicacion.error.status === 409 && <p className="muted">Esta evaluación se emitió antes de que el sistema guardara su traza: se muestran solo sus motivos.</p>}
      {e.motivos.slice(0, 4).map(m => <p key={m.id} className="row"><span className="badge">{m.regla}</span> {m.mensaje}</p>)}
      {e.motivos.length > 4 && <p className="muted">Y {e.motivos.length - 4} motivos más en el fundamento técnico.</p>}
    </Panel>

    {/* 3. Acciones */}
    <Panel title="Acciones requeridas">{e.acciones_requeridas.length ? e.acciones_requeridas.map((a, i) => <div className="row" key={i}><p>{a.descripcion}<small>Responsable: {nombre(a.responsable_requerido)}</small></p></div>) : <p>No se requieren acciones correctivas adicionales.</p>}</Panel>

    {/* 4. Pendientes */}
    <Panel title="Datos pendientes">{pendientesPorPaso.length
      ? <>{pendientesPorPaso.map((p, i) => <p className="row" key={i}><strong>P{p.paso} · {etiqueta(p.campo)}</strong><span>{p.motivo}</span></p>)}<button onClick={() => navigate('evaluacion', e.id_unidad)}>Completar datos</button></>
      : <p>No hay datos pendientes.</p>}</Panel>

    {/* 5. Próximo control */}
    <Panel title="Próximo control"><div className="metrics"><div><span>Próximo control</span><strong>{fecha(e.fecha_proximo_control)}</strong></div><div><span>Vencimiento de la autorización</span><strong>{fecha(e.fecha_vencimiento_autorizacion)}</strong></div></div></Panel>

    {/* Fundamento técnico: plegado por defecto */}
    <details className="panel">
      <summary><strong>Ver fundamento técnico</strong></summary>
      <div className="stack">
        {x && <Explicado x={x} />}
        <h3>Motivos, evidencias y fuentes</h3>
        {e.motivos.map(m => <details key={m.id} className="reason"><summary><span className="badge">{m.regla}</span> {m.mensaje}</summary><p>Fundamento: {nombre(m.fundamento)}</p>{m.evidencias.map((ev, i) => <p key={i}>{etiqueta(ev.campo)}: {String(ev.valor_observado ?? 'Desconocido')} {ev.unidad} {ev.operador && `· ${ev.operador} ${ev.umbral ?? ''}`} · {fecha(ev.fecha_observacion)}</p>)}{m.fuentes.map((f, i) => <div key={i}><strong>{f.id_fuente}</strong> {f.localizador}<Source text={catalogo.data?.fuentes.find(s => s.id === f.id_fuente)?.referencia_markdown || 'Fuente disponible en la base de conocimiento'} /></div>)}</details>)}
        <p>Reglas activadas: {e.reglas_activadas.join(', ') || 'Sin activaciones diagnósticas'}</p>
        <h3>Tiempo de almacenamiento</h3>
        <div className="metrics">{[['Vida consumida', e.calculos_tiempo.vida_consumida], ['Vida proyectada', e.calculos_tiempo.vida_proyectada], ['Referencia actual (días)', e.calculos_tiempo.tiempo_referencia_actual]].map(([label, value]) => <div key={String(label)}><span>{label}</span><strong>{value === null ? 'No disponible' : value}</strong></div>)}</div>
        <p>Las fracciones expresan consumo del tiempo de referencia del modelo. No representan porcentajes de seguridad.</p>
        {e.calculos_tiempo.vida_consumida === null && <p>Mínimo documentado: {e.calculos_tiempo.vida_minima_documentada ?? 'No disponible'}. No sustituye el total desconocido.</p>}
        {e.estimaciones_y_sustituciones.map((s, i) => <p className="message" key={i}>{nombre(s.tipo)}: {s.descripcion}</p>)}
        <h3>Observaciones utilizadas</h3>
        <div className="table-scroll"><table><thead><tr><th>Campo</th><th>Valor</th><th>Estado</th><th>Procedencia</th><th>Fecha</th></tr></thead><tbody>{e.observaciones_aplicadas.map(o => <tr key={o.id}><td>{etiqueta(o.entrada.campo)}</td><td>{o.entrada.valor === null ? 'Sin dato' : String(o.entrada.valor)}</td><td>{o.estado_dato || 'No aplica'}</td><td>{o.procedencia}</td><td>{fecha(o.entrada.fecha_observacion)}</td></tr>)}</tbody></table></div>
        <p className="muted">Base {e.version_base} · Parámetros {e.version_parametros} · Motor {e.version_motor}{x ? ` · Huella ${x.hash_base.slice(0, 12)}` : ''} · {e.id}</p>
      </div>
    </details>
  </div>
}

/** Módulo de explicación: ¿cómo?, ¿por qué no? y hechos del caso. */
function Explicado({ x }: { x: Explicacion }) {
  const inferidos = new Set(x.cadena.map(p => p.conclusion).filter(Boolean))
  return <div className="stack">
    <h3>¿Cómo se llegó a la decisión?</h3>
    {x.cadena.length ? <ol className="cadena">
      {x.cadena.map(p => <li key={p.orden}><strong>{p.regla}</strong>{p.conclusion && <> concluyó <span className="badge">{p.conclusion}</span></>}{p.solicitudes.length > 0 && <> y solicitó {p.solicitudes.map(nombre).join(', ')}</>}
        <small>Porque: {p.porque.map(s => inferidos.has(s) ? s : etiqueta(s)).join('; ') || 'condición cumplida'}</small>
        {p.antecedente && <small>Regla: {p.antecedente}</small>}
        <small>Etapa {p.etapa}, pasada {p.pasada}</small></li>)}
      <li className="decision-final"><strong>{x.rama}</strong> → {x.etiqueta}<small>Primera rama de R30 que se cumple, en orden de prioridad.</small></li>
    </ol> : <p>La decisión no depende de ninguna regla diagnóstica: {x.resumen}</p>}

    {x.por_que_no.length > 0 && <>
      <h3>¿Por qué no se autorizó{x.decision.startsWith('AUTORIZAR') ? ' con controles ordinarios' : ''}?</h3>
      {x.por_que_no.map(r => <div className="reason" key={r.rama}><strong>{r.rama} · {decision(r.decision)}</strong>
        <ul>{r.faltan.map((f, i) => <li className="falta" key={i}>{f}</li>)}</ul></div>)}
    </>}

    <details><summary>Orden de prioridad de R30</summary>
      <div className="table-scroll"><table><thead><tr><th>Rama</th><th>Decisión</th><th>Condición</th></tr></thead>
        <tbody>{x.ramas.map(r => <tr key={r.rama}><td>{r.rama}{r.aplicada ? ' ✓' : ''}</td><td>{decision(r.decision)}</td><td>{nombre(r.valor)}</td></tr>)}</tbody></table></div>
    </details>

    <details><summary>Hechos del caso ({x.hechos_iniciales.length} iniciales · {x.hechos_inferidos.length} inferidos)</summary>
      <p><strong>Inferidos por el motor:</strong></p><div className="chips">{x.hechos_inferidos.map(h => <span className="chip" key={h}>{h}</span>)}</div>
      <p><strong>Observados o registrados:</strong></p>
      <div className="table-scroll"><table><thead><tr><th>Dato</th><th>Valor</th><th>Procedencia</th></tr></thead>
        <tbody>{x.hechos_iniciales.map(h => <tr key={h.campo}><td>{etiqueta(h.campo)}</td><td>{String(h.valor)}</td><td>{nombre(h.procedencia)}</td></tr>)}</tbody></table></div>
      {x.no_aplicables.length > 0 && <p className="muted">Reglas que no aplican a esta modalidad o fase: {x.no_aplicables.join(', ')}.</p>}
    </details>

    <details><summary>Traza completa del motor ({x.traza_completa.length} disparos)</summary>
      {x.traza_completa.map(p => <p className="row" key={p.orden}><span>{p.orden}. {p.regla} · {p.etapa} · pasada {p.pasada}</span><span>{p.conclusion || p.solicitudes.join(', ')}</span></p>)}
    </details>
  </div>
}

export function Source({ text }: { text: string }) {
  const chunks = text.split(/(\[[^\]]+\]\(https?:\/\/[^)]+\))/g)
  return <p className="source">{chunks.map((part, i) => { const m = part.match(/^\[([^\]]+)\]\((https?:\/\/[^)]+)\)$/); return m ? <a key={i} href={m[2]} target="_blank" rel="noreferrer">{m[1]}</a> : <span key={i}>{part.replaceAll('<br>', ' ')}</span> })}</p>
}
