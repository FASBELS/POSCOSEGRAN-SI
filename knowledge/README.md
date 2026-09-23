# Base de conocimiento

Copia versionada del material de dominio y el catálogo que carga el backend.

| Archivo | Contenido |
|---|---|
| `POSCOSEGRAN_30_reglas_base_conocimiento_actualizado.md` | Base operativa 2.0: reglas, parámetros, tablas, R30 y casos C01–C40 |
| `base_conocimiento.yaml` | **Base operativa que ejecuta el motor**: reglas SI–ENTONCES, parámetros, definiciones, tabla de tiempo, datos exigibles, resolución R30 y restricciones de integridad |
| `catalogo.yaml` | Transcripción documental de las 30 reglas, las nueve ramas y las nueve fuentes |
| `casos_referencia.json` | 242 casos congelados (C01–C40 y variaciones) para regresión y para medir el impacto de un cambio |
| `POSCOSEGRAN_30_reglas_base_conocimiento_v1.md` | Versión anterior, conservada para comparar |
| `Avance_SI.md` | Contexto académico |
| `POSCOSEGRAN_Guia_construccion_completa.md` | Contrato de API, matriz de campos y escenarios |

## Dos archivos, una versión

`base_conocimiento.yaml` es lo que el motor ejecuta; `catalogo.yaml` es el texto
del documento que ve el usuario. Se versionan y se cargan juntos, y el cargador
exige que describan exactamente las mismas reglas, ramas y fuentes: la pantalla de
conocimiento nunca muestra una regla distinta de la que se aplicó.

```bash
# Regenerar el texto documental desde el documento revisado
python scripts/transcribir_base.py knowledge/POSCOSEGRAN_30_reglas_base_conocimiento_actualizado.md
# Validar y registrar la versión (semilla) como activa
python -m poscosegran.conocimiento.cargar knowledge --activar
```

Si la base no es válida, el cargador lista los errores y no registra nada. Volver
a cargar el mismo contenido no duplica la versión: se identifica por su huella
SHA-256. Cada evaluación queda ligada por `id_version_conocimiento` a la versión
con la que se resolvió.

## Cambiar el conocimiento

En un entorno en marcha, los cambios se hacen desde el **módulo de adquisición**
(pantalla *Adquisición*, rol `INGENIERO_CONOCIMIENTO`): la propuesta se valida, se
mide contra los casos de referencia y las evaluaciones recientes, y se activa como
versión nueva. Las evaluaciones ya emitidas conservan su versión.

Editar este archivo a mano también es válido para la semilla; después:

```bash
cd backend && pytest tests/test_base_conocimiento.py tests/casos
```

Si un cambio intencional altera decisiones, `test_casos_de_referencia_se_reproducen`
fallará: revisa los casos afectados y regenera el archivo con
`python scripts/generar_casos_referencia.py`.

## Lo que la base deja abierto

El propio documento lo enumera en su sección 11 y el motor lo respeta en lugar
de rellenarlo:

- Los límites transferidos de maíz amarillo duro y de criterios comerciales no
  están validados para chulpi.
- La tabla de tiempo de referencia es de cereales NDSU, con celdas sin duración
  publicada. El motor avanza a una celda numérica más exigente y registra la
  sustitución; nunca interpola ni extrapola.
- No existe todavía una tabla de humedad de equilibrio que cubra el clima
  altoandino. Mientras no se cargue, `humedad_equilibrio_maiz` llega como
  observación y, sin ella, R10 y R11 no recomiendan aireación.
- Los casos C01–C40 son expectativas de aceptación, no ensayos de campo.
