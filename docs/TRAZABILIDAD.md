# Trazabilidad

Cómo se responde a "¿por qué el sistema decidió esto?" sin recurrir a la memoria
de nadie.

## Qué se guarda de cada evaluación

Una evaluación es una instantánea inmutable. Guarda:

- **La entrada efectiva** tal como llegó, en `entrada_efectiva`, para poder
  reproducir la inferencia.
- **Las revisiones usadas** de unidad y de almacén. Si cualquiera cambia después,
  la vigencia deja de ser `VIGENTE`.
- **Los motivos**, en tablas relacionales y no en un JSON: cada motivo lleva su
  regla, su mensaje, su evidencia (campo, valor observado, operador y umbral) y
  sus fuentes con localizador.
- **Las reglas activadas**, en orden de disparo.
- **Los cálculos de tiempo**, incluida la celda de la tabla que se usó.
- **Las observaciones aplicadas**, con las recuperadas del historial marcadas
  `HISTORICA` y con su fecha original.
- **Las versiones** de base, parámetros y motor, y el identificador de la versión
  de conocimiento cargada, con su hash.

Cambiar un parámetro o corregir el catálogo produce una versión nueva; las
evaluaciones anteriores siguen apuntando a la suya. Una decisión de marzo se
puede volver a explicar con los umbrales de marzo: cada evaluación guarda sus
hechos iniciales y la huella de la base, y `GET /evaluaciones/{id}/explicacion`
la reproduce con esa versión exacta y reconstruye la cadena de reglas.

## De la regla a la fuente

La sección `fundamentos:` de `knowledge/base_conocimiento.yaml` asigna a cada regla
sus fuentes y la naturaleza de su fundamento; cada parámetro declara también el
suyo:

| Fundamento | Significado |
|---|---|
| `PUBLICADO` | El umbral aparece como tal en la fuente citada |
| `TRANSFERIDO` | Procede de maíz amarillo duro o de criterios comerciales, sin validación para chulpi |
| `POLITICA_PROTOTIPO` | Decisión de diseño; la fuente no la respalda |
| `MIXTO` | Umbral publicado con una decisión de diseño encima |

La distinción importa: presentar una política del prototipo como respaldo
bibliográfico sería atribuir a la FAO, a SENASA o al Codex algo que no dicen. El
aviso al 80 % de vida consumida, la banda condicional de 13–14 %, el plazo de 30
días y los filtros de aireación son decisiones del prototipo, y la interfaz debe
poder decirlo.

## Qué no se guarda porque se calcula

La **vigencia** no se almacena. Se calcula en cada consulta con el reloj del
servidor, a partir de la decisión, su fecha de vencimiento, los eventos
posteriores, las incidencias abiertas después de la evaluación y las revisiones
de unidad y almacén.

Así una autorización vencida sigue existiendo como decisión histórica sin seguir
autorizando, que es exactamente lo que pide el caso C24.

## Historial y corrección

No hay edición. Corregir significa registrar algo nuevo:

- Una medición equivocada se corrige con otra observación, no editando la
  anterior.
- Una evaluación se corrige emitiendo otra.
- Una cuarentena se levanta con una resolución registrada, con evidencia y
  disposición. Que desaparezca un olor o cambie una medición no la cierra.
- Una autorización se invalida por evento o por cambio de revisión, no borrando
  la evaluación.

Los disparadores de la migración `0002` imponen esto en la propia base, de modo
que tampoco una consulta manual pueda reescribir el historial.

## Auditoría

Cada escritura deja un registro con usuario, roles, acción, recurso, método,
ruta, estado HTTP, revisión resultante, identificador de solicitud y un resumen
depurado de credenciales. Para una evaluación, el resumen incluye la decisión,
la rama y las reglas activadas: basta para reconstruir qué pasó sin abrir la
evaluación completa.

El registro se escribe en la misma transacción que el cambio. Si la operación
falla, no queda un rastro afirmando algo que no ocurrió.
