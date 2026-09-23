import { useQuery, useQueryClient } from '@tanstack/react-query'
import { list, fecha, nombre, tieneRol, type Schema, type Unidad } from '../api/client'
import Panel, { Empty, ErrorMessage, Loading } from '../components/Shared'
import { useAppNavigate } from '../App'

const PRIORIDAD: Record<string, number> = { CUARENTENA: 0, REVISION_PLAGAS: 1, REVISION_TERMICA: 2, CORRECCION: 3 }
const QUE_HACER: Record<string, string> = {
  CUARENTENA: 'Verificar la separación física y resolver con disposición fundamentada.',
  REVISION_PLAGAS: 'Inspeccionar y registrar si la infestación se confirma o se descarta.',
  REVISION_TERMICA: 'Revisar varios puntos del grano y la causa del aumento térmico.',
  CORRECCION: 'Comprobar que la corrección se ejecutó antes de cerrar.',
}

/** Revisión técnica: bandeja de incidencias abiertas en las unidades asignadas. */
export default function Revision() {
  const navigate = useAppNavigate()
  const perfil = useQueryClient().getQueryData<Schema['Perfil']>(['perfil'])
  const data = useQuery({ queryKey: ['revision-tecnica'], queryFn: async () => {
    const unidades = await list<Unidad>('/unidades')
    const incidencias = (await Promise.all(unidades.map(u => list<Schema['Incidencia']>(`/unidades/${u.id}/incidencias`)))).flat()
    return { unidades, incidencias }
  } })
  if (data.isLoading) return <Loading />
  if (!data.data) return <ErrorMessage error={data.error} />
  const { unidades, incidencias } = data.data
  const abiertas = incidencias.filter(i => i.estado === 'ABIERTA').sort((a, b) => (PRIORIDAD[a.tipo] ?? 9) - (PRIORIDAD[b.tipo] ?? 9) || a.creada_en.localeCompare(b.creada_en))
  const cerradas = incidencias.filter(i => i.estado === 'CERRADA').sort((a, b) => (b.cerrada_en || '').localeCompare(a.cerrada_en || '')).slice(0, 10)
  const tecnico = tieneRol(perfil, 'TECNICO')

  return <div className="stack">
    <div className="page-heading"><div><p className="eyebrow">Competencia técnica</p><h1>Revisión técnica</h1><p className="muted">{abiertas.length} incidencias abiertas en {new Set(abiertas.map(i => i.id_unidad)).size} unidades</p></div></div>
    {!tecnico && <p className="message">Solo el personal técnico registra revisiones, dictámenes y resoluciones. Puedes consultar el estado de las incidencias.</p>}
    <ErrorMessage error={data.error} />
    <Panel title="Pendientes de revisión">{abiertas.length ? abiertas.map(i => {
      const u = unidades.find(x => x.id === i.id_unidad)
      return <div className="reason" key={i.id}>
        <p><span className={`badge ${i.tipo === 'CUARENTENA' ? '' : 'good'}`}>{nombre(i.tipo)}</span> <strong>{u?.nombre_recipiente}</strong> · abierta {fecha(i.creada_en)}</p>
        <p>Causas: {i.causas.map(nombre).join(', ') || 'sin detalle'}</p>
        <p className="muted">{QUE_HACER[i.tipo]}</p>
        <div className="actions"><button className="primary" onClick={() => navigate('seguimiento', i.id_unidad)}>{tecnico ? 'Revisar o resolver' : 'Ver seguimiento'}</button>{u?.id_evaluacion_actual && <button onClick={() => navigate('resultado', u.id_evaluacion_actual!)}>Ver explicación</button>}</div>
      </div>
    }) : <Empty>No hay incidencias abiertas.</Empty>}</Panel>
    <Panel title="Cerradas recientemente">{cerradas.length ? cerradas.map(i => <div className="row" key={i.id}><span>{nombre(i.tipo)} · {unidades.find(x => x.id === i.id_unidad)?.nombre_recipiente}</span><small>Cerrada {fecha(i.cerrada_en)}</small></div>) : <Empty>Sin incidencias cerradas.</Empty>}</Panel>
  </div>
}
