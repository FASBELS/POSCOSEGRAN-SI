# Decisiones

## Etapa 6

**El frontend no se tocó.** Llegó un prototipo web (React 19 + Vite +
Tailwind, navegación por estado en `App.tsx`, datos incrustados en las vistas) en
lugar del frontend de las etapas 1–5. Sus tipos no son los del anexo A.2:
`LotStatus` con tres valores frente a los cinco de `EstadoVigencia`,
`ContainerType` con nombres de recipiente frente a `Modalidad`, y `Role` con
`'TÉCNICO'` acentuado frente a `'TECNICO'`. Se conservó intacto por indicación
expresa. Conectarlo a la API real exigirá realinear tipos, añadir enrutamiento y
una capa de servicios; no basta con cambiar un adaptador.

**Línea base de migración generada desde los modelos.** No existía base previa y
no hay forma de autogenerar aquí una migración fiable sin una instancia de
PostgreSQL. Se documenta como punto de partida, no como práctica: a partir de
`0001` cada cambio se escribe explícitamente y `alembic check` debe salir limpio.

**Valores cerrados como VARCHAR + CHECK, no ENUM nativo.** Añadir un valor no
exige `ALTER TYPE` fuera de transacción y el conjunto admitido queda legible en
el esquema.

**Motivos relacionales, entrada efectiva en JSONB.** La trazabilidad regla →
fuente → evidencia es lo que hay que consultar y auditar, así que vive en tablas.
La entrada se guarda tal como llegó para poder reproducir la inferencia.

**Inmutabilidad en la base, no solo en la aplicación.** Disparadores sobre
evaluaciones, observaciones, controles, eventos, revisiones, resoluciones,
admisiones y auditoría. Una consulta manual tampoco puede reescribir historial.

**El administrador no accede a datos de producción.** El contrato no define
endpoints de provisión de roles y no se inventan endpoints fuera del contrato,
así que roles y asignaciones se gestionan por procedimiento administrativo.

**RLS como defensa en profundidad, desactivada por omisión.** El pool comparte
conexiones entre usuarios; la autorización la aplica la capa de permisos.

**Sin SQLite en las pruebas de base.** Los disparadores, los índices parciales y
los arrays no se comportan igual; una prueba que pasa en SQLite no demostraría
nada. Las pruebas marcadas `bd` se omiten si no hay PostgreSQL.

## Etapa 7

**El motor es una función pura, separada de la base de datos.** Recibe una
instantánea y devuelve una decisión. Es lo que permite ejecutar C01–C40 sin
PostgreSQL y lo que hace que el resultado dependa solo de los hechos, no del
orden de inserción ni del estado de una sesión.

**Reglas en Python, no en un lenguaje de reglas propio.** Cada antecedente se lee
junto a su fila de la sección 4. Un motor con `eval` o un DSL inventado habría
añadido una capa que nadie puede revisar contra el documento.

**`Tri.__bool__` lanza TypeError.** Un `if comprobacion:` distraído convertiría un
desconocido en verdadero, que es precisamente el error que la versión 2.0 de la
base vino a corregir. Mejor que falle en voz alta.

**Motivos relacionales y entrada efectiva en JSONB.** La trazabilidad regla →
fuente → evidencia se consulta y se audita, así que vive en tablas. La entrada se
guarda tal como llegó para poder reproducir la inferencia.

**La vigencia se calcula, no se guarda.** Una autorización vencida sigue siendo
una decisión histórica cierta; lo que caduca es su efecto.

**El catálogo se transcribe con un script, no a mano.**
`scripts/transcribir_base.py` copia el texto de cada celda del documento. Una
transcripción manual se desincroniza en la primera corrección de la base.

**Las incidencias las abre el backend y solo las cierra una resolución.**
Registrar una revisión no cierra el episodio ni autoriza almacenamiento.

**C35 exigió precisar el supuesto del caso, no cambiar el motor.** Sin sensor
interno declarado, el escenario de planificación de la sección 6.2 se aplica y
exige plan de monitoreo. El caso dice "autorizar según datos internos", de modo
que supone un recipiente con sensor.

## Integración y revisión end-to-end (septiembre de 2026)

Se conserva la SPA React/Vite inicial y se integran TanStack Router, Query y tipos generados desde OpenAPI. Se reemplazan los datos simulados y el selector de roles por autenticación y permisos efectivos. No se migra a Start/SSR; el despliegue estático con proxy está documentado en ARQUITECTURA.md.

