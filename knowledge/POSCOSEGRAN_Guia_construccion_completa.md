# POSCOSEGRAN — guía única de construcción
Versión 1.1 · 12 de septiembre de 2026

## Uso y alcance
Este archivo reúne los prompts de construcción, el contrato de API, la matriz de campos y los escenarios de interfaz. Ejecuta **una etapa por turno**: 1–5 en Lovable; 6–8 en Claude sobre el repositorio exportado. Entrega este archivo como contexto permanente y copia el texto de la etapa correspondiente.

La fuente del dominio sigue siendo [POSCOSEGRAN_30_reglas_base_conocimiento_actualizado.md](POSCOSEGRAN_30_reglas_base_conocimiento_actualizado.md), **versión 2.0 completa**, que debe estar disponible en ambos entornos. Esta guía sustituye los prompts anteriores; no sustituye las 30 reglas, sus fuentes, tablas auxiliares ni los casos C01–C40. Avance_SI.md aporta contexto académico. Si falta la base operativa, se puede construir la estructura, pero no completar ni validar el motor mediante supuestos.

Piloto: maíz chulpi seco para alimentación; ingreso y seguimiento en almacenamiento hermético/no hermético; captura manual. Cada evaluación corresponde a un lote, recipiente o grupo homogéneo y almacén. Condiciones distintas requieren unidades separadas. El resultado orienta el almacenamiento; no certifica inocuidad.

## Arquitectura decidida
| Componente | Elección y responsabilidad |
|---|---|
| Interfaz | React + TypeScript estricto + TanStack Start/Router, Tailwind CSS, shadcn/ui, Lucide, React Hook Form, Zod y TanStack Query. |
| Backend | Python 3.13, FastAPI y Pydantic 2; monolito modular con dominio, servicios de aplicación, persistencia y API separados. |
| Motor | Encadenamiento hacia adelante determinista; reglas y parámetros versionados, ejecución exclusiva en Python. |
| Persistencia | PostgreSQL de Supabase, SQLAlchemy 2, Psycopg 3 y Alembic. Es necesaria para historial, vigencia, incidencias y auditoría. |
| Identidad | Supabase Auth; FastAPI verifica identidad y permisos sobre cada recurso. |
| Despliegue | Frontend SSR Node y backend FastAPI como servicios Docker en Render; Supabase para PostgreSQL/Auth. |

