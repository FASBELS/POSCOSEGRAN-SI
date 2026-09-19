# Base de conocimiento

Copia versionada del material de dominio y el catálogo que carga el backend.

| Archivo | Contenido |
|---|---|
| `POSCOSEGRAN_30_reglas_base_conocimiento_actualizado.md` | Base operativa 2.0: reglas, parámetros, tablas, R30 y casos C01–C40 |
| `catalogo.yaml` | Transcripción cargable de las 30 reglas, las nueve ramas y las nueve fuentes |
| `POSCOSEGRAN_30_reglas_base_conocimiento_v1.md` | Versión anterior, conservada para comparar |
| `Avance_SI.md` | Contexto académico |
| `POSCOSEGRAN_Guia_construccion_completa.md` | Contrato de API, matriz de campos y escenarios |

## Cargar el catálogo

```bash
python scripts/transcribir_base.py knowledge/POSCOSEGRAN_30_reglas_base_conocimiento_actualizado.md
python -m poscosegran.conocimiento.cargar knowledge/catalogo.yaml --activar
```

`catalogo.yaml` se genera, no se edita a mano: el script copia el texto de cada
celda del documento para que la pantalla de conocimiento muestre exactamente lo
que dice la base revisada. La validación rechaza el archivo si falta cualquiera
de las 30 reglas, de las nueve ramas o de las fuentes que citan.

Cada evaluación queda ligada por `id_version_conocimiento` a la versión con la
que se resolvió, y el hash del archivo se guarda en `version_conocimiento`.

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
