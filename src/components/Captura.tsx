import campos from '../campos.json'
import { nombre, type Observacion } from '../api/client'
import { Field } from './Shared'

export type CapturaValor = { valor: string; captura: 'APORTADO' | 'DESCONOCIDO' | 'NO_APLICA'; fecha: string; metodo: string; evidencia: string; causa: string }
export type CapturaDatos = Record<string, CapturaValor>
export const fechaLocal = (value: string) => { const d = new Date(value); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16) }
export const ahoraLocal = () => fechaLocal(new Date().toISOString())
export const vacio = (): CapturaValor => ({ valor: '', captura: 'DESCONOCIDO', fecha: ahoraLocal(), metodo: '', evidencia: '', causa: '' })
const labels: Record<string, string> = { humedad_grano: 'Humedad del grano', temperatura_grano: 'Temperatura del grano', moho_visible: 'Moho visible', hr_almacen: 'Humedad relativa del almacén', aw_medida: 'Actividad de agua medida', fecha_control_almacen: 'Fecha del control del almacén', ingreso_inspeccionado: 'Inspección de ingreso completa' }
export function convertir(datos: CapturaDatos): Observacion[] {
  return Object.entries(datos).map(([campo, value]) => {
    const def = campos[campo as keyof typeof campos]
    let valor: string | number | boolean | null = null
    if (value.captura === 'APORTADO') {
      if (!value.valor.trim()) throw new Error(`Completa ${labels[campo] || nombre(campo)} o marca No se sabe.`)
      valor = def.tipo === 'N' ? Number(value.valor.replace(',', '.')) : def.tipo === 'B' ? value.valor === 'true' : def.tipo === 'F' ? new Date(value.valor).toISOString() : value.valor
      if (typeof valor === 'number' && !Number.isFinite(valor)) throw new Error(`Número inválido en ${nombre(campo)}`)
      if (!value.metodo.trim() || !value.fecha) throw new Error(`Indica fecha y método de ${nombre(campo)}.`)
    }
    return { campo, captura: value.captura, valor, unidad: def.unidad as Observacion['unidad'], valor_original: value.valor || null,
      fecha_observacion: value.captura === 'APORTADO' ? new Date(value.fecha).toISOString() : null,
      metodo: value.metodo || null, evidencia: value.evidencia || null, motivo_no_aplica: value.causa || null }
  })
}
export function desdeObservaciones(observaciones: Observacion[]): CapturaDatos {
  return Object.fromEntries(observaciones.map(o => [o.campo, { valor: o.valor === null ? '' : campos[o.campo as keyof typeof campos]?.tipo === 'F' ? fechaLocal(String(o.valor)) : String(o.valor), captura: o.captura,
    fecha: o.fecha_observacion ? new Date(new Date(o.fecha_observacion).getTime() - new Date(o.fecha_observacion).getTimezoneOffset() * 60000).toISOString().slice(0, 16) : ahoraLocal(),
    metodo: o.metodo || '', evidencia: o.evidencia || '', causa: o.motivo_no_aplica || '' }]))
}
export default function Captura({ datos, onChange, paso, filtro }: { datos: CapturaDatos; onChange: (d: CapturaDatos) => void; paso?: number; filtro?: string[] }) {
  return <div className="capture-grid">{Object.entries(campos).filter(([key, def]) => key !== 'clima_calido' && (!paso || def.paso === paso) && (!filtro || filtro.includes(key))).map(([campo, def]) => {
    const value = datos[campo] || vacio(), label = labels[campo] || nombre(campo)
    const change = (patch: Partial<CapturaValor>) => onChange({ ...datos, [campo]: { ...value, ...patch } })
    return <div className="capture-field" key={campo}>
      <Field label={`${label}${def.tipo === 'N' ? ' · ' + def.unidad : ''}`}>
        {def.tipo === 'B' ? <select value={value.captura === 'APORTADO' ? value.valor : value.captura} onChange={e => change(e.target.value === 'true' || e.target.value === 'false' ? { valor: e.target.value, captura: 'APORTADO' } : { valor: '', captura: e.target.value as CapturaValor['captura'] })}><option value="DESCONOCIDO">No se sabe</option><option value="true">Sí</option><option value="false">No</option>{def.admite_no_aplica && <option value="NO_APLICA">No aplica (justificar)</option>}</select>
          : campo === 'metodo_humedad' ? <select value={value.valor} onChange={e => change({ valor: e.target.value, captura: e.target.value ? 'APORTADO' : 'DESCONOCIDO' })}><option value="">No se sabe</option><option>INSTRUMENTAL</option><option>LABORATORIO</option><option>ESTIMACION_INDIRECTA</option></select>
          : <input type={def.tipo === 'F' ? 'datetime-local' : 'text'} inputMode={def.tipo === 'N' ? 'decimal' : undefined} value={value.valor} placeholder="Sin dato" onChange={e => change({ valor: e.target.value, captura: e.target.value ? 'APORTADO' : 'DESCONOCIDO' })} />}
      </Field>
      {def.tipo !== 'B' && def.admite_no_aplica && <label className="check"><input type="checkbox" checked={value.captura === 'NO_APLICA'} onChange={e => change({ captura: e.target.checked ? 'NO_APLICA' : 'DESCONOCIDO', valor: '' })} />No aplica</label>}
      {value.captura === 'NO_APLICA' && <Field label={`Motivo de no aplicación · ${label}`}><input value={value.causa} onChange={e => change({ causa: e.target.value })} /></Field>}
      {value.captura === 'APORTADO' && <details open={!value.metodo}><summary>Fecha, método y evidencia</summary><div className="stack compact">
        <Field label={`Fecha de observación · ${label}`}><input type="datetime-local" value={value.fecha} onChange={e => change({ fecha: e.target.value })} /></Field>
        <Field label={`Método · ${label}`}><input value={value.metodo} placeholder="Procedimiento o equipo utilizado" onChange={e => change({ metodo: e.target.value })} /></Field>
        <Field label={`Evidencia · ${label}`}><input value={value.evidencia} onChange={e => change({ evidencia: e.target.value })} /></Field>
      </div></details>}
    </div>
  })}</div>
}
