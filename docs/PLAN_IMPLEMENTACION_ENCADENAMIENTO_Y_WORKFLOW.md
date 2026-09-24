# Plan de implementación del motor de encadenamiento y recuperación del workflow

**Proyecto:** POSCOSEGRAN  
**Fecha de elaboración:** 2026-09-23  
**Alcance:** motor de inferencia, base de conocimiento de 30 reglas, flujo de adquisición, pruebas y CI/CD  
**Estado del documento:** plan técnico; no representa cambios funcionales ya implementados

---

## 1. Objetivo

Dejar el sistema experto POSCOSEGRAN en un estado verificable, mantenible y listo para entrega mediante:

1. la recuperación del workflow de integración continua;
2. la documentación técnica del algoritmo de encadenamiento que ya está implementado;
3. el fortalecimiento de las validaciones de la base de conocimiento;
4. el cierre de los casos incompletos del flujo de adquisición de conocimiento;
5. la ampliación de las pruebas automáticas del motor, la API y la persistencia;
6. una verificación final reproducible sobre PostgreSQL y el stack completo.

El plan conserva la arquitectura actual: React en el frontend, FastAPI y SQLAlchemy en el backend, PostgreSQL como sistema de persistencia, Alembic para migraciones y archivos YAML versionados para representar el conocimiento.

---

## 2. Alcance y límites

### 2.1 Incluido

- Las 30 reglas `R01` a `R30` descritas en `knowledge/catalogo.yaml` y en el documento fuente.
- Las 40 producciones ejecutables definidas en `knowledge/base_conocimiento.yaml`.
- Las nueve ramas de resolución `R30.1` a `R30.9`.
- El motor genérico ubicado en `backend/src/poscosegran/sistema_experto/`.
- El ciclo de propuesta, simulación, activación y descarte de versiones de conocimiento.
- Los controles de integridad, concurrencia, trazabilidad y auditoría asociados.
- Los jobs de backend, contrato OpenAPI, frontend, navegador y Docker del workflow.

### 2.2 No incluido

- Cambios de reglas o umbrales del dominio sin aprobación del experto responsable.
- Sustitución del algoritmo por un framework externo de reglas.
- Rediseños visuales que no sean necesarios para completar el flujo de adquisición.
- Refactorizaciones generales ajenas a los fallos y riesgos documentados aquí.

---

## 3. Línea base comprobada

El diagnóstico se ejecutó sobre el commit `a0db9ba`, con el árbol de trabajo limpio antes de crear este documento.

| Componente | Comando o evidencia | Resultado observado | Interpretación |
|---|---|---:|---|
| Ruff | `python -m ruff check src tests scripts` | Correcto | No hay errores de estilo detectados por Ruff. |
| Mypy estricto | `python -m mypy` | **43 errores en 4 archivos** | El workflow falla actualmente en este punto. |
| Pytest sin URL de BD | `python -m pytest -q` | 126 pasan, 19 omitidas | Las pruebas unitarias pasan; no valida la integración real con PostgreSQL. |
| Frontend | `pnpm.cmd lint` | Correcto | ESLint pasa. |
| Compilación | `pnpm.cmd build` | Correcto | TypeScript y Vite compilan. |
| Alembic | Requiere una instancia PostgreSQL configurada | Pendiente en esta ejecución | Debe comprobarse dentro del workflow o con la base local preparada. |
| API/E2E/Docker | Requieren base y servicios activos | Pendiente en esta ejecución | No se debe declarar el workflow recuperado hasta ejecutar estas capas. |

### 3.1 Causa raíz confirmada del fallo inmediato

El commit que introdujo el nuevo motor dejó seis módulos de la implementación anterior dentro de `backend/src/poscosegran/dominio/`:

- `reglas.py`
- `resolucion.py`
- `tiempo.py`
- `comprobaciones.py`
- `catalogo.py`
- `parametros.py`

La búsqueda de referencias no encontró consumidores en `backend/src`, `backend/tests`, `backend/scripts`, `docs` ni `knowledge`. Cuatro de esos módulos producen los 43 errores porque todavía esperan `Instantanea.parametros`, `tablas.Celda` y `tablas.ID_TABLA`, elementos que ya no existen en la arquitectura vigente.

