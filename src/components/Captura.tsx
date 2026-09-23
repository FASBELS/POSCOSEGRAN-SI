import { useQuery } from '@tanstack/react-query'
import campos from '../campos.json'
import { nombre, request, type Observacion, type Schema } from '../api/client'
import { Field } from './Shared'

export type CapturaValor = { valor: string; captura: 'APORTADO' | 'DESCONOCIDO' | 'NO_APLICA'; fecha: string; metodo: string; evidencia: string; causa: string }
export type CapturaDatos = Record<string, CapturaValor>
export const fechaLocal = (value: string) => { const d = new Date(value); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16) }
export const ahoraLocal = () => fechaLocal(new Date().toISOString())
export const vacio = (): CapturaValor => ({ valor: '', captura: 'DESCONOCIDO', fecha: ahoraLocal(), metodo: '', evidencia: '', causa: '' })
const labels: Record<string, string> = {
  humedad_grano: 'Humedad del grano', metodo_humedad: 'Método de medición de humedad', equipo_humedad_verificado: 'Equipo de humedad verificado',
  muestra_representativa: 'Muestra representativa', procedimiento_medicion_cumplido: 'Procedimiento de medición cumplido', temperatura_muestra: 'Temperatura de la muestra',
  temperatura_grano: 'Temperatura del grano', temperatura_grano_previa: 'Temperatura del grano anterior', punto_medicion: 'Punto de medición', punto_medicion_previo: 'Punto de medición anterior',
  metodo_termico: 'Método de medición térmica', metodo_termico_previo: 'Método térmico anterior', temperatura_almacen: 'Temperatura del almacén', hr_almacen: 'Humedad relativa del almacén',
  aw_medida: 'Actividad de agua medida', actividad_agua: 'Actividad de agua', hr_aire_exterior: 'Humedad relativa exterior', temperatura_aire_exterior: 'Temperatura exterior',
  lluvia_o_niebla: 'Lluvia o niebla', humedad_equilibrio_maiz: 'Humedad de equilibrio del maíz', tabla_equilibrio_id: 'Tabla de equilibrio usada',
  insectos_vivos: 'Insectos vivos', granos_perforados: 'Granos perforados', polvillo_inusual: 'Polvillo inusual', exuvias_larvas: 'Exuvias o larvas', ruido_alimentacion: 'Ruido de alimentación',
  heces_roedores_aves_entorno: 'Heces de roedores o aves en el entorno', huellas: 'Huellas', bolsa_roida: 'Envase roído', grano_derramado_por_plaga: 'Grano derramado por plaga',
  moho_visible: 'Moho visible', olor_anormal: 'Olor anormal', condensacion_interna: 'Condensación interna', germinacion: 'Germinación',
  suciedad_origen_animal: 'Suciedad de origen animal', heces_visibles: 'Heces visibles en el producto', granos_defectuosos: 'Granos defectuosos', granos_enfermos: 'Granos enfermos',
  granos_quebrados: 'Granos quebrados', materia_organica_extrana: 'Materia orgánica extraña', materia_inorganica_extrana: 'Materia inorgánica extraña',
  recipiente_limpio: 'Recipiente limpio', recipiente_seco: 'Recipiente seco', material_grado_alimentario: 'Material de grado alimentario', recipiente_resistente: 'Recipiente resistente',
  cierre_seguro: 'Cierre seguro', sello_integro: 'Sello íntegro', perforacion_barrera: 'Perforación de la barrera', bolsa_abierta_sin_resellar: 'Envase abierto sin resellar',
  distancia_piso: 'Separación al piso', distancia_pared: 'Separación a la pared', distancia_techo: 'Separación al techo',
  fecha_limpieza_general: 'Fecha de la última limpieza general', limpieza_diaria: 'Limpieza diaria', limpieza_previa_nuevo_lote: 'Limpieza previa al nuevo lote', limpieza_tras_operaciones: 'Limpieza tras operaciones',
  polvo_humo_gases_vapores: 'Polvo, humo, gases o vapores', quimicos_combustibles_en_almacen: 'Químicos o combustibles en el almacén',
  fecha_control_almacen: 'Fecha del control del almacén', fecha_inspeccion_grano: 'Fecha de la inspección del grano', fecha_inspeccion_exterior: 'Fecha de la inspección exterior',
  ingreso_inspeccionado: 'Inspección de ingreso completa', hay_evento_que_invalida_control: 'Evento posterior que invalida controles', temperatura_ambiente_maxima_intervalo: 'Temperatura ambiente máxima del intervalo', sensor_interno_hermetico: 'Sensor interno en recipiente hermético',
  vida_consumida: 'Vida consumida', tiempo_referencia_actual: 'Tiempo de referencia', dias_previstos_restantes: 'Días previstos restantes', fecha_salida_prevista: 'Fecha de salida prevista',
  tipo_almacenamiento: 'Modalidad de almacenamiento', fase: 'Fase de la evaluación', clima_calido: 'Clima cálido documentado', plazo_compatible: 'Compatibilidad del plazo',
}
/** Nombre legible de un campo; los códigos técnicos no se muestran al usuario. */
export const etiqueta = (campo: string) => labels[campo] || nombre(campo)

