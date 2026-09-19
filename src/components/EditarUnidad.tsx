import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { request, type Schema, type Unidad } from '../api/client'
import { ErrorMessage, Field } from './Shared'

export default function EditarUnidad({ unidad }: { unidad: Unidad }) {
  const [open, setOpen] = useState(false)
  const almacen = useQuery({ queryKey: ['almacen', unidad.id_almacen], queryFn: () => request<Schema['Almacen']>(`/almacenes/${unidad.id_almacen}`), enabled: open })
  return <details onToggle={e => setOpen(e.currentTarget.open)}><summary>Corregir modalidad o clima</summary><ErrorMessage error={almacen.error} />{open && almacen.data && <Editor key={`${unidad.revision}:${almacen.data.revision}`} unidad={unidad} almacen={almacen.data} />}</details>
}
function Editor({ unidad, almacen }: { unidad: Unidad; almacen: Schema['Almacen'] }) {
  const qc = useQueryClient()
  const [modalidad, setModalidad] = useState(unidad.tipo_almacenamiento || '')
  const [clima, setClima] = useState(almacen.clima_calido === null ? '' : String(almacen.clima_calido))
  const [fundamento, setFundamento] = useState(almacen.fundamento_clima || '')
  const [busy, setBusy] = useState(false), [error, setError] = useState<unknown>(null)
  async function save(kind: 'unidad' | 'almacen') {
    setBusy(true); setError(null)
    try {
      const body = kind === 'unidad' ? { id_lote: unidad.id_lote, id_almacen: unidad.id_almacen, nombre_recipiente: unidad.nombre_recipiente, tipo_almacenamiento: modalidad || null }
        : { nombre: almacen.nombre, ubicacion: almacen.ubicacion, clima_calido: clima === '' ? null : clima === 'true', fundamento_clima: fundamento || null }
      await request(`/${kind === 'unidad' ? 'unidades' : 'almacenes'}/${kind === 'unidad' ? unidad.id : almacen.id}`, { method: 'PATCH', headers: { 'If-Match': `"${kind === 'unidad' ? unidad.revision : almacen.revision}"` }, body: JSON.stringify(body) })
      await qc.invalidateQueries()
    } catch (err) { setError(err) } finally { setBusy(false) }
  }
  return <div className="stack"><p>Estos cambios invalidan la autorización anterior y requieren una nueva evaluación. El clima se comparte con las unidades del almacén.</p><ErrorMessage error={error} />
    <Field label="Nueva modalidad"><select value={modalidad} onChange={e => setModalidad(e.target.value)}><option value="">No se sabe</option><option value="HERMETICO">Hermético</option><option value="NO_HERMETICO">No hermético</option></select></Field><button disabled={busy} onClick={() => void save('unidad')}>Guardar modalidad</button>
    <Field label="Clima del almacén"><select value={clima} onChange={e => setClima(e.target.value)}><option value="">No se sabe</option><option value="true">Cálido</option><option value="false">No cálido</option></select></Field><Field label="Fundamento actualizado del clima"><input value={fundamento} onChange={e => setFundamento(e.target.value)} /></Field><button disabled={busy || (clima !== '' && !fundamento.trim())} onClick={() => void save('almacen')}>Guardar clima</button>
  </div>
}