La causa raíz no está en el motor nuevo: es una eliminación incompleta durante la sustitución de la implementación anterior. La corrección adecuada es retirar los seis módulos huérfanos, no adaptar código obsoleto a los modelos nuevos.

### 3.2 Limitación del diagnóstico local

El archivo `backend/tests/conftest.py` omite las pruebas marcadas con `bd` cuando no existe `POSCOSEGRAN_BD_URL_PRUEBAS`. Por ello, “126 pruebas aprobadas” no equivale a “integración completa aprobada”. El cierre debe hacerse con PostgreSQL migrado y con las 19 pruebas actualmente omitidas en ejecución efectiva.

### 3.3 Advertencias no bloqueantes observadas

- Pytest no pudo escribir parte de `.pytest_cache` por permisos del entorno. No afecta el resultado funcional, pero debe corregirse si ocurre en el entorno oficial.
- En PowerShell con ejecución de scripts restringida debe usarse `pnpm.cmd`; no es un defecto del proyecto ni del workflow Linux.

---

## 4. Documentación técnica del algoritmo existente

### 4.1 Conclusión

No es necesario crear un algoritmo de encadenamiento desde cero. El sistema ya implementa un motor de producción genérico con **encadenamiento hacia adelante**, dirigido por datos, dividido en etapas y ejecutado hasta alcanzar un punto fijo.

El motor no codifica reglas, umbrales o prioridades del negocio. Esos elementos se cargan desde la base de conocimiento. Esta separación permite modificar y versionar el conocimiento sin reescribir el algoritmo.

### 4.2 Fuentes de conocimiento

| Archivo | Responsabilidad |
|---|---|
| `knowledge/base_conocimiento.yaml` | Definición operativa: parámetros, condiciones, producciones, cálculos, datos exigibles y resolución. |
| `knowledge/catalogo.yaml` | Descripción documental de las 30 reglas y sus fuentes. |
| `knowledge/casos_referencia.json` | 242 casos congelados para regresión e impacto. |
| `knowledge/POSCOSEGRAN_30_reglas_base_conocimiento_actualizado.md` | Documento de dominio que fundamenta las reglas. |

El cargador exige coherencia entre la parte operativa y la documental. El catálogo debe contener exactamente `R01` a `R30`; la parte operativa debe implementar `R01` a `R29`, mientras `R30` se representa mediante sus nueve ramas de resolución.

### 4.3 Inventario ejecutable

- 30 reglas documentales.
- 40 producciones operativas.
- 26 definiciones reutilizables.
- 24 especificaciones de datos exigibles.
- 9 ramas de resolución final.
- 5 etapas de agenda.
- 7 decisiones finales posibles.

Las 40 producciones no contradicen la existencia de 30 reglas. Algunas reglas se descomponen en varias producciones para separar conclusiones y efectos. Por ejemplo, `R02` tiene tres producciones, `R27` tiene dos y existen producciones auxiliares de validación y consolidación.

### 4.4 Componentes del motor

| Componente | Archivo | Función |
|---|---|---|
| Carga y validación | `sistema_experto/base_conocimiento.py` | Convierte YAML en objetos inmutables y rechaza estructuras incoherentes. |
| Memoria de trabajo | `sistema_experto/base_hechos.py` | Conserva hechos iniciales, inferidos, solicitudes, acciones y traza. |
| Lenguaje de condiciones | `sistema_experto/lenguaje.py` | Evalúa operadores cerrados sin utilizar `eval`. |
| Cálculos | `sistema_experto/calculos.py` | Resuelve tiempos, plazos, tablas y fechas. |
| Ciclo de inferencia | `sistema_experto/motor.py` | Ejecuta reconocer–actuar y resuelve la decisión. |
| Explicaciones | `sistema_experto/explicacion.py` | Reconstruye cómo se decidió, por qué no se decidió otra cosa y por qué se solicita un dato. |
| Serialización | `sistema_experto/serializacion.py` | Convierte casos entre objetos de dominio y JSON. |
| Entrada pública | `dominio/motor.py` | Expone la operación de evaluación al resto del backend. |

### 4.5 Memoria de trabajo

Cada evaluación crea una `BaseHechos` nueva. Contiene:

- observaciones y contexto recibidos en la `Instantanea`;
- hechos calculados;
- hallazgos inferidos;
- solicitudes de cuarentena, suspensión, corrección o monitoreo;
- motivos y acciones;
- reglas disparadas;
- activaciones ordenadas para explicación;
- ramas de decisión evaluadas;
- datos pendientes.