/** "¿Por qué se pide este dato?": reglas de la base que lo usan para decidir. */
function PorQueSePide({ campo, uso }: { campo: string; uso?: Record<string, string[]> }) {
  if (!uso) return null
  const reglas = uso[campo] || []
  return <details className="why"><summary>¿Por qué se pide este dato?</summary>
    <p>{reglas.length ? `Lo usan las reglas ${reglas.join(', ')} de la base de conocimiento. Si no se conoce, esas comprobaciones quedan pendientes: no se asume un valor favorable.` : 'Ninguna regla lo usa para decidir; se registra como contexto del caso.'}</p>
  </details>
}
export function convertir(datos: CapturaDatos): Observacion[] {
  return Object.entries(datos).map(([campo, value]) => {
    const def = campos[campo as keyof typeof campos]
    let valor: string | number | boolean | null = null
    if (value.captura === 'APORTADO') {
      if (!value.valor.trim()) throw new Error(`Completa ${etiqueta(campo)} o marca No se sabe.`)
      valor = def.tipo === 'N' ? Number(value.valor.replace(',', '.')) : def.tipo === 'B' ? value.valor === 'true' : def.tipo === 'F' ? new Date(value.valor).toISOString() : value.valor
      if (typeof valor === 'number' && !Number.isFinite(valor)) throw new Error(`Número inválido en ${etiqueta(campo)}`)
      if (!value.metodo.trim() || !value.fecha) throw new Error(`Indica fecha y método de ${etiqueta(campo)}.`)
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
  const catalogo = useQuery({ queryKey: ['conocimiento'], queryFn: () => request<Schema['Catalogo']>('/conocimiento'), staleTime: 300000 })
  const uso = catalogo.data?.uso_campos
  return <div className="capture-grid">{Object.entries(campos).filter(([key, def]) => key !== 'clima_calido' && (!paso || def.paso === paso) && (!filtro || filtro.includes(key))).map(([campo, def]) => {
    const value = datos[campo] || vacio(), label = etiqueta(campo)
    const change = (patch: Partial<CapturaValor>) => onChange({ ...datos, [campo]: { ...value, ...patch } })
    return <div className="capture-field" key={campo}>
      <Field label={`${label}${def.tipo === 'N' ? ' · ' + def.unidad : ''}`}>
        {def.tipo === 'B' ? <select value={value.captura === 'APORTADO' ? value.valor : value.captura} onChange={e => change(e.target.value === 'true' || e.target.value === 'false' ? { valor: e.target.value, captura: 'APORTADO' } : { valor: '', captura: e.target.value as CapturaValor['captura'] })}><option value="DESCONOCIDO">No se sabe</option><option value="true">Sí</option><option value="false">No</option>{def.admite_no_aplica && <option value="NO_APLICA">No aplica (justificar)</option>}</select>
          : campo === 'metodo_humedad' ? <select value={value.valor} onChange={e => change({ valor: e.target.value, captura: e.target.value ? 'APORTADO' : 'DESCONOCIDO' })}><option value="">No se sabe</option><option>INSTRUMENTAL</option><option>LABORATORIO</option><option>ESTIMACION_INDIRECTA</option></select>
          : <input type={def.tipo === 'F' ? 'datetime-local' : 'text'} inputMode={def.tipo === 'N' ? 'decimal' : undefined} value={value.valor} placeholder="Sin dato" onChange={e => change({ valor: e.target.value, captura: e.target.value ? 'APORTADO' : 'DESCONOCIDO' })} />}
      </Field>
      {def.tipo !== 'B' && def.admite_no_aplica && <label className="check"><input type="checkbox" checked={value.captura === 'NO_APLICA'} onChange={e => change({ captura: e.target.checked ? 'NO_APLICA' : 'DESCONOCIDO', valor: '' })} />No aplica</label>}
      <PorQueSePide campo={campo} uso={uso} />
      {value.captura === 'NO_APLICA' && <Field label={`Motivo de no aplicación · ${label}`}><input value={value.causa} onChange={e => change({ causa: e.target.value })} /></Field>}
      {value.captura === 'APORTADO' && <details open={!value.metodo}><summary>Fecha, método y evidencia</summary><div className="stack compact">
        <Field label={`Fecha de observación · ${label}`}><input type="datetime-local" value={value.fecha} onChange={e => change({ fecha: e.target.value })} /></Field>
        <Field label={`Método · ${label}`}><input value={value.metodo} placeholder="Procedimiento o equipo utilizado" onChange={e => change({ metodo: e.target.value })} /></Field>
        <Field label={`Evidencia · ${label}`}><input value={value.evidencia} onChange={e => change({ evidencia: e.target.value })} /></Field>
      </div></details>}
    </div>
  })}</div>
}
