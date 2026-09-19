# Verificación de la integración

Revisión ejecutada el 16 de septiembre de 2026 en Windows, Python 3.13, Node y PostgreSQL 16. El navegador también se verificó contra la compilación servida por Nginx y FastAPI en Docker.

| Comprobación | Resultado |
| --- | --- |
| Suite Python con PostgreSQL real | 113 pruebas aprobadas; 1 omitida por requerir otra credencial |
| Cuenta de aplicación sin DDL, ejecutada por separado con `poscosegran_app` | 1 aprobada |
| Mypy estricto | Sin errores en 57 archivos |
| Ruff sobre código, pruebas y scripts | Sin errores |
| ESLint, TypeScript y compilación Vite | Correctos |
| Alembic upgrade/check | Migraciones aplicadas; sin diferencias de modelos |
| Tipos OpenAPI y catálogo de campos regenerados | Generación y TypeScript correctos |
| Playwright contra `localhost:8080` | 2 recorridos aprobados en 10,7 s |
| Imágenes y servicios Docker | Construidos; PostgreSQL y API saludables |
| Stack Docker desde volumen vacío | Inicialización 0, API/web saludables y 2 recorridos Playwright aprobados |
| Reinicialización Docker | Idempotente: 3 usuarios, 3 roles y 1 versión de conocimiento antes/después |
| Respaldo PostgreSQL y restauración en base independiente | 48 evaluaciones recuperadas con instantáneas y decisiones iguales al original; revisión `0002_inmutabilidad` |

La suite incluye C01–C40 e invariantes del motor, JWT y permisos, inmutabilidad, errores HTTP, idempotencia, borradores, revisiones obsoletas, historial, vigencia, controles, eventos, planes, dictámenes, revisión/resolución técnica y admisión. Las regresiones adicionales cubren NO_APLICA incorrecto, intervalos solapados y lagunas, control adverso sin evaluación y solicitudes concurrentes con la misma clave o claves distintas.

El recorrido de navegador crea almacén/lote/unidad, guarda y recupera un borrador del servidor, verifica que la fecha conserve su hora, evalúa moho, confirma cuarentena y bloqueo de admisión, registra apertura y reevalúa. Verifica que el borrador consumido no reaparezca y que un dato favorable no cierre la incidencia. Consulta conocimiento/fuentes. El segundo recorrido comprueba sesión, cierre y ausencia de desbordamiento global a 360, 768 y 1440 píxeles. Se revisaron capturas de pantalla; la tabla puede desplazarse horizontalmente dentro de su contenedor en móvil.

Durante la revisión se corrigió un fallo reproducible del ciclo de borradores. Un intento posterior del navegador coincidió con el reinicio del contenedor y recibió conexión rechazada; se repitió tras completar el arranque, con ambos recorridos aprobados. Las advertencias observadas son de depreciación de AnyIO, caché de pytest restringida por el entorno y colores de consola, no fallos de aserciones.

## Repetir

Usa una base local de prueba migrada; estas pruebas añaden registros históricos y no deben apuntar a producción. Desde `backend`:

```powershell
$env:POSCOSEGRAN_BD_URL_PRUEBAS='postgresql+psycopg://postgres:revision_local_2026@127.0.0.1:55432/poscosegran'
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m mypy
.venv/Scripts/python.exe -m ruff check src tests scripts
.venv/Scripts/python.exe -m alembic check
$env:POSCOSEGRAN_BD_URL_PRUEBAS='postgresql+psycopg://poscosegran_app:local_app_2026@127.0.0.1:55432/poscosegran'
.venv/Scripts/python.exe -m pytest -q tests/test_esquema_bd.py::test_la_credencial_de_aplicacion_no_puede_crear_tablas
```

Desde la raíz, con la aplicación arrancada:

```powershell
pnpm.cmd lint
pnpm.cmd build
pnpm.cmd exec playwright install chromium
$env:E2E_BASE_URL='http://localhost:8080'
pnpm.cmd test:e2e
```

Para Vite utiliza `http://localhost:8443`, con API en puerto 8000. Playwright lee la contraseña local desde `backend/.env` sin imprimirla. Los artefactos quedan en `test-results/`, excluido del control de versiones. Hay un workflow reproducible en `.github/workflows/ci.yml`; no se ha ejecutado en GitHub en esta revisión.

El mismo recorrido se ejecutó contra el stack Docker en `http://localhost:8080` y contra Vite/FastAPI locales en `http://localhost:8443`. En Docker también se comprobó que la API no recibe las conexiones administrativa o de migraciones.

## Límites

No se verificó Supabase real porque aún no existe el proyecto, ni un despliegue público, carga sostenida o recuperación del proveedor. La validación técnica no sustituye la revisión del conocimiento por especialistas del dominio. La base restaurada de esta revisión se llama `poscosegran_revision_restore_20260916`; se conserva separada del original.