Ante la ausencia de proyecto Supabase se incorpora acceso local explícito con usuarios sembrados y contraseña generada. Firma JWT y atraviesa las mismas comprobaciones de identidad/permisos que la API; la configuración prohíbe habilitarlo en producción. Supabase queda pendiente de aprovisionamiento y verificación real.

Las observaciones inmutables reciben su origen al insertarse. La procedencia efectiva se conserva en la instantánea, sin actualizar el registro original. La reutilización selecciona la última captura del campo dentro de la unidad, aunque sea desconocida o inválida. Se valida NO_APLICA según contexto y se conserva el mínimo de vida consumida documentada.

Las escrituras toman un bloqueo transaccional compartido por PostgreSQL para mantener atómicos los controles de revisión y sus efectos. Hay pruebas con solicitudes concurrentes y claves de idempotencia iguales/distintas. El bloqueo global es una limitación de rendimiento deliberada para el piloto.

Controles adversos abren incidencias inmediatamente. Eventos, planes, actuaciones técnicas y cambios de metadatos invalidan resultados anteriores. Consultar una evaluación histórica no muestra la autorización de una posterior. Los episodios no se cierran con un simple dato favorable.

El borrador del autor se consume dentro de la transacción de evaluación; la evaluación conserva la captura inmutable. La interfaz espera a recuperar el borrador antes de permitir editar y convierte fechas de forma explícita entre UTC y hora local. Las capturas pendientes y las claves de operaciones inciertas se conservan en la pestaña.

Se separan preparación de roles, migraciones y permisos posteriores; la imagen API arranca con cuenta sin DDL. La revisión ahora incluye PostgreSQL real y navegador, superando la validación sintáctica descrita para las etapas anteriores. Los resultados y las limitaciones se registran en PRUEBAS.md.

## Sistema experto: base de conocimiento como datos (septiembre de 2026)

**D-SE-1. Reglas como datos y motor genérico.** El diagrama de arquitectura de la
asignatura separa base de conocimiento, base de hechos, motor de inferencia,
módulo de explicación y módulo de adquisición. El motor anterior tenía las reglas
escritas en Python: no había una base de conocimiento separada ni una vía para
adquirir conocimiento. Las 30 reglas, sus parámetros, la tabla de tiempo y la
resolución R30 pasan a `knowledge/base_conocimiento.yaml`, y el motor se reduce a
un intérprete genérico. Alternativa descartada: sacar solo los umbrales a un
archivo y dejar las reglas en código, porque seguía mezclando conocimiento y motor.

**D-SE-2. Lenguaje de condiciones cerrado.** Un evaluador con operadores
explícitos en lugar de `eval` o de un motor externo (CLIPS, Drools, Experta). Da
control completo sobre la lógica de tres estados y deja cada operador probado. La
negación se llama `negar` porque YAML 1.1 lee `no:` como `False`.

**D-SE-3. Extensión del contrato del anexo A.** Nuevos endpoints
`GET /evaluaciones/{id}/explicacion` y `/adquisicion/*`. `Catalogo` añade
`version_parametros`, `hash_base`, `parametros` y `uso_campos`, todos opcionales
para no romper clientes. Nuevo rol `INGENIERO_CONOCIMIENTO`.

**D-SE-4. Reproducir en lugar de almacenar la traza.** Cada evaluación guarda sus
hechos iniciales serializados y la huella de la base en `entrada_efectiva`, que ya
es inmutable. La explicación se obtiene reevaluando con esa versión: el motor es
determinista y la fecha forma parte de los hechos. Si la decisión reproducida no
coincide con la almacenada, se responde 409. Así no hace falta una tabla de trazas.

**D-SE-5. Versiones de conocimiento en la base de datos.** `version_conocimiento`
guarda el contenido completo y su ciclo de vida (PROPUESTA, ACTIVADA, SUPERADA, DESCARTADA).
La aplicación puede insertar versiones y cambiar cuál está activa (UPDATE
restringido a `activa`, `estado`, `activada_en`, `activada_por`), pero no reescribir
el contenido de una versión existente. La migración 0003 es idempotente porque la
0001 crea el esquema desde los modelos actuales.

**D-SE-6. Impacto antes de activar.** Una propuesta se evalúa contra 242 casos de
referencia congelados y las últimas 200 evaluaciones con hechos reproducibles. Se
advierte de toda autorización nueva y de todo cambio de umbral publicado. La
simulación es síncrona y tarda unos segundos: las propuestas son infrecuentes.

**D-SE-7. Etiquetas oficiales de decisión.** La interfaz muestra las siete
etiquetas del Prompt 1 ("Separar y solicitar evaluación técnica", etc.). El código
técnico se conserva en la API y en el fundamento técnico.
