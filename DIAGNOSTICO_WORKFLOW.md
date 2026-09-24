# Diagnóstico del workflow, encadenamiento y plan de correcciones — POSCOSEGRAN

Fecha: 2026-09-23 · Commit revisado: `2bbbf34` ("feat: Add Adquisicion module…")

---

## 1. Resumen ejecutivo

**Sí: el workflow de CI (`.github/workflows/ci.yml`) falla, y tus colegas tienen razón.** El commit `2bbbf34` se hizo copiando el ZIP encima del repositorio. La copia añade y sobrescribe archivos, pero **no borra**, y además no se ejecutaron los pasos que el propio mensaje de entrega pedía. Resultado: el CI se detiene en el primer paso de verificación y, aunque ese pasara, fallarían tres más.

| # | Paso del CI | Estado en `2bbbf34` | Causa | Estado ahora |
|---|---|---|---|---|
| 1 | `ruff check` | ❌ 13 errores E701 | `generar_casos_referencia.py` escrito con `if x: y` en una sola línea | ✅ Corregido |
| 2 | `mypy` (strict) | ❌ 55 errores en 10 archivos | 43 vienen de **4 módulos huérfanos** que debían eliminarse. Los 12 restantes son anotaciones de tipos en código nuevo | ✅ Corregido: los 6 huérfanos eliminados, 0 errores |
| 3 | `alembic check` | ✅ | — | ✅ |
| 4 | `pytest` con BD | ❌ ERROR en todas las pruebas de API | `conftest.py` llama a `cargar(knowledge/catalogo.yaml)`, pero el nuevo `cargar()` espera la carpeta | ✅ Corregido: 143 pasan |
| 5 | Privilegios de aplicación | ✅ | — | ✅ |
| 6 | `git diff --exit-code` del contrato | ❌ | `docs/openapi.json` no se regeneró (≈1300 líneas de diferencia) y `src/api/contrato.ts` se escribió a mano y difiere del generado (≈735 líneas) | ✅ Regenerados |
| 7 | `pnpm lint` y `pnpm build` | ✅ | — | ✅ |
| 8 | Playwright contra la API real | ✅ 2/2 | — | ✅ |
| 9 | Stack Docker | No verificado (no hay Docker en esta máquina) | Por revisión estática, `COPY knowledge /knowledge` y `POSCOSEGRAN_KNOWLEDGE` son correctos | — |

---

## 2. Cómo lo verifiqué (ejecutado de verdad, no supuesto)

- Python 3.13 (uv) con `backend/.venv` y `pip install -e backend[dev]`.
- **PostgreSQL 16.2 real** (binarios de `pgserver`) en `127.0.0.1:55432`, con las mismas credenciales que el CI.
- `preparar_local.py`, migraciones `0001→0002→0003` y carga de la semilla: correctos.
- Node 22.20 portable y pnpm 10.24.0: `install --frozen-lockfile`, `api:types`, `tsc`, `eslint` y `vite build`.
- API (uvicorn) y Vite levantados; `playwright test`: **2 passed**.
- Módulo de adquisición recorrido por HTTP **con la credencial restringida `poscosegran_app`**, que es la de producción: simular → guardar → activar → listar. Funciona, y la demo reproduce **4 casos que cambian de decisión** (3 `CORREGIR_Y_REEVALUAR→BLOQUEAR_INGRESO` y 1 `AUTORIZAR_CON_MONITOREO→BLOQUEAR_INGRESO`) con `humedad_admision_max = 13.5`.
- Explicación de una evaluación emitida con la versión 1.0 **después** de activar la 1.1: se reproduce con la versión original. Correcto.

---

## 3. Fallos detallados y por qué

### F1. Módulos huérfanos no eliminados (rompía `mypy`) — ✅ corregido
La entrega decía "los 6 módulos que tenían el conocimiento en el código, eliminados". En el commit `a0db9ba` **seguían presentes**:

```
backend/src/poscosegran/dominio/reglas.py          (690 líneas)
backend/src/poscosegran/dominio/resolucion.py      (296)
backend/src/poscosegran/dominio/tiempo.py          (225)
backend/src/poscosegran/dominio/comprobaciones.py  (264)
backend/src/poscosegran/dominio/catalogo.py        (78)
backend/src/poscosegran/dominio/parametros.py      (50)
```
**Por qué ocurre:** al descomprimir el ZIP encima del repositorio no se borra nada. Nadie importa estos módulos (lo verifiqué con grep en `src`, `tests`, `scripts` y `docs`), pero siguen usando `Instantanea.parametros` y `tablas.ID_TABLA`, que ya no existen, así que `mypy` falla. Además contradicen el documento de arquitectura: un evaluador que abra `dominio/reglas.py` verá "conocimiento en el código".