Los hechos inferidos solo existen durante esa evaluación. Los episodios, controles y resultados persistentes se recuperan desde la base de datos como parte de la instantánea de entrada.

### 4.6 Lógica de cuatro valores

El lenguaje diferencia:

- `VERDADERO`: la condición está demostrada;
- `FALSO`: la condición está refutada;
- `DESCONOCIDO`: no existe evidencia suficiente;
- `NO_APLICA`: el dato o la condición no corresponde al contexto.

Una producción únicamente se dispara cuando su condición completa es `VERDADERO`. En particular, negar un valor desconocido continúa siendo desconocido; la ausencia de información nunca se convierte en evidencia favorable.

### 4.7 Agenda por etapas

El orden vigente es:

1. `validacion`: detecta inconsistencias y datos inválidos;
2. `encadenamiento`: ejecuta las reglas de condición del producto y del almacenamiento;
3. `tiempo`: calcula vida consumida, aviso y agotamiento;
4. `control`: comprueba vigencia de controles y eventos invalidantes;
5. `consolidacion`: deriva solicitudes y condiciones agregadas necesarias para decidir.

Distribución de producciones después de aplicar los valores por defecto del cargador:

| Etapa | Producciones |
|---|---:|
| Validación | 2 |
| Encadenamiento | 27 |
| Tiempo | 2 |
| Control | 2 |
| Consolidación | 7 |
| **Total** | **40** |

### 4.8 Ciclo reconocer–actuar

Pseudocódigo equivalente a la implementación:

```text
evaluar(instantanea, base):
    hechos = construir_hechos_iniciales(instantanea)
    preparar_calculos(hechos, base)

    para cada etapa en base.etapas:
        reglas_etapa = reglas cuya etapa coincide

        repetir como máximo cantidad(reglas_etapa) + 1 veces:
            disparos = 0

            para cada regla en reglas_etapa, en orden declarativo:
                si regla ya está disparada:
                    continuar

                si aplica_si existe y no es VERDADERO:
                    registrar no aplicabilidad
                    continuar

                juicio = evaluar(regla.si)
                si juicio no es VERDADERO:
                    continuar

                marcar regla como disparada
                afirmar hallazgo
                agregar solicitudes, motivo y acción
                registrar activación y soportes
                disparos += 1

            si disparos == 0:
                terminar etapa: se alcanzó el punto fijo

    calcular datos pendientes
    evaluar las nueve ramas R30
    escoger la primera rama verdadera
    calcular próximo control y vencimiento, si corresponden
    devolver resultado y traza completa
```

### 4.9 Propiedades del ciclo

**Refracción.** Una producción se dispara como máximo una vez por evaluación mediante `hechos.disparadas`.

**Terminación.** Si una pasada no termina la etapa, al menos una producción nueva tuvo que dispararse. Por tanto, cada etapa alcanza el punto fijo en un máximo de `n + 1` pasadas, donde `n` es su número de producciones.

**Determinismo.** Con la misma instantánea, la misma versión de conocimiento y el mismo orden de producciones, el resultado es el mismo.

**Aislamiento.** El motor es una función sin acceso directo a la base de datos ni al reloj del sistema. La fecha de evaluación llega dentro de la instantánea.

**Trazabilidad.** Cada activación registra orden, etapa, pasada, producción, regla documental, hallazgo, soportes y solicitudes.

**Complejidad.** En el peor caso, el ciclo actual vuelve a revisar todas las producciones no disparadas durante cada pasada. Para una etapa con `n` producciones, el límite es cuadrático, `O(n²)`, más el costo de recorrer los árboles de condiciones. Con 40 producciones repartidas en cinco etapas este costo es pequeño; la prioridad debe ser la corrección y la trazabilidad, no una red RETE.

### 4.10 Encadenamiento real entre producciones

Las conclusiones de una producción pueden ser premisas de otra. La prueba `test_traza_registra_encadenamiento_en_dos_pasadas` demuestra el caso:

1. `R20` afirma `CONTAMINACION_ANIMAL_OBSERVADA` en la primera pasada.
2. `R19`, ubicada antes en la agenda, no pudo verla durante su primera comprobación.
3. La segunda pasada vuelve a reconocer las reglas pendientes.
4. `R19` se dispara usando el hecho inferido por `R20`.
5. La resolución termina en `CUARENTENA`.

