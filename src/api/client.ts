import { createClient } from '@supabase/supabase-js'
import type { components } from './contrato'

export type Schema = components['schemas']
export type Unidad = Schema['Unidad']
export type EvaluacionEntrada = Schema['EvaluacionEntrada-Input']
export type Observacion = Schema['ObservacionEntrada']
export type Resultado = Schema['ResultadoEvaluacion']
export const localAuth = import.meta.env.VITE_AUTH_MODE === 'local'
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY
export const supabase = !localAuth && supabaseUrl && supabaseKey
  ? createClient(supabaseUrl, supabaseKey) : null
export const baseUrl = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '')

export class ApiError extends Error {
  constructor(public status: number, message: string, public requestId?: string) { super(message) }
}

export async function accessToken(): Promise<string | null> {
  if (localAuth) {
    const raw = sessionStorage.getItem('poscosegran-session')
    if (!raw) return null
    try {
      const session = JSON.parse(raw) as { access_token: string; expires_at: number }
      return session.expires_at > Date.now() / 1000 ? session.access_token : null
    } catch { return null }
  }
  return (await supabase?.auth.getSession())?.data.session?.access_token || null
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await accessToken()
  if (!token) throw new ApiError(401, 'Inicia sesión para continuar. Tu captura se conserva.')
  const response = await fetch(baseUrl + path, {
    ...options, headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, ...options.headers },
  })
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = data?.campos?.map((f: {ruta: string; mensaje: string}) => `${f.ruta}: ${f.mensaje}`).join('; ')
    throw new ApiError(response.status, `${data?.mensaje || data?.detail || 'No se pudo completar la operación'}${detail ? ': ' + detail : ''}`, data?.id_solicitud)
  }
  return data as T
}

// Mantiene la misma clave en reintentos de una operación de resultado incierto.
export async function write<T>(path: string, body: unknown, method = 'POST', headers: Record<string, string> = {}): Promise<T> {
  const signature = `${method}:${path}:${JSON.stringify(body)}`
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(signature))
  const storageKey = 'operacion:' + Array.from(new Uint8Array(digest), v => v.toString(16).padStart(2, '0')).join('')
  const key = sessionStorage.getItem(storageKey) || crypto.randomUUID()
  sessionStorage.setItem(storageKey, key)
  try {
    const result = await request<T>(path, { method, body: JSON.stringify(body), headers: { 'Idempotency-Key': key, ...headers } })
    sessionStorage.removeItem(storageKey)
    return result
  } catch (error) {
    if (error instanceof ApiError && error.status < 500 && error.status !== 429) sessionStorage.removeItem(storageKey)
    throw error
  }
}

export async function list<T>(path: string): Promise<T[]> {
  const items: T[] = []
  let cursor: string | null = null
  do {
    const page: { items: T[]; siguiente_cursor: string | null } = await request(
      `${path}${path.includes('?') ? '&' : '?'}limite=100${cursor ? '&cursor=' + encodeURIComponent(cursor) : ''}`,
    )
    items.push(...page.items)
    cursor = page.siguiente_cursor
  } while (cursor)
  return items
}

export const revisiones = (u: Unidad) => ({ revision_unidad: u.revision, revision_almacen: u.revision_almacen })
export const fecha = (value: string | null) => value ? new Date(value).toLocaleString('es-PE', { timeZone: 'America/Lima' }) : 'Sin registro'
export const nombre = (value: string) => value.toLowerCase().replaceAll('_', ' ').replace(/^./, c => c.toUpperCase())
