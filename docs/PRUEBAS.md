# Verificación de la integración

## Estado tras el plan de encadenamiento y workflow (24 de septiembre de 2026)

Ejecutado en Windows con Python 3.13, pnpm 10.24.0 y PostgreSQL 16.15 en contenedor.

| Comprobación | Resultado |
| --- | --- |
| Ruff sobre código, pruebas y scripts | Sin errores |
| Mypy estricto | Sin errores en 62 archivos (antes: 43 errores en 4 módulos huérfanos) |
| `alembic upgrade head` desde base vacía (0001→0004) | Correcto |
| `alembic check` | Sin diferencias de modelos |
| Suite Python con PostgreSQL real | 175 aprobadas; 1 omitida, la de la credencial restringida, que corre en su propio paso |
| Cuenta de aplicación sin DDL, con `poscosegran_app` | 1 aprobada |
| Casos de referencia reproducidos | 242 de 242, sin diferencias |
| API de adquisición (`tests/test_adquisicion_api.py`) | 18 aprobadas |
| Carga idempotente de la base de conocimiento | Dos ejecuciones seguidas, sin cambios |
| ESLint y compilación Vite | Correctos |
| Contrato OpenAPI y tipos regenerados | `src/campos.json` sin cambios |

### Cómo se comprueba que nada se omite en silencio

`POSCOSEGRAN_EXIGIR_BD=1` convierte en fallo la omisión de las pruebas marcadas
`bd`. Sin `POSCOSEGRAN_BD_URL_PRUEBAS`, la sesión termina con código 4 y nombra
las 19 pruebas que se habrían saltado, en lugar de pasar en verde. El workflow lo
define para todo el job.

`scripts/verificar.ps1` reproduce los gates del workflow en Windows, en el mismo
orden, y se detiene en el primero que falle. Lee las credenciales del entorno y se
niega a arrancar sin URL de pruebas; con `-SinBd` avisa explícitamente de que el
resultado no equivale al del workflow.

### Aislamiento de las pruebas de integración

`test_solo_una_incidencia_abierta_por_tipo` crea su propia unidad dentro de una
transacción que revierte al terminar. Antes tomaba una unidad cualquiera de la
base, así que fallaba el *primer* INSERT en cuanto una ejecución anterior —o el
uso normal de la aplicación— ya había dejado una cuarentena abierta sobre ella: la
suite daba resultados distintos en pasadas consecutivas sobre la misma base.

---

## Revisión anterior

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

## Revisión del sistema experto (23 de septiembre de 2026)

Ejecutada en un entorno sin red, sin PostgreSQL y sin dependencias de Node. Se
distingue lo que se ejecutó de lo que queda por ejecutar.

**Ejecutado**

| Comprobación | Resultado |
| --- | --- |
| C01–C40 con el motor genérico (`tests/casos/test_aceptacion.py`) | 65 asertos aprobados |
| Arquitectura del sistema experto (`tests/test_base_conocimiento.py`) | 31 pruebas aprobadas |
| Regresión de historial sin base de datos | Aprobada |
| Equivalencia con el motor anterior: 67 instantáneas de prueba | 0 diferencias |
| Equivalencia con el motor anterior: 48 000 casos aleatorios en modo intenso, suave y dirigido | 0 diferencias en 12 dimensiones |
| Casos de referencia (`knowledge/casos_referencia.json`) reproducidos desde el archivo | 242 de 242 |
| Compilación de todo el backend, migraciones, scripts y pruebas | Correcta |
| Referencias del backend al contrato (`api.X`) e importaciones internas | Sin referencias rotas |
| TypeScript con dependencias simuladas: propiedades del contrato usadas por las vistas nuevas | Sin errores |

**Pendiente de ejecutar en el entorno completo**

```powershell
cd backend
.venv/Scripts/python.exe -m pytest                 # suite completa con PostgreSQL
.venv/Scripts/python.exe -m alembic upgrade head   # incluye 0003_sistema_experto
.venv/Scripts/python.exe -m alembic check          # debe salir limpio
.venv/Scripts/python.exe -m mypy src
.venv/Scripts/python.exe -m ruff check src tests scripts
.venv/Scripts/python.exe scripts/exportar_contrato.py
cd ..
pnpm.cmd api:types; pnpm.cmd typecheck; pnpm.cmd lint; pnpm.cmd build
pnpm.cmd exec playwright test
```

Tras `api:types`, `src/api/contrato.ts` debe quedar igual que la versión escrita a
mano en esta revisión, salvo el orden de los esquemas. El recorrido de Playwright
se actualizó: el encabezado de la decisión es ahora la etiqueta oficial *Separar y
solicitar evaluación técnica*.