Este caso prueba que el motor no es una simple lista de validaciones independientes.

### 4.11 Resolución del conjunto conflicto

Después del punto fijo, el motor evalúa todas las ramas para conservar explicación, pero selecciona la primera cuyo valor sea verdadero:

| Prioridad | Rama | Decisión |
|---:|---|---|
| 1 | R30.1 | CUARENTENA |
| 2 | R30.2 | BLOQUEAR_INGRESO |
| 3 | R30.3 | RETIRAR_LOTE |
| 4 | R30.4 | CORREGIR_Y_REEVALUAR |
| 5 | R30.5 | SIN_CONCLUSION_AUTOMATICA |
| 6 | R30.6 | AUTORIZAR_CON_MONITOREO |
| 7 | R30.7 | AUTORIZAR_CON_MONITOREO |
| 8 | R30.8 | AUTORIZAR_ALMACENAMIENTO |
| 9 | R30.9 | SIN_CONCLUSION_AUTOMATICA |

La última rama debe ser incondicional para garantizar que toda evaluación produzca exactamente una decisión.

### 4.12 Riesgo técnico identificado: negación dependiente del orden

`R28` niega el hecho `VIDA_O_PLAZO_AGOTADO`, producido por `R29` en la misma etapa. El resultado actual es correcto porque `R29` aparece antes que `R28`.

La refracción impide retractar una producción ya disparada. Por ello, si una futura versión reordena estas producciones, `R28` podría activarse antes de que `R29` afirme el agotamiento. El validador actual comprueba sintaxis, referencias y ciclos de definiciones, pero no estratifica negaciones entre producciones.

La solución propuesta es validar el grafo de dependencias antes de aceptar una base: toda producción que niegue un hecho debe ejecutarse en una etapa estrictamente posterior a sus productores, o someterse a una política de orden explícita y comprobada. Se recomienda la primera opción porque elimina la dependencia silenciosa del orden YAML.

---

## 5. Estrategia de implementación

El trabajo se organizará en cambios pequeños y verificables. Cada fase empieza con una condición de entrada y termina con un criterio de aceptación objetivo. No se mezclarán reparaciones de CI, cambios funcionales y endurecimiento del motor en un solo commit.

Orden recomendado:

```text
Línea base
   ↓
Recuperar CI estático
   ↓
Documentar y blindar el motor
   ↓
Completar adquisición
   ↓
Ampliar pruebas e integración
   ↓
Validar stack y cerrar entrega
```

---

## 6. Fase 0 — Congelar y reproducir la línea base

**Objetivo:** garantizar que los cambios posteriores se comparen contra evidencia repetible.

### Actividades

1. Crear una rama de trabajo exclusiva.
2. Registrar commit base, versiones de Python, Node, pnpm, Docker y PostgreSQL.
3. Preparar una base de pruebas limpia mediante `backend/scripts/preparar_local.py`.
4. Ejecutar cada gate del workflow por separado y guardar su salida.
5. Confirmar que las 19 pruebas omitidas localmente se ejecutan al definir `POSCOSEGRAN_BD_URL_PRUEBAS`.
6. Registrar duración de arranque, migraciones, carga de conocimiento, pruebas de backend, build y E2E.

### Entregables

- Registro de línea base adjunto al issue o pull request.
- Lista exacta de pruebas aprobadas, fallidas y omitidas.
- Evidencia del fallo de Mypy antes de la corrección.

### Criterio de aceptación

- El fallo puede reproducirse desde un clon limpio con comandos documentados.
- Ninguna prueba de integración queda omitida silenciosamente en CI.

### Estimación

2 a 3 horas.

---

## 7. Fase 1 — Recuperar el workflow estático

**Objetivo:** eliminar el bloqueo confirmado de Mypy sin modificar el comportamiento vigente.

### Actividades

1. Verificar nuevamente con `rg` que nadie importe los seis módulos huérfanos.
2. Eliminarlos con `git rm`.
3. Ejecutar Ruff y Mypy.
4. Ejecutar todas las pruebas unitarias sin base.
5. Buscar referencias documentales que todavía presenten esos módulos como implementación vigente.
6. Actualizar `DIAGNOSTICO_WORKFLOW.md` para diferenciar el problema histórico de su estado resuelto.