**Corrección aplicada** (fase 1 del plan de implementación):
```powershell
git rm backend/src/poscosegran/dominio/{reglas,resolucion,tiempo,comprobaciones,catalogo,parametros}.py
```

Antes de borrarlos se comprobó que los seis solo se importaban **entre ellos**
(`resolucion→reglas`, `resolucion→tiempo`, `reglas→comprobaciones`, `reglas→catalogo`):
ningún consumidor externo en `src`, `tests` ni `scripts`. `dominio/tablas.py` **no**
es huérfano —lo usa `tests/casos/test_aceptacion.py`— y se conserva.

**Resultado medido tras el borrado:** `mypy` pasa de 43 errores a `Success: no issues
found in 62 source files`; `ruff` sigue limpio; las 126 pruebas sin base de datos
siguen pasando y los 242 casos de referencia no cambian.

### F2. `conftest.py` y `cargar()` incompatibles (rompe `pytest`) — ✅ corregido
`cargar()` pasó a recibir la **carpeta** `knowledge/`, y la compatibilidad con la ruta antigua (`catalogo.yaml`) quedó solo en `main()`. `conftest.py` sigue pasando el archivo y se intenta abrir `knowledge/catalogo.yaml/base_conocimiento.yaml`.
- `backend/src/poscosegran/conocimiento/cargar.py`: la compatibilidad se movió dentro de `cargar()`.
- `backend/tests/conftest.py`: ahora pasa `knowledge`.

**Por qué nadie lo vio:** sin `POSCOSEGRAN_BD_URL_PRUEBAS` esas pruebas se **omiten**, y así se obtuvo el "65/65 + 31/31" de la entrega.

### F3. Contrato OpenAPI desactualizado (rompe `git diff --exit-code`) — ✅ corregido
- `docs/openapi.json` no incluía `/adquisicion/*` ni `/evaluaciones/{id}/explicacion`.
- `src/api/contrato.ts` estaba escrito a mano. El generado por `openapi-typescript` difiere en estructura, aunque los nombres coincidan.
- Los regeneré con `exportar_contrato.py` y `pnpm api:types`. `tsc`, `lint` y `build` pasan con el contrato generado.

### F4. `ruff` E701 — ✅ corregido
Separé las 13 sentencias `if …: …` en dos líneas. **Comprobé que la salida es idéntica byte a byte**: al regenerar `casos_referencia.json` en una copia salen los mismos 242 casos, porque el orden de las llamadas a `random` no cambió.

### F5. 12 errores de tipos en código nuevo — ✅ corregidos
- `esquemas/contrato.py`: `dict` → `dict[str, Any]`. El esquema OpenAPI no cambia.
- `sistema_experto/calculos.py`: la propiedad `tiempo` devuelve un valor tipado.
- `sistema_experto/base_hechos.py`: anotaciones de `iniciales()`.
- `sistema_experto/serializacion.py`: el diccionario de lambdas se sustituyó por `if` explícitos, con el mismo comportamiento.
- `api/rutas/adquisicion.py` y `conocimiento.py`: se quitaron `type: ignore` innecesarios y `_casos_historicos` quedó tipado con `Session` e `Instantanea`.

### F6. Otros problemas del flujo de trabajo (funcionales, no rompen el CI)
1. **No se puede descartar una propuesta.** El estado `DESCARTADA` existe en BD, enum y migración, pero ningún endpoint ni pantalla lo asigna. Las propuestas se acumulan para siempre.
2. **Estado ambiguo de la versión anterior.** Tras activar la 1.1, la 1.0 queda `estado=ACTIVADA, activa=false` (lo observé en la API). Falta un estado como `RETIRADA`/`SUPERADA`, o documentar que `estado` es histórico.
3. **Sin separación de funciones.** El mismo ingeniero propone y activa. En un sistema experto con adquisición conviene el "principio de cuatro ojos": quien activa debe ser distinto de quien propone, o al menos debe dejar un motivo obligatorio, que ya existe.
4. **La activación no vuelve a medir el impacto.** Entre la propuesta y la activación pueden haberse emitido nuevas evaluaciones. Recomendado: recalcular el impacto al activar y guardarlo en auditoría.
5. **Fuga menor de información.** El impacto incluye `historica:<id_evaluacion>` de **todas** las unidades, aunque el ingeniero "no ve unidades". Conviene anonimizar esos identificadores.
6. **No hay pruebas de API para `/adquisicion`.** Solo hay pruebas del módulo Python (`test_base_conocimiento.py`). El permiso de producción (F7 de la entrega) no está cubierto por ninguna prueba automática; lo verifiqué a mano.
7. **Prueba frágil:** `test_esquema_bd.py::test_solo_una_incidencia_abierta_por_tipo` falla si la BD ya tiene datos, porque toma una unidad existente con cuarentena abierta. En CI la BD es nueva y pasa, pero en local falla tras usar la app.

