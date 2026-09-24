# POSCOSEGRAN

Sistema experto para evaluar condiciones de almacenamiento de maíz chulpi. React + Vite, FastAPI, motor Python y PostgreSQL 16. La interfaz consume la API real; las decisiones, permisos e incidencias se calculan en el servidor.


**Sistema experto.** El conocimiento del dominio —las 30 reglas, sus umbrales y la resolución R30— está en [`knowledge/base_conocimiento.yaml`](knowledge/base_conocimiento.yaml), separado de un motor de inferencia genérico, con módulos de explicación y de adquisición. Ver [`docs/ARQUITECTURA_SE.md`](docs/ARQUITECTURA_SE.md).

## Ejecutar todo con Docker

Solo requiere Docker Desktop. Desde la raíz:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/iniciar_docker.ps1
```

El script genera secretos locales si todavía no existe `backend/.env`, construye las imágenes, prepara PostgreSQL mediante un contenedor efímero y levanta frontend y backend. Abre [la aplicación Docker](http://localhost:8080). La salud de la API queda en [localhost:8080/salud/bd](http://localhost:8080/salud/bd) y su documentación en [localhost:8080/documentacion](http://localhost:8080/documentacion).

Para detenerlo sin borrar los datos:

```powershell
docker compose --env-file backend/.env down
```

## Ejecutar en desarrollo local

Requisitos: Docker Desktop iniciado, Python 3.13, Node.js 22 y pnpm. Desde la raíz:

```powershell
docker compose up -d bd
py -3.13 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -e "backend[dev]"
pnpm.cmd install --frozen-lockfile
backend/.venv/Scripts/python.exe backend/scripts/preparar_local.py
```

Si usas uv: `uv venv backend/.venv --python 3.13` y `uv pip install --python backend/.venv/Scripts/python.exe -e "backend[dev]"`. No recrees el entorno si ya existe.

El preparador aplica migraciones, carga la base 2.0 y crea cuatro usuarios de desarrollo: `productor`, `tecnico`, `administrador` e `ingeniero` (ingeniería del conocimiento, para el módulo de adquisición). La contraseña está en `POSCOSEGRAN_AUTH_LOCAL_PASSWORD` de `backend/.env`; se genera al preparar el entorno y no se publica. Los archivos existentes no se sobrescriben.

En dos terminales:

```powershell
cd backend
.venv/Scripts/python.exe -m uvicorn poscosegran.api.app:crear_app --factory --reload --host 127.0.0.1 --port 8000
```

```powershell
pnpm.cmd dev
```

Abre [la aplicación local](http://localhost:8443). API interactiva: [documentación local](http://127.0.0.1:8000/documentacion). El técnico necesita una asignación al lote o almacén para ver sus unidades; el administrador no obtiene acceso general a datos de producción. El ingeniero del conocimiento mantiene la base desde *Adquisición* y tampoco ve unidades.

> Activar una versión de conocimiento exige **cuatro ojos**: quien la propuso no puede activarla. Para recorrer el ciclo completo con la única cuenta `ingeniero` de desarrollo, añade `POSCOSEGRAN_ADQUISICION_PERMITIR_AUTOACTIVACION=true` a `backend/.env`. La configuración rechaza esa opción si el entorno es `produccion`.

## Verificar antes de subir

```powershell
$env:POSCOSEGRAN_BD_URL_PRUEBAS = 'postgresql+psycopg://postgres:revision_local_2026@127.0.0.1:55432/poscosegran'
$env:POSCOSEGRAN_BD_URL_PRUEBAS_APP = 'postgresql+psycopg://poscosegran_app:local_app_2026@127.0.0.1:55432/poscosegran'
powershell -ExecutionPolicy Bypass -File scripts/verificar.ps1
```

Reproduce los gates del workflow en el mismo orden y se detiene en el primero que falle. Añade `-SaltarE2E` para omitir Playwright, o `-SinBd` para una verificación parcial que avisa de que no equivale al CI. No contiene credenciales: las lee del entorno.

## Documentación

- [Instalación, contenedores, Supabase y respaldos](docs/INSTALACION_DESPLIEGUE.md)
- [Manual de uso](docs/MANUAL_USUARIO.md)
- [Arquitectura e integración](docs/ARQUITECTURA.md)
- [API y contrato generado](docs/API.md)
- [Pruebas y límites de la verificación](docs/PRUEBAS.md)
- [Decisiones de implementación](docs/DECISIONES.md)
- [Base de conocimiento vigente](knowledge/POSCOSEGRAN_30_reglas_base_conocimiento_actualizado.md)

Supabase todavía no está configurado. El acceso local permite recorrer la aplicación sin ese servicio y está bloqueado en producción. Este prototipo orienta sobre almacenamiento; no certifica inocuidad ni ausencia de micotoxinas.
