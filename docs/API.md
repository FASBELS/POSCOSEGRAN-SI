# API

El contrato ejecutable se encuentra en [openapi.json](openapi.json). La documentación interactiva local está en `/documentacion`; se desactiva en producción. Base de recursos: `/api/v1`.

| Grupo | Recursos |
| --- | --- |
| Identidad y resumen | `/me`, `/inicio` |
| Registro | `/almacenes`, `/lotes`, `/unidades` y consultas/actualizaciones por ID |
| Evaluación | `/unidades/{id}/evaluaciones`, `/evaluaciones/{id}`, `/unidades/{id}/historial`, `/unidades/{id}/vigencia` |
| Captura | `/unidades/{id}/borrador` |
| Seguimiento | controles, eventos, planes, dictámenes, admisiones e incidencias de la unidad |
| Actuación técnica | `/incidencias/{id}/revisiones`, `/incidencias/{id}/resoluciones` |
| Conocimiento | versión, reglas y fuentes bajo `/conocimiento` |

Los POST y PUT de creación requieren `Idempotency-Key`. Los PATCH usan `If-Match: "revision"`. El primer borrador usa `If-None-Match: *`; las actualizaciones, `If-Match`. La evaluación y las actuaciones envían las revisiones de unidad y almacén; las actuaciones técnicas también la de incidencia. Una revisión obsoleta devuelve 409/412 según el recurso, sin aplicar parcialmente el cambio.

El cliente conserva la clave de una operación de resultado incierto en la misma pestaña, incluso al recargar. Los errores de validación permiten corregir y reenviar. No se debe asumir que una evaluación histórica sigue autorizando: consultar la vigencia actual.

Los errores incluyen `codigo`, `mensaje`, `campos` e `id_solicitud`. La cabecera `X-Id-Solicitud` permite correlacionar. Las listas usan `limite` y `cursor`; la interfaz recorre las páginas. Fechas ISO 8601 con zona; números finitos; booleanos estrictos. Una cadena `"false"` no equivale al booleano `false`.

## Extensión: sistema experto (D-SE-3)

| Método y ruta | Rol | Uso |
|---|---|---|
| `GET /evaluaciones/{id}/explicacion` | acceso a la unidad | Módulo de explicación: cadena de reglas (¿cómo?), autorizaciones no concedidas (¿por qué no?), ramas R30 evaluadas y hechos del caso. 409 si la evaluación es anterior a la versión 0.8.0 del motor o no se reproduce. |
| `GET /adquisicion/versiones` | `INGENIERO_CONOCIMIENTO` | Versiones de la base con estado, motivo y huella. |
| `GET /adquisicion/versiones/{id}` | `INGENIERO_CONOCIMIENTO` | Parámetros, reglas de producción y cambios respecto de su origen. |
| `POST /adquisicion/propuestas` | `INGENIERO_CONOCIMIENTO` | Valida y mide una propuesta. `guardar: false` solo simula; `guardar: true` la registra como `PROPUESTA`. |
| `POST /adquisicion/versiones/{id}/activar` | `INGENIERO_CONOCIMIENTO` | Activa una versión registrada, con motivo. Las evaluaciones emitidas no cambian. |

`GET /conocimiento` añade `version_parametros`, `hash_base`, `parametros` y
`uso_campos` (para cada campo, las reglas que lo usan).

Para actualizar tipos tras cambiar esquemas, desde la raíz:

```powershell
backend/.venv/Scripts/python.exe backend/scripts/exportar_contrato.py
pnpm.cmd api:types
pnpm.cmd typecheck
```

`src/api/contrato.ts` y `src/campos.json` son generados. El endpoint `/auth/local/sesion` existe únicamente cuando el entorno habilita explícitamente acceso local. No es el mecanismo de autenticación de producción.