### Archivos afectados

- Los seis módulos huérfanos de `backend/src/poscosegran/dominio/`.
- `DIAGNOSTICO_WORKFLOW.md`, si conserva tareas ya resueltas como pendientes.

### Pruebas

```powershell
cd backend
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m pytest -q -m "not bd"
```

### Criterio de aceptación

- Ruff: cero errores.
- Mypy: cero errores.
- No cambia ninguno de los 242 resultados de referencia.
- No existen importaciones rotas ni referencias arquitectónicas contradictorias.

### Estimación

1 a 2 horas.

---

## 8. Fase 2 — Formalizar y endurecer el encadenamiento

**Objetivo:** convertir las propiedades implícitas del motor en invariantes verificadas automáticamente.

### 8.1 Construir el grafo de dependencias

Durante `BaseConocimiento.construir()` se debe obtener, para cada producción:

- hechos positivos que consume;
- hechos que consume bajo `negar`;
- solicitudes que consume;
- hallazgo que produce;
- solicitudes que produce;
- etapa y posición de agenda.

El análisis debe recorrer el árbol completo de condiciones, incluidas definiciones reutilizables.

### 8.2 Validar productores y consumidores

Agregar errores de carga para:

- referencia a un hecho que no tiene productor ni está declarado como inicial;
- dos productores incompatibles para un hallazgo que debería ser único;
- dependencia de una etapa anterior respecto de un hecho producido solo en una etapa posterior;
- negación de un hecho producido en la misma etapa o en una etapa posterior;
- dependencia circular negativa;
- producción imposible de alcanzar por una etapa mal asignada.

### 8.3 Corregir el caso R28/R29

Alternativa recomendada:

1. mantener `R29` en `tiempo`;
2. mover `R28` a una etapa posterior específica, por ejemplo `aviso_tiempo`, o a `control` si el significado de esa etapa lo permite;
3. documentar que el agotamiento se establece antes del aviso preventivo;
4. regenerar los casos de referencia solo después de demostrar que las decisiones no cambian.

No se debe aceptar como solución depender únicamente de que `R29` aparezca antes en el YAML.

### 8.4 Pruebas nuevas

- Rechazo de una negación cuyo productor está en la misma etapa.
- Rechazo de una negación cuyo productor está en una etapa posterior.
- Aceptación cuando el productor pertenece a una etapa anterior.
- Detección de dependencias indirectas a través de `definicion`.
- Permanencia de los 242 casos de referencia.
- Prueba de terminación y refracción.
- Prueba de determinismo al repetir una evaluación.
- Prueba explícita de una cadena de al menos tres producciones.

### Archivos previstos

- `backend/src/poscosegran/sistema_experto/base_conocimiento.py`
- `knowledge/base_conocimiento.yaml`
- `backend/tests/test_base_conocimiento.py`
- `docs/MOTOR.md`
- `docs/ARQUITECTURA_SE.md`

### Criterio de aceptación

- Una versión de conocimiento insegura por negación no puede guardarse ni activarse.
- La base oficial carga sin errores.
- Los 242 casos reproducen exactamente sus resultados aprobados.
- La explicación conserva orden, soportes y regla documental.

### Estimación

4 a 6 horas.

---

## 9. Fase 3 — Completar el workflow de adquisición de conocimiento

**Objetivo:** cubrir todo el ciclo de vida de una versión sin estados muertos ni activaciones no controladas.

### 9.1 Descartar propuestas

Implementar:

```text
POST /api/v1/adquisicion/versiones/{id}/descartar
```

Reglas del comando:

- solo admite versiones en `PROPUESTA`;
- exige rol `INGENIERO_CONOCIMIENTO`;
- exige motivo no vacío;
- cambia el estado a `DESCARTADA` dentro de una transacción;
- registra auditoría con versión, usuario, motivo y fecha;
- es idempotente frente a un reintento idéntico;
- devuelve conflicto si la versión ya fue activada.

Añadir la acción equivalente en `src/views/Adquisicion.tsx`, con confirmación y visualización del motivo.

### 9.2 Estado de la versión reemplazada

Definir el estado `SUPERADA` para una versión que fue activada pero dejó de ser la vigente. La activación debe ejecutar atómicamente:

