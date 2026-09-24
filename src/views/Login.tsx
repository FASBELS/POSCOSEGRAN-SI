import { useState } from 'react'
import { baseUrl, localAuth, supabase } from '../api/client'
import Panel, { ErrorMessage, Field } from '../components/Shared'

export default function Login({ onLogin }: { onLogin: () => void }) {
  const [user, setUser] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  async function login(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError(null)
    try {
      if (localAuth) {
        const res = await fetch(baseUrl.replace(/\/api\/v1$/, '') + '/auth/local/sesion', {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ usuario: user, password }),
        })
        const session = await res.json()
        if (!res.ok) throw new Error(session.mensaje || 'No se pudo iniciar sesión')
        sessionStorage.setItem('poscosegran-session', JSON.stringify(session))
      } else {
        if (!supabase) throw new Error('Configura Supabase o prepara el entorno local siguiendo el README.')
        const result = await supabase.auth.signInWithPassword({ email: user, password })
        if (result.error) throw result.error
      }
      onLogin()
    } catch (err) { setError(err) } finally { setBusy(false) }
  }
  return <div className="login"><div className="eyebrow">POSCOSEGRAN · Gestión poscosecha</div>
    <h1>El cuidado del grano<br />empieza con información.</h1>
    <p>Evalúa tus unidades de almacenamiento y conserva un seguimiento explicable.</p>
    <Panel title="Iniciar sesión"><form onSubmit={login} className="stack">
      {localAuth && <p className="message">Entorno local de desarrollo · datos guardados en PostgreSQL.</p>}
      <Field label={localAuth ? 'Usuario local' : 'Correo electrónico'}>
        <input value={user} onChange={e => setUser(e.target.value)} required autoComplete="username" type={localAuth ? 'text' : 'email'} placeholder={localAuth ? 'testeo' : 'tu@correo.com'} />
      </Field>
      <Field label="Contraseña"><input type="password" value={password} onChange={e => setPassword(e.target.value)} required autoComplete="current-password" /></Field>
      <ErrorMessage error={error} /><button className="primary" disabled={busy}>{busy ? 'Ingresando…' : 'Entrar'}</button>
    </form></Panel><p className="muted">Prototipo académico para maíz chulpi. No certifica inocuidad ni aptitud para consumo.</p>
  </div>
}
