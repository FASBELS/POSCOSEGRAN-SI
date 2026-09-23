# Base de datos

Etapa 6. PostgreSQL 16, SQLAlchemy 2, Alembic. Todo vive en el esquema privado
`poscosegran`, fuera de cualquier Data API.

## Idea central

El historial no se edita. Una evaluación es una instantánea de lo que se sabía
en ese momento, con la entrada efectiva, los motivos, las reglas disparadas y
las versiones de conocimiento, parámetros y motor que la produjeron. Corregir
significa registrar algo nuevo, nunca reescribir lo anterior. Esa regla está en
la base con disparadores, no solo en la aplicación, para que tampoco pueda
saltársela una consulta manual.

La vigencia no se guarda. Se calcula al consultar, con el reloj del servidor.
Una autorización de la semana pasada sigue existiendo como decisión histórica,
pero ya no autoriza nada.

## Tablas

**Identidad.** `usuario`, `usuario_rol`, `asignacion_almacen`, `asignacion_lote`.
El identificador de usuario es el `sub` del proveedor de identidad. No se guardan
contraseñas ni tokens. Los roles se acumulan: un mismo usuario puede ser
productor y técnico, y ser administrador no implica ninguno de los dos.

**Dominio.** `almacen`, `lote`, `recipiente`, `unidad`. Cada unidad es un lote en
un recipiente dentro de un almacén: la cosa que efectivamente se evalúa. Dos
recipientes con condiciones distintas son dos unidades.

`revision_almacen` no se copia en la unidad: se lee del almacén al serializar,
de modo que un cambio del almacén afecta a todas sus unidades sin necesidad de
propagar valores.

**Captura.** `borrador`, `observacion`, `control`, `evento`. Una observación
guarda su valor en la columna de su tipo — `valor_numero`, `valor_booleano` o
`valor_texto` — y nunca en texto plano: un booleano no queda como `'true'`. Un
`CHECK` impide que haya más de uno relleno.

Las tres formas de captura están separadas por restricción:

- `APORTADO` exige valor, fecha y método.
- `DESCONOCIDO` exige que no haya valor. Ausencia no es falso ni cero.
- `NO_APLICA` exige motivo.

`estado_dato` solo puede ser nulo cuando la aplicabilidad es `NO_APLICA`, para
que un nulo no acabe leyéndose como condición favorable.

El historial temporal se reconstruye por `(id_unidad, campo, fecha_observacion)`,
que es el índice que sostiene la reutilización de observaciones previas.

**Evaluación.** `evaluacion` más `evaluacion_motivo`, `motivo_evidencia`,
`motivo_fuente`, `evaluacion_accion`, `evaluacion_dato_pendiente`,
`evaluacion_estimacion` y `observacion_aplicada`.

Los motivos son relacionales y no un JSON, porque la trazabilidad regla → fuente
→ evidencia es lo que hay que poder consultar y auditar. `CalculosTiempo` está
desplegado en columnas por el mismo motivo. La entrada efectiva sí es JSONB: se
guarda tal cual llegó, para poder reproducir la inferencia.

Dos restricciones que conviene conocer: una decisión que no autoriza no puede
llevar fecha de vencimiento de autorización, y la celda de la tabla de tiempo
seguro se guarda completa o no se guarda.

`observacion_aplicada` recoge todas las observaciones que el motor usó de hecho,
incluidas las recuperadas del historial. Es lo que permite mostrar la
procedencia y la fecha de un dato reutilizado en vez de presentarlo como una
lectura recién tomada.

**Seguimiento.** `plan`, `dictamen`, `incidencia`, `revision_incidencia`,
`resolucion`, `admision`. Un índice parcial garantiza un solo plan vigente por
unidad y una sola incidencia abierta por unidad y tipo, de modo que una
cuarentena no se duplica ni desaparece al cambiar una medición: se cierra con
su resolución registrada.

`vigente` no se almacena en `dictamen`; se deriva de `vence_en` y `anulado_en`.

**Conocimiento.** `version_conocimiento`, `fuente`, `regla`. Cada evaluación
apunta a la versión con la que se resolvió. El catálogo se carga desde un
archivo validado; no se edita por API, y los umbrales no son configurables desde
la interfaz.

**Operación.** `auditoria` e `idempotencia`. Ver `SEGURIDAD.md`.

## Inmutabilidad

La migración `0002_inmutabilidad` instala dos funciones y sus disparadores:

- `impedir_modificacion()` bloquea UPDATE y DELETE en evaluaciones y sus tablas
  hijas, observaciones, controles, eventos, revisiones, resoluciones,
  admisiones y auditoría.
- `impedir_borrado()` bloquea solo DELETE en almacenes, lotes, unidades,
  incidencias, planes, dictámenes, usuarios, asignaciones y catálogo. Estas sí
  se actualizan, siempre con auditoría.

`borrador` e `idempotencia` quedan fuera: son estado transitorio y se borran.

## Migraciones

`0001_linea_base` crea el esquema a partir de los modelos declarativos. Es una
línea base deliberada, no un atajo permanente: no existía base previa, y así el
ORM y el esquema no pueden divergir en el punto de partida. A partir de aquí
cada cambio se escribe de forma explícita.

```bash
export POSCOSEGRAN_BD_URL_MIGRACIONES='postgresql+psycopg://poscosegran_migraciones:...@localhost:5432/poscosegran'
alembic upgrade head
alembic check          # debe salir limpio antes de publicar cambios de modelos
alembic revision --autogenerate -m "descripcion"
```

Las migraciones usan su propia credencial. La de aplicación no puede ejecutar
DDL; ver `backend/sql/roles_privilegios.sql`.

### 0003_sistema_experto

Añade a `version_conocimiento` el contenido completo de la base (`contenido`,
JSONB), su ciclo de vida (`estado`: PROPUESTA, ACTIVADA o DESCARTADA), `motivo`,
`id_version_origen`, `activada_en` y `activada_por`, y el rol
`INGENIERO_CONOCIMIENTO`. Es idempotente porque 0001 crea el esquema desde los
modelos actuales: en una base nueva no hace nada y en una anterior añade las
columnas. Las versiones registradas antes de 0003 no tienen contenido; vuelve a
cargar la semilla con `python -m poscosegran.conocimiento.cargar knowledge --activar`.

Cada evaluación guarda además, en `entrada_efectiva`, `_hechos_iniciales` (la base
de hechos serializada, reproducible) y `_hash_base`.

## Tipos cerrados

Los valores cerrados se implementan como `VARCHAR` con `CHECK`, no como tipos
`ENUM` nativos. Añadir un valor no exige entonces un `ALTER TYPE` fuera de
transacción, y el conjunto admitido queda legible en el propio esquema. Las
tuplas viven en `poscosegran/db/enums.py`, que las migraciones importan: ese
módulo está congelado por convención, se añade pero no se edita ni se recorta.

## Pendientes

- Afinar índices de paginación con volúmenes representativos y planes EXPLAIN;
  la paginación real está implementada, pero no se ha realizado prueba de carga.
- Política de retención de `auditoria`: sin definir.
- Las políticas RLS de `backend/sql/rls_opcional.sql` no se aplican solas.
