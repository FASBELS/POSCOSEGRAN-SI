import { useState, useEffect } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import {
  request,
  fecha,
  nombre,
  decision,
  tieneRol,
  type Schema,
} from "../api/client"
import Panel, { Empty, ErrorMessage, Field, Loading } from "../components/Shared"
import camposJson from "../campos.json"

type Resultado = Schema["PropuestaResultado"]
type Version = Schema["VersionConocimientoResumen"]
type Ficha = Schema["FichaRegla"] & { fuentes: string[] }

const post = <T,>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) })

const OPERADORES = ["GT", "GTE", "LT", "LTE", "EQ", "NEQ"] as const
const SOLICITUDES = [
  "CUARENTENA",
  "SUSPENSION",
  "CORRECCION",
  "MONITOREO",
] as const
const camposDisponibles = Object.keys(camposJson)
const ETAPAS = ["encadenamiento"] as const
const FUNDAMENTOS = ["POLITICA_PROTOTIPO", "TRANSFERIDO", "MIXTO", "PUBLICADO"] as const

function esObjeto(valor: unknown): valor is Record<string, unknown> {
  return !!valor && typeof valor === "object" && !Array.isArray(valor)
}

function esAdicional(codigo: string): boolean {
  return /^R[0-9]{2,}$/.test(codigo) && Number(codigo.slice(1)) >= 31
}

function codigoDocumental(regla: Record<string, unknown>): string {
  return String(regla.regla || regla.id || "")
}

function admiteEditorVisual(nodo: unknown): boolean {
  if (!esObjeto(nodo)) return false
  if ("todos" in nodo || "alguno" in nodo) {
    const hijos = nodo.todos ?? nodo.alguno
    return Array.isArray(hijos) && hijos.every(admiteEditorVisual)
  }
  return "dato" in nodo || "hecho" in nodo || "definicion" in nodo
}

function fichaVacia(id: string): Ficha {
  return {
    id,
    antecedente: "",
    consecuente: "",
    accion: "",
    fundamento_markdown: "",
    fundamento: "POLITICA_PROTOTIPO",
    fuentes: [],
  }
}

// ─── Plantilla de regla vacía ──────────────────────────────────────
function reglaVacia(id = ""): Record<string, unknown> {
  return {
    id,
    regla: id,
    etapa: "encadenamiento",
    si: { dato: "", op: "GT", valor: 0 },
    entonces: { hallazgo: "", solicitudes: [], mensaje: "" },
    registrar_motivo: true,
  }
}

// ─── Mini-componentes del constructor visual ───────────────────────