1. bloquear la propuesta y la versión activa;
2. recalcular el impacto;
3. marcar la versión vigente como `SUPERADA` y `activa=false`;
4. marcar la propuesta como `ACTIVADA` y `activa=true`;
5. guardar responsable y fecha;
6. registrar el resumen de impacto en auditoría.

Crear una migración nueva; no modificar migraciones que ya pudieron aplicarse.

### 9.3 Separación de funciones

Impedir que la misma identidad proponga y active una versión. Si el entorno académico necesita operar con una sola cuenta, permitir una excepción únicamente en entorno local mediante una configuración explícita, desactivada por defecto y prohibida en producción.

### 9.4 Recalcular impacto al activar

La simulación inicial es informativa. En la activación se debe volver a ejecutar la propuesta contra los casos de referencia y contra la muestra histórica vigente dentro del límite definido. Si aparecen errores estructurales o cambios no autorizados, la activación debe abortar sin cambiar la versión vigente.

### 9.5 Minimización de datos

Los resultados de impacto no deben exponer identificadores directos de evaluaciones de unidades fuera del alcance del ingeniero. Utilizar índices de caso, identificadores opacos o resúmenes agregados.

### Archivos previstos

- `backend/src/poscosegran/api/rutas/adquisicion.py`
- `backend/src/poscosegran/servicios/conocimiento.py`
- `backend/src/poscosegran/db/enums.py`
- `backend/src/poscosegran/db/modelos/conocimiento.py`
- `backend/migrations/versions/0004_*.py`
- `backend/sql/permisos_aplicacion.sql`
- `backend/scripts/preparar_local.py`
- `src/views/Adquisicion.tsx`
- `src/api/client.ts`
- Contratos OpenAPI generados.

### Criterio de aceptación

- Una propuesta puede simularse, guardarse, descartarse o activarse.
- Solo existe una versión activa.
- La versión reemplazada queda inequívocamente como `SUPERADA`.
- Proponente y activador son personas distintas en producción.
- Todo cambio de estado queda auditado.
- No se filtran identificadores de evaluaciones ajenas.

### Estimación

6 a 9 horas.

---

## 10. Fase 4 — Pruebas de persistencia, concurrencia y API

**Objetivo:** demostrar que las garantías declaradas funcionan sobre PostgreSQL real.

### 10.1 API de adquisición

Crear `backend/tests/test_adquisicion_api.py` con casos de:

- simulación válida;
- propuesta sin cambios;
- propuesta sin motivo;
- contenido inválido;
- guardado exitoso;
- descarte exitoso y repetido;
- activación exitosa;
- activación por el proponente;
- activación de una versión descartada;
- activación concurrente de dos propuestas;
- permisos para ingeniero y respuestas 403 para otros roles;
- persistencia de auditoría y resumen de impacto.

### 10.2 Integridad y concurrencia

Cubrir explícitamente:

- una sola versión activa;
- una sola incidencia abierta por unidad y tipo;
- evaluación inmutable;
- historial no eliminable;
- bloqueo de actualización mediante `FOR UPDATE` y advisory lock;
- idempotencia con dos solicitudes simultáneas;
- rollback completo ante fallo intermedio.

La prueba `test_solo_una_incidencia_abierta_por_tipo` debe crear su propia unidad y no reutilizar datos persistentes de una ejecución anterior.

### 10.3 Aislamiento de pruebas

Cada prueba de integración debe operar con datos propios. Se recomienda una de estas estrategias:

1. transacción por prueba con rollback, cuando el código bajo prueba comparte la conexión;
2. truncado controlado entre pruebas en una base exclusiva;
3. base efímera por job mediante el servicio de PostgreSQL de GitHub Actions.

Para este proyecto se recomienda la tercera como entorno de CI y la primera donde sea técnicamente compatible con `TestClient`.

### Criterio de aceptación

- Ninguna prueba se omite en el job de CI.
- Dos activaciones concurrentes no dejan dos versiones activas.
- La suite pasa tanto con la credencial de migración como con las verificaciones específicas de la credencial restringida.
- Los errores esperados comprueban código HTTP y cuerpo, no solo el código.

### Estimación

5 a 7 horas.

---

## 11. Fase 5 — Fortalecer el workflow de integración continua

**Objetivo:** hacer que un fallo real no pueda ocultarse por omisiones o artefactos desactualizados.

