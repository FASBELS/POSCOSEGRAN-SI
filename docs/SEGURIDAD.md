# Seguridad

Etapa 6. Verificación de identidad, permisos, auditoría, idempotencia y
superficie HTTP.

## Identidad

El backend no emite credenciales: las verifica. `POSCOSEGRAN_JWT_MODO` decide
cómo, y las comprobaciones no cambian entre modos.

| Modo | Uso | Algoritmos |
|---|---|---|
| `JWKS` | Proveedor real, por ejemplo Supabase Auth | RS256, RS512, ES256 |
| `SECRETO_COMPARTIDO` | Solo desarrollo local | HS256 |

En todos los casos:

- El algoritmo se toma de una lista permitida, nunca de la cabecera del token.
  `none` se rechaza siempre, y la configuración rechaza mezclar JWKS con
  algoritmos simétricos.
- Firma, emisor, audiencia, expiración y emisión se comprueban contra valores
  exactos, con un margen de reloj configurable.
- `sub` debe tener forma de UUID. Un token sin `sub` utilizable no identifica a
  nadie.
- El secreto compartido exige al menos 32 caracteres y la configuración se niega
  a arrancar con él si el entorno es producción.

Las claves JWKS se cachean con TTL propio, porque el cliente de PyJWT no
controla por sí solo cuándo caducan.

**Los roles no vienen del token.** Se leen de `usuario_rol` en cada petición. El
cliente no decide sus permisos, y un token viejo no conserva un rol revocado.

## Permisos

Implementados en `poscosegran/seguridad/permisos.py`, contra la base:

- **Productor**: sus lotes y sus almacenes.
- **Técnico**: lo que tenga asignado, por almacén o por lote.
- **Administrador**: no obtiene acceso a datos de producción ni competencia
  técnica por ser administrador. La provisión de roles y asignaciones se realiza
  mediante procedimiento administrativo, no por la API, porque el contrato no
  define endpoints para ello y no se inventan endpoints fuera del contrato.

Acciones que exigen técnico asignado y que ser propietario no habilita:
dictámenes, revisiones de incidencia y resoluciones. Si el solicitante es
propietario pero no técnico asignado recibe 403; si no tiene ninguna relación
con el recurso recibe 404, para no confirmar la existencia de datos ajenos.

Cada comando sobre una unidad declara las revisiones de unidad y de almacén que
creyó estar usando, y ambas se comprueban dentro de la transacción. Así no se
decide sobre condiciones que cambiaron mientras el formulario estaba abierto.

### Ingeniería del conocimiento

`INGENIERO_CONOCIMIENTO` propone, simula y activa versiones de la base de
conocimiento desde el módulo de adquisición. No concede acceso a unidades ni
competencia técnica, igual que `ADMINISTRADOR`. Cada propuesta y cada activación
quedan en auditoría con motivo, versiones y cambios. La base de datos refuerza el
límite: la cuenta de aplicación puede insertar versiones y cambiar cuál está
activa, pero no modificar el contenido de una versión ya registrada.

**Separación de funciones.** Quien propone una versión no puede activarla: la
activación exige otra persona con el mismo rol y devuelve 409 en caso contrario.
Un cambio de umbral altera lo que el sistema decidirá sobre lotes reales, así que
se revisa con cuatro ojos como cualquier cambio con efecto en producción. La
excepción `POSCOSEGRAN_ADQUISICION_PERMITIR_AUTOACTIVACION` permite recorrer el
ciclo con una sola cuenta en desarrollo; la configuración la rechaza si el entorno
es `produccion`, de modo que no puede quedarse encendida por descuido.

**Minimización de datos.** La simulación de impacto evalúa las últimas
evaluaciones emitidas, que pertenecen a unidades de otras personas. Los resultados
identifican cada caso por su posición en la muestra (`historica:0007`), nunca por
el identificador de la evaluación: el ingeniero del conocimiento necesita saber
cuántas decisiones cambian y en qué sentido, no de quién son.

**Integridad de la activación.** La activación toma un advisory lock de
transacción antes de leer la versión vigente, vuelve a medir el impacto contra la
evidencia del momento y aborta sin tocar nada si la propuesta no evalúa. Dos
activaciones simultáneas quedan serializadas y el índice parcial único sobre
`activa` es la última defensa; hay una prueba que lanza ambas en paralelo y
comprueba que solo queda una versión activa.

## RLS

`backend/sql/rls_opcional.sql` contiene políticas de fila como defensa en
profundidad, no como autorización principal, y no se aplican automáticamente.

El motivo es concreto: el pool de SQLAlchemy comparte conexiones entre usuarios,
así que una política que dependa solo de la conexión no identifica a nadie. La
aplicación publica el usuario con `SET LOCAL` dentro de cada transacción y las
políticas lo leen de ahí; si esa variable falta, no se ve nada. Actívelas solo
tras comprobar que todas las rutas fijan la variable.

## Credenciales de base de datos

Dos roles separados, en `backend/sql/roles_privilegios.sql`:

- `poscosegran_migraciones`: dueño del esquema, con DDL. Solo se usa al desplegar.
- `poscosegran_app`: SELECT, INSERT y UPDATE sobre las tablas; DELETE únicamente
  sobre `borrador` e `idempotencia`. No puede crear ni alterar tablas.

`REVOKE` explícito sobre `public`, el esquema y la base. Las tablas futuras
heredan el mismo reparto mediante `ALTER DEFAULT PRIVILEGES`.

Ninguna credencial de base de datos ni clave de servicio llega al navegador. El
frontend habla con la API; la API habla con la base.

## Auditoría

`servicios/auditoria.py` escribe en la misma transacción que el cambio: si la
operación falla, no queda un rastro que afirme algo que no ocurrió.

Guarda usuario, roles, acción, recurso, método, ruta, estado HTTP, revisión
resultante, identificador de solicitud y un resumen. La función `depurar()`
elimina en cualquier nivel de anidamiento las claves que puedan contener
credenciales — `authorization`, `token`, `password`, `service_role`, `cookie` y
similares — sustituyéndolas por `[omitido]`.

## Idempotencia

`POST` y `PUT` llevan `Idempotency-Key`. La clave se reserva antes de ejecutar:

- Reintento idéntico: se devuelve la respuesta original sin repetir el efecto.
- Misma clave con otro contenido: 409. Sería otra operación.
- Reintento mientras el original sigue en curso: 409.

La huella del cuerpo es un SHA-256 del JSON normalizado, así que el orden de las
claves no la altera pero un cambio de tipo sí: `true` y `"true"` no son el mismo
contenido.

## Superficie HTTP

- CORS con lista explícita de orígenes. La configuración rechaza el comodín en
  producción. Se exponen `ETag` y `X-Id-Solicitud`.
- Límite de peticiones por usuario, con cupo menor para escrituras.
- Cada petición recibe un identificador que viaja en la respuesta y en los
  errores, para poder cruzar un fallo con su registro.
- Los errores devuelven el `ErrorAPI` del contrato. El detalle de un fallo
  interno va al log, no al cliente.

## Pendientes

- **El límite de peticiones es en memoria.** Vale para un proceso; con varias
  réplicas hace falta un contador compartido.
- **Retención de auditoría** sin definir.
- **Rotación del secreto local** sin procedimiento.
- La cabecera `Idempotency-Key` y las precondiciones están conectadas y probadas
  con HTTP/PostgreSQL, incluidas solicitudes concurrentes.
- La integración con el proveedor Supabase queda pendiente de crear el proyecto.
  Los resultados ejecutados constan en [PRUEBAS.md](PRUEBAS.md).