---

## 4. Algoritmos de encadenamiento: ¿hay?, ¿cuáles?, ¿por qué?

**Sí, los hay.** Están en `backend/src/poscosegran/sistema_experto/motor.py`.

### 4.1 Encadenamiento hacia adelante (forward chaining), guiado por datos — el algoritmo principal
El ciclo **reconocer → actuar** sigue la arquitectura clásica de un sistema de producción (estilo OPS5/CLIPS):
1. **Base de hechos** (`base_hechos.py`): se afirman los hechos iniciales, que son las observaciones del lote, y los calculados (`calculos.py`).
2. **Agenda por etapas**, con 5 en orden fijo: `validacion → encadenamiento → tiempo → control → consolidacion`.
3. En cada etapa se hacen **pasadas** repetidas:
   - *reconocer*: se evalúa `aplica_si` y `si` de cada regla aún no disparada, con lógica de tres estados;
   - *actuar*: si el resultado es VERDADERO, se dispara la regla, que añade un hallazgo (hecho inferido), un motivo, una acción y solicitudes;
   - se repite hasta que una pasada no dispare ninguna regla (**punto fijo**).
4. **Refracción:** cada regla dispara como máximo una vez, lo que garantiza que el ciclo termina en ≤ n+1 pasadas.
5. Las reglas se **encadenan** porque las conclusiones de unas son premisas de otras (`{hecho: HUMEDAD_CONDICIONAL}` → `R02-secado`, `AMBIENTE_BASE_APTO`, `riesgo_activo`…). En la base hay 39 hallazgos y numerosas referencias `hecho:` / `algun_hecho:`.

**Por qué se usó:** el problema va de los datos a la decisión. Se capturan mediciones de campo (humedad, temperatura, plagas…) y hay que deducir **todas** las consecuencias: motivos, acciones, pendientes y próximo control, no solo comprobar una hipótesis. Esto encaja con el encadenamiento hacia adelante. Además hace falta la traza completa para el módulo de explicación y hay múltiples conclusiones simultáneas.

**Evidencia medida** en los 242 casos de referencia: 613 disparos en la pasada 1 de `encadenamiento`, **4 en la pasada 2** (encadenamiento real entre reglas de la misma etapa) y el resto repartido en las otras etapas.

### 4.2 Resolución del conjunto conflicto por prioridad (R30)
`_resolver()` recorre las 9 ramas `R30.1…R30.9` en orden fijo y **gana la primera VERDADERO**. Esta es la estrategia de *resolución por prioridad/saliencia*. Se evalúan todas las ramas para poder explicar "qué le faltó a cada autorización".
**Por qué:** las decisiones son excluyentes y la seguridad alimentaria exige que la más conservadora (cuarentena o retiro) prevalezca siempre.

### 4.3 Evaluación bajo demanda de definiciones (componente guiado por objetivos)
Los predicados derivados (`definicion: medicion_confirmada`, `riesgo_activo`…) se evalúan **cuando una regla los necesita** y se memorizan. Esto es evaluación perezosa guiada por el objetivo, parecida al encadenamiento hacia atrás, pero **no es un motor de encadenamiento hacia atrás completo**: no hay búsqueda de metas con submetas ni preguntas al usuario. El módulo de explicación hace un recorrido *hacia atrás* sobre la traza (`fallidas`, `por_que_se_pide`), pero solo con fines explicativos.

### 4.4 Riesgo detectado en el encadenamiento: negación no monótona
El motor **no retracta** disparos, así que una regla que niega un hecho solo es segura si ese hecho se produce antes. Un análisis estático de toda la base encontró un único caso:
- `R28` (etapa `tiempo`) usa `negar: {hecho: VIDA_O_PLAZO_AGOTADO}`, que produce `R29` en **la misma etapa**. Hoy es correcto solo porque `R29` va escrita antes que `R28` en el YAML.
- **Riesgo:** desde *Adquisición*, un ingeniero puede reordenar o añadir reglas, y el motor dispararía un "próximo al límite" con la vida ya agotada.
- **Corrección propuesta** (plan P2): el validador de `base_conocimiento.py` debe rechazar toda regla que niegue un hecho producido en la misma etapa o en una posterior, o bien el motor debe ordenar la etapa por estratos (estratificación de la negación, como en Datalog).

---

## 5. Cambios aplicados en esta sesión