### Orden de gates recomendado

1. Instalar dependencias con versiones bloqueadas.
2. Preparar y migrar PostgreSQL.
3. Cargar la base de conocimiento de forma idempotente.
4. Ejecutar Ruff.
5. Ejecutar Mypy estricto.
6. Ejecutar `alembic check`.
7. Ejecutar Pytest y fallar si alguna prueba marcada `bd` fue omitida.
8. Ejecutar pruebas con la credencial restringida.
9. Regenerar OpenAPI, tipos y catálogo de campos.
10. Exigir `git diff --exit-code` para los artefactos generados.
11. Ejecutar lint y build del frontend.
12. Ejecutar Playwright contra la API real.
13. Construir y probar el stack Docker completo.
14. Subir logs y resultados de Playwright cuando falle cualquier gate.

### Cambios propuestos

- Añadir una comprobación temprana de `POSCOSEGRAN_BD_URL_PRUEBAS`.
- Configurar Pytest para que un skip por ausencia de BD falle en CI.
- Añadir carga idempotente del conocimiento al workflow.
- Incorporar las pruebas de adquisición con la credencial de aplicación.
- Mantener la comprobación de contrato generado.
- Asegurar que el teardown de Docker se ejecute con `if: always()`.
- Dividir el job si se necesita diagnóstico más rápido, sin perder el orden de dependencias.

### Script local equivalente

Crear `scripts/verificar.ps1` que reproduzca los gates compatibles con Windows y falle en el primer error. El script no debe contener credenciales; debe leerlas de variables de entorno.

### Criterio de aceptación

- El workflow termina en verde desde un clon limpio.
- Una modificación manual de `docs/openapi.json` o `src/api/contrato.ts` hace fallar el gate de contrato.
- La ausencia de PostgreSQL o de su URL de prueba hace fallar el job, no omitir pruebas.
- Los logs permiten identificar con precisión el primer componente que falló.

### Estimación

3 a 5 horas.

---

## 12. Fase 6 — Verificación funcional y cierre

**Objetivo:** demostrar que el sistema completo satisface sus invariantes después de todos los cambios.

### Matriz final

| Área | Verificación | Resultado exigido |
|---|---|---|
| Conocimiento | Cargar catálogo y base operativa | Sin errores; exactamente 30 reglas documentales. |
| Regresión | Ejecutar 242 casos | Cero diferencias no aprobadas. |
| Encadenamiento | Caso R20 → R19 | Segunda pasada registrada y decisión correcta. |
| Terminación | Evaluaciones repetidas | Sin ciclos; cada producción dispara una vez. |
| Resolución | R30.1–R30.9 | Se evalúan nueve ramas y se elige una sola. |
| Explicación | Cómo/por qué no/por qué se pide | Respuestas coherentes con la traza. |
| Adquisición | Simular → guardar → activar/descartar | Todos los estados y permisos correctos. |
| Persistencia | Migraciones desde cero | `upgrade head` y `alembic check` correctos. |
| Seguridad | Credencial restringida | Sin DDL ni operaciones no concedidas. |
| API | Suite completa | Cero fallos y cero omisiones inesperadas. |
| Frontend | Lint y build | Correctos. |
| E2E | Flujo real en navegador | Todos los escenarios pasan. |
| Docker | Stack desde cero | Servicios saludables y E2E correcto. |

### Revisión documental

Actualizar de forma coordinada:

- `docs/MOTOR.md`
- `docs/ARQUITECTURA_SE.md`
- `docs/PRUEBAS.md`
- `docs/API.md`
- `docs/BASE_DATOS.md`
- `docs/SEGURIDAD.md`
- `DIAGNOSTICO_WORKFLOW.md`
- `README.md` y `backend/README.md`, si cambian comandos de preparación.

### Criterio de aceptación

- El pull request incluye evidencia de todos los gates.
- La documentación coincide con el código y el contrato generado.
- No quedan tareas “pendientes” sin issue, responsable o justificación.
- El equipo puede reproducir el entorno desde las instrucciones del repositorio.

### Estimación

3 a 4 horas.

---

## 13. Comandos de verificación final

Los siguientes comandos presuponen que PostgreSQL está activo y que las variables del archivo local están configuradas:

