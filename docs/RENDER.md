# Despliegue en Render

El archivo [`render.yaml`](../render.yaml) crea los tres recursos del sistema:
el frontend React como Static Site, la API FastAPI como Docker Web Service y una
base Render Postgres. El frontend usa Supabase Auth; la autenticación local está
deshabilitada para el entorno público.

## Antes de desplegar

1. Sube el repositorio a GitHub y confirma que `render.yaml` esté en la raíz.
2. Crea un proyecto en Supabase y habilita el proveedor de inicio de sesión que
   vas a usar. Copia la URL del proyecto y su clave pública `anon`/publishable.
   No uses la clave `service_role` en el frontend.
3. Desde Supabase, identifica el emisor JWT y su endpoint JWKS. Para un proyecto
   estándar son `https://<ref>.supabase.co/auth/v1` y
   `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json`. Configura una clave
   de firma `ES256` o `RS256`, que son los algoritmos aceptados por el backend
   en producción.

## Crear los servicios

1. En Render elige **New > Blueprint** y conecta el repositorio y la rama que
   quieras desplegar. Render encontrará `render.yaml` en la raíz.
2. En los campos secretos del Blueprint proporciona estos valores:

   - `VITE_SUPABASE_URL`: URL del proyecto Supabase.
   - `VITE_SUPABASE_ANON_KEY`: clave pública anon/publishable de Supabase.
   - `POSCOSEGRAN_JWT_EMISOR`: emisor JWT del proyecto Supabase.
   - `POSCOSEGRAN_JWT_JWKS_URL`: URL JWKS del proyecto Supabase.
   - `POSCOSEGRAN_CORS_ORIGENES`: origen del Static Site, por ejemplo
     `https://poscosegran-web.onrender.com` (sin `/` al final).

3. Revisa los planes antes de confirmar: la API y PostgreSQL estan en el nivel
   gratuito; el Static Site tambien es gratuito. La API puede suspenderse por
   inactividad y tardar en responder al primer acceso. Render elimina la base
   gratuita a los 30 dias, por lo que este plan sirve para pruebas y no para
   conservar datos a largo plazo.
4. Despliega el Blueprint. Al iniciar la API, el comando de arranque aplica
   Alembic y carga el catalogo inicial unicamente cuando aun no hay una version
   activa. Se ejecuta al inicio porque Render no ofrece `preDeployCommand` en
   servicios gratuitos.
5. Cuando aparezcan las URLs, comprueba que coincidan con las usadas en la
   configuración. El Blueprint supone `https://poscosegran-api.onrender.com` y
   `https://poscosegran-web.onrender.com`. Si Render asignó otra URL:

   - Cambia `VITE_API_URL` en el Static Site a
     `https://<url-real-de-la-api>/api/v1` y vuelve a desplegar el frontend.
   - Cambia `POSCOSEGRAN_CORS_ORIGENES` en la API a `https://<url-real-del-web>`.
     El cambio de CORS reinicia la API.

6. En **Settings > General** del proyecto Supabase configura la URL pública del
   Static Site como Site URL y como URL permitida de retorno para el flujo de
   autenticación. Para una SPA sin retorno específico, permite también
   `https://<url-real-del-web>/**` según el proveedor que hayas habilitado.
7. Abre el Static Site y prueba `/salud/bd` en la URL de la API. La respuesta
   debe ser `{"estado":"conectado"}`.

## Habilitar usuarios

Crear una cuenta en Supabase no concede por sí solo acceso a POSCOSEGRAN. El
`sub` del usuario de Supabase debe coincidir con el UUID de `usuario.id`, y el
rol se asigna en `usuario_rol`. Desde tu equipo, prepara Python con las
dependencias del backend y configura temporalmente la URL externa de PostgreSQL
como `POSCOSEGRAN_BD_URL_MIGRACIONES`. Usa la URL externa solo desde tu equipo;
la API usa la URL interna que Render inyecta.

En **CMD**, desde la raíz del repositorio, instala el backend una sola vez:

```cmd
py -3.13 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -e "backend[dev]"
```

Luego crea y asigna el usuario:

```cmd
set POSCOSEGRAN_BD_URL_MIGRACIONES=postgresql+psycopg://USUARIO:CLAVE@HOST_EXTERNO/poscosegran?sslmode=require
backend\.venv\Scripts\python.exe backend\scripts\administrar.py --usuario UUID_SUB_SUPABASE --nombre "Nombre del usuario" --rol PRODUCTOR --motivo "Alta inicial en Render"
```

Repite el comando con el UUID del usuario y rol que corresponda (`TECNICO`,
`ADMINISTRADOR` o `INGENIERO_CONOCIMIENTO`). Los técnicos necesitan además una
asignación vigente a un lote o almacén. Para dar acceso al módulo de adquisición,
crea dos cuentas con rol `INGENIERO_CONOCIMIENTO`: una propone y la otra revisa
y activa. No uses las cuentas locales `ingeniero`/`testeo` en Render.

La cadena externa contiene la contraseña de PostgreSQL: no la guardes en Git ni
la compartas. Al cerrar CMD se elimina la variable de esa sesión. Puedes rotar la
credencial inicial de Render después de preparar los usuarios.

## Despliegues posteriores

Cada actualizacion enviada a la rama conectada inicia el despliegue. Al iniciar
la API se ejecutan las migraciones pendientes. La carga inicial no reactiva el
catalogo de ejemplo si ya hay otra version activa.

La API usa la credencial administrada de Render Postgres para migraciones y
operaciones. Las cuentas JWT y sus roles de aplicación son independientes de
esta credencial SQL. Para operación con mayor separación de privilegios, revisa
los mecanismos de credenciales PostgreSQL de Render y define usuarios SQL
separados antes de abrir el servicio a más organizaciones.