Stack de proyectos nuevos confirmado en la [FAQ de Lovable](https://docs.lovable.dev/introduction/faq). No mezclarlo con React Router o una segunda arquitectura. Durante Lovable, utilizar datos simulados identificados; no activar Lovable Cloud ni implementar reglas en funciones del frontend.

Flujo definitivo: navegador → Supabase Auth → FastAPI → motor y PostgreSQL. El SSR entrega la estructura; las consultas privadas se realizan después de autenticar, sin caché compartida. La interfaz muestra decisiones; el servidor las determina.

## Instrucción común para todas las etapas
Conserva lo construido, usa exactamente el contrato del anexo A y la matriz del anexo B y limita cada turno a su etapa. No derives nuevos campos, umbrales ni decisiones. Separa presentación, servicios y adaptadores mock/API con una interfaz común. Un cambio incompatible requiere actualizar conjuntamente contrato, cliente, backend y pruebas; no improvises variantes.

Entrega código ejecutable, comprobaciones realizadas, documentación actualizada y pendientes concretos. No presentes simulaciones como resultados reales ni declares pruebas que no ejecutaste. Mantén secretos fuera del repositorio.

## Etapa 1 — Lovable: estructura y diseño
Actúa como diseñador UX/UI senior. Construye únicamente el sistema visual, componentes básicos, navegación y pantalla Inicio de POSCOSEGRAN con el stack fijado. Deja identificadas las rutas posteriores del anexo B.

Diseño móvil primero: marfil, verde profundo y acento maíz; texto base de 16 px, objetivos táctiles de 44 px, contraste WCAG AA, foco visible, navegación por teclado y estados con texto además de color. Usa español, lenguaje de productores y fechas America/Lima. Prioriza “Evaluar unidad” y controles pendientes. Evita gráficos decorativos. Crea adaptador mock tipado y comprueba compilación y vistas de 360 y 1440 px.

## Etapa 2 — Lovable: captura guiada
Continúa sin rediseñar. Implementa alta/selección de almacén, lote y unidad, y el formulario P1–P6 del anexo B con React Hook Form y Zod. Muestra unidades, fecha, método, evidencia, procedencia y obligatoriedad condicional. Diferencia Sí/No/No se sabe; no preselecciones respuestas favorables. Los derivados son solo lectura.

Permite guardar/recuperar borrador y enviar observaciones parciales. La ausencia de otras mediciones no debe impedir registrar moho conocido. En seguimiento hermético no exijas apertura rutinaria. El envío usa el contrato y confirma la demostración; todavía no calcula decisiones. Comprueba validación, navegación y recuperación del borrador.

## Etapa 3 — Lovable: resultados explicables
Implementa ResultadoEvaluacion usando los ocho escenarios del anexo C, elegidos explícitamente en modo demostración. Editar mediciones no ejecuta reglas simuladas.

Muestra decisión única, acciones, motivos con identificadores de reglas y fuentes, datos pendientes, estimaciones y vigencia. Distingue resultado histórico de autorización vigente. Explica vida_consumida como fracción del tiempo de referencia, nunca porcentaje de seguridad. Añade carga, ausencia de datos, error y sesión expirada; conserva el formulario ante fallos. Verifica los siete códigos de decisión y el caso vencido.

## Etapa 4 — Lovable: seguimiento y conocimiento
Implementa historial por unidad, controles, eventos, planes, dictámenes, revisión de incidencias y catálogo de conocimiento con los esquemas fijados. Conserva R01–R30, sus nueve ramas R30 y fuentes.

Identifica roles simulados. Las acciones técnicas corresponden al técnico asignado; el backend aplicará el permiso real. Una incidencia no desaparece al cambiar una medición ni un control se completa al abrir una pantalla. No permitas editar umbrales. Usa el reloj fijo de los escenarios y etiqueta la información simulada.

## Etapa 5 — Lovable: entrega del frontend
Corrige rutas, formularios, accesibilidad y estados vacíos/errores. Verifica vistas de 360, 768 y 1440 px, tipos, compilación y pruebas pertinentes. Exporta a GitHub.

Crea docs/FRONTEND.md, docs/UX_UI.md y docs/INTEGRACION_FRONTEND.md: estructura, decisiones visuales, adaptadores, comandos y conexiones pendientes. Guarda esta guía como especificación fija. Documenta que conectar producción requiere autenticación, permisos, URL, CORS y pruebas; cambiar el adaptador por sí solo no completa la integración.

## Etapa 6 — Claude: persistencia y seguridad
Trabaja sobre el repositorio de Lovable; conserva su estructura y añade backend/, knowledge/ y docs/ donde corresponda. Prepara configuración reproducible y dependencias fijadas. Copia la base operativa a knowledge/ con su versión y fuentes.

Implementa SQLAlchemy/Alembic para usuarios y asignaciones, almacenes, lotes/unidades, borradores, observaciones e historial temporal, evaluaciones, controles, eventos, planes, dictámenes, incidencias/revisiones/resoluciones, admisiones, versiones de conocimiento, auditoría e idempotencia. Usa claves foráneas, restricciones, índices y transacciones. Las evaluaciones son inmutables: conserva entradas efectivas, trazas, fuentes, versiones y fecha del servidor. Corrige registros mediante nuevos eventos trazables.

Configura Supabase Auth y verifica JWT en FastAPI mediante JWKS, algoritmo permitido, firma, emisor, audiencia y expiración. Aplica rol y propiedad/asignación en toda consulta y escritura; administrador no implica técnico. Usa un esquema privado fuera de la Data API y una credencial de aplicación con privilegios mínimos; reserva la credencial de migraciones para despliegue. No presupongas que RLS identifica al usuario con una conexión SQLAlchemy compartida. Nunca expongas credenciales de base de datos o service_role al navegador.

Añade auditoría sin tokens ni secretos, límites de petición y CORS por orígenes explícitos. Documenta en docs/BASE_DATOS.md y docs/SEGURIDAD.md el modelo, migraciones, permisos y aprovisionamiento de roles/asignaciones. Estos últimos se gestionan mediante un procedimiento administrativo documentado, sin inventar endpoints fuera del contrato.

## Etapa 7 — Claude: motor y API
Implementa el contrato del anexo A con FastAPI/Pydantic, incluidos eventos del anexo B. Genera OpenAPI y tipos cliente verificables contra esta especificación. Separa validación estructural, validación del dominio, inferencia y persistencia.

Transcribe la base 2.0 completa a reglas declarativas validadas y operadores permitidos; nunca eval/exec ni inferencia mediante LLM. Conserva fuentes por regla y diferencia evidencia publicada, transferencia y política del prototipo. Implementa:
- Lógica VERDADERO/FALSO/DESCONOCIDO; NO_APLICA solo cuando proceda. Datos inválidos o vencidos nunca se convierten en favorables.
- Encadenamiento R01–R26 hasta punto fijo; después riesgo temporal R28–R29, vigencia R27, consolidación y resolución R30 conforme a la base. Detecta ciclos improductivos y comprueba R20→R19.
- Una decisión final, según las nueve ramas ordenadas R30. Conserva hallazgos prioritarios aunque falten otros datos. Reconstruye hechos derivados en cada evaluación; mantén incidencias hasta su resolución válida.
- Cálculo temporal conservador con tablas, intervalos y conversiones de la base: sin extrapolaciones, sin interpretar celdas vacías como cero y sin reiniciar vida consumida al secar/enfriar. Trata expresamente lagunas del historial y estimaciones.
- Vigencia calculada con reloj del servidor al consultar y antes de admitir/continuar. Una evaluación histórica no se modifica ni recupera vigencia por cambiar fechas.

Ejecuta el motor sobre una instantánea coherente; guarda evaluación y efectos en una transacción con comprobación de revisiones de unidad/almacén. Implementa idempotencia, conflictos y propagación de cambios del almacén a unidades afectadas. No persistas resultados parciales si falla la operación.

Ejecuta C01–C40 y pruebas de límites, desconocidos, vencimientos, conflictos concurrentes, reintentos y acceso entre usuarios. Usa pytest y pruebas de propiedades donde aporten valor; comprueba determinismo. Documenta en docs/MOTOR.md y docs/TRAZABILIDAD.md la relación regla→fuente→implementación→prueba. Un caso no resoluble con la base se registra como pendiente, no se “resuelve” inventando conocimiento.

## Etapa 8 — Claude: integración, despliegue y uso
Integra Supabase Auth, el cliente tipado y el adaptador API real. Conserva la interfaz de Lovable. Añade inicio/cierre y recuperación de sesión, renovación de credenciales, errores de permisos y conflictos sin perder captura. Desactiva el selector de escenarios en producción y no uses mock como respaldo ante fallos.

Prueba el recorrido real: acceso → crear almacén/lote/unidad → capturar → evaluar → consultar explicación y fuentes → registrar seguimiento → revisión técnica cuando proceda → reevaluar. Comprueba también vencimiento, cuarentena persistente y bloqueo de admisión no autorizada.

Entrega Dockerfiles y Docker Compose para frontend/backend local, conectado a un proyecto Supabase de desarrollo; documenta que requiere conexión. Para Render: configura Supabase y sus URLs de autenticación, ejecuta migraciones con credencial separada, despliega FastAPI, configura URL pública y CORS, y despliega el servidor Node SSR con HTTPS. Añade verificaciones de salud, logs con identificador de solicitud, copias de seguridad con procedimiento de restauración probado y reversión compatible de aplicación/migraciones.

Crea .env.example sin secretos. Ejecuta lint, tipos, pruebas del backend, compilación y recorridos esenciales Playwright contra API real; incorpora estas verificaciones a CI. Documenta comandos exactos y resultados reales.

Completa README.md y docs/ARQUITECTURA.md, docs/API.md, docs/INSTALACION_DESPLIEGUE.md, docs/MANUAL_USUARIO.md y docs/PRUEBAS.md, además de los documentos anteriores. Incluye diagrama de componentes, configuración, roles, puesta en marcha, respaldo/restauración, limitaciones y pendientes; evita repetir contenido entre archivos. Registra decisiones y cambios en docs/DECISIONES.md.

**Criterio de entrega:** frontend utilizable conectado al backend, contrato coherente, motor reproducible con fuentes, historial persistente, permisos comprobados y despliegue documentado. La validación técnica no equivale a validación agronómica de campo.

---

# Anexos de implementación
Especificación de diseño obligatoria; no implica que exista un servidor desplegado. Se conserva el contrato v1 y la matriz completa para evitar que Lovable o Claude deban deducirlos.

## Anexo A — Contrato de API

### A.1 Reglas de intercambio

- Base: `/api/v1`. JSON UTF-8, nombres snake_case. Rutas de la aplicación y rutas API son diferentes.
- UUID como identificadores; fechas-hora ISO 8601 con zona, normalizadas a UTC; presentación America/Lima. El reloj de autorización pertenece al servidor.
- Todas las propiedades de los tipos de este documento están presentes. `| null` significa ausencia explícita. Listas sin elementos: `[]`. No inventar valores favorables para completar objetos.
- Números JSON finitos; los decimales se envían con punto. El formulario acepta coma y punto. El servidor compara sin redondeos de presentación.
- Un campo de observación omitido significa desconocido; no implica falso, cero ni no aplicable. Las evaluaciones aceptan observaciones parciales.
- Observaciones no aplicables requieren causa válida; el servidor decide su aplicabilidad. Un dato fuera de dominio puede conservarse y producir corrección; no se usa en comparaciones. Un fallo estructural de JSON/tipo utiliza HTTP 422. La interfaz debe permitir registrar moho conocido aun con otras observaciones incompletas o inválidas.
- Bearer de Supabase Auth en la API real. El servidor obtiene usuario, roles y asignaciones. No acepta identidad del evaluador, decisiones ni campos calculados impuestos por el cliente.
- POST y PUT requieren `Idempotency-Key` (UUID). Reintento idéntico devuelve el recurso original; reutilización con otro contenido devuelve 409.
- PATCH de recursos y PUT de borrador requieren `If-Match` con la revisión numérica entre comillas. Crear borrador requiere `If-None-Match: *`. Escritura con revisión obsoleta: 409; falta de precondición: 428. GET del recurso devuelve ETag.
- Los comandos de unidad incluyen revisiones esperadas de unidad y almacén. El servidor verifica ambas dentro de la transacción para evitar decidir sobre condiciones concurrentemente modificadas.
- Listas: `?cursor=...&limite=20`, límite máximo 100. Filtros expresamente admitidos se indican en las rutas. Orden estable por fecha descendente e ID; catálogos por código.
- Errores: 401 sesión, 403 permiso, 404 inexistente/no accesible, 409 conflicto, 422 estructura, 428 precondición, 429 límite, 500/503 servicio. El cliente conserva el formulario y no simula una decisión ante un fallo técnico.
- `SIN_CONCLUSION_AUTOMATICA` es una decisión de dominio con respuesta exitosa, no un error HTTP.
- Ninguna respuesta GET crea evaluaciones o cierra incidencias. La vigencia se calcula al consultar y antes de actuar.

### A.2 Esquemas cerrados

Notación TypeScript como especificación de formas JSON, no como implementación de motor. `CampoCapturable` y sus tipos/unidades se enumeran en la matriz; el servidor rechaza claves fuera de esa lista y valida cada valor contra la fila correspondiente. El sufijo `Entrada` identifica cuerpos de escritura. No se permiten propiedades adicionales.

```typescript
type ID = string; // UUID
type Fecha = string; // ISO 8601 con zona horaria
type Rol = 'PRODUCTOR' | 'TECNICO' | 'ADMINISTRADOR';
type Fase = 'INGRESO' | 'SEGUIMIENTO';
type Modalidad = 'HERMETICO' | 'NO_HERMETICO';
type Decision = 'CUARENTENA' | 'BLOQUEAR_INGRESO' | 'RETIRAR_LOTE'
  | 'CORREGIR_Y_REEVALUAR' | 'SIN_CONCLUSION_AUTOMATICA'
  | 'AUTORIZAR_CON_MONITOREO' | 'AUTORIZAR_ALMACENAMIENTO';
type Rama = 'R30.1' | 'R30.2' | 'R30.3' | 'R30.4' | 'R30.5'
  | 'R30.6' | 'R30.7' | 'R30.8' | 'R30.9';
type UnidadDato = 'PCT_BH' | 'PCT_HR' | 'PCT_MASA' | 'CELSIUS'
  | 'METROS' | 'DIAS' | 'FRACCION' | 'BOOLEANO' | 'TEXTO';
type EstadoDato = 'VALIDO' | 'DESCONOCIDO' | 'INVALIDO' | 'VENCIDO';
type EstadoVigencia = 'VIGENTE' | 'VENCIDA' | 'INVALIDADA' | 'NO_AUTORIZADO' | 'SIN_EVALUACION';
interface Pagina<T> { items: T[]; siguiente_cursor: string | null; }
interface ErrorAPI { codigo: string; mensaje: string;
  campos: { ruta: string; codigo: string; mensaje: string }[]; id_solicitud: ID; }
interface Revisiones { revision_unidad: number; revision_almacen: number; }
interface Perfil { id: ID; nombre: string; roles: Rol[]; }

interface AlmacenEntrada { nombre: string; ubicacion: string;
  clima_calido: boolean | null; fundamento_clima: string | null; }
interface Almacen extends AlmacenEntrada { id: ID; revision: number; creado_en: Fecha; }
interface LoteEntrada { codigo: string; variedad: 'MAIZ_CHULPI'; uso_final: 'ALIMENTACION'; }
interface Lote extends LoteEntrada { id: ID; id_propietario: ID; revision: number; creado_en: Fecha; }
interface UnidadEntrada { id_lote: ID; id_almacen: ID; nombre_recipiente: string;
  tipo_almacenamiento: Modalidad | null; }
interface Unidad extends UnidadEntrada { id: ID; id_recipiente: ID; revision: number;
  revision_almacen: number; id_evaluacion_actual: ID | null; creado_en: Fecha; }

interface ObservacionEntrada { campo: string; // CampoCapturable de la matriz
  captura: 'APORTADO' | 'DESCONOCIDO' | 'NO_APLICA';
  valor: number | boolean | string | null; unidad: UnidadDato;
  valor_original: string | null; fecha_observacion: Fecha | null;
  metodo: string | null; evidencia: string | null; motivo_no_aplica: string | null; }
// APORTADO: valor no nulo, fecha y método presentes; evidencia puede ser null.
// DESCONOCIDO: valor null; NO_APLICA: valor null y motivo presente.
// Unidades y tipos deben coincidir con la matriz; no convertir strings a booleanos.
interface ObservacionValidada { id: ID; entrada: ObservacionEntrada;
  aplicabilidad: 'APLICA' | 'NO_APLICA'; estado_dato: EstadoDato | null;
  id_responsable: ID; procedencia: 'ACTUAL' | 'HISTORICA' | 'ESTIMADA';
  incidencias_validacion: string[]; }
// estado_dato es null solo para NO_APLICA validado. No usarlo como FALSE.

interface IntervaloEntrada { inicio: Fecha; fin: Fecha;
  humedad_grano: number | null; temperatura_grano: number | null;
  metodo: string | null; evidencia: string | null; }
interface HistorialEntrada { fecha_inicio_historial: Fecha | null;
  vida_previa_documentada: number | null; evidencia_vida_previa: string | null;
  intervalos_historial: IntervaloEntrada[]; }
interface EvaluacionEntrada extends Revisiones { fase: Fase | null;
  observaciones: ObservacionEntrada[]; historial: HistorialEntrada;
  dias_previstos_restantes: number | null; fecha_salida_prevista: Fecha | null; }
interface Borrador { id: ID; id_unidad: ID; revision: number;
  contenido: EvaluacionEntrada; actualizado_en: Fecha; }

interface FuenteRef { id_fuente: string; localizador: string | null; }
interface EvidenciaMotivo { campo: string; valor_observado: number | boolean | string | null;
  unidad: UnidadDato | null; fecha_observacion: Fecha | null;
  operador: 'GT' | 'GTE' | 'LT' | 'LTE' | 'EQ' | 'NEQ' | 'PRESENCIA' | 'VIGENCIA' | null;
  umbral: number | boolean | string | null; }
interface Motivo { id: string; regla: string; mensaje: string;
  evidencias: EvidenciaMotivo[]; fuentes: FuenteRef[];
  fundamento: 'PUBLICADO' | 'TRANSFERIDO' | 'POLITICA_PROTOTIPO' | 'MIXTO'; }
interface Accion { codigo: string; descripcion: string;
  responsable_requerido: 'PRODUCTOR' | 'TECNICO'; id_incidencia: ID | null; }
interface DatoPendiente { campo: string; motivo: string; paso: 1 | 2 | 3 | 4 | 5 | 6; }
interface Estimacion { tipo: 'ESTIMACION_HERMETICA' | 'SUSTITUCION_TABLA';
  descripcion: string; campos: string[]; id_tabla: string | null; }
interface CalculosTiempo { vida_consumida: number | null; vida_minima_documentada: number | null;
  vida_proyectada: number | null; tiempo_referencia_actual: number | null;
  celda_tabla: { id_tabla: string; humedad_fila: number; temperatura_columna_f: number;
    dias_referencia: number } | null; }
interface Vigencia { id_unidad: ID; id_evaluacion: ID | null; estado: EstadoVigencia;
  consultada_en: Fecha; fecha_proximo_control: Fecha | null;
  fecha_vencimiento_autorizacion: Fecha | null; causas: string[]; }
interface Evaluacion { id: ID; id_unidad: ID; id_lote: ID; id_recipiente: ID; id_almacen: ID;
  fecha_evaluacion: Fecha; fase: Fase | null; decision_final: Decision; rama_r30: Rama;
  motivos: Motivo[]; acciones_requeridas: Accion[]; datos_pendientes: DatoPendiente[];
  estimaciones_y_sustituciones: Estimacion[]; reglas_activadas: string[];
  observaciones_aplicadas: ObservacionValidada[]; calculos_tiempo: CalculosTiempo;
  fecha_proximo_control: Fecha | null; fecha_vencimiento_autorizacion: Fecha | null;
  version_base: string; version_parametros: string; version_motor: string; }
interface ResultadoEvaluacion { evaluacion: Evaluacion; vigencia: Vigencia; }
// Evaluacion es instantánea inmutable. Vigencia es estado actual consultado.

interface ControlEntrada extends Revisiones { tipo: 'INGRESO' | 'GRANO' | 'EXTERIOR' | 'ALMACEN';
  fecha: Fecha; observaciones: ObservacionEntrada[]; evidencia: string; }
interface Control { id: ID; id_unidad: ID; tipo: ControlEntrada['tipo']; fecha: Fecha;
  completo: boolean; campos_pendientes: string[]; id_responsable: ID; evidencia: string; }
// completo y fechas de última inspección los obtiene el servidor de requisitos y observaciones.
interface PlanEntrada extends Revisiones { fecha_proximo_control: Fecha;
  intervalo_dias: number; fecha_salida_prevista: Fecha; actividades: string; }
interface Plan { id: ID; id_unidad: ID; fecha_proximo_control: Fecha; intervalo_dias: number;
  fecha_salida_prevista: Fecha; actividades: string; vigente: boolean; id_responsable: ID; }
interface DictamenEntrada extends Revisiones { humedad_min: number; humedad_max: number;
  plazo_maximo_dias: number; vence_en: Fecha; condiciones: string; evidencia: string; }
interface Dictamen { id: ID; id_unidad: ID; humedad_min: number; humedad_max: number;
  plazo_maximo_dias: number; emitido_en: Fecha; vence_en: Fecha;
  condiciones: string; evidencia: string; id_tecnico: ID; vigente: boolean; }
interface Incidencia { id: ID; id_unidad: ID; revision: number;
  tipo: 'CUARENTENA' | 'REVISION_PLAGAS' | 'REVISION_TERMICA' | 'CORRECCION';
  estado: 'ABIERTA' | 'CERRADA'; causas: string[]; creada_en: Fecha; cerrada_en: Fecha | null; }
interface RevisionEntrada extends Revisiones { revision_incidencia: number;
  resultado: 'PENDIENTE' | 'CONFIRMADA' | 'DESCARTADA'; evidencia: string; }
interface Revision { id: ID; id_incidencia: ID; resultado: RevisionEntrada['resultado'];
  evidencia: string; id_tecnico: ID; fecha: Fecha; }
interface ResolucionEntrada extends Revisiones { revision_incidencia: number;
  evidencia: string; disposicion: string; }
interface Resolucion { id: ID; id_incidencia: ID; evidencia: string;
  disposicion: string; id_tecnico: ID; fecha: Fecha; }
interface AdmisionEntrada extends Revisiones { id_evaluacion: ID; tipo: 'INGRESO' | 'CONTINUIDAD'; }
interface Admision { id: ID; id_unidad: ID; id_evaluacion: ID;
  tipo: AdmisionEntrada['tipo']; registrado_en: Fecha; id_responsable: ID; }
interface Fuente { id: string; referencia_markdown: string; }
interface Regla { id: string; antecedente: string; consecuente: string;
  accion: string; fundamento_markdown: string; }
interface Catalogo { version_base: string; reglas: Regla[]; ramas_r30: Regla[]; fuentes: Fuente[]; }
interface Inicio { unidades_total: number; cuarentenas_abiertas: number;
  correcciones_pendientes: number; controles_proximos: { id_unidad: ID; nombre: string;
  fecha: Fecha; estado: 'PENDIENTE' | 'ATRASADO' }[]; }
```

Los esquemas de escritura de almacén, lote y unidad se utilizan completos también en PATCH: actualizan exclusivamente las propiedades declaradas, manteniendo identidad y auditoría del servidor. No permiten reasignar propietario. Un cambio de ubicación o modalidad requiere invalidación de controles afectados. No hay DELETE operativo de historial.

`observaciones_aplicadas` contiene todas las observaciones efectivamente utilizadas, incluidas las recuperadas válidamente del historial. La vista técnica puede mostrar la lista completa. Los borradores no producen una autorización y no invalidan por sí mismos el resultado vigente: comunicar una observación real adversa exige enviarla como evaluación/control, no dejarla exclusivamente en borrador.

Las consultas y acciones devuelven el estado actualizado. No marcar inspección completa al abrir una pantalla. Registrar un plan no equivale a cumplirlo; registrar revisión no autoriza almacenamiento. No se permitirá admisión con vigencia distinta de VIGENTE.

### A.3 Endpoints fijos

Todos requieren autenticación; los controles de salud del backend quedan fuera de este contrato de interfaz. Productor y técnico solo acceden a recursos propios o asignados. ADMINISTRADOR no obtiene competencia técnica por defecto.

| Método y ruta | Entrada / filtros | Salida exitosa | Permiso de escritura |
|---|---|---|---|
| GET /me | — | 200 Perfil | — |
| GET /inicio | — | 200 Inicio | — |
| GET /almacenes | cursor, limite | 200 Pagina<Almacen> | — |
| POST /almacenes | AlmacenEntrada | 201 Almacen | Productor/técnico en su ámbito |
| GET /almacenes/{id} | — | 200 Almacen | — |
| PATCH /almacenes/{id} | AlmacenEntrada + If-Match | 200 Almacen | Propietario/técnico asignado |
| GET /lotes | cursor, limite, q (código) | 200 Pagina<Lote> | — |
| POST /lotes | LoteEntrada | 201 Lote | Productor; propietario = usuario autenticado |
| GET /lotes/{id} | — | 200 Lote | — |
| PATCH /lotes/{id} | LoteEntrada + If-Match | 200 Lote | Propietario/técnico asignado |
| GET /unidades | cursor, limite, id_lote, id_almacen | 200 Pagina<Unidad> | — |
| POST /unidades | UnidadEntrada | 201 Unidad | Propietario/técnico asignado |
| GET /unidades/{id} | — | 200 Unidad | — |
| PATCH /unidades/{id} | UnidadEntrada + If-Match | 200 Unidad | Propietario/técnico asignado |
| GET /unidades/{id}/borrador | — | 200 Borrador o 404 | — |
| PUT /unidades/{id}/borrador | EvaluacionEntrada + precondición | 201/200 Borrador | Propietario/técnico asignado; borrador por usuario/unidad |
| POST /unidades/{id}/evaluaciones | EvaluacionEntrada | 201 ResultadoEvaluacion | Propietario/técnico asignado |
| GET /evaluaciones/{id} | — | 200 ResultadoEvaluacion | — |
| GET /unidades/{id}/historial | cursor, limite | 200 Pagina<ResultadoEvaluacion> | — |
| GET /unidades/{id}/vigencia | — | 200 Vigencia | — |
| GET /unidades/{id}/controles | cursor, limite | 200 Pagina<Control> | — |
| POST /unidades/{id}/controles | ControlEntrada | 201 Control | Propietario/técnico asignado |
| GET /unidades/{id}/planes | cursor, limite | 200 Pagina<Plan> | — |
| POST /unidades/{id}/planes | PlanEntrada | 201 Plan | Propietario/técnico asignado |
| GET /unidades/{id}/dictamenes | cursor, limite | 200 Pagina<Dictamen> | — |
| POST /unidades/{id}/dictamenes | DictamenEntrada | 201 Dictamen | Técnico asignado |
| GET /unidades/{id}/incidencias | cursor, limite, estado | 200 Pagina<Incidencia> | — |
| GET /incidencias/{id} | — | 200 Incidencia | — |
| GET /incidencias/{id}/revisiones | cursor, limite | 200 Pagina<Revision> | — |
| POST /incidencias/{id}/revisiones | RevisionEntrada | 201 Revision | Técnico asignado |
| GET /incidencias/{id}/resoluciones | cursor, limite | 200 Pagina<Resolucion> | — |
| POST /incidencias/{id}/resoluciones | ResolucionEntrada | 201 Resolucion | Técnico asignado |
| POST /unidades/{id}/admisiones | AdmisionEntrada | 201 Admision; 409 si autorización incompatible/vencida | Propietario/técnico asignado |
| GET /conocimiento | — | 200 Catalogo | Solo lectura |

Las incidencias las genera el backend. Las correcciones simples se cierran mediante comprobación posterior satisfactoria, sin exigir dictamen técnico para cada limpieza. Cuarentena, sospecha térmica y revisión de plagas requieren el procedimiento documentado. Cada comando actualiza revisiones y deja auditoría. El servidor propaga el cambio de un almacén a las unidades afectadas; el cliente refresca Unidad y Almacen antes de reenviar un conflicto.

## Anexo B — Matriz completa de campos

### Convenciones ya resueltas

Pasos: P1 identificación; P2 mediciones; P3 inspección; P4 recipiente/almacén; P5 historial/plan; P6 revisar/enviar. Rutas: `/lotes`, `/lotes/$id`, `/evaluar/$id_unidad`, `/resultados/$id`, `/seguimiento/$id_unidad`, `/revision/$id_incidencia`, `/conocimiento` y `/acceso`.

Origen: O = ObservacionEntrada.campo, editable por productor o técnico; C = recurso/contexto; H = historial; S = servidor/solo lectura; T = formulario técnico. La columna requisito indica lo necesario para una conclusión favorable, no para permitir enviar una evaluación parcial.

Tipos de entrada: B = booleano (Sí/No/No se sabe); N = número; E = selección enumerada; F = fecha-hora; X = texto; J = estructura del anexo A.2. Para O: B usa BOOLEANO, X/E usan TEXTO y N usa la unidad indicada. Ningún B se inicia en falso. Los campos históricos muestran siempre procedencia y fecha; la reutilización la decide el servidor.

Aplicación: G = datos internos actuales en ingreso/no hermético; en seguimiento hermético se muestran los previos al sellado como históricos y el servidor comprueba su reutilización. En hermético no exigir apertura rutinaria. A = módulo opcional «Evaluar aireación», exclusivo de NO_HERMETICO. Si no se usa A, no exigir sus mediciones para autorizar almacenamiento. Métodos/rangos de instrumentos y cobertura de tablas se validan en backend según el protocolo documentado.

| Campo canónico | Ubicación | Tipo / unidad | Origen | Requisito o conducta exacta |
|---|---|---|---|---|
| variedad | P1 / lote | E | C | Fijo MAIZ_CHULPI, visible sin edición |
| uso_final | P1 / lote | E | C | Fijo ALIMENTACION |
| fase | P1 | E | C | INGRESO/SEGUIMIENTO; null permitido para evaluación parcial |
| tipo_almacenamiento | P1 / unidad | E | C | HERMETICO/NO_HERMETICO; null no permite autorización |
| clima_calido | P1 / almacén | B | C | Clasificación documentada; no inferir de un termómetro |
| humedad_grano | P2 | N / PCT_BH | O | G; dominio 0 < valor < 100; confirmar método en servidor |
| metodo_humedad | P2 | E / TEXTO | O | INSTRUMENTAL/LABORATORIO/ESTIMACION_INDIRECTA |
| temperatura_muestra | P2 | N / CELSIUS | O | Para confirmar medición según método; no confundir con temperatura del lote |
| equipo_humedad_verificado | P2 | B | O | Necesario para confirmación, no preseleccionar |
| muestra_representativa | P2 | B | O | Necesario para confirmación |
| procedimiento_medicion_cumplido | P2 | B | O | Cumplimiento documentado; no deducir por aportar número |
| aw_medida | P2 opcional | B | O | Preguntar si se midió; desconocido no equivale a No |
| actividad_agua | P2 opcional | N / FRACCION | O | 0–1; exigible si aw_medida=true; NO_APLICA solo si false |
| temperatura_grano | P2 | N / CELSIUS | O | G; estimación hermética del servidor separada de medición |
| temperatura_grano_previa | P2 comparación | N / CELSIUS | S | Lectura previa registrada; sin pareja no aplica R09 |
| fecha_temperatura_grano | P2 | F | S | Proyección de fecha_observacion de temperatura_grano |
| fecha_temperatura_previa | P2 comparación | F | S | Del registro previo, no inventar fecha |
| punto_medicion | P2 | X | O | Identificar punto real de lectura |
| punto_medicion_previo | P2 comparación | X | S | Del registro previo |
| metodo_termico | P2 | X | O | Procedimiento/instrumento de temperatura |
| metodo_termico_previo | P2 comparación | X | S | Del registro previo |
| temperatura_almacen | P2 | N / CELSIUS | O | Ambiente del local, aplicable a ambas modalidades |
| hr_almacen | P2 | N / PCT_HR | O | 0–100; exigible NO_HERMETICO, informativa HERMETICO |
| temperatura_aire_exterior | P2 / A | N / CELSIUS | O | Solo A, lectura simultánea con las otras de aireación |
| hr_aire_exterior | P2 / A | N / PCT_HR | O | Solo A; 0–100, no copiar hr_almacen |
| lluvia_o_niebla | P2 / A | B | O | Solo A; observación actual |
| humedad_equilibrio_maiz | P2 / A | N / PCT_BH | S | Tabla aplicable validada; nunca número inventado por interfaz |
| tabla_equilibrio_id | P2 / A | X | S | Tabla y versión elegidas por backend; no disponible si falta cobertura |
| sello_integro | P4 | B | O | Solo HERMETICO; inspección exterior de barrera |
| perforacion_barrera | P4 | B | O | Solo HERMETICO; distinguir cubierta exterior |
| bolsa_abierta_sin_resellar | P4 | B | O | Solo HERMETICO; no equivale a «se abrió alguna vez» |
| cierre_seguro | P4 | B | O | Ambas modalidades; requisito de recipiente |
| recipiente_limpio | P4 | B | O | Ingreso y cuando un evento invalide verificación anterior |
| recipiente_seco | P4 | B | O | Igual criterio; no presumir por material |
| material_grado_alimentario | P4 | B | O | Evidencia del recipiente, no apariencia |
| recipiente_resistente | P4 | B | O | Inspección de recipiente |
| insectos_vivos | P3 | B | O | G; larvas vivas también se registran aquí |
| granos_perforados | P3 | B | O | G; indicio, no diagnóstico |
| polvillo_inusual | P3 | B | O | G; no equivale a polvo ordinario |
| exuvias_larvas | P3 | B | O | G; describir evidencia |
| ruido_alimentacion | P3 | B | O | G; indicio, no confirmación |
| resultado_revision_plagas | Revisión técnica / P3 lectura | E | T | PENDIENTE/CONFIRMADA/DESCARTADA, ligado al episodio |
| revision_plagas_id | Revisión técnica / P3 lectura | ID | S | Referencia a revisión, no editable |
| heces_roedores_aves_entorno | P3 | B | O | Del entorno/recipiente, distinto de heces en producto |
| huellas | P3 | B | O | Entorno de unidad, indicar lugar en evidencia |
| bolsa_roida | P3 | B | O | Recipiente afectado |
| grano_derramado_por_plaga | P3 | B | O | Evidencia local, no aplicar a todos los lotes |
| moho_visible | P3 | B | O | G; permite registrar hallazgo aunque falten mediciones |
| olor_anormal | P3 | B | O | G; describir olor en evidencia |
| condensacion_interna | P3 | B | O | G; interior del recipiente, no techo del almacén |
| germinacion | P3 | B | O | G |
| suciedad_origen_animal | P3 calidad | N / PCT_MASA | O | G; muestra y método; 0–100 |
| heces_visibles | P3 calidad | B | O | G; se refiere al producto |
| granos_defectuosos | P3 calidad | N / PCT_MASA | O | G; 0–100 |
| granos_enfermos | P3 calidad | N / PCT_MASA | O | G; no exceder defectuosos si subcategoría según protocolo |
| granos_quebrados | P3 calidad | N / PCT_MASA | O | G; 0–100 |
| materia_organica_extrana | P3 calidad | N / PCT_MASA | O | G; 0–100; no sumar categorías solapadas |
| materia_inorganica_extrana | P3 calidad | N / PCT_MASA | O | G; 0–100 |
| distancia_piso | P4 | N / METROS | O | Mínima separación efectiva, >=0 |
| distancia_pared | P4 | N / METROS | O | Pared/columna; >=0 |
| distancia_techo | P4 | N / METROS | O | Techo/viga; >=0 |
| fecha_limpieza_general | P4 | F | H | Registro de evento LIMPIEZA_GENERAL, descrito abajo |
| limpieza_previa_nuevo_lote | P4 | B | O | Solo INGRESO; no exigible en SEGUIMIENTO |
| limpieza_diaria | P4 | B | O | Comprobación actual, no copiar true de otro día |
| limpieza_tras_operaciones | P4 | B | O | NO_APLICA solo sin carga/descarga desde última limpieza |
| polvo_humo_gases_vapores | P4 | B | O | Presencia en local |
| quimicos_combustibles_en_almacen | P4 | B | O | Presencia en local |
| fecha_inspeccion_grano | Seguimiento / P5 lectura | F | S | Último control interno completo válido |
| fecha_inspeccion_exterior | Seguimiento / P5 lectura | F | S | Último control exterior completo válido |
| fecha_control_almacen | Seguimiento / P5 lectura | F | S | Último control del local completo válido |
| ingreso_inspeccionado | P6 lectura | B | S | Derivado de control INGRESO completo |
| hay_evento_que_invalida_control | Seguimiento / P5 lectura | B | S | Derivado de eventos del historial |
| fecha_inicio_historial | P5 | F | H | Origen documentado; null si desconocido |
| intervalos_historial | P5 | J | H | Inicio/fin, humedad, temperatura, método y evidencia; detectar huecos |
| vida_previa_documentada | P5 | N / FRACCION | H | >=0 sin límite superior 1; cero requiere evidencia |
| dias_previstos_restantes | P5 | N / DIAS | C | >0 para autorización; comprobar fecha de salida |
| plan_monitoreo_registrado | P5 lectura | B | S | Existencia de un plan válido; no checkbox de autoaprobación |
| fecha_proximo_control | P5 plan / resultado | F | C/S | Usuario propone en PlanEntrada; servidor valida/calcula resultado |
| dictamen_humedad_condicional | Revisión técnica / P5 lectura | J | T | Dictamen vigente ligado a unidad, condiciones, plazo y técnico |
| episodios_cuarentena_abiertos | Seguimiento / resultado | J | S | Registros persistentes, no booleanos editables |
| incidencias_revision_abiertas | Seguimiento / resultado | J | S | Registros persistentes |

### Campos de soporte y acciones: definición adicional explícita

Estos campos resuelven requisitos de la especificación que no tenían un identificador de interfaz. No agregan reglas agronómicas.

| Campo | Ubicación | Tipo / unidad | Condición y destino |
|---|---|---|---|
| fundamento_clima | P1 almacén | X | Obligatorio al clasificar clima; AlmacenEntrada |
| fecha_salida_prevista | P5 | F | EvaluacionEntrada; debe concordar con días restantes |
| evidencia_vida_previa | P5 | X | HistorialEntrada; necesario incluso cuando fracción=0 |
| evidencia | Cada observación/acción | X | Descripción y referencia documental; archivos binarios fuera de v1 |
| fecha_observacion | Cada observación O | F | Real, no futura; no es fecha de envío |
| metodo | Cada observación O | X | Procedimiento; para números identificar equipo y rango aplicable |
| valor_original | Cada observación O | X/null | Texto antes de normalizar; no usarlo como resultado calculado |
| motivo_no_aplica | Observación O | X/null | Solo para NO_APLICA solicitado |
| instante_referencia | Demostración | F | Reloj fijo en fixtures; no parámetro de autorización real |

Eventos necesitan su propio registro para conservar controles y fechas sin permitir editar derivados:

```typescript
interface EventoEntrada extends Revisiones {
  tipo: 'LIMPIEZA_GENERAL' | 'APERTURA' | 'RESELLADO' | 'SECADO' | 'ENFRIAMIENTO'
    | 'EXPOSICION_AGUA' | 'CARGA_DESCARGA';
  fecha: Fecha; evidencia: string;
}
interface Evento { id: ID; id_unidad: ID; tipo: EventoEntrada['tipo']; fecha: Fecha;
  evidencia: string; id_responsable: ID; }
```

GET `/unidades/{id}/eventos` devuelve 200 Pagina<Evento>. POST en la misma ruta recibe EventoEntrada y devuelve 201 Evento; propietario/técnico asignado. LIMPIEZA_GENERAL actualiza el historial del almacén relacionado, visible a las otras unidades afectadas; APERTURA/RESELLADO requieren comprobación nueva del cierre, no lo aprueban por sí solos. Un traslado se registra mediante PATCH de Unidad con cambio de almacén y auditoría del servidor. Fechas de eventos pasados no pueden reactivar autorizaciones históricas. Registrar evento no reinicia la vida consumida.

### Metadatos y derivados: nunca capturables como observaciones

| Campo | Pantalla | Propietario del valor |
|---|---|---|
| id_lote, id_recipiente, id_almacen, id_unidad | Contexto y resultado | Recursos vinculados, verificados por servidor |
| id_evaluacion, fecha_evaluacion | Resultado | Servidor |
| responsable / id_responsable | Evidencia e historial | Identidad del servidor; sin selector de suplantación |
| estado_dato, aplicabilidad | Revisión de datos | Validación del servidor |
| medicion_confirmada | P2 y resultado | Servidor |
| integridad_hermetica_verificada | P4 y resultado | Servidor |
| lecturas_termicas_comparables, horas_entre_lecturas | P2 comparación | Servidor |
| dias_almacenados | P5 | Servidor |
| riesgo_activo, control_vigente | Resultado/seguimiento | Servidor |
| tiempo_referencia_actual, vida_consumida, vida_minima_documentada, vida_proyectada | P5 resultado | Servidor; CalculosTiempo |
| plazo_compatible, requisitos_completos, condiciones_comunes_aptas | Resultado técnico | Servidor; reflejados en motivos y pendientes |
| version_base, version_parametros, version_motor | Resultado técnico | Servidor |
| decision_final, rama_r30 | Resultado | Motor del servidor |

Los hechos auxiliares no incluidos como propiedades independientes en Evaluacion se explican mediante motivos/pendientes; no agregarlos unilateralmente a la API. Si una futura vista necesita todos, se versionará el contrato. La matriz enumera las 81 variables de entrada canónicas del diccionario original, además de sus metadatos, derivados y campos de soporte.

## Anexo C — Escenarios de interfaz

Son fixtures de interfaz, no pruebas del motor ni evidencia de campo. Su reloj se congela en `2026-09-12T15:00:00Z` para que su apariencia no cambie mañana. La API real no acepta este reloj. La forma de todos los resultados es ResultadoEvaluacion del anexo A.2. El modo mock usa una selección explícita de escenario en herramientas de demostración; editar una humedad no debe ejecutar ni aparentar ejecutar las reglas.

| ID | Referencia del caso | Decisión / rama | Contenido indispensable |
|---|---|---|---|
| F01 | C01 | AUTORIZAR_ALMACENAMIENTO / R30.8 | Condiciones base; humedad 12,5 %, temperatura 10 °C; vida 0,10 y proyección 0,20; referencia 200 días; control 26-09; salida 02-10; vigencia VIGENTE |
| F02 | C03 | AUTORIZAR_CON_MONITOREO / R30.6 | Humedad 13,5 %, NO_HERMETICO, clima no cálido, plazo 20 días; dictamen y plan cada 7 días; control 19-09; vigencia VIGENTE |
| F03 | C05 | BLOQUEAR_INGRESO / R30.2 | INGRESO, humedad confirmada 14,01 %; R01; acondicionar y reevaluar; NO_AUTORIZADO |
| F04 | C06 | RETIRAR_LOTE / R30.3 | SEGUIMIENTO, humedad 14,01 %; R01; suspender condiciones actuales, sin ordenar destrucción; NO_AUTORIZADO |
| F05 | C07 | CORREGIR_Y_REEVALUAR / R30.4 | Temperatura del grano 26 °C; R08; corregir y reevaluar; NO_AUTORIZADO |
| F06 | C09 | SIN_CONCLUSION_AUTOMATICA / R30.5 | Falta equipo_humedad_verificado; indicar P2; no describir dato ausente como falla confirmada; NO_AUTORIZADO |
| F07 | C26 | CUARENTENA / R30.1 | Moho visible, humedad confirmada 15 % y HR pendiente; R18→R19, conservar R01; separar y revisión técnica; NO_AUTORIZADO |
| F08 | Estado temporal de F01 | Misma decisión histórica R30.8 | consultada_en=2026-09-27T15:00:00Z, estado VENCIDA; conservar evaluación original y evitar presentarla como autorización utilizable |

En F01/F02 el vencimiento mostrado coincide con el próximo control (el menor límite en esos ejemplos); dictamen de F02 vigente hasta 02-10. Las fechas completas se fijan a 15:00:00Z en 2026. Para resultados no autorizados no inventar vencimiento de autorización. Un próximo control puede ser null cuando corresponde actuación inmediata.

Ejemplo cerrado de ObservacionEntrada para el hallazgo de F07:

```json
{
  "campo": "moho_visible",
  "captura": "APORTADO",
  "valor": true,
  "unidad": "BOOLEANO",
  "valor_original": "Sí",
  "fecha_observacion": "2026-09-12T14:30:00Z",
  "metodo": "INSPECCION_VISUAL",
  "evidencia": "Moho visible en la muestra de la unidad evaluada.",
  "motivo_no_aplica": null
}
```

Los fixtures de resultado usarán exactamente todos los campos de ResultadoEvaluacion. Los motivos representan las causas indicadas en la tabla; las observaciones aplicadas deben corresponder a ellas. No completar una traza con datos inventados ni anunciar pruebas de inferencia a partir de estos escenarios visuales. Las pruebas de motor se basan en C01–C40 del documento operativo.