```powershell
# Preparación
backend\.venv\Scripts\python.exe backend\scripts\preparar_local.py

# Backend
Set-Location backend
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m mypy
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe -m pytest -q
Set-Location ..

# Contrato generado
backend\.venv\Scripts\python.exe backend\scripts\exportar_contrato.py
pnpm.cmd api:types
git diff --exit-code -- docs/openapi.json src/api/contrato.ts src/campos.json

# Frontend
pnpm.cmd lint
pnpm.cmd build

# Navegador
pnpm.cmd test:e2e
```

Para el stack contenerizado:

```powershell
docker compose --env-file backend/.env up -d --build
docker compose --env-file backend/.env ps
pnpm.cmd test:e2e
docker compose --env-file backend/.env down
```

En caso de fallo, conservar los logs antes de desmontar el stack.

---

## 14. Estrategia de commits

Se recomienda la siguiente separación:

1. `fix(ci): eliminar implementación de reglas obsoleta`
2. `test(motor): cubrir dependencias y negación estratificada`
3. `fix(motor): validar orden seguro de dependencias`
4. `feat(adquisicion): permitir descartar propuestas`
5. `feat(adquisicion): gestionar versiones superadas y cuatro ojos`
6. `test(api): cubrir adquisición, permisos y concurrencia`
7. `ci: impedir omisiones y verificar carga idempotente`
8. `docs: actualizar motor, arquitectura y diagnóstico`

Cada commit debe pasar los gates correspondientes a su capa. No se deben regenerar casos de referencia para ocultar regresiones: cualquier cambio esperado requiere revisión explícita del experto de dominio.

---

## 15. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Eliminar un módulo que todavía se usa dinámicamente | Importación rota | Búsqueda estática, arranque real de API y suite completa antes de fusionar. |
| Cambiar el orden de R28/R29 altera decisiones | Decisión insegura | Grafo de dependencias, prueba específica y 242 regresiones. |
| Activaciones concurrentes | Dos versiones activas | Transacción, bloqueos y restricción única comprobada. |
| Pruebas que pasan por omisión | Falsa confianza | Fallar CI si falta la configuración de BD. |
| Contrato frontend desactualizado | Error en ejecución | Regeneración y `git diff --exit-code`. |
| Casos de referencia modificados sin revisión | Regresión encubierta | Revisión del experto y comparación de impacto obligatoria. |
| Mismo usuario propone y activa | Falta de separación de funciones | Regla de cuatro ojos y auditoría. |
| Datos de otras unidades en simulación | Exposición indebida | Resultados agregados o identificadores opacos. |

---

## 16. Definición de terminado

El trabajo estará terminado únicamente cuando se cumplan simultáneamente estas condiciones:

- Ruff, Mypy y Alembic pasan sin errores.
- Todas las pruebas de backend se ejecutan; no hay omisiones inesperadas.
- Los 242 casos de referencia se reproducen sin diferencias no aprobadas.
- El motor rechaza dependencias negativas inseguras.
- El flujo de adquisición permite descartar y activar con estados inequívocos.
- La activación vuelve a medir impacto y respeta separación de funciones.
- El contrato OpenAPI y los tipos del frontend están sincronizados.
- Lint, build y Playwright pasan.
- El stack Docker se construye y supera los E2E desde cero.
- La documentación técnica refleja el comportamiento efectivo.
- El workflow remoto finaliza en verde en la rama de entrega.

---

## 17. Estimación global y prioridad

| Prioridad | Fases | Esfuerzo estimado |
|---|---|---:|
| P0 — Desbloqueo | Fases 0 y 1 | 3–5 horas |
| P1 — Seguridad lógica | Fase 2 | 4–6 horas |
| P1 — Flujo completo | Fase 3 | 6–9 horas |
| P1 — Evidencia automática | Fases 4 y 5 | 8–12 horas |
| P2 — Cierre | Fase 6 | 3–4 horas |
| **Total estimado** | **Todas** | **24–36 horas efectivas** |

La estimación supone conocimiento previo del proyecto y disponibilidad del entorno PostgreSQL. Debe tratarse como un rango técnico, no como una fecha contractual.

---

## 18. Primer paso recomendado

Ejecutar las fases 0 y 1 en un cambio aislado. Eso recupera el análisis estático y proporciona una línea base confiable. Solo después debe modificarse la semántica del motor o el flujo de adquisición.