| Archivo | Cambio |
|---|---|
| `backend/src/poscosegran/conocimiento/cargar.py` | `cargar()` acepta la carpeta o `catalogo.yaml` |
| `backend/tests/conftest.py` | Pasa la carpeta `knowledge` |
| `backend/scripts/generar_casos_referencia.py` | E701 corregido; salida idéntica |
| `backend/src/poscosegran/esquemas/contrato.py` | Tipos `dict[str, Any]` |
| `backend/src/poscosegran/sistema_experto/{calculos,base_hechos,serializacion}.py` | Tipado estricto |
| `backend/src/poscosegran/api/rutas/{adquisicion,conocimiento}.py` | Tipado; se quitaron ignores |
| `docs/openapi.json`, `src/api/contrato.ts` | Regenerados con las herramientas oficiales |

Estado tras los cambios: ruff ✅ · mypy ✅ salvo los 4 huérfanos · alembic ✅ · pytest con BD 143 ✅ (en BD limpia) · tsc/lint/build ✅ · Playwright 2/2 ✅.

---

## 6. Plan de implementación pendiente (priorizado)

### P0 — Para que el CI quede en verde (≈5 min)
1. `git rm` de los 6 módulos huérfanos (§F1).
2. `cd backend && python -m mypy` → debe dar 0 errores.
3. Confirmar el commit con los cambios de §5 y hacer push. El CI completo, Docker incluido, se valida allí.

### P1 — Flujo de adquisición completo (≈½ día)
1. `POST /api/v1/adquisicion/versiones/{id}/descartar` (motivo obligatorio, solo `PROPUESTA` → `DESCARTADA`, auditoría) y un botón "Descartar" en `src/views/Adquisicion.tsx`.
2. Al activar, la versión anterior pasa a `SUPERADA`: se añade el valor a `ESTADO_VERSION` en una migración `0004` y se amplía el `GRANT UPDATE (estado)`, que ya está concedido.
3. Separación de funciones: `activar` rechaza con 409 si `identidad.id == version.cargada_por`. Puede hacerse configurable con `POSCOSEGRAN_ADQUISICION_CUATRO_OJOS` para una demo con un solo ingeniero.
4. Recalcular el impacto al activar y guardarlo en el `resumen` de auditoría.
5. Anonimizar `historica:<id>` → `historica:<n>`.

### P2 — Robustez del motor (≈½ día)
1. Validación de negación estratificada en `base_conocimiento.desde_contenido()`: se construye el mapa `hallazgo → etapa/posición del productor` y se rechaza `negar hecho X` si X se produce en la misma etapa o después (§4.4). Se añade la prueba correspondiente en `test_base_conocimiento.py`.
2. Mover `R28` a la etapa `control`, o comprobar que el validador la acepta por orden, y documentarlo en `ARQUITECTURA_SE.md`.

### P3 — Pruebas (≈½ día)
1. `tests/test_adquisicion_api.py`: simular, guardar, activar y descartar con el rol ingeniero, más 403 para los otros roles. Ejecutarlo también con la credencial `poscosegran_app` en el paso "Privilegios de aplicación" del CI.
2. Aislar `test_solo_una_incidencia_abierta_por_tipo`: crear su propia unidad en lugar de tomar una existente.
3. Añadir al CI un paso `python -m poscosegran.conocimiento.cargar knowledge --activar` para comprobar la idempotencia.

### P4 — Proceso (para que no se repita)
- No volcar ZIPs sobre el repositorio. Aplicar las entregas con `git apply`/rama o, al menos, ejecutar `git status` y buscar las eliminaciones esperadas.
- Añadir un hook `pre-push` o un `Makefile`/script `scripts/verificar.ps1` que ejecute ruff, mypy, pytest, `exportar_contrato` + `api:types` + `git diff --exit-code`, lint y build antes de subir.
- `pytest` debería **fallar** en el CI si faltara `POSCOSEGRAN_BD_URL_PRUEBAS`, en lugar de omitir en silencio: el "65/65" de la entrega ocultó el fallo F2.

---

## 7. Cómo reproducir la verificación localmente
```powershell
docker compose up -d bd
backend/.venv/Scripts/python.exe backend/scripts/preparar_local.py
cd backend
.venv/Scripts/python.exe -m ruff check src tests scripts
.venv/Scripts/python.exe -m mypy
.venv/Scripts/python.exe -m alembic check
$env:POSCOSEGRAN_BD_URL_PRUEBAS="postgresql+psycopg://postgres:revision_local_2026@127.0.0.1:55432/poscosegran"
.venv/Scripts/python.exe -m pytest -q
cd ..
backend/.venv/Scripts/python.exe backend/scripts/exportar_contrato.py; pnpm api:types
git diff --exit-code -- docs/openapi.json src/api/contrato.ts src/campos.json
pnpm lint; pnpm build; pnpm test:e2e
```
