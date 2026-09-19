import { cloneElement, isValidElement, useId, type ReactNode, type ReactElement } from 'react'
import { ApiError } from '../api/client'

export default function Panel({ title, children }: { title?: string; children: ReactNode }) {
  return <section className="panel">{title && <h2>{title}</h2>}{children}</section>
}
export function ErrorMessage({ error }: { error: unknown }) {
  if (!error) return null
  return <div role="alert" className="message error">{error instanceof Error ? error.message : String(error)}
    {error instanceof ApiError && error.status === 409 && <p>Actualiza las revisiones y revisa la captura antes de reenviar.</p>}
    {error instanceof ApiError && error.status === 401 && <p>Vuelve a iniciar sesión desde el botón de la cabecera.</p>}
    {error instanceof ApiError && error.requestId && <small>Referencia: {error.requestId}</small>}
  </div>
}
export function Field({ label, children }: { label: string; children: ReactNode }) {
  const id = useId()
  return <div className="field"><label htmlFor={id}>{label}</label>{isValidElement(children) ? cloneElement(children as ReactElement<{id: string}>, { id }) : children}</div>
}
export function Loading() { return <p role="status" className="message">Cargando datos…</p> }
export function Empty({ children }: { children: ReactNode }) { return <p className="empty">{children}</p> }