function CondicionEditor({
  nodo,
  onChange,
}: {
  nodo: Record<string, unknown>
  onChange: (n: Record<string, unknown>) => void
}) {
  const tipo: string =
    "todos" in nodo
      ? "todos"
      : "alguno" in nodo
        ? "alguno"
        : "dato" in nodo
          ? "dato"
          : "hecho" in nodo
            ? "hecho"
            : "definicion" in nodo
              ? "definicion"
              : "dato"

  return (
    <div className="condicion-editor">
      <div className="condicion-row">
        <select
          value={tipo}
          onChange={(e) => {
            const t = e.target.value
            if (t === "dato")
              onChange({ dato: "", op: "GT", valor: 0 })
            else if (t === "hecho") onChange({ hecho: "" })
            else if (t === "definicion") onChange({ definicion: "" })
            else if (t === "todos" || t === "alguno")
              onChange({ [t]: [{ dato: "", op: "GT", valor: 0 }] })
          }}
        >
          <option value="dato">Campo (dato)</option>
          <option value="hecho">Hecho inferido</option>
          <option value="definicion">Definición</option>
          <option value="todos">Todos (AND)</option>
          <option value="alguno">Alguno (OR)</option>
        </select>
      </div>
      {tipo === "dato" && (
        <div className="condicion-row">
          <select
            value={String(nodo.dato || "")}
            onChange={(e) => onChange({ ...nodo, dato: e.target.value })}
          >
            <option value="">Seleccionar campo</option>
            {camposDisponibles.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <select
            value={String(nodo.op || "GT")}
            onChange={(e) => onChange({ ...nodo, op: e.target.value })}
          >
            {OPERADORES.map((o) => (
              <option key={o} value={o}>
                {o === "GT"
                  ? ">"
                  : o === "GTE"
                    ? "≥"
                    : o === "LT"
                      ? "<"
                      : o === "LTE"
                        ? "≤"
                        : o === "EQ"
                          ? "="
                          : "≠"}
              </option>
            ))}
          </select>
          <input
            type="text"
            inputMode="decimal"
            value={String(nodo.valor ?? "")}
            placeholder="Valor / umbral"
            onChange={(e) => {
              const v = e.target.value
              const num = Number(v.replace(",", "."))
              onChange({
                ...nodo,
                valor: v === "" ? "" : Number.isFinite(num) ? num : v,
              })
            }}
          />
        </div>
      )}
      {tipo === "hecho" && (
        <input
          type="text"
          value={String(nodo.hecho || "")}
          placeholder="Nombre del hecho"
          onChange={(e) => onChange({ hecho: e.target.value })}
        />
      )}
      {tipo === "definicion" && (
        <input
          type="text"
          value={String(nodo.definicion || "")}
          placeholder="Nombre de la definición"
          onChange={(e) => onChange({ definicion: e.target.value })}
        />
      )}
      {(tipo === "todos" || tipo === "alguno") && (
        <div className="condicion-hijos">
          {(Array.isArray(nodo[tipo]) ? (nodo[tipo] as Record<string, unknown>[]) : []).map(
            (hijo, i) => (
              <div key={i} className="condicion-hijo">
                <CondicionEditor
                  nodo={hijo}
                  onChange={(updated) => {
                    const lista = [
                      ...(nodo[tipo] as Record<string, unknown>[]),
                    ]
                    lista[i] = updated
                    onChange({ [tipo]: lista })
                  }}
                />
                <button
                  type="button"
                  className="chip-btn danger"
                  onClick={() => {
                    const lista = (
                      nodo[tipo] as Record<string, unknown>[]
                    ).filter((_, j) => j !== i)
                    onChange({ [tipo]: lista.length ? lista : [{ dato: "", op: "GT", valor: 0 }] })
                  }}
                >
                  ✕
                </button>
              </div>
            )
          )}
          <button
            type="button"
            className="chip-btn"
            onClick={() =>
              onChange({
                [tipo]: [
                  ...(nodo[tipo] as Record<string, unknown>[]),
                  { dato: "", op: "GT", valor: 0 },
                ],
              })
            }
          >
            + Añadir condición
          </button>
        </div>
      )}
    </div>
  )
}

function ConsecuenteEditor({
  entonces,
  onChange,
}: {
  entonces: Record<string, unknown>
  onChange: (e: Record<string, unknown>) => void
}) {
  const solicitudes = Array.isArray(entonces.solicitudes)
    ? (entonces.solicitudes as string[])
    : []
  return (
    <div className="consecuente-editor">
      <Field label="Hallazgo (hecho deducido)">
        <input
          type="text"
          value={String(entonces.hallazgo || "")}
          placeholder="Ej: INFRAESTRUCTURA_CON_FILTRACION"
          onChange={(e) =>
            onChange({ ...entonces, hallazgo: e.target.value })
          }
        />
      </Field>
      <Field label="Solicitudes de acción">
        <div className="check-group">
          {SOLICITUDES.map((s) => (
            <label key={s} className="check">
              <input
                type="checkbox"
                checked={solicitudes.includes(s)}
                onChange={(e) => {
                  const next = e.target.checked
                    ? [...solicitudes, s]
                    : solicitudes.filter((x) => x !== s)
                  onChange({ ...entonces, solicitudes: next })
                }}
              />
              {nombre(s)}
            </label>
          ))}
        </div>
      </Field>
      <Field label="Mensaje explicativo">
        <textarea
          value={String(entonces.mensaje || "")}
          placeholder="Texto que verá el usuario en el módulo de explicación"
          onChange={(e) =>
            onChange({ ...entonces, mensaje: e.target.value })
          }
        />
      </Field>
    </div>
  )
}

// ─── Validación en vivo ────────────────────────────────────────────

function useValidacionEnVivo(definicion: Record<string, unknown> | null, habilitada: boolean) {
  const [errores, setErrores] = useState<string[]>([])
  const [validando, setValidando] = useState(false)
  const [validada, setValidada] = useState(false)

  useEffect(() => {
    if (!habilitada || !definicion) {
      setErrores([])
      setValidada(false)
      setValidando(false)
      return
    }
    let cancelada = false
    setValidando(true)
    setValidada(false)
    const timer = setTimeout(async () => {
      try {
        const r = await post<{ valida: boolean; errores: string[] }>(
          "/adquisicion/validar-regla", { definicion }
        )
        if (!cancelada) {
          setErrores(r.errores)
          setValidada(true)
        }
      } catch {
        if (!cancelada) setErrores(["No se pudo validar la regla. Revisa la conexión."])
      } finally {
        if (!cancelada) setValidando(false)
      }
    }, 600)
    return () => { cancelada = true; clearTimeout(timer) }
  }, [definicion, habilitada])

  return { errores, validando, validada }
}

// ─── Componente principal ──────────────────────────────────────────

/**
 * Módulo de adquisición del conocimiento (Cognimática).
 * El ingeniero del conocimiento modifica la base sin tocar el motor: propone,
 * el sistema valida y mide el impacto sobre casos de referencia y evaluaciones
 * reales, y solo entonces se registra y activa la nueva versión.
 */
export default function Adquisicion() {
  const qc = useQueryClient()
  const perfil = qc.getQueryData<Schema["Perfil"]>(["perfil"])
  const permitido = tieneRol(perfil, "INGENIERO_CONOCIMIENTO")
  const catalogo = useQuery({
    queryKey: ["conocimiento"],
    queryFn: () => request<Schema["Catalogo"]>("/conocimiento"),
  })
  const versiones = useQuery({
    queryKey: ["versiones"],
    queryFn: () => request<Version[]>("/adquisicion/versiones"),
    enabled: permitido,
  })
  const activa = versiones.data?.find((v) => v.activa)
  const detalle = useQuery({
    queryKey: ["version", activa?.id],
    queryFn: () =>
      request<Schema["DetalleVersion"]>(
        `/adquisicion/versiones/${activa!.id}`
      ),
    enabled: !!activa,
  })

  // ─── Estado del formulario ─────────────────────────────────────
  const [valores, setValores] = useState<Record<string, string>>({})
  const [motivo, setMotivo] = useState("")
  const [versionParametros, setVersionParametros] = useState("")
  const [versionBase, setVersionBase] = useState("")

  // ─── Estado del editor de reglas ───────────────────────────────
  const [modoRegla, setModoRegla] = useState<"visual" | "codigo">("visual")
  const [reglaActual, setReglaActual] = useState<Record<string, unknown> | null>(null)
  const [fichaActual, setFichaActual] = useState<Ficha | null>(null)
  const [codigoRegla, setCodigoRegla] = useState("")
  const [reglaId, setReglaId] = useState("")
  const [panelReglas, setPanelReglas] = useState(false)
  const [filtroRegla, setFiltroRegla] = useState("")
  const [cambiosReglas, setCambiosReglas] = useState<Record<string, Record<string, unknown> | null>>({})
  const [cambiosFichas, setCambiosFichas] = useState<Record<string, Ficha>>({})
  const [errorEditor, setErrorEditor] = useState("")

  // ─── Estado de la propuesta ────────────────────────────────────
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [busy, setBusy] = useState(false)
  const [firmaSimulada, setFirmaSimulada] = useState("")
  const [motivoActivacion, setMotivoActivacion] = useState<
    Record<string, string>
  >({})
  const [motivoDescarte, setMotivoDescarte] = useState<Record<string, string>>({})

  // Validación en vivo
  const { errores: erroresVivo, validando, validada } = useValidacionEnVivo(
    reglaActual, permitido && panelReglas
  )

  if (!permitido)
    return (
      <Panel title="Adquisición del conocimiento">
        <p>
          Esta función corresponde al rol de ingeniería del conocimiento. Los
          umbrales y las reglas no se modifican desde la captura ni desde el
          seguimiento.
        </p>
      </Panel>
    )
  if (catalogo.isLoading || versiones.isLoading || detalle.isLoading) return <Loading />
  const parametros = catalogo.data?.parametros || []

  // ─── Sincronización visual ↔ código ────────────────────────────
  function abrirRegla(regla: Record<string, unknown>, ficha?: Ficha | null) {
    const copia = structuredClone(regla)
    const codigo = codigoDocumental(copia)
    const fichaBase = ficha ?? cambiosFichas[codigo] ?? detalle.data?.fichas.find((f) => f.id === codigo)
    setReglaActual(copia)
    setCodigoRegla(JSON.stringify(copia, null, 2))
    setReglaId(String(copia.id || ""))
    setFichaActual(fichaBase ? { ...structuredClone(fichaBase), fuentes: [...(fichaBase.fuentes || [])] } : null)
    setModoRegla(admiteEditorVisual(copia.si) ? "visual" : "codigo")
    setErrorEditor("")
    setPanelReglas(true)
  }

  function siguienteId(): string {
    const ids = [
      ...(detalle.data?.reglas.map((r) => String(r.id)) || []),
      ...Object.keys(cambiosReglas),
    ]
    const maximo = Math.max(30, ...ids.map((id) => {
      const match = /^R([0-9]+)$/.exec(id)
      return match ? Number(match[1]) : 0
    }))
    return `R${String(maximo + 1).padStart(2, "0")}`
  }

  function sugerirVersion(): void {
    if (versionBase || !activa) return
    const partes = /^(.*\.)([0-9]+)$/.exec(activa.version_base)
    if (!partes) return
    const usadas = new Set(versiones.data?.map((v) => `${v.version_base}/${v.version_parametros}`))
    let numero = Number(partes[2]) + 1
    while (usadas.has(`${partes[1]}${numero}/${versionParametros || activa.version_parametros}`)) numero++
    setVersionBase(`${partes[1]}${numero}`)
  }

  function nuevaRegla() {
    const id = siguienteId()
    abrirRegla(reglaVacia(id), fichaVacia(id))
  }

  function cargarReglaExistente(id: string) {
    const regla = cambiosReglas[id] ?? detalle.data?.reglas.find((r) => r.id === id)
    if (regla) abrirRegla(regla)
  }

  function actualizarDesdeVisual(updated: Record<string, unknown>) {
    setReglaActual(updated)
    setCodigoRegla(JSON.stringify(updated, null, 2))
    setErrorEditor("")
  }

  function actualizarDesdeCodigo(code: string) {
    setCodigoRegla(code)
    try {
      const parsed = JSON.parse(code)
      if (!esObjeto(parsed)) throw new Error("La definición debe ser un objeto JSON")
      setReglaActual(parsed)
      setErrorEditor("")
    } catch {
      setReglaActual(null)
      setErrorEditor("El JSON de la regla no es válido")
    }
  }

  function aplicarRegla() {
    if (!reglaActual || String(reglaActual.id || "") !== reglaId) {
      setErrorEditor("El identificador de la regla no debe cambiarse")
      return
    }
    if (!validada || validando || erroresVivo.length) {
      setErrorEditor("Corrige los errores de la regla antes de aplicarla")
      return
    }
    const codigo = codigoDocumental(reglaActual)
    const esNueva = !detalle.data?.reglas.some((r) => r.id === reglaId)
    if (esNueva && (!esAdicional(reglaId) || codigo !== reglaId)) {
      setErrorEditor("Una regla nueva debe usar el siguiente código R31+ como ID y ficha")
      return
    }
    if (esNueva && !fichaActual) {
      setErrorEditor("La regla nueva necesita una ficha documental")
      return
    }
    if (fichaActual && [fichaActual.antecedente, fichaActual.consecuente, fichaActual.accion, fichaActual.fundamento_markdown].some((v) => !v.trim())) {
      setErrorEditor("Completa el antecedente, consecuente, acción y fundamento de la ficha")
      return
    }
    setCambiosReglas((actuales) => ({ ...actuales, [reglaId]: structuredClone(reglaActual) }))
    if (fichaActual) setCambiosFichas((actuales) => ({ ...actuales, [codigo]: structuredClone(fichaActual) }))
    sugerirVersion()
    setPanelReglas(false)
    setResultado(null)
  }

  // ─── Construcción del cuerpo de la propuesta ───────────────────
  function cuerpo(guardar: boolean) {
    const cambios: Record<string, number> = {}
    for (const [k, v] of Object.entries(valores)) {
      if (v.trim() === "") continue
      const n = Number(v.replace(",", "."))
      if (!Number.isFinite(n))
        throw new Error(`El valor de ${k} no es un número`)
      cambios[k] = n
    }
    return {
      motivo,
      parametros: cambios,
      reglas: cambiosReglas,
      fichas: cambiosFichas,
      version_parametros: versionParametros || null,
      version_base: versionBase || null,
      guardar,
    }
  }

  const firmaActual = JSON.stringify({ valores, motivo, versionParametros, versionBase, cambiosReglas, cambiosFichas })
  const hayCambiosReglas = Object.keys(cambiosReglas).length > 0 || Object.keys(cambiosFichas).length > 0

  async function enviar(guardar: boolean) {
    setBusy(true)
    setError(null)
    try {
      if (panelReglas) throw new Error("Aplica o cancela la edición de la regla antes de continuar")
      if (guardar && (firmaSimulada !== firmaActual || !resultado?.valida || resultado.version)) {
        throw new Error("Simula los cambios actuales antes de registrar la propuesta")
      }
      const r = await post<Resultado>("/adquisicion/propuestas", cuerpo(guardar))
      setResultado(r)
      if (!guardar) setFirmaSimulada(firmaActual)
      if (r.version) await qc.invalidateQueries({ queryKey: ["versiones"] })
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  async function activar(v: Version) {
    setBusy(true)
    setError(null)
    try {
      await post<Version>(`/adquisicion/versiones/${v.id}/activar`, {
        motivo: motivoActivacion[v.id] || "",
      })
      setResultado(null)
      setValores({})
      setCambiosReglas({})
      setCambiosFichas({})
      setVersionBase("")
      setVersionParametros("")
      setMotivo("")
      setFirmaSimulada("")
      await qc.invalidateQueries()
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  async function descartar(v: Version) {
    setBusy(true)
    setError(null)
    try {
      await post<Version>(`/adquisicion/versiones/${v.id}/descartar`, { motivo: motivoDescarte[v.id] || "" })
      await qc.invalidateQueries({ queryKey: ["versiones"] })
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }

  function retirarRegla(id: string) {
    const regla = detalle.data?.reglas.find((r) => r.id === id) ?? cambiosReglas[id]
    if (!regla) return
    const codigo = codigoDocumental(regla)
    if (!esAdicional(codigo)) return
    if (detalle.data?.reglas.some((r) => r.id === id)) {
      setCambiosReglas((actuales) => ({ ...actuales, [id]: null }))
    } else {
      setCambiosReglas((actuales) => {
        const copia = { ...actuales }
        delete copia[id]
        return copia
      })
    }
    setCambiosFichas((actuales) => {
      const copia = { ...actuales }
      delete copia[codigo]
      return copia
    })
    if (reglaId === id) setPanelReglas(false)
    sugerirVersion()
    setResultado(null)
  }

  function deshacerRetiro(id: string) {
    setCambiosReglas((actuales) => {
      const copia = { ...actuales }
      delete copia[id]
      return copia
    })
    setResultado(null)
  }

  const reglasListado = [
    ...(detalle.data?.reglas || []).map((r) => cambiosReglas[r.id] || r),
    ...Object.entries(cambiosReglas)
      .filter(([id, regla]) => regla && !detalle.data?.reglas.some((r) => r.id === id))
      .map(([, regla]) => regla!),
  ]
  const reglasFiltradas = filtroRegla
    ? reglasListado.filter(
        (r) =>
          String(r.id).toLowerCase().includes(filtroRegla.toLowerCase()) ||
          String(r.regla || "")
            .toLowerCase()
            .includes(filtroRegla.toLowerCase()) ||
          String(r.etapa || "")
            .toLowerCase()
            .includes(filtroRegla.toLowerCase())
      )
    : reglasListado

  return (
    <div className="stack">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Módulo de adquisición del conocimiento</p>
          <h1>Mantener la base de conocimiento</h1>
          <p className="muted">
            Activa: base {activa?.version_base} · parámetros{" "}
            {activa?.version_parametros} · huella{" "}
            {activa?.hash_base.slice(0, 12)}
          </p>
        </div>
      </div>
      <p className="message">
        Un cambio aquí altera lo que el sistema decide para las evaluaciones
        futuras. Las evaluaciones ya emitidas conservan la versión con que se
        resolvieron.
      </p>
      <ErrorMessage error={error || catalogo.error || versiones.error || detalle.error} />

      {/* ── 1. Proponer cambios de parámetros ────────────────────── */}
      <Panel title="1. Proponer cambios de parámetros">
        <div className="table-scroll">
          <table className="parametros">
            <thead>
              <tr>
                <th>Parámetro</th>
                <th>Descripción</th>
                <th>Fundamento</th>
                <th>Actual</th>
                <th>Propuesto</th>
              </tr>
            </thead>
            <tbody>
              {parametros.map((p) => (
                <tr
                  key={p.nombre}
                  className={valores[p.nombre] ? "modificado" : ""}
                >
                  <td>
                    <code>{p.nombre}</code>
                  </td>
                  <td>
                    {p.descripcion}
                    <small>{nombre(p.unidad)}</small>
                  </td>
                  <td>
                    {nombre(p.fundamento)}
                    {p.fuentes.length > 0 && (
                      <small>{p.fuentes.join(", ")}</small>
                    )}
                  </td>
                  <td>{p.valor}</td>
                  <td>
                    <input
                      aria-label={`Nuevo valor de ${p.nombre}`}
                      inputMode="decimal"
                      value={valores[p.nombre] || ""}
                      placeholder="Sin cambio"
                      onChange={(e) =>
                        setValores((v) => ({
                          ...v,
                          [p.nombre]: e.target.value,
                        }))
                      }
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* ── 2. Gestión de reglas de producción ────────────────────── */}
      <Panel title="2. Reglas de producción">
        <div className="reglas-toolbar">
          <input
            type="search"
            placeholder="Buscar regla por ID, nombre o etapa…"
            value={filtroRegla}
            onChange={(e) => setFiltroRegla(e.target.value)}
          />
          <button className="primary" onClick={nuevaRegla} disabled={!detalle.data}>
            + Añadir nueva regla
          </button>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Regla</th>
                <th>Etapa</th>
                <th>Hallazgo</th>
                <th>Solicitudes</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {reglasFiltradas.map((r) => (
                <tr
                  key={String(r.id)}
                  className={reglaId === String(r.id) ? "modificado" : ""}
                >
                  <td>
                    <code>{String(r.id)}</code>
                  </td>
                  <td>{String(r.regla || r.id)}</td>
                  <td>
                    <small>{String(r.etapa || "encadenamiento")}</small>
                  </td>
                  <td>
                    <small>
                      {String(
                        (r.entonces as Record<string, unknown>)?.hallazgo || "—"
                      )}
                    </small>
                  </td>
                  <td>
                    {(
                      (r.entonces as Record<string, unknown>)?.solicitudes as
                        | string[]
                        | undefined
                    )
                      ?.map((s) => (
                        <span key={s} className="chip">
                          {s}
                        </span>
                      )) || "—"}
                  </td>
                  <td>
                    <div className="actions-inline">
                      {Object.prototype.hasOwnProperty.call(cambiosReglas, String(r.id)) && (
                        <span className="chip cambio">
                          {cambiosReglas[String(r.id)] === null ? "Retiro pendiente" : "Cambio pendiente"}
                        </span>
                      )}
                      {cambiosReglas[String(r.id)] === null ? (
                        <button onClick={() => deshacerRetiro(String(r.id))}>Deshacer</button>
                      ) : <>
                      <button
                        onClick={() => cargarReglaExistente(String(r.id))}
                      >
                        Editar
                      </button>
                      <button
                        onClick={() => {
                          const id = siguienteId()
                          const copia = structuredClone(r)
                          copia.id = id
                          copia.regla = id
                          const original = detalle.data?.fichas.find((f) => f.id === codigoDocumental(r))
                          abrirRegla(copia, original ? { ...structuredClone(original), id, fuentes: [...(original.fuentes || [])] } : fichaVacia(id))
                        }}
                      >
                        Duplicar
                      </button>
                      <button
                        className="danger"
                        disabled={!esAdicional(codigoDocumental(r))}
                        title={!esAdicional(codigoDocumental(r)) ? "Las reglas base no se pueden retirar" : undefined}
                        onClick={() => retirarRegla(String(r.id))}
                      >
                        Retirar
                      </button>
                      </>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {reglasListado.length === 0 && (
          <Empty>No hay reglas cargadas en la versión activa.</Empty>
        )}
        {hayCambiosReglas && <p className="message">Hay cambios de reglas pendientes. Simula el impacto y registra una propuesta para conservarlos.</p>}
      </Panel>

      {/* ── 3. Editor híbrido de regla ────────────────────────────── */}
      {panelReglas && (
        <Panel title={`3. Editor de regla: ${reglaId || "nueva"}`}>
          <div className="editor-tabs">
            <button
              className={modoRegla === "visual" ? "tab active" : "tab"}
              onClick={() => setModoRegla("visual")}
            >
              🧩 Asistente visual
            </button>
            <button
              className={modoRegla === "codigo" ? "tab active" : "tab"}
              onClick={() => setModoRegla("codigo")}
            >
              {"</>"} Código JSON
            </button>
            {validando && <span className="muted">Validando…</span>}
          </div>

          {modoRegla === "visual" && reglaActual && (
            <div className="editor-visual stack">
              <div className="form-grid">
                <Field label="Identificador">
                  <input
                    type="text"
                    value={String(reglaActual.id || "")}
                    readOnly
                  />
                </Field>
                <Field label="Etapa">
                  <select
                    value={String(reglaActual.etapa || "encadenamiento")}
                    onChange={(e) =>
                      actualizarDesdeVisual({
                        ...reglaActual,
                        etapa: e.target.value,
                      })
                    }
                  >
                    {ETAPAS.map((et) => (
                      <option key={et} value={et}>
                        {nombre(et)}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
              <h3>Condición SI</h3>
              <CondicionEditor
                nodo={
                  (reglaActual.si as Record<string, unknown>) || {
                    dato: "",
                    op: "GT",
                    valor: 0,
                  }
                }
                onChange={(si) =>
                  actualizarDesdeVisual({ ...reglaActual, si })
                }
              />
              <h3>Consecuente ENTONCES</h3>
              <ConsecuenteEditor
                entonces={
                  (reglaActual.entonces as Record<string, unknown>) || {
                    hallazgo: "",
                    solicitudes: [],
                    mensaje: "",
                  }
                }
                onChange={(entonces) =>
                  actualizarDesdeVisual({ ...reglaActual, entonces })
                }
              />
            </div>
          )}

          {modoRegla === "codigo" && (
            <div className="editor-codigo">
              <textarea
                rows={20}
                spellCheck={false}
                value={codigoRegla}
                onChange={(e) => actualizarDesdeCodigo(e.target.value)}
                style={{ fontFamily: "monospace", fontSize: 12 }}
              />
            </div>
          )}

          {fichaActual && (
            <div className="stack">
              <h3>Ficha documental {fichaActual.id}</h3>
              <p className="muted">Describe y fundamenta el cambio que quedará en el catálogo de conocimiento.</p>
              <div className="form-grid">
                <Field label="Antecedente documentado">
                  <textarea value={fichaActual.antecedente} onChange={(e) => setFichaActual({ ...fichaActual, antecedente: e.target.value })} />
                </Field>
                <Field label="Consecuente documentado">
                  <textarea value={fichaActual.consecuente} onChange={(e) => setFichaActual({ ...fichaActual, consecuente: e.target.value })} />
                </Field>
                <Field label="Acción recomendada">
                  <textarea value={fichaActual.accion} onChange={(e) => setFichaActual({ ...fichaActual, accion: e.target.value })} />
                </Field>
                <Field label="Tipo de fundamento">
                  <select value={fichaActual.fundamento} onChange={(e) => setFichaActual({ ...fichaActual, fundamento: e.target.value as Ficha["fundamento"] })}>
                    {FUNDAMENTOS.map((f) => <option key={f} value={f}>{nombre(f)}</option>)}
                  </select>
                </Field>
              </div>
              <Field label="Fundamento y referencias">
                <textarea value={fichaActual.fundamento_markdown} onChange={(e) => setFichaActual({ ...fichaActual, fundamento_markdown: e.target.value })} placeholder="Explica la evidencia y cita sus fuentes" />
              </Field>
              <Field label="Fuentes del catálogo">
                <div className="check-group">
                  {catalogo.data?.fuentes.map((fuente) => (
                    <label key={fuente.id} className="check">
                      <input type="checkbox" checked={fichaActual.fuentes.includes(fuente.id)} onChange={(e) => setFichaActual({
                        ...fichaActual,
                        fuentes: e.target.checked ? [...fichaActual.fuentes, fuente.id] : fichaActual.fuentes.filter((id) => id !== fuente.id),
                      })} />
                      {fuente.id}
                    </label>
                  ))}
                </div>
              </Field>
            </div>
          )}

          {/* Errores de validación en vivo */}
          {erroresVivo.length > 0 && (
            <div className="aviso">
              <strong>Errores de sintaxis detectados:</strong>
              <ul>
                {erroresVivo.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          )}
          {erroresVivo.length === 0 && reglaActual && validada && !validando && (
            <p className="message" style={{ color: "var(--ok)" }}>
              ✓ La regla es sintácticamente correcta
            </p>
          )}

          {errorEditor && <p className="aviso" role="alert">{errorEditor}</p>}

          <div className="actions">
            <button className="primary" disabled={busy || validando || !reglaActual} onClick={aplicarRegla}>Aplicar cambio a la propuesta</button>
            <button onClick={() => { setPanelReglas(false); setErrorEditor("") }}>Cancelar edición</button>
          </div>
          <p className="muted">
            Un cambio de reglas exige una nueva versión de la base. El validador
            rechaza operadores, parámetros o definiciones que no existan.
          </p>
        </Panel>
      )}

      {/* ── 4. Versión y motivo ───────────────────────────────────── */}
      <Panel title="3. Versión y envío">
        <div className="form-grid">
          <Field label="Motivo del cambio (obligatorio)">
            <textarea
              required
              minLength={15}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              placeholder="Fuente, revisión técnica o evidencia que justifica el cambio"
            />
          </Field>
          <Field label="Nueva versión de parámetros">
            <input
              value={versionParametros}
              onChange={(e) => setVersionParametros(e.target.value)}
              placeholder={`Actual ${activa?.version_parametros}`}
            />
          </Field>
          {(panelReglas || hayCambiosReglas) && (
            <Field label="Nueva versión de la base">
              <input
                value={versionBase}
                onChange={(e) => setVersionBase(e.target.value)}
                placeholder={`Actual ${activa?.version_base}`}
              />
            </Field>
          )}
        </div>
        <div className="actions">
          <button disabled={busy || panelReglas} onClick={() => void enviar(false)}>
            {busy ? "Evaluando casos…" : "Simular impacto"}
          </button>
          <button
            className="primary"
            disabled={busy || panelReglas || !resultado?.valida || !!resultado.version || firmaSimulada !== firmaActual}
            onClick={() => void enviar(true)}
          >
            Registrar propuesta
          </button>
        </div>
        <p className="muted">
          La simulación evalúa los casos de referencia y las últimas evaluaciones
          emitidas con la versión activa y con la propuesta. Puede tardar unos
          segundos.
        </p>
        {panelReglas && <p className="muted">Aplica o cancela la edición abierta para continuar.</p>}
      </Panel>

      {/* ── Validación e impacto ──────────────────────────────────── */}
      {resultado && (
        <Panel title="Validación e impacto">
          {resultado.valida ? (
            <p className="message">
              Propuesta válida · versión {resultado.version_base}/
              {resultado.version_parametros}
              {resultado.version ? " · registrada como propuesta" : ""}
            </p>
          ) : (
            <div className="aviso">
              <strong>La propuesta no es válida:</strong>
              <ul>
                {resultado.errores.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </div>
          )}
          {resultado.advertencias.map((a, i) => (
            <p className="aviso" key={i}>
              ⚠ {a}
            </p>
          ))}
          {resultado.cambios_parametros.length > 0 && (
            <div className="chips">
              {resultado.cambios_parametros.map((c) => (
                <span className="chip cambio" key={c.nombre}>
                  {c.nombre}: {c.anterior} → {c.nuevo}
                </span>
              ))}
            </div>
          )}
          {resultado.cambios_reglas.length > 0 && (
            <div className="chips">
              {resultado.cambios_reglas.map((c) => (
                <span className="chip cambio" key={c.produccion}>
                  {nombre(c.tipo)}: {c.produccion}
                </span>
              ))}
            </div>
          )}
          {resultado.impacto && (
            <>
              <div className="metrics">
                <div>
                  <span>Casos evaluados</span>
                  <strong>{resultado.impacto.evaluados}</strong>
                </div>
                <div>
                  <span>Cambian de decisión</span>
                  <strong>{resultado.impacto.cambian}</strong>
                </div>
                <div>
                  <span>Nuevas autorizaciones</span>
                  <strong>{resultado.impacto.nuevas_autorizaciones}</strong>
                </div>
              </div>
              {Object.entries(resultado.impacto.transiciones).map(([t, n]) => (
                <p className="row" key={t}>
                  <span>
                    {t
                      .split(" → ")
                      .map(decision)
                      .join(" → ")}
                  </span>
                  <strong>{n}</strong>
                </p>
              ))}
              {resultado.impacto.casos.length > 0 && (
                <details>
                  <summary>
                    Casos afectados ({resultado.impacto.casos.length})
                  </summary>
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Caso</th>
                          <th>Antes</th>
                          <th>Después</th>
                          <th>Reglas</th>
                        </tr>
                      </thead>
                      <tbody>
                        {resultado.impacto.casos.map((c) => (
                          <tr key={c.id}>
                            <td>
                              <small>{c.origen}</small>
                              {c.id.split(":").slice(1).join(":")}
                            </td>
                            <td>
                              {decision(c.decision_antes)}
                              <small>{c.rama_antes}</small>
                            </td>
                            <td>
                              {decision(c.decision_despues)}
                              <small>{c.rama_despues}</small>
                            </td>
                            <td>
                              {c.reglas_nuevas
                                .map((r) => "+" + r)
                                .concat(c.reglas_retiradas.map((r) => "−" + r))
                                .join(" ")}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
              )}
              {resultado.impacto.cambian === 0 && (
                <p className="muted">
                  Ningún caso cambia de decisión. Revisa si el cambio tiene
                  efecto en la práctica.
                </p>
              )}
            </>
          )}
        </Panel>
      )}

      {/* ── Versiones ─────────────────────────────────────────────── */}
      <Panel title="Versiones">
        {versiones.data?.length ? (
          versiones.data.map((v) => (
            <div className="reason" key={v.id}>
              <p>
                <strong>
                  Base {v.version_base} · parámetros {v.version_parametros}
                </strong>{" "}
                <span className={`badge ${v.activa ? "good" : ""}`}>
                  {v.activa ? "Activa" : nombre(v.estado)}
                </span>
              </p>
              <p className="muted">
                {v.motivo || "Sin motivo registrado"} · cargada{" "}
                {fecha(v.cargada_en)}
                {v.activada_en ? ` · activada ${fecha(v.activada_en)}` : ""} ·
                motor {v.version_motor} · {v.hash_base.slice(0, 12)}
              </p>
              {!v.activa && v.estado === "PROPUESTA" && (
                <div className="form-grid">
                  <Field label="Motivo de la activación">
                    <input
                      value={motivoActivacion[v.id] || ""}
                      onChange={(e) =>
                        setMotivoActivacion((m) => ({
                          ...m,
                          [v.id]: e.target.value,
                        }))
                      }
                      placeholder="Revisión y aprobación de la propuesta"
                    />
                  </Field>
                  <div className="actions">
                    <button
                      className="primary"
                      disabled={
                        busy || (motivoActivacion[v.id] || "").length < 15
                      }
                      onClick={() => void activar(v)}
                    >
                      Activar esta versión
                    </button>
                  </div>
                  <p className="muted">La activación requiere otra cuenta de ingeniería. En local, inicia sesión como <code>revisor</code> con la contraseña configurada.</p>
                  <Field label="Motivo del descarte">
                    <input value={motivoDescarte[v.id] || ""} onChange={(e) => setMotivoDescarte((m) => ({ ...m, [v.id]: e.target.value }))} placeholder="Razón para cerrar esta propuesta" />
                  </Field>
                  <div className="actions">
                    <button className="danger" disabled={busy || (motivoDescarte[v.id] || "").trim().length < 15} onClick={() => void descartar(v)}>Descartar propuesta</button>
                  </div>
                </div>
              )}
            </div>
          ))
        ) : (
          <Empty>No hay versiones registradas.</Empty>
        )}
      </Panel>
    </div>
  )
}
