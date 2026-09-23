# Instalación, despliegue y operación

## Stack Docker completo

Este modo requiere únicamente Docker Desktop. Desde la raíz del proyecto:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/iniciar_docker.ps1
```

El script crea `backend/.env` con secretos aleatorios si no existe y ejecuta `docker compose up -d --build`. Compose levanta PostgreSQL, ejecuta `inicializar` hasta completarlo, espera la salud de la API y sirve React mediante Nginx. La inicialización es idempotente: aplica solo migraciones pendientes y no duplica usuarios ni el catálogo.

En `docker compose ps --all`, `inicializar` debe aparecer como `Exited (0)`: es una tarea terminada correctamente, no un servicio caído. `bd`, `api` y `web` deben aparecer saludables.

- Aplicación: `http://localhost:8080`
- Salud del backend: `http://localhost:8080/salud/bd`
- OpenAPI: `http://localhost:8080/documentacion`
- PostgreSQL administrativo: `127.0.0.1:55432`

Para inspeccionar y detener sin eliminar el volumen:

```powershell
docker compose --env-file backend/.env ps --all
docker compose --env-file backend/.env logs -f inicializar api web
docker compose --env-file backend/.env down
```

También puede ejecutarse directamente `docker compose --env-file backend/.env up -d --build` cuando el archivo ya existe. La API solo recibe la credencial de aplicación; la conexión administrativa y la de migraciones pertenecen al contenedor efímero `inicializar`. Los Dockerfiles usan la raíz como contexto. No uses `down -v` salvo que quieras eliminar explícitamente todos los datos locales.

## Desarrollo local

Sigue el [README](../README.md). PostgreSQL se publica solo en `127.0.0.1:55432`; el volumen `poscosegran_datos` conserva los datos. Las contraseñas SQL del Compose son exclusivamente de desarrollo. `preparar_local.py` genera el secreto JWT y la contraseña de acceso, crea roles separados, ejecuta Alembic y registra el catálogo. Se puede repetir sin borrar datos.

Levanta solo PostgreSQL y prepara el entorno del host:

```powershell
docker compose up -d bd
backend/.venv/Scripts/python.exe backend/scripts/preparar_local.py
```

Después ejecuta FastAPI en el puerto 8000 y Vite en el 8443 con los comandos del README. Este modo requiere Python 3.13, Node 22 y pnpm en el host, y ofrece recarga automática.

## Incorporar Supabase más adelante

Esta conexión requiere crear el proyecto; no se ha probado con un servicio Supabase real.

1. Configura el proveedor Auth, sus usuarios y URLs de retorno. En el frontend copia `.env.example` a `.env.local`, usa `VITE_AUTH_MODE=supabase`, URL del proyecto y clave pública. Nunca incluyas una clave `service_role`, contraseña SQL ni secreto JWT en variables `VITE_*`.
2. En el backend configura `POSCOSEGRAN_ENTORNO=produccion`, `POSCOSEGRAN_JWT_MODO=JWKS`, algoritmos acordes a la firma del proyecto (`ES256`/`RS256`), `POSCOSEGRAN_JWT_EMISOR=https://PROYECTO.supabase.co/auth/v1`, audiencia `authenticated` y `POSCOSEGRAN_JWT_JWKS_URL=https://PROYECTO.supabase.co/auth/v1/.well-known/jwks.json`. Deshabilita `POSCOSEGRAN_AUTH_LOCAL_HABILITADA`. El modo local con secreto compartido se rechaza en producción.
3. Usa conexiones PostgreSQL Psycopg y SSL para las dos credenciales. Aprovisiona roles/esquema con `backend/sql/roles_privilegios.sql`, sustituyendo los marcadores, antes de migrar. Ejecuta Alembic con `POSCOSEGRAN_BD_URL_MIGRACIONES`; después aplica `backend/sql/permisos_aplicacion.sql`. La cuenta de aplicación tiene datos, no DDL ni administración de identidades.
4. Carga la semilla de la base de conocimiento con `python -m poscosegran.conocimiento.cargar knowledge --activar` en un proceso administrativo cuya `POSCOSEGRAN_BD_URL_APP` apunte temporalmente a la credencial administrativa. No cambies la credencial del servicio API para hacerlo. Los cambios posteriores del conocimiento se hacen desde el módulo de adquisición con un usuario `INGENIERO_CONOCIMIENTO`, dado de alta con `scripts/administrar.py --rol INGENIERO_CONOCIMIENTO`.
5. Aprovisiona el UUID `sub` de cada usuario mediante `scripts/administrar.py`. Los roles del JWT no otorgan acceso por sí solos. Configura asignaciones para técnicos.
6. Construye el frontend con las variables públicas de Supabase. Despliega ambos contenedores detrás de HTTPS y usa CORS con orígenes explícitos si separas dominios. El Compose incluido es local; no constituye una configuración pública de producción.

## Usuarios y asignaciones

Ejecuta desde `backend`, con la credencial de migraciones configurada en ese proceso:

```powershell
.venv/Scripts/python.exe scripts/administrar.py --usuario UUID_AUTH --nombre "Nombre" --rol PRODUCTOR --motivo "Alta autorizada"
.venv/Scripts/python.exe scripts/administrar.py --usuario UUID_TECNICO --rol TECNICO --lote UUID_LOTE --responsable UUID_ADMIN --motivo "Asignación autorizada"
```

Puede usarse `--almacen UUID_ALMACEN` en vez de lote. En local los UUID terminan en `0001` (productor), `0002` (técnico), `0003` (administrador), con prefijo `00000000-0000-4000-8000-`. El ID de la unidad está en la URL y los IDs de lote/almacén se consultan en la API. El script deja auditoría. No concede al administrador acceso automático a la producción ni permite al navegador gestionar privilegios.

## Respaldo y restauración

Desde la raíz, estos comandos generan un respaldo y lo restauran en una base **nueva**, sin reemplazar el original:

```powershell
docker compose exec -T bd pg_dump -U postgres -d poscosegran -Fc -f /tmp/poscosegran.dump
docker compose cp bd:/tmp/poscosegran.dump ./respaldo.dump
docker compose exec -T bd createdb -U postgres poscosegran_restaurada
docker compose exec -T bd pg_restore -U postgres -d poscosegran_restaurada --no-owner /tmp/poscosegran.dump
docker compose exec -T bd psql -U postgres -d poscosegran_restaurada -c "SELECT count(*) FROM poscosegran.evaluacion;"
```

Para una copia que procede de otro equipo, usa primero `docker compose cp ./respaldo.dump bd:/tmp/poscosegran.dump`. El respaldo contiene datos privados y debe guardarse fuera del repositorio con acceso restringido. Los roles SQL se aprovisionan aparte; vuelve a aplicar privilegios al destino. Comprueba conteos, versión Alembic y un resultado histórico antes de cambiar la conexión de la aplicación. En producción define retención, cifrado y pruebas periódicas de restauración según la operación.

## Diagnóstico

`/salud` comprueba proceso; `/salud/bd`, conexión SQL. Los errores de API llevan identificador de solicitud. Un 401 exige renovar sesión, 403/404 revisar permisos/asignación, 409/412 actualizar revisiones, 422 corregir campos. Si Docker está detenido, arráncalo antes de la API. No hay evaluaciones sin catálogo activo.

El limitador en memoria es por proceso y se reinicia al reiniciar el servicio. Para despliegue con varios procesos conviene añadir límites compartidos en el proxy. El bloqueo global de escritura es suficiente para el piloto, no una medición de capacidad productiva. La verificación actual no incluye despliegue público, recuperación ante desastre del proveedor ni prueba de carga.
