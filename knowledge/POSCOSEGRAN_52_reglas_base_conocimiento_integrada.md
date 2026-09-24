# POSCOSEGRAN: base de conocimiento integrada R01–R52

**Versión:** 3.0 (propuesta integrada para revisión técnica)  
**Fecha de revisión:** 24 de septiembre de 2026  
**Documento de origen:** POSCOSEGRAN_30_reglas_base_conocimiento.md, investigación del 8 de septiembre de 2026.  
**Ámbito:** almacenamiento poscosecha de maíz chulpi seco, destinado a alimentación, por pequeños productores de la sierra sur del Perú.  
**Objetivo:** especificar una base de conocimiento implementable mediante encadenamiento hacia adelante, con decisiones reproducibles y trazables.

## 1. Alcance y criterio de uso

Esta versión corrige conexiones incompletas, solapamientos operativos, nombres inconsistentes, tratamiento de datos desconocidos y conservación indebida de conclusiones antiguas. Conserva R01–R30 y añade R31–R52 sin renumerar: R30 sigue siendo la única regla de decisión y se ejecuta al final, después de las reglas diagnósticas con identificadores mayores.

Se distinguen tres elementos:

1. **Validación y cálculos:** comprueban datos, construyen listas de verificación y calculan tiempo y vigencia.
2. **Reglas R01–R29 y R31–R52:** generan hallazgos, solicitudes o avisos de despacho. R47 es solo aviso de despacho.
3. **R30:** selecciona una única decisión final mediante una tabla ordenada, cuando terminó la inferencia diagnóstica.

R30 es una regla de decisión compuesta. Si el motor exige una producción por cada combinación SI–ENTONCES, sus ramas se implementan por separado. Por tanto, se definen **52 identificadores principales**, sin afirmar que existan exactamente 52 producciones atómicas.

Los límites transferidos de maíz general, amarillo duro y otras variedades son referencias provisionales. La corrección lógica de esta especificación no equivale a validación agronómica o sanitaria para chulpi. El sistema autoriza condiciones de almacenamiento dentro de su alcance; no certifica inocuidad, ausencia de micotoxinas ni aptitud para consumo.

**Políticas explícitas del prototipo:**

- Humedad confirmada de hasta 13 % b.h.: condición base.
- Más de 13 % y hasta 14 %: admisión excepcional con revisión técnica, plazo corto y monitoreo.
- Más de 14 %: suspender almacenamiento normal y acondicionar.
- Temperatura del almacén o del grano de 25 °C o más: corregir y reevaluar.
- HR del almacén de 60 % o más: corregir en almacenamiento no hermético.
- Recipientes herméticos: humedad de hasta 13 %, barrera íntegra y cierre comprobado.
- Nunca convertir un dato desconocido en una condición favorable.
- Las alertas no resueltas mantienen su efecto hasta completar la actuación correspondiente.

## 2. Modelo de datos y semántica

### 2.1 Unidad de evaluación

Cada evaluación pertenece a un único lote, recipiente o grupo homogéneo de recipientes y almacén. Todos los hechos incluyen:

| Campo | Contenido |
|---|---|
| id_lote, id_recipiente, id_almacen | Identificadores relacionados. Si un lote tiene recipientes en condiciones diferentes, evaluarlos por separado. |
| id_evaluacion, fecha_evaluacion | Identificador y fecha-hora de la evaluación. |
| fase | INGRESO o SEGUIMIENTO. INGRESO evalúa la admisión al almacenamiento normal de un lote acondicionado y envasado; SEGUIMIENTO evalúa su permanencia. |
| valor, unidad, fecha_observacion | Dato original, unidad y momento real de la observación. |
| metodo, responsable, evidencia | Procedimiento, persona y registro que sustentan el dato. |
| estado_dato | VALIDO, DESCONOCIDO, INVALIDO o VENCIDO. |
| version_base, version_parametros | Versiones utilizadas para reproducir el resultado. |

El envasado necesario para comprobar un cierre no constituye por sí mismo una autorización de almacenamiento. La inspección de grano previa al sellado se conserva como parte de la evaluación de ingreso.

**Estados lógicos:** VERDADERO, FALSO y DESCONOCIDO. NO_APLICA se permite únicamente cuando esta especificación excluye expresamente una comprobación.

- SI dispara solamente cuando el antecedente completo es VERDADERO.
- En una conjunción, un FALSO basta para obtener FALSO; si no hay falsos y falta información, el resultado es DESCONOCIDO.
- En una disyunción, un VERDADERO basta para obtener VERDADERO; si no hay verdaderos y falta información, el resultado es DESCONOCIDO.
- Negar DESCONOCIDO produce DESCONOCIDO.
- Un dato inválido no participa en comparaciones numéricas. Genera una solicitud de corrección.
- Un incumplimiento ya comprobado se conserva aunque falten otros datos. Por ejemplo, moho observado basta para solicitar cuarentena.

### 2.2 Diccionario de entradas

Los porcentajes son números en escala 0–100; la actividad de agua se expresa en escala 0–1. Los tiempos se calculan con fechas, sin redondear para decidir.

| Grupo | Variables canónicas | Dominio y observaciones |
|---|---|---|
| Contexto | variedad, uso_final, fase, tipo_almacenamiento, clima_calido | Tipo: HERMETICO o NO_HERMETICO. Clima cálido es una clasificación territorial documentada, no una inferencia a partir de una sola temperatura. |
| Humedad | humedad_grano, metodo_humedad, temperatura_muestra, equipo_humedad_verificado, muestra_representativa, procedimiento_medicion_cumplido | Humedad: 0 < valor < 100, b.h. Método: INSTRUMENTAL, LABORATORIO o ESTIMACION_INDIRECTA. |
| Actividad de agua | actividad_agua, aw_medida | aw entre 0 y 1, con instrumento y procedimiento válidos. Si no se mide, aw_medida = FALSO y actividad_agua = NO_APLICA. |
| Temperatura del lote | temperatura_grano, temperatura_grano_previa, fecha_temperatura_grano, fecha_temperatura_previa, punto_medicion, punto_medicion_previo, metodo_termico, metodo_termico_previo | °C. Las comparaciones temporales requieren mismo punto y método y registros comparables. |
| Ambiente del almacén | temperatura_almacen, hr_almacen | °C y % HR. No confundir con aire exterior de ventilación. |
| Aire de ventilación | temperatura_aire_exterior, hr_aire_exterior, lluvia_o_niebla, humedad_equilibrio_maiz, tabla_equilibrio_id | Datos de una misma evaluación de aireación. La humedad de equilibrio depende de temperatura, HR y tabla identificada. |
| Hermeticidad | sello_integro, perforacion_barrera, bolsa_abierta_sin_resellar, cierre_seguro | Inspección de la barrera interna, no solo de la cubierta exterior. Una apertura resellada exige una nueva comprobación documentada. |
| Recipiente | recipiente_limpio, recipiente_seco, material_grado_alimentario, recipiente_resistente | Booleanos comprobados antes del llenado y cuando corresponda revisar el recipiente. |
| Insectos | insectos_vivos, granos_perforados, polvillo_inusual, exuvias_larvas, ruido_alimentacion | Observaciones del lote. Las larvas vivas se registran también como insectos_vivos. |
| Revisión de plagas | resultado_revision_plagas, revision_plagas_id | PENDIENTE, CONFIRMADA o DESCARTADA; el resultado debe referirse al episodio y observaciones actuales. No se reutiliza un descarte para indicios nuevos. |
| Roedores y aves | heces_roedores_aves_entorno, huellas, bolsa_roida, grano_derramado_por_plaga | Evidencias en el recipiente o entorno directamente relacionado con el lote; registrar ubicación y recipientes afectados. |
| Deterioro | moho_visible, olor_anormal, condensacion_interna, germinacion | Observaciones del grano o interior del envase. La condensación del edificio se registra en la inspección del local y no equivale por sí sola a deterioro del lote. |
| Calidad física | suciedad_origen_animal, heces_visibles, granos_defectuosos, granos_enfermos, granos_quebrados, materia_organica_extrana, materia_inorganica_extrana | Porcentajes en masa, salvo heces_visibles, que es booleano y se refiere al producto. Identificar muestra y método. |
| Estiba | distancia_piso, distancia_pared, distancia_techo | Metros; tomar la menor separación efectiva a piso, pared/columna y techo/viga. |
| Limpieza | fecha_limpieza_general, limpieza_previa_nuevo_lote, limpieza_diaria, limpieza_tras_operaciones | Booleanos y fecha. limpieza_tras_operaciones = NO_APLICA si no hubo carga o descarga desde la última limpieza del área. |
| Calidad del aire | polvo_humo_gases_vapores, quimicos_combustibles_en_almacen | Booleanos de presencia observada. |
| Control | fecha_inspeccion_grano, fecha_inspeccion_exterior, fecha_control_almacen, ingreso_inspeccionado, hay_evento_que_invalida_control | Fechas de inspecciones completas; no se actualizan por abrir una pantalla o tomar un dato aislado. |
| Tiempo | fecha_inicio_historial, intervalos_historial, vida_previa_documentada, dias_previstos_restantes | Días restantes previstos > 0. Los intervalos no se solapan y cubren el tiempo transcurrido desde el origen documentado del cálculo. |
| Plan y seguimiento | plan_monitoreo_registrado, fecha_proximo_control, dictamen_humedad_condicional | El dictamen incluye responsable, lote, condiciones aprobadas, fecha de expiración y plazo máximo autorizado. |
| Casos abiertos | episodios_cuarentena_abiertos, incidencias_revision_abiertas | Registros persistentes con causa, fecha, evidencia, responsable y estado de resolución. No son booleanos editables libremente por el operador. |

**Campos calculados**, no introducidos arbitrariamente: medicion_confirmada, integridad_hermetica_verificada, lecturas_termicas_comparables, horas_entre_lecturas, dias_almacenados, riesgo_activo, control_vigente, tiempo_referencia_actual, vida_consumida, vida_minima_documentada, vida_proyectada, plazo_compatible, requisitos_completos y condiciones_comunes_aptas.

**Migración de nombres del documento original:**

| Nombre anterior | Tratamiento |
|---|---|
| temperatura_ambiente / hr_ambiente | temperatura_almacen / hr_almacen. No copiar automáticamente a las mediciones exteriores. |
| polvillo | polvillo_inusual; confirmar que el registro se refiere a un indicio anormal. |
| olor_mohoso_anormal | olor_anormal, manteniendo descripción del olor. |
| bolsa_abierta | No equivale a bolsa_abierta_sin_resellar: una bolsa pudo abrirse y luego sellarse. Requiere aclaración. |
| perforacion_recipiente | perforacion_barrera si afecta la barrera hermética; conservar por separado daños superficiales. |
| signos_roedores_aves | Desglosar en signos concretos; no crear observaciones negativas inexistentes. |
| nivel_riesgo | Sustituir por riesgo_activo calculado y lista de causas. |
| plazo_previsto | Convertir a dias_previstos_restantes con fecha de referencia. |

### 2.3 Validación y coherencia

Antes de ejecutar las reglas:

1. Verificar unidades, dominios, fechas no futuras, identificación del lote y procedimiento de medición.
2. No aceptar un mismo hecho como VERDADERO y FALSO en la misma evaluación.
3. Si sello_integro = VERDADERO pero perforacion_barrera o bolsa_abierta_sin_resellar = VERDADERO, marcar DATOS_INCONSISTENTES e impedir declarar protección hermética. Conservar el indicio adverso y solicitar revisión.
4. Una revisión de plagas DESCARTADA no puede anular insectos vivos actuales. Marcar la discrepancia y aplicar R14.
5. Comprobar que granos_enfermos no exceda granos_defectuosos cuando el protocolo lo define como subcategoría. No sumar porcentajes de categorías que se solapan.
6. Vida consumida admite cualquier valor finito no negativo, incluidos valores mayores que 1. No truncarla a 1.
7. Los sensores deben operar dentro de su rango documentado. Una temperatura fuera de la tabla de tiempo no es necesariamente un dato inválido: puede ser un dato válido con cálculo no disponible.
8. Un cambio de recipiente, almacén, exposición al agua, apertura, infestación o incidencia relevante invalida los controles afectados. No reutilizar una lista favorable que ya no describe la situación.

## 3. Parámetros y hechos auxiliares

### 3.1 Parámetros del prototipo

| Parámetro | Valor inicial | Naturaleza |
|---|---:|---|
| humedad_base_max | 13 % b.h. | Referencia transferida, S01/S03. |
| humedad_admision_max | 14 % b.h. | Política conservadora basada en calidad de maíz amarillo duro, S01. |
| temperatura_alerta | 25 °C | Referencia ambiental S01; aplicada también al grano como política preventiva. |
| hr_almacen_no_hermetico_max_exclusiva | 60 % | Referencia S01. |
| aw_alerta | 0,70 | Referencia general S04. |
| aumento_termico_alerta | 2 °C | Referencia indicativa S04, no diagnóstico causal. |
| intervalo_termico_max | 30 días | Ventana máxima operativa para comparar dos lecturas; no es un umbral biológico ni depende del riesgo calculado en esa misma evaluación. |
| hr_aireacion_max_exclusiva | 70 % | Filtro operativo conservador; no sustituye el equilibrio higroscópico ni es un límite universal publicado por FAO. |
| muestra_fria_umbral | 4,4 °C | Referencia S07 para medición de humedad; respetar además el procedimiento del equipo. |
| plazo_corto_max | 30 días restantes | Decisión de diseño, no umbral biológico validado para chulpi. |
| control_no_hermetico_normal | 14 días | Periodicidad inicial basada en S05. |
| control_con_riesgo | 7 días | Periodicidad inicial basada en S05. |
| control_exterior_hermetico_normal | 30 días | Aproximación operativa a inspección mensual, S06. |
| vida_alerta | 0,80 | Decisión de diseño. |
| vida_limite | 1,00 | Límite del modelo aproximado, S08. |
| limite_calido_no_hermetico | 90 días acumulados | Aproximación operativa de tres meses, S01. No se presenta como equivalencia exacta entre días y meses. |

Toda modificación requiere versión, motivo y responsable. Los valores nuevos se revisan como cambios en la base, no como ajustes ocultos del motor.

### 3.2 Comprobaciones favorables explícitas

Las comprobaciones usan datos válidos y vigentes. Si falta un requisito, devuelven DESCONOCIDO. Si un requisito conocido falla, devuelven FALSO.

| Hecho | Definición para ser VERDADERO |
|---|---|
| medicion_confirmada | Método INSTRUMENTAL o LABORATORIO; equipo verificado, muestra representativa y procedimiento cumplido. Para INSTRUMENTAL, temperatura_muestra >= 4,4 °C y dentro del rango del equipo. En LABORATORIO se cumple el acondicionamiento del método y se registra la temperatura exigida por este. |
| integridad_hermetica_verificada | Tipo HERMETICO; sello_integro y cierre_seguro verdaderos; perforacion_barrera y bolsa_abierta_sin_resellar falsos; sin contradicción entre esos registros. |
| RECIPIENTE_APTO | recipiente_limpio, recipiente_seco, material_grado_alimentario, recipiente_resistente y cierre_seguro verdaderos. |
| ESTIBA_APTA | Piso >= 0,15 m, pared/columna >= 0,50 m y techo/viga >= 1,00 m. |
| ALMACEN_HIGIENICO | Limpieza general dentro del mes calendario siguiente a la última limpieza; limpieza diaria verdadera; limpieza tras operaciones verdadera o NO_APLICA; en INGRESO, limpieza_previa_nuevo_lote verdadera. |
| CALIDAD_AIRE_ADECUADA | polvo_humo_gases_vapores y quimicos_combustibles_en_almacen falsos. |
| CALIDAD_FISICA_CONFORME | Suciedad animal <= 0,1 %; heces_visibles falso; defectuosos <= 7 %; enfermos <= 0,5 %; quebrados <= 6 %; materia orgánica extraña <= 1,5 %; inorgánica extraña <= 0,5 %. |
| SIN_EVIDENCIA_DE_PLAGAS | insectos_vivos falso; signos de roedores/aves falsos; todos los indicios de R15 falsos o cada indicio residual explicado en una revisión DESCARTADA válida; ningún episodio de plagas sin resolver. |
| SIN_EVIDENCIA_DE_DETERIORO | moho_visible, olor_anormal, condensacion_interna y germinacion falsos en la inspección aplicable; ningún episodio de deterioro sin resolver. |
| AW_SIN_ALERTA | aw_medida falso, o aw medida válida < 0,70. NO medir aw no prueba ausencia de hongos: permite el cribado basado en humedad confirmada y demás controles. |
| CONTROL_VIGENTE | Inspección completa vigente para el tipo de almacenamiento y control del almacén al día, según sección 5. |
| requisitos_completos | Todos los datos exigibles para la decisión, incluidos los de R31–R52 que apliquen al contexto, están disponibles, son válidos y vigentes o tienen NO_APLICA permitido. No exige mediciones opcionales de aireación si no se solicita esa recomendación. |
| condiciones_comunes_aptas | RECIPIENTE_APTO, ESTIBA_APTA, ALMACEN_HIGIENICO, CALIDAD_AIRE_ADECUADA, CALIDAD_FISICA_CONFORME, SIN_EVIDENCIA_DE_PLAGAS, SIN_EVIDENCIA_DE_DETERIORO, AW_SIN_ALERTA, CONTROL_VIGENTE y AMBIENTE_BASE_APTO verdaderos; medicion_confirmada verdadera; temperatura_grano < 25 °C según medición aplicable; tipo de almacenamiento y contexto válidos; comprobaciones adicionales aplicables de infraestructura, entorno, estiba, identidad y trazabilidad conformes. R47 no forma parte de esta aptitud. |

Para sumar un mes calendario se conserva el día del mes y, si no existe en el mes siguiente, se usa su último día. El vencimiento se compara con fecha-hora; no se sustituye por “más de 30 días” de manera silenciosa.

En seguimiento hermético, los hallazgos internos favorables provienen de la inspección previa al sellado o última apertura controlada. Solo siguen siendo aplicables mientras la barrera y el control exterior permanezcan vigentes y no haya incidencias. No se presentan como mediciones internas recién tomadas. La estimación de temperatura y tiempo se trata en la sección 6.

## 4. Base de conocimiento: R01–R30

**Convención de ejecución:** los hallazgos y las solicitudes son conjuntos sin duplicados. Una solicitud CORRECCION_SOLICITADA significa que el motor debe resolver CORREGIR_Y_REEVALUAR si no existe una causa de mayor prioridad. Las acciones descritas aquí son parte de la especificación, no simples comentarios.

### A. Humedad y aptitud inicial

| ID | Antecedente SI | Consecuente ENTONCES | Acción y fundamento | Fuente(s) y base de la regla |
|---|---|---|---| --- |
| R01 | medicion_confirmada = VERDADERO y humedad_grano > 14 | HUMEDAD_NO_APTA y SUSPENSION_SOLICITADA | En INGRESO, bloquear admisión; en SEGUIMIENTO, suspender permanencia normal y acondicionar. Secar, medir y reevaluar. S01. | **S01.** Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro*, pp. 30–31. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf).<br>**Base de diseño:** La suspensión por fase es una decisión del prototipo. |
| R02 | medicion_confirmada = VERDADERO y 13 < humedad_grano <= 14 | HUMEDAD_CONDICIONAL | Aplicar exclusivamente la rama condicional de R30. Si es hermético, clima cálido o plazo restante > 30 días, generar también CORRECCION_SOLICITADA para secado hasta <= 13 %. S01/S03; banda y plazo son política del prototipo. | **S01.** Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro*, pp. 30–31. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf).<br>**S03.** Food and Agriculture Organization of the United Nations. (s. f.). *Agricultural engineering in development: Storage*. [Capítulo](https://www.fao.org/4/t0522e/T0522E09.htm).<br>**Base de diseño:** La banda condicional, el plazo de 30 días y la revisión técnica son políticas del prototipo. |
| R03 | medicion_confirmada = VERDADERO y humedad_grano <= 13 | HUMEDAD_APTA_BASE | Continuar con las demás comprobaciones. Este hecho no autoriza por sí solo. S01/S03. | **S01.** Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro*, pp. 30–31. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf).<br>**S03.** Food and Agriculture Organization of the United Nations. (s. f.). *Agricultural engineering in development: Storage*. [Capítulo](https://www.fao.org/4/t0522e/T0522E09.htm).<br>**Base de diseño:** La confirmación de la medición corresponde a la validación del prototipo. |
| R04 | aw_medida = VERDADERO y actividad_agua válida >= 0,70 | RIESGO_FUNGICO_HIDRICO y CORRECCION_SOLICITADA | Secado o evaluación técnica y nueva medición. Se elimina del antecedente la expresión “aproximadamente 25 °C”: la equivalencia orientativa de humedad no se usa como sustituto automático de una medición de aw. S04. | **S04.** Codex Alimentarius Commission. (2017). *Code of practice for the prevention and reduction of mycotoxin contamination in cereals* (CXC 51-2003), párrs. 37–39. [Documento oficial](https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXC+51-2003%2FCXC_051e.pdf).<br>**Base de diseño:** La fuente respalda el umbral de aw; su conexión con la corrección es diseño del prototipo. |
| R05 | Hay una medición de humedad aportada y medicion_confirmada = FALSO | MEDICION_HUMEDAD_NO_CONFIRMADA y CORRECCION_SOLICITADA | Corregir método, equipo, representatividad o acondicionamiento. Una estimación indirecta no autoriza ni sustenta por sí sola R01–R03. Si faltan comprobaciones, registrar datos pendientes en vez de suponer confirmación. S07 y validación del sistema. | **S07.** Hellevang, K., & Proulx, R. (2026, 27 de febrero). *Proper grain storage crucial in late winter and spring*. North Dakota State University Extension. [Artículo](https://www.ag.ndsu.edu/news/newsreleases/2026/february/proper-grain-storage-crucial-in-late-winter-and-spring).<br>**Base de diseño:** La fuente sustenta precauciones de medición; la lista de confirmación es diseño del prototipo. |

La relación aproximada humedad–aw a una temperatura concreta puede mostrarse como explicación bibliográfica, pero no se transforma en una equivalencia exacta para chulpi. Si hay discordancia entre humedad y aw, conservar la alerta válida y revisar muestreo e instrumentos.

### B. Ambiente, aireación y hermeticidad

| ID | Antecedente SI | Consecuente ENTONCES | Acción y fundamento | Fuente(s) y base de la regla |
|---|---|---|---| --- |
| R06 | temperatura_almacen < 25 y: (NO_HERMETICO con hr_almacen < 60) o (HERMETICO con integridad_hermetica_verificada = VERDADERO) | AMBIENTE_BASE_APTO | En hermético, la HR externa no representa por sí sola la humedad interna; se exige barrera comprobada y se conserva R08. Es una adaptación de diseño basada en S01/S06, pendiente de validación local. | **S01.** Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro*, pp. 30–31. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf).<br>**S06.** Purdue Extension. (2015). *A guide on the use of PICS bags* (E-265-W). [Guía](https://extension.entm.purdue.edu/publications/E-265.pdf).<br>**Base de diseño:** La adaptación para recipientes herméticos es una decisión de diseño, pendiente de validación local. |
| R07 | tipo_almacenamiento = NO_HERMETICO y hr_almacen >= 60 | RIESGO_REHUMEDECIMIENTO y CORRECCION_SOLICITADA | Corregir exposición a humedad. Consultar R10–R11 solamente si se dispone de aire exterior medido. S01/S05. | **S01.** Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro*, pp. 30–31. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf).<br>**S05.** Food and Agriculture Organization of the United Nations. (s. f.). *Manual of the prevention of post-harvest grain losses: Central storage*, secciones 5.2.4.2–5.2.4.3. [Manual](https://www.fao.org/4/x5065e/x5065E0a.htm). |
| R08 | temperatura_almacen >= 25 o temperatura_grano aplicable >= 25 | RIESGO_TERMICO y CORRECCION_SOLICITADA | No autorizar automáticamente. Evaluar enfriamiento, revisar el grano y recalcular tiempo. La aireación solo se recomienda si R10 la permite. S01/S04. | **S01.** Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro*, pp. 30–31. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf).<br>**S04.** Codex Alimentarius Commission. (2017). *Code of practice for the prevention and reduction of mycotoxin contamination in cereals* (CXC 51-2003), párrs. 37–39. [Documento oficial](https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXC+51-2003%2FCXC_051e.pdf).<br>**Base de diseño:** Aplicar el umbral ambiental al grano y exigir corrección es política preventiva del prototipo. |
| R09 | lecturas_termicas_comparables = VERDADERO y temperatura_grano - temperatura_grano_previa >= 2 | PUNTO_CALIENTE_SOSPECHADO y CORRECCION_SOLICITADA | Abrir incidencia de revisión, inspeccionar varios puntos y buscar causas. El aumento no confirma infestación ni actividad microbiana. S04. | **S04.** Codex Alimentarius Commission. (2017). *Code of practice for the prevention and reduction of mycotoxin contamination in cereals* (CXC 51-2003), párrs. 37–39. [Documento oficial](https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXC+51-2003%2FCXC_051e.pdf).<br>**Base de diseño:** El aumento térmico procede de Codex; la ventana de 30 días y los criterios de comparabilidad son diseño del prototipo. |
| R10 | NO_HERMETICO, datos_aireacion_completos = VERDADERO, humedad_grano > humedad_equilibrio_maiz, hr_aire_exterior < 70, lluvia_o_niebla = FALSO y temperatura_aire_exterior <= temperatura_grano | AIREACION_FAVORABLE | Recomendar aireación para acondicionamiento, siempre subordinada a R30. El filtro de temperatura evita recomendar aire que aumente la temperatura del grano. S05 y política conservadora del prototipo. | **S05.** Food and Agriculture Organization of the United Nations. (s. f.). *Manual of the prevention of post-harvest grain losses: Central storage*, secciones 5.2.4.2–5.2.4.3. [Manual](https://www.fao.org/4/x5065e/x5065E0a.htm).<br>**Base de diseño:** El equilibrio higroscópico procede de FAO; los filtros de HR y temperatura exterior son políticas del prototipo. |
| R11 | NO_HERMETICO y al menos una condición exterior válida demuestra: humedad_grano <= humedad_equilibrio_maiz, hr_aire_exterior >= 70, lluvia_o_niebla = VERDADERO o temperatura_aire_exterior > temperatura_grano | AIREACION_DESFAVORABLE | No recomendar apertura o funcionamiento del sistema de aireación del grano. Con igualdad de humedad se adopta el criterio conservador de no airear automáticamente. S05 y política del prototipo. | **S05.** Food and Agriculture Organization of the United Nations. (s. f.). *Manual of the prevention of post-harvest grain losses: Central storage*, secciones 5.2.4.2–5.2.4.3. [Manual](https://www.fao.org/4/x5065e/x5065E0a.htm).<br>**Base de diseño:** El equilibrio higroscópico procede de FAO; la igualdad de humedad y los filtros de HR y temperatura son políticas del prototipo. |
| R12 | HERMETICO, HUMEDAD_APTA_BASE e integridad_hermetica_verificada = VERDADERO | PROTECCION_HERMETICA_ACTIVA | Mantener sellado y usar control exterior. No demuestra eliminación de insectos ni corrige un lote previamente deteriorado. S06. | **S06.** Purdue Extension. (2015). *A guide on the use of PICS bags* (E-265-W). [Guía](https://extension.entm.purdue.edu/publications/E-265.pdf).<br>**S01.** Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro*, pp. 30–31. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf).<br>**S03.** Food and Agriculture Organization of the United Nations. (s. f.). *Agricultural engineering in development: Storage*. [Capítulo](https://www.fao.org/4/t0522e/T0522E09.htm).<br>**Base de diseño:** El umbral de humedad se hereda de R03; la comprobación conjunta de integridad es diseño del prototipo. |
| R13 | HERMETICO y: sello_integro = FALSO, perforacion_barrera = VERDADERO, bolsa_abierta_sin_resellar = VERDADERO o cierre_seguro = FALSO | HERMETICIDAD_COMPROMETIDA y CORRECCION_SOLICITADA | Invalidar la protección y controles internos heredados del sellado; reparar o sustituir, inspeccionar cuando corresponda y documentar nuevo cierre. No cambiar automáticamente a NO_HERMETICO. S06. | **S06.** Purdue Extension. (2015). *A guide on the use of PICS bags* (E-265-W). [Guía](https://extension.entm.purdue.edu/publications/E-265.pdf).<br>**Base de diseño:** La invalidación de controles y el nuevo registro de cierre son decisiones de implementación. |

**Comparación térmica de R09:** calcular horas_entre_lecturas a partir de fechas. Se exige mismo punto y método, 0 < horas_entre_lecturas <= 720 y ausencia de secado, trasvase o cambio de ubicación que rompa la comparación. La ventana de 30 días es un parámetro operativo independiente del resultado de R09, evitando una dependencia circular con riesgo_activo. Se informa el intervalo junto al aumento: no se interpreta como una tasa fija. Sin pareja comparable, R09 = NO_APLICA; la primera evaluación no queda bloqueada por no tener historia térmica. Una sospecha ya registrada permanece abierta hasta revisión documentada.

**Datos de aireación:** humedad confirmada, temperatura del grano actual y lecturas exteriores simultáneas según el procedimiento de medición, más una tabla aplicable identificada. La tabla debe cubrir las condiciones observadas; no extrapolar una tabla de 20–30 °C a aire altoandino de 5 °C. Si faltan datos y ninguna observación válida basta para activar R11, devolver AIREACION_SIN_DATOS y no recomendar aireación. Si ya existe una contraindicación comprobada, R11 puede determinar AIREACION_DESFAVORABLE aun con otros datos pendientes. Esto no impide evaluar almacenamiento si la recomendación de aireación no es necesaria para resolver una corrección.

R10 y R11 son excluyentes con datos coherentes de una misma evaluación. Ambas son NO_APLICA para almacenamiento hermético. La ventilación del edificio no equivale a abrir recipientes herméticos.

### C. Plagas, deterioro y separación

| ID | Antecedente SI | Consecuente ENTONCES | Acción y fundamento | Fuente(s) y base de la regla |
|---|---|---|---| --- |
| R14 | insectos_vivos = VERDADERO o resultado_revision_plagas = CONFIRMADA con evidencia actual | INFESTACION_CONFIRMADA | Activar R19. No recomendar ingredientes activos ni dosis. S09. | **S09.** Food and Agriculture Organization of the United Nations & World Health Organization. (2026). *Standard for maize (corn)* (CXS 153-1985, enmienda 2026 según el catálogo oficial). [Registro](https://openknowledge.fao.org/handle/20.500.14283/ce0295en). [Catálogo oficial](https://www.fao.org/fao-who-codexalimentarius/codex-texts/all-standards/en/). Los porcentajes comerciales se conservan de la propuesta original; confirmar edición, métodos y aplicabilidad al tipo de chulpi antes del uso productivo.<br>**Base de diseño:** La transición desde una revisión confirmada es parte del flujo del prototipo. |
| R15 | Hay granos_perforados, polvillo_inusual, exuvias_larvas o ruido_alimentacion y la revisión de esos indicios no está válidamente DESCARTADA | INFESTACION_SOSPECHADA y CORRECCION_SOLICITADA | Abrir incidencia y solicitar inspección. Si se confirma infestación, el registro de revisión activa R14 y después R19; si se descarta, registrar causa y alcance. La sospecha sola no se transforma automáticamente en confirmación. S05. | **S05.** Food and Agriculture Organization of the United Nations. (s. f.). *Manual of the prevention of post-harvest grain losses: Central storage*, secciones 5.2.4.2–5.2.4.3. [Manual](https://www.fao.org/4/x5065e/x5065E0a.htm).<br>**Base de diseño:** La revisión por episodio y la transición a R14–R19 son diseño del prototipo. |
| R16 | NO_HERMETICO y 15 <= temperatura_grano <= 35 | AMBIENTE_FAVORABLE_A_INSECTOS y MONITOREO_SOLICITADO | Intensificar inspección. Es riesgo ambiental, no infestación. Si también se cumple R08, prevalece la corrección térmica. S03. | **S03.** Food and Agriculture Organization of the United Nations. (s. f.). *Agricultural engineering in development: Storage*. [Capítulo](https://www.fao.org/4/t0522e/T0522E09.htm).<br>**Base de diseño:** La restricción a NO_HERMETICO y la solicitud de monitoreo son decisiones del prototipo. |
| R17 | heces_roedores_aves_entorno, huellas, bolsa_roida o grano_derramado_por_plaga = VERDADERO en el ámbito evaluado | CONTAMINACION_BIOLOGICA_SOSPECHADA | Activar R19 para los recipientes afectados; inspeccionar el resto sin presumir contaminación de todos los lotes. S02/S05. | **S02.** Servicio Nacional de Sanidad Agraria. (s. f.). *Guía sobre almacenamiento*, secciones 3.1–3.6. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf).<br>**S05.** Food and Agriculture Organization of the United Nations. (s. f.). *Manual of the prevention of post-harvest grain losses: Central storage*, secciones 5.2.4.2–5.2.4.3. [Manual](https://www.fao.org/4/x5065e/x5065E0a.htm). |
| R18 | moho_visible, olor_anormal, condensacion_interna o germinacion = VERDADERO | DETERIORO_SOSPECHADO | Activar R19, separar y remitir a evaluación técnica; considerar análisis según el hallazgo. S04. | **S04.** Codex Alimentarius Commission. (2017). *Code of practice for the prevention and reduction of mycotoxin contamination in cereals* (CXC 51-2003), párrs. 37–39. [Documento oficial](https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXC+51-2003%2FCXC_051e.pdf). |
| R19 | INFESTACION_CONFIRMADA, CONTAMINACION_BIOLOGICA_SOSPECHADA, CONTAMINACION_ANIMAL_OBSERVADA, DETERIORO_SOSPECHADO o episodio de cuarentena abierto | CUARENTENA_SOLICITADA | Abrir o mantener un episodio de cuarentena; prohibir mezcla y salida para consumo sin evaluación competente. R30 determina CUARENTENA con máxima prioridad. S02/S04. | **S02.** Servicio Nacional de Sanidad Agraria. (s. f.). *Guía sobre almacenamiento*, secciones 3.1–3.6. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf).<br>**S04.** Codex Alimentarius Commission. (2017). *Code of practice for the prevention and reduction of mycotoxin contamination in cereals* (CXC 51-2003), párrs. 37–39. [Documento oficial](https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXC+51-2003%2FCXC_051e.pdf).<br>**Base de diseño:** Las fuentes respaldan separación y evaluación; el episodio persistente y la prioridad son diseño del prototipo. |

La resolución de una cuarentena exige registrar responsable técnico, evidencia de evaluación, disposición del lote y cierre del episodio. La simple desaparición de un olor, secado del grano o cambio de fecha no levanta la cuarentena.

### D. Calidad física, recipiente, estiba e higiene

| ID | Antecedente SI | Consecuente ENTONCES | Acción y fundamento | Fuente(s) y base de la regla |
|---|---|---|---| --- |
| R20 | suciedad_origen_animal > 0,1 % o heces_visibles = VERDADERO | CONTAMINACION_ANIMAL_OBSERVADA | Activar R19. El nombre indica material animal observado o exceso del criterio de calidad; no afirma confirmación microbiológica por laboratorio. S09/S01. | **S09.** Food and Agriculture Organization of the United Nations & World Health Organization. (2026). *Standard for maize (corn)* (CXS 153-1985, enmienda 2026 según el catálogo oficial). [Registro](https://openknowledge.fao.org/handle/20.500.14283/ce0295en). [Catálogo oficial](https://www.fao.org/fao-who-codexalimentarius/codex-texts/all-standards/en/). Los porcentajes comerciales se conservan de la propuesta original; confirmar edición, métodos y aplicabilidad al tipo de chulpi antes del uso productivo.<br>**S01.** Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro*, pp. 30–31. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf).<br>**Base de diseño:** La denominación distingue material animal observado de confirmación microbiológica. |
| R21 | granos_defectuosos > 7 % o granos_enfermos > 0,5 % | LOTE_NO_CONFORME_POR_DEFECTOS y CORRECCION_SOLICITADA | Separar para revisión y clasificación; si existen indicadores de R18, aplicar además cuarentena. Cribado comercial provisional. S09. | **S09.** Food and Agriculture Organization of the United Nations & World Health Organization. (2026). *Standard for maize (corn)* (CXS 153-1985, enmienda 2026 según el catálogo oficial). [Registro](https://openknowledge.fao.org/handle/20.500.14283/ce0295en). [Catálogo oficial](https://www.fao.org/fao-who-codexalimentarius/codex-texts/all-standards/en/). Los porcentajes comerciales se conservan de la propuesta original; confirmar edición, métodos y aplicabilidad al tipo de chulpi antes del uso productivo.<br>**Base de diseño:** Aplicación provisional de criterios comerciales a chulpi. |
| R22 | granos_quebrados > 6 %, materia_organica_extrana > 1,5 % o materia_inorganica_extrana > 0,5 % | LOTE_REQUIERE_LIMPIEZA_Y_CLASIFICACION y CORRECCION_SOLICITADA | Limpiar o clasificar; nueva muestra y reevaluación. No inferir conformidad por haber realizado la acción. S09. | **S09.** Food and Agriculture Organization of the United Nations & World Health Organization. (2026). *Standard for maize (corn)* (CXS 153-1985, enmienda 2026 según el catálogo oficial). [Registro](https://openknowledge.fao.org/handle/20.500.14283/ce0295en). [Catálogo oficial](https://www.fao.org/fao-who-codexalimentarius/codex-texts/all-standards/en/). Los porcentajes comerciales se conservan de la propuesta original; confirmar edición, métodos y aplicabilidad al tipo de chulpi antes del uso productivo.<br>**Base de diseño:** Aplicación provisional de criterios comerciales a chulpi. |
| R23 | Cualquiera de recipiente_limpio, recipiente_seco, material_grado_alimentario, recipiente_resistente o cierre_seguro = FALSO | RECIPIENTE_NO_APTO y SUSPENSION_SOLICITADA | En INGRESO, bloquear admisión; en SEGUIMIENTO, suspender permanencia en el recipiente actual. Reemplazar o acondicionar de forma apropiada. S09. | **S09.** Food and Agriculture Organization of the United Nations & World Health Organization. (2026). *Standard for maize (corn)* (CXS 153-1985, enmienda 2026 según el catálogo oficial). [Registro](https://openknowledge.fao.org/handle/20.500.14283/ce0295en). [Catálogo oficial](https://www.fao.org/fao-who-codexalimentarius/codex-texts/all-standards/en/). Los porcentajes comerciales se conservan de la propuesta original; confirmar edición, métodos y aplicabilidad al tipo de chulpi antes del uso productivo.<br>**Base de diseño:** La distinción entre bloqueo y retiro por fase es diseño del prototipo. |
| R24 | distancia_piso < 0,15 m, distancia_pared < 0,50 m o distancia_techo < 1,00 m | ESTIBA_NO_APTA y CORRECCION_SOLICITADA | Reubicar y medir de nuevo. S02. | **S02.** Servicio Nacional de Sanidad Agraria. (s. f.). *Guía sobre almacenamiento*, secciones 3.1–3.6. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf). |
| R25 | Limpieza general vencida, limpieza_diaria = FALSO, limpieza_tras_operaciones = FALSO, o fase INGRESO con limpieza_previa_nuevo_lote = FALSO | ALMACEN_NO_HIGIENICO y CORRECCION_SOLICITADA | Limpiar y registrar verificación antes de autorizar ingreso o continuidad. Las fechas o comprobaciones ausentes generan datos pendientes. S02. | **S02.** Servicio Nacional de Sanidad Agraria. (s. f.). *Guía sobre almacenamiento*, secciones 3.1–3.6. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf).<br>**Base de diseño:** El cálculo de vencimiento y el manejo de datos pendientes son decisiones de implementación. |
| R26 | polvo_humo_gases_vapores = VERDADERO o quimicos_combustibles_en_almacen = VERDADERO | CALIDAD_AIRE_INADECUADA y CORRECCION_SOLICITADA | Retirar la fuente del área de alimentos y reevaluar. Si se sospecha afectación del grano, abrir evaluación técnica y aplicar R18 cuando haya evidencia correspondiente. S02. | **S02.** Servicio Nacional de Sanidad Agraria. (s. f.). *Guía sobre almacenamiento*, secciones 3.1–3.6. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf). |

### E. Seguimiento, tiempo y decisión final

| ID | Antecedente SI | Consecuente ENTONCES | Acción y fundamento | Fuente(s) y base de la regla |
|---|---|---|---| --- |
| R27 | Se ha superado alguna fecha límite de control aplicable según sección 5 | CONTROL_ATRASADO y CORRECCION_SOLICITADA | Completar la inspección requerida antes de autorizar. Una inspección exterior no cuenta como muestreo interno. S05/S06. | **S05.** Food and Agriculture Organization of the United Nations. (s. f.). *Manual of the prevention of post-harvest grain losses: Central storage*, secciones 5.2.4.2–5.2.4.3. [Manual](https://www.fao.org/4/x5065e/x5065E0a.htm).<br>**S06.** Purdue Extension. (2015). *A guide on the use of PICS bags* (E-265-W). [Guía](https://extension.entm.purdue.edu/publications/E-265.pdf).<br>**Base de diseño:** La asignación de plazos por riesgo y la aproximación mensual a 30 días son políticas del prototipo. |
| R28 | vida_consumida calculada >= 0,80 y < 1,00 | VIDA_ESTIMADA_PROXIMA_AL_LIMITE y MONITOREO_SOLICITADO | Solicitar plan de seguimiento y salida dentro del horizonte restante del modelo. El 80 % es una política preventiva. S08. | **S08.** North Dakota State University Extension. (s. f.). *Allowable storage time for cereal grains, malting barley and soybeans*. [Tabla de referencia](https://www.ndsu.edu/agriculture/ag-hub/allowable-storage-time-cereal-grains-malting-barley-and-soybeans).<br>**Base de diseño:** La fuente sustenta el tiempo acumulativo; el aviso al 80 % es decisión de diseño. |
| R29 | vida_consumida >= 1,00, vida_minima_documentada >= 1,00, o clima_calido = VERDADERO con NO_HERMETICO y dias_almacenados >= 90 | VIDA_O_PLAZO_AGOTADO y SUSPENSION_SOLICITADA | Bloquear ingreso o retirar de almacenamiento normal según fase; evaluar disposición técnica. No ordenar consumo ni destrucción automáticamente. S01/S08. | **S01.** Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro*, pp. 30–31. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf).<br>**S08.** North Dakota State University Extension. (s. f.). *Allowable storage time for cereal grains, malting barley and soybeans*. [Tabla de referencia](https://www.ndsu.edu/agriculture/ag-hub/allowable-storage-time-cereal-grains-malting-barley-and-soybeans).<br>**Base de diseño:** El uso del subtotal documentado, la aproximación a 90 días y la actuación por fase son políticas del prototipo. |
| R30 | Evaluación diagnóstica de R01–R29 y R31–R52 completada y solicitudes consolidadas | Una única decisión de la sección 7 | Resolver después de completar los encadenamientos. Conservar todos los hallazgos y causas, aunque una decisión prioritaria determine la actuación principal. | Síntesis de diseño del prototipo (secciones 7 y 8), que integra R01–R29 y R31–R52 y sus fuentes: [S01](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf), [S02](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf), [S03](https://www.fao.org/4/t0522e/T0522E09.htm), [S04](https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXC+51-2003%2FCXC_051e.pdf), [S05](https://www.fao.org/4/x5065e/x5065E0a.htm), [S06](https://extension.entm.purdue.edu/publications/E-265.pdf), [S07](https://www.ag.ndsu.edu/news/newsreleases/2026/february/proper-grain-storage-crucial-in-late-winter-and-spring), [S08](https://www.ndsu.edu/agriculture/ag-hub/allowable-storage-time-cereal-grains-malting-barley-and-soybeans), [S09](https://openknowledge.fao.org/handle/20.500.14283/ce0295en). La decisión única y las prioridades son decisiones de implementación; no se atribuyen a una regla externa literal. |

## 5. Control y vigencia sin apertura innecesaria

### 5.1 Cálculo de riesgo

riesgo_activo es VERDADERO si existe cualquier hallazgo adverso de R01, R02, R04, R05, R07, R08, R09, R13–R18, R20–R26, R28, R29, R31–R43, R45–R46 o R48–R52 que aplique, o alguna incidencia pendiente. R27, R44 y R47 no se usan para calcular riesgo_activo: R27 depende del riesgo, R44 depende de un episodio y R47 pertenece a despacho.

riesgo_activo es FALSO únicamente si las comprobaciones de riesgo aplicables están completas y no hay causas activas. Si faltan comprobaciones y no existe un hallazgo positivo, es DESCONOCIDO. Para programar controles, DESCONOCIDO utiliza 7 días; no habilita autorizaciones.

### 5.2 Qué inspección corresponde

| Situación | Inspección exigida | Plazo máximo inicial |
|---|---|---:|
| INGRESO | Grano, recipiente, cierre, local, estiba y calidad física. | En el acondicionamiento e ingreso; ingreso_inspeccionado verdadero. |
| SEGUIMIENTO NO_HERMETICO, riesgo_activo FALSO | Inspección del grano y recipiente. | 14 días desde la última inspección completa. |
| SEGUIMIENTO NO_HERMETICO, riesgo_activo VERDADERO o DESCONOCIDO | Inspección del grano y recipiente. | 7 días. |
| SEGUIMIENTO HERMETICO, sin riesgo | Inspección exterior de barrera, cierre, plagas, daños y entorno. | 30 días. |
| SEGUIMIENTO HERMETICO, con riesgo o riesgo desconocido | Revisión exterior y evaluación técnica del indicio. | Inmediata si existe hallazgo que exige corrección o cuarentena; mientras corresponda monitoreo, máximo 7 días entre controles exteriores. |
| Cualquier modalidad | Control del almacén: ambiente, limpieza, fuentes de contaminación y estiba. | 7 días con riesgo o riesgo desconocido; 14 días sin riesgo, además de la limpieza diaria y comprobación ante incidencias. |

El control está vencido cuando fecha_evaluacion es posterior a la fecha límite; en la fecha exacta vence al final del instante autorizado y debe ejecutarse el control programado. En implementaciones que solo registren fecha, realizarlo a más tardar ese día, sin agregar otro día de gracia.

CONTROL_VIGENTE requiere todos los controles aplicables y ausencia de eventos que invaliden su contenido. Un registro inexistente no genera CONTROL_ATRASADO como si tuviera fecha conocida: genera dato pendiente y no permite autorización.

En hermético no se exige abrir rutinariamente para volver a tomar humedad u olor. Si hay motivo para revisión interna, el responsable establece la apertura controlada; luego se registran resultados, nuevo cierre y nueva evaluación. La cuarentena no se omite para preservar el sellado.

## 6. Modelo de tiempo de almacenamiento

### 6.1 Significado y tabla de referencia

vida_consumida es una **fracción acumulada de tiempo de referencia del modelo**, no una medida directa de inocuidad ni una fecha de caducidad validada para chulpi.

Se conserva la tabla numérica de cereales de NDSU utilizada en el documento original [S08]. Las temperaturas exactas de cálculo son las conversiones de 50, 60, 70 y 80 °F; los decimales de la tabla son solo de presentación.

| Humedad b.h. | 10 °C (50 °F) | 15,56 °C (60 °F) | 21,11 °C (70 °F) | 26,67 °C (80 °F) |
|---:|---:|---:|---:|---:|
| 14 % | — | — | 200 días | 140 días |
| 15 % | — | 240 días | 125 días | 70 días |
| 16 % | 230 días | 120 días | 70 días | 40 días |
| 17 % | 130 días | 75 días | 45 días | 20 días |
| 18 % | 90 días | 50 días | 30 días | 15 días |
| 19 % | 70 días | 35 días | 20 días | 10 días |
| 20 % | 50 días | 25 días | 14 días | 7 días |

Los guiones representan las celdas sin duración numérica explícita en la selección original. No significan cero días ni vida infinita.

**Selección operativa determinista:**

1. Elegir la menor fila cuya humedad sea mayor o igual que la observada; para humedades menores que 14 %, usar la fila de 14 %.
2. En esa fila, elegir la columna numérica de menor temperatura que sea mayor o igual que la observada. Se permite avanzar hacia una columna más cálida para evitar una celda sin número.
3. Si no existe fila o columna elegible, el cálculo es NO_DISPONIBLE. No recortar una temperatura alta a 26,67 °C ni una humedad alta a 20 %.
4. Registrar humedad y temperatura reales, celda utilizada y motivo de la sustitución.
5. Este procedimiento es una aproximación conservadora **dentro de la tabla elegida**; no demuestra que sus tiempos sean conservadores respecto de la biología del chulpi. Requiere calibración local.

Ejemplo: humedad 12,5 % y temperatura de referencia 10 °C seleccionan 14 % y 21,11 °C, con 200 días. Así se evita un cálculo indefinido sin inventar un valor para la celda vacía.

### 6.2 Acumulación y datos históricos

~~~text
vida_consumida =
    vida_previa_documentada
    + suma(dias_intervalo / tiempo_referencia_intervalo)

vida_proyectada =
    vida_consumida
    + dias_previstos_restantes / tiempo_referencia_actual
~~~

- Cada intervalo tiene fecha inicial/final y humedad y temperatura representativas documentadas; usar máximos observados del intervalo cuando existan varias lecturas.
- Un intervalo sin cobertura suficiente deja el total DESCONOCIDO. vida_minima_documentada suma únicamente las fracciones conocidas y la vida previa que sí esté documentada, sin duplicar periodos; es un límite inferior del modelo. Puede mostrarse, pero no autorizar usando ese subtotal como si fuese el total. Una parte desconocida no se registra como un cero observado.
- El punto de inicio debe corresponder al origen documentado del historial. En un lote con almacenamiento previo desconocido no se asigna vida_previa_documentada = 0.
- El valor cero solo es válido si existe constancia de inicio del historial de almacenamiento considerado. El tiempo previo de secado se evalúa mediante su procedimiento y no se declara inocuo por iniciar el contador.
- Secar, enfriar, trasvasar, resellar o cambiar de almacén no reinicia el acumulado.
- Una corrección de datos históricos puede modificar el resultado, con auditoría del valor anterior; una actuación física posterior no borra la fracción ya consumida.
- Si un subtotal conocido ya es >= 1, existe evidencia suficiente para R29 aunque otros intervalos sigan pendientes.

En NO_HERMETICO se utilizan mediciones del grano. Entre inspecciones, la representación de intervalos debe seguir un procedimiento de registro documentado; una lectura aislada no demuestra las condiciones de semanas anteriores.

En HERMETICO se prefieren sensores internos instalados sin apertura. Si no existen, se permite un **escenario de planificación** con humedad confirmada al sellar y temperatura igual al máximo entre la última temperatura interna válida y las máximas ambientales documentadas del intervalo. Solo se aplica con barrera íntegra, inspección exterior vigente y sin sospecha interna. Se etiqueta ESTIMACION_HERMETICA, exige monitoreo y no se presenta como temperatura interna medida. Ante señal de calentamiento, daño, pérdida de sello o registros insuficientes, deja de ser aplicable.

### 6.3 Plazo compatible y vencimiento

plazo_compatible es VERDADERO solo si:

- vida_consumida y tiempo_referencia_actual están disponibles, este último es mayor que cero y vida_proyectada < 1;
- hay una fecha de salida prevista consistente con dias_previstos_restantes;
- si clima_calido es VERDADERO y el almacenamiento es NO_HERMETICO, dias_almacenados + dias_previstos_restantes < 90;
- en humedad condicional, dias_previstos_restantes <= 30. El dictamen y demás requisitos de la rama condicional se comprueban después, en R30; no intervienen recursivamente en este cálculo.

Cuando el cálculo existe pero el plazo excede estas condiciones, solicitar reducir el plazo o reevaluar; no declarar vida ya agotada si únicamente se excede la proyección futura.

Toda autorización vence como máximo en la menor fecha entre próximo control obligatorio, salida prevista, vencimiento del dictamen aplicable y cruce estimado del límite de vida. Con vida actual < 0,80, programar también reevaluación antes de alcanzar 0,80. Los cambios relevantes invalidan la autorización antes de ese vencimiento.

## 7. R30: resolución completa de la decisión

### 7.1 Conjuntos de solicitudes

Al terminar R01–R29 y R31–R52, consolidar:

- **CUARENTENA_SOLICITADA:** R19 o episodio de cuarentena abierto.
- **SUSPENSION_SOLICITADA:** R01, R23 o R29.
- **CORRECCION_SOLICITADA:** R02 cuando obliga a secar; R04, R05, R07, R08, R09, R13, R15, R21, R22, R24, R25, R26 o R27; datos inválidos/inconsistentes; incidencias de revisión abiertas; plazo calculado incompatible; condición favorable exigible conocida como FALSA.
- **MONITOREO_SOLICITADO:** R16, R28, humedad condicional admisible o uso de ESTIMACION_HERMETICA.
- **DATOS_PENDIENTES:** comprobaciones obligatorias desconocidas, vencidas sin renovación o cálculos no disponibles.

En la ampliación, R36/R43/R46/R50/R51 se suman directamente a CUARENTENA_SOLICITADA; R52 a SUSPENSION_SOLICITADA; R31–R35, R37–R42, R44–R45, R48–R49 a CORRECCION_SOLICITADA cuando su antecedente es verdadero. R47 produce únicamente un aviso del flujo de despacho. Una falta conocida (`FALSO`) se corrige; un requisito `DESCONOCIDO` queda pendiente. Varias reglas pueden compartir la misma solicitud, pero cada causa queda registrada.

Que varias causas generen la misma solicitud no elimina ninguna causa. Se muestra una actuación principal con una lista de motivos.

La falta de un dictamen condicional, o de un plan de monitoreo requerido, produce CORRECCION_SOLICITADA para completar la revisión o el plan. La ausencia de una medición requerida produce DATOS_PENDIENTES. El usuario debe poder distinguir ambas situaciones. La expresión «condición favorable exigible» se refiere a los componentes de condiciones_comunes_aptas y a los requisitos de la rama realmente aplicable: no exige HUMEDAD_APTA_BASE a un lote que se está evaluando por la rama condicional.

### 7.2 Rama de humedad condicional

HUMEDAD_CONDICIONAL es admisible únicamente cuando se cumplen **todas** estas condiciones:

1. NO_HERMETICO, clima_calido = FALSO y dias_previstos_restantes <= 30.
2. condiciones_comunes_aptas y plazo_compatible verdaderos.
3. Dictamen técnico vigente para ese lote y ese rango de humedad, con plazo autorizado no menor que el solicitado.
4. Plan de monitoreo registrado, control como máximo cada 7 días y fecha de salida definida.

Si tipo, clima o plazo hacen inadmisible la banda, devolver CORREGIR_Y_REEVALUAR con secado hasta <= 13 %. Si faltan mediciones para evaluarla, devolver SIN_CONCLUSION_AUTOMATICA, salvo otra causa de mayor prioridad. Un dictamen favorable no anula cuarentena, suspensión, deterioro, temperatura alta u otra corrección.

### 7.3 Tabla de decisión ordenada

Evaluar de arriba hacia abajo **después de agotar la inferencia diagnóstica**. Elegir la primera fila aplicable; las filas inferiores no pueden emitir una segunda decisión.

| Orden / rama | Condición | Decisión final | Fuente(s) y base de la regla |
|---:|---|---| --- |
| R30.1 | CUARENTENA_SOLICITADA | CUARENTENA | Diseño del prototipo: rama de resolución de la sección 7. Sustento de las reglas de origen: **S02.** Servicio Nacional de Sanidad Agraria. (s. f.). *Guía sobre almacenamiento*, secciones 3.1–3.6. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf).<br>**S04.** Codex Alimentarius Commission. (2017). *Code of practice for the prevention and reduction of mycotoxin contamination in cereals* (CXC 51-2003), párrs. 37–39. [Documento oficial](https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXC+51-2003%2FCXC_051e.pdf). |
| R30.2 | SUSPENSION_SOLICITADA y fase INGRESO | BLOQUEAR_INGRESO | Diseño del prototipo: rama de resolución de la sección 7. Sustento de las reglas de origen: **S01.** Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro*, pp. 30–31. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf).<br>**S08.** North Dakota State University Extension. (s. f.). *Allowable storage time for cereal grains, malting barley and soybeans*. [Tabla de referencia](https://www.ndsu.edu/agriculture/ag-hub/allowable-storage-time-cereal-grains-malting-barley-and-soybeans).<br>**S09.** Food and Agriculture Organization of the United Nations & World Health Organization. (2026). *Standard for maize (corn)* (CXS 153-1985, enmienda 2026 según el catálogo oficial). [Registro](https://openknowledge.fao.org/handle/20.500.14283/ce0295en). [Catálogo oficial](https://www.fao.org/fao-who-codexalimentarius/codex-texts/all-standards/en/). Los porcentajes comerciales se conservan de la propuesta original; confirmar edición, métodos y aplicabilidad al tipo de chulpi antes del uso productivo. |
| R30.3 | SUSPENSION_SOLICITADA y fase SEGUIMIENTO | RETIRAR_LOTE | Diseño del prototipo: rama de resolución de la sección 7. Sustento de las reglas de origen: **S01.** Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro*, pp. 30–31. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf).<br>**S08.** North Dakota State University Extension. (s. f.). *Allowable storage time for cereal grains, malting barley and soybeans*. [Tabla de referencia](https://www.ndsu.edu/agriculture/ag-hub/allowable-storage-time-cereal-grains-malting-barley-and-soybeans).<br>**S09.** Food and Agriculture Organization of the United Nations & World Health Organization. (2026). *Standard for maize (corn)* (CXS 153-1985, enmienda 2026 según el catálogo oficial). [Registro](https://openknowledge.fao.org/handle/20.500.14283/ce0295en). [Catálogo oficial](https://www.fao.org/fao-who-codexalimentarius/codex-texts/all-standards/en/). Los porcentajes comerciales se conservan de la propuesta original; confirmar edición, métodos y aplicabilidad al tipo de chulpi antes del uso productivo. |
| R30.4 | CORRECCION_SOLICITADA | CORREGIR_Y_REEVALUAR | Diseño del prototipo: rama de resolución de la sección 7. Se basa en las comprobaciones y solicitudes de R01–R29 y R31–R52; no procede de un umbral externo único. |
| R30.5 | DATOS_PENDIENTES o requisitos_completos no es VERDADERO | SIN_CONCLUSION_AUTOMATICA | Diseño del prototipo: rama de resolución de la sección 7. Se basa en las comprobaciones y solicitudes de R01–R29 y R31–R52; no procede de un umbral externo único. |
| R30.6 | condiciones_comunes_aptas, plazo_compatible y rama condicional admisible | AUTORIZAR_CON_MONITOREO | Diseño del prototipo: rama de resolución de la sección 7. Sustento de las reglas de origen: **S01.** Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro*, pp. 30–31. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf).<br>**S03.** Food and Agriculture Organization of the United Nations. (s. f.). *Agricultural engineering in development: Storage*. [Capítulo](https://www.fao.org/4/t0522e/T0522E09.htm).<br>**S08.** North Dakota State University Extension. (s. f.). *Allowable storage time for cereal grains, malting barley and soybeans*. [Tabla de referencia](https://www.ndsu.edu/agriculture/ag-hub/allowable-storage-time-cereal-grains-malting-barley-and-soybeans). |
| R30.7 | condiciones_comunes_aptas, plazo_compatible, HUMEDAD_APTA_BASE, protección requerida satisfecha, MONITOREO_SOLICITADO y plan registrado vigente | AUTORIZAR_CON_MONITOREO | Diseño del prototipo: rama de resolución de la sección 7. Sustento de las reglas de origen: **S03.** Food and Agriculture Organization of the United Nations. (s. f.). *Agricultural engineering in development: Storage*. [Capítulo](https://www.fao.org/4/t0522e/T0522E09.htm).<br>**S06.** Purdue Extension. (2015). *A guide on the use of PICS bags* (E-265-W). [Guía](https://extension.entm.purdue.edu/publications/E-265.pdf).<br>**S08.** North Dakota State University Extension. (s. f.). *Allowable storage time for cereal grains, malting barley and soybeans*. [Tabla de referencia](https://www.ndsu.edu/agriculture/ag-hub/allowable-storage-time-cereal-grains-malting-barley-and-soybeans). |
| R30.8 | condiciones_comunes_aptas, plazo_compatible, HUMEDAD_APTA_BASE, protección requerida satisfecha y ausencia comprobada de motivos de monitoreo especial | AUTORIZAR_ALMACENAMIENTO | Diseño del prototipo: rama de resolución de la sección 7. Se basa en las comprobaciones y solicitudes de R01–R29 y R31–R52; no procede de un umbral externo único. |
| R30.9 | Cualquier otro caso | SIN_CONCLUSION_AUTOMATICA; informar la condición que impide resolver y derivar a revisión | Diseño del prototipo: rama de resolución de la sección 7. Se basa en las comprobaciones y solicitudes de R01–R29 y R31–R52; no procede de un umbral externo único. |

**Protección requerida satisfecha:** en NO_HERMETICO no se exige R12; en HERMETICO se exige PROTECCION_HERMETICA_ACTIVA. La ausencia comprobada de motivos de monitoreo requiere evaluación completa de sus causas; no se basa en que ninguna regla haya disparado por falta de información.

AUTORIZAR_ALMACENAMIENTO también mantiene controles ordinarios. AUTORIZAR_CON_MONITOREO impone el plan reforzado especificado. RETIRAR_LOTE significa suspender permanencia en las condiciones actuales y evaluar traslado/acondicionamiento o disposición técnica; no implica automáticamente desecharlo.

Si fase es desconocida y existe una suspensión, devolver CORREGIR_Y_REEVALUAR por contexto incompleto y mostrar “almacenamiento normal no permitido hasta definir la actuación”. Si existe cuarentena, esta prevalece aun con fase desconocida.

### 7.4 Contrato de salida

~~~text
id_evaluacion
id_lote / id_recipiente / id_almacen
decision_final
motivos[]: regla, observacion, valor, umbral, fuente, fecha
acciones_requeridas[]
datos_pendientes[]
estimaciones_y_sustituciones[]
fecha_proximo_control
fecha_vencimiento_autorizacion
version_base / version_parametros
~~~

No ejecutar recomendaciones incompatibles con la decisión. En cuarentena, priorizar separación y evaluación competente; una alerta AIREACION_FAVORABLE no habilita automáticamente manipular o ventilar el lote afectado.

## 8. Ciclo del motor y persistencia

1. Cargar observaciones, historial, incidencias y episodios abiertos por unidad; validar estado, fecha, ámbito y procedencia de cada dato. Crear una nueva evaluación.
2. Ejecutar R01–R26 y R31–R43, R45–R46, R48–R52 hasta punto fijo. Los identificadores indican trazabilidad, no orden de ejecución. R47 se evalúa solo en el flujo de despacho y no modifica la aptitud de almacenamiento.
3. Consolidar causas de cuarentena de R19/R36/R43/R46/R50/R51. Persistir un episodio por unidad y evento, con todas las causas; luego evaluar R44 sobre episodios abiertos. La corrección de aislamiento no cierra el episodio.
4. Calcular historial de vida, R28–R29 y riesgo_activo con hechos independientes de R27. Calcular plazos de control y R27; construir CONTROL_VIGENTE.
5. Calcular requisitos_completos, condiciones_comunes_aptas y plazo_compatible; deduplicar solicitudes por tipo conservando todos los motivos. Desconocido no equivale a falso comprobado.
6. Ejecutar R30 **una vez al final** y publicar una decisión, explicación y vigencia conjunta. Guardar la evaluación como historial; ante cambios iniciar una nueva evaluación.

El grafo de dependencias fluye de observaciones a hallazgos, episodios, cálculos y R30. Ningún resultado de R30 es antecedente de una regla diagnóstica; R44 consulta el estado persistente del episodio, no la decisión final. R47 queda fuera del grafo de almacenamiento.

**Refracción:** una activación se identifica por regla, lote, evaluación y versión de los hechos que la sustentan. No se repite sobre los mismos hechos.

**Retirada de conclusiones antiguas:** los hechos derivados pertenecen a una evaluación. No se copian como verdades a la siguiente; se reconstruyen con las observaciones aplicables. Puede implementarse reconstruyendo la memoria derivada por evaluación o mediante mantenimiento de dependencias.

**Persistencia distinta de la inferencia:** cuarentenas e incidencias abiertas son registros de seguimiento y no desaparecen al reconstruir la memoria. Se cierran mediante evidencia de resolución. Las correcciones simples se cierran al comprobar nuevamente el requisito afectado; sospechas térmicas o de plagas exigen registrar la revisión, no solo una lectura posterior normal.

No autorizar antes de completar el encadenamiento. La prioridad no es una simple preferencia visual ni permite conservar una autorización paralela. Debe existir como máximo una decisión final vigente por unidad evaluada.

## 9. Casos de aceptación para desarrollar el motor

**Caso base B:** lote chulpi en INGRESO, NO_HERMETICO, humedad confirmada 12,5 %, temperatura del grano 10 °C, almacén 10 °C y HR 50 %, clima_calido FALSO; listas físicas y sanitarias conformes; inspecciones de ingreso completas; sin incidencias; vida previa documentada 0,10; plazo restante 20 días; tiempo de referencia 200 días. Vida proyectada 0,20. Primera lectura térmica, sin comparación aplicable. Los demás datos exigibles están completos.

Cada caso modifica B, salvo que se indique otro contexto. Los resultados son **expectativas de aceptación**; no equivalen a ensayos de campo.

| Caso | Modificación o situación | Resultado esperado |
|---|---|---|
| C01 | Sin modificaciones. | AUTORIZAR_ALMACENAMIENTO. |
| C02 | Humedad confirmada = 13 %. | HUMEDAD_APTA_BASE; mismo resultado que C01. |
| C03 | Humedad = 13,5 %, dictamen vigente y plan cada 7 días. | AUTORIZAR_CON_MONITOREO. |
| C04 | Humedad = 14 %, mismas condiciones de C03. | AUTORIZAR_CON_MONITOREO; no aplicar R01. |
| C05 | Humedad confirmada = 14,01 %. | BLOQUEAR_INGRESO. |
| C06 | C05 en SEGUIMIENTO con controles vigentes. | RETIRAR_LOTE. |
| C07 | Temperatura del grano = 26 °C; ambiente 20 °C y HR 50 %. | CORREGIR_Y_REEVALUAR por R08; R30 no autoriza. |
| C08 | Humedad estimada indirectamente = 12,5 %. | CORREGIR_Y_REEVALUAR; R03 no se activa. |
| C09 | Falta equipo_humedad_verificado, sin otros hallazgos. | SIN_CONCLUSION_AUTOMATICA. |
| C10 | HERMETICO; sello íntegro y perforación de barrera verdaderos. | CORREGIR_Y_REEVALUAR; no PROTECCION_HERMETICA_ACTIVA. |
| C11 | SEGUIMIENTO HERMETICO con sensor interno válido; barrera íntegra, control exterior hace 15 días, control del local hace 5 días, sin riesgos. | No activar R27 por una supuesta inspección interna quincenal. |
| C12 | C11 con inspección exterior hace 31 días. | CORREGIR_Y_REEVALUAR por R27. |
| C13 | Moho visible verdadero, humedad favorable. | CUARENTENA. |
| C14 | Polvillo inusual verdadero y revisión pendiente. | CORREGIR_Y_REEVALUAR; no confirmar infestación automáticamente. |
| C15 | C14 con revisión CONFIRMADA. | R14 -> R19 -> CUARENTENA. |
| C16 | Vida consumida = 0,80; plazo restante 10 días, plan reforzado válido. | AUTORIZAR_CON_MONITOREO si el resto es apto. |
| C17 | Vida consumida = 1,00 o 1,20. | BLOQUEAR_INGRESO; en SEGUIMIENTO, RETIRAR_LOTE. |
| C18 | Humedad 12,5 %, temperatura 10 °C para la tabla. | Seleccionar fila 14 % y columna 21,11 °C: 200 días. |
| C19 | Temperatura válida = 30 °C. | R08 exige corrección; tiempo de tabla NO_DISPONIBLE, sin extrapolar. |
| C20 | NO_HERMETICO: humedad 12,5 %, equilibrio 11 %, HR exterior 55 %, aire 8 °C, grano 10 °C, sin lluvia. | R10 verdadera, R11 falsa. |
| C21 | C20 con humedad de equilibrio = 12,5 %. | R11 verdadera, R10 falsa. |
| C22 | C20 con aire exterior 15 °C y grano 10 °C. | R11 verdadera; no recomendar aire más caliente. |
| C23 | C20 con HERMETICO y barrera íntegra. | R10 y R11 NO_APLICA. |
| C24 | Primero humedad 12,5 %; luego nueva evaluación con 15 %. | La autorización previa deja de ser vigente; bloquear o retirar según fase. |
| C25 | Cuarentena abierta; una inspección posterior no encuentra moho, sin cierre técnico. | Mantener CUARENTENA. |
| C26 | Cuadro de moho visible y humedad 15 %, con otros datos pendientes. | CUARENTENA; conservar también la causa de suspensión. |
| C27 | NO_HERMETICO, temperatura del grano = 20 °C y plan reforzado vigente. | R16 -> AUTORIZAR_CON_MONITOREO si no existen otras causas. |
| C28 | C27 sin plan de monitoreo requerido. | CORREGIR_Y_REEVALUAR para registrar el plan. |
| C29 | Humedad 13,5 %, plazo 31 días o clima_calido VERDADERO. | CORREGIR_Y_REEVALUAR: secado hasta <= 13 %. |
| C30 | Vida 0,95, referencia 200 días y plazo restante 20 días. | Proyección 1,05: CORREGIR_Y_REEVALUAR para revisar plazo; no afirmar que la vida actual ya llegó a 1. |
| C31 | NO_HERMETICO en clima cálido, 90 días acumulados, SEGUIMIENTO. | RETIRAR_LOTE por R29, aunque el modelo de vida sea < 1. |
| C32 | Historia previa desconocida y resto favorable. | SIN_CONCLUSION_AUTOMATICA; no inicializar vida a cero. |
| C33 | HERMETICO sin sensor interno, escenario de planificación admisible y plan exterior registrado. | AUTORIZAR_CON_MONITOREO; mostrar ESTIMACION_HERMETICA. |
| C34 | Temperatura del almacén = 25 °C o HR = 60 % en NO_HERMETICO. | CORREGIR_Y_REEVALUAR. |
| C35 | HERMETICO íntegro, HR del local 65 %, temperaturas < 25 °C, resto conforme. | HR externa sola no activa R07 ni impide R06; autorizar según datos internos y necesidad de monitoreo. |
| C36 | Heces en producto o suciedad animal > 0,1 %. | R20 -> R19 -> CUARENTENA. |
| C37 | Recipiente no alimentario, fase desconocida. | CORREGIR_Y_REEVALUAR con almacenamiento no permitido hasta definir fase y corregir recipiente. |
| C38 | Nueva humedad favorable tras secado, pero vida consumida documentada = 1,10. | R29 sigue activa; el secado no reinicia el historial. |
| C39 | Dato inválido sin hallazgos sanitarios. | CORREGIR_Y_REEVALUAR para corregir el dato. |
| C40 | Plagas descartadas en un episodio anterior y aparecen insectos vivos nuevos. | R14 -> R19 -> CUARENTENA; el descarte anterior no se aplica. |

**Invariantes a comprobar durante implementación:**

- Ninguna evaluación con CUARENTENA_SOLICITADA, SUSPENSION_SOLICITADA o CORRECCION_SOLICITADA termina en autorización.
- Ninguna autorización se obtiene a partir de datos obligatorios desconocidos.
- Exactamente una decisión final por evaluación; todos los motivos se conservan.
- R10/R11 no recomiendan actuaciones opuestas para el mismo conjunto coherente de datos.
- R12 no coexiste con R13 en una evaluación válida.
- Repetir una evaluación idéntica no duplica avisos o tareas.
- Los cambios de un lote no alteran hechos de otro.
- Levantar una cuarentena exige cierre documentado.
- El encadenamiento produce el mismo resultado independientemente del orden de inserción de observaciones.

## 10. Cambios respecto de la versión original

| Problema | Resolución |
|---|---|
| Alertas sin efecto formal sobre autorización. | Solicitudes explícitas y resolución única en R30. |
| CORREGIR_Y_REEVALUAR y AUTORIZAR_CON_MONITOREO sin reglas productoras. | Ramas R30.4 y R30.6–R30.7. |
| Sospecha de plagas sin transición de confirmación. | Revisión vinculada al episodio; R15 -> revisión -> R14 -> R19. |
| Controles internos quincenales aplicables por error a herméticos. | Separación de control interno, exterior y del almacén. |
| Protección hermética compatible con datos de perforación. | Comprobación conjunta de integridad y validación de contradicciones. |
| Mezcla de aire del local y aire de ventilación. | Variables separadas para almacén y exterior. |
| Hechos positivos de R30 indefinidos. | Listas de verificación expresas, vigencia y lógica de tres estados. |
| Vida limitada artificialmente a 0–1 y celdas vacías. | Acumulado no truncado y selección determinista de una celda numérica más exigente dentro de la tabla. |
| Comparación térmica y equivalencia de aw ambiguas. | Comparación con fechas, punto y método; eliminación del sustituto aproximado de aw como antecedente automático. |
| Autorizaciones antiguas persistentes tras cambiar datos. | Evaluaciones versionadas, reconstrucción de hechos y revocación de vigencia. |
| Cuarentena eliminada al desaparecer un síntoma. | Episodios persistentes con cierre técnico. |
| Confusión entre límite comercial y seguridad del chulpi. | Identificación expresa de criterios transferidos y decisiones de diseño. |

## 11. Fuentes y validación pendiente

Las referencias se conservan para trazabilidad. Cuando se adopta una decisión de diseño adicional, se identifica como tal; la fuente no se presenta como validación de esa decisión.

- **S01.** Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro*, pp. 30–31. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf).
- **S02.** Servicio Nacional de Sanidad Agraria. (s. f.). *Guía sobre almacenamiento*, secciones 3.1–3.6. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf).
- **S03.** Food and Agriculture Organization of the United Nations. (s. f.). *Agricultural engineering in development: Storage*. [Capítulo](https://www.fao.org/4/t0522e/T0522E09.htm).
- **S04.** Codex Alimentarius Commission. (2017). *Code of practice for the prevention and reduction of mycotoxin contamination in cereals* (CXC 51-2003), párrs. 37–39. [Documento oficial](https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXC+51-2003%2FCXC_051e.pdf).
- **S05.** Food and Agriculture Organization of the United Nations. (s. f.). *Manual of the prevention of post-harvest grain losses: Central storage*, secciones 5.2.4.2–5.2.4.3. [Manual](https://www.fao.org/4/x5065e/x5065E0a.htm).
- **S06.** Purdue Extension. (2015). *A guide on the use of PICS bags* (E-265-W). [Guía](https://extension.entm.purdue.edu/publications/E-265.pdf).
- **S07.** Hellevang, K., & Proulx, R. (2026, 27 de febrero). *Proper grain storage crucial in late winter and spring*. North Dakota State University Extension. [Artículo](https://www.ag.ndsu.edu/news/newsreleases/2026/february/proper-grain-storage-crucial-in-late-winter-and-spring).
- **S08.** North Dakota State University Extension. (s. f.). *Allowable storage time for cereal grains, malting barley and soybeans*. [Tabla de referencia](https://www.ndsu.edu/agriculture/ag-hub/allowable-storage-time-cereal-grains-malting-barley-and-soybeans).
- **S09.** Food and Agriculture Organization of the United Nations & World Health Organization. (2026). *Standard for maize (corn)* (CXS 153-1985, enmienda 2026 según el catálogo oficial). [Registro](https://openknowledge.fao.org/handle/20.500.14283/ce0295en). [Catálogo oficial](https://www.fao.org/fao-who-codexalimentarius/codex-texts/all-standards/en/). Los porcentajes comerciales se conservan de la propuesta original; confirmar edición, métodos y aplicabilidad al tipo de chulpi antes del uso productivo.

**Evidencia complementaria del documento de origen:**

- Coronel-Rojas, K., Baributsa, D., Zanabria-Gálvez, S. J., Díaz-Valderrama, J. R., & Casa-Coila, V. H. (2025). Estudio de almacenamiento de maíz morado en Arequipa. *Insects, 16*(12), 1240. [Artículo por DOI](https://doi.org/10.3390/insects16121240). Es evidencia sobre otra variedad, no una calibración directa para chulpi.
- Díaz-Valderrama, J. R., et al. (2020). Postharvest practices, challenges and opportunities for grain producers in Arequipa, Peru. *PLOS ONE, 15*(11), e0240857. [Artículo](https://doi.org/10.1371/journal.pone.0240857).
- Yewle, N. R., Stroshine, R. L., Ambrose, R. P. K., & Baributsa, D. (2024). Hermetic bags: A short-term solution to preserve high-moisture maize during grain drying. *Foods, 13*(5), 760. [Artículo](https://doi.org/10.3390/foods13050760). No habilita almacenar chulpi húmedo mediante las reglas de esta versión.

**Antes de uso productivo:** validar con un especialista los límites y la calidad culinaria del chulpi; aprobar el procedimiento de muestreo y medición; seleccionar una tabla de equilibrio que cubra el clima local; calibrar el modelo de tiempo y su escenario hermético; ejecutar los casos de aceptación sobre el motor real; contrastar resultados con lotes locales y registrar falsos positivos y negativos. La versión 2.0 fue la base lógica inicial; esta propuesta 3.0 añade R31–R52 y conserva la necesidad de validación local y revisión técnica antes del uso productivo.

## 12. Ampliación de la base de conocimiento

Estas reglas conservan sus fuentes por registro y requieren revisión técnica antes de ser activadas en el motor existente. Se incorporan como propuesta, no como funcionalidad ya implementada.

### 12.1 Diccionario adicional de observaciones

| Grupo | Variables nuevas | Dominio y alcance |
|---|---|---|
| Infraestructura | filtracion_agua_almacen, drenaje_obstruido, malla_ventana_danada, abertura_ingreso_plagas, humedad_por_agua_en_unidad | Booleanos observados y fechados. La filtración del edificio no demuestra por sí misma grano mojado; `humedad_por_agua_en_unidad` requiere inspección de la unidad. |
| Entorno e higiene | agua_estancada_entorno, residuos_o_maleza_entorno, sacos_usados_o_desechos_en_almacen, residuos_de_proceso_sin_retirar | Booleanos por almacén, con ubicación y evidencia. |
| Estiba | paleta_danada_o_con_salientes, estiba_inestable, altura_supera_limite_proveedor, pasillo_inspeccion_obstruido, distancia_entre_estantes | Booleanos y metros. `distancia_entre_estantes` solo se aplica cuando hay estantes; el mínimo de S02 es 1 m. No sustituye las separaciones piso, pared y techo de R24. |
| Identidad y movimientos | identificacion_unidad_legible, registro_trazabilidad_completo, movimiento_sin_registro, contacto_con_unidad_en_cuarentena, separacion_cuarentena_verificada, derrame_grano_en_piso, grano_derramado_reincorporado | Booleanos ligados a la unidad y al evento. `registro_trazabilidad_completo` exige origen, lote, fechas de entrada/salida cuando existan, destino y responsable; fecha de vencimiento solo si corresponde. `contacto_con_unidad_en_cuarentena` exige unidad origen identificada y episodio vigente en la fecha del contacto. |
| Orden y sustancias | alimentos_olor_incompatible_en_contacto, programa_control_plagas_documentado, aplicacion_plaguicida_sin_registro_competente, exposicion_quimica_del_grano | Booleanos. Exposición química exige evidencia de contacto o afectación del grano; la mera presencia de químicos en el local sigue en R26. |
| Fecha aplicable | fecha_vencimiento_producto, fecha_actual, vencimiento_aplicable | Fecha y booleano. El vencimiento comercial del producto es distinto de la vida estimada de R29. Si no corresponde, marcar `NO_APLICA` con motivo. |

Todo dato nuevo conserva valor original, fecha, método, responsable, evidencia, estado y versión de la base. Los campos de contexto de almacén se reutilizan solo para unidades que compartieron efectivamente la condición y el intervalo; si no puede establecerse esa relación, se solicita inspección individual. `FALSO` comprobado es un incumplimiento; `DESCONOCIDO` es falta de dato. En eventos extraordinarios, un registro de inspección vigente debe confirmar la ausencia del evento: silencio del usuario no equivale a `FALSO`.

### 12.2 Reglas R31–R52

#### E. Infraestructura y entorno

| Regla | Condición SI | Hecho derivado ENTONCES | Actuación y relación con la base 2.0 | Fuentes |
|---|---|---|---|---|
| R31 | `filtracion_agua_almacen = VERDADERO` | `INFRAESTRUCTURA_CON_FILTRACION` y `CORRECCION_SOLICITADA` | Reparar y verificar estanqueidad; inspeccionar las unidades expuestas. No inferir moho ni humedad de grano sin observación. | [S02, §3.1](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf); [S05, §§5.2.3.2 y 5.2.4.3](https://www.fao.org/4/x5065e/x5065E0a.htm). **Base de diseño:** incidencia y reevaluación por unidad. |
| R32 | `drenaje_obstruido = VERDADERO` | `DRENAJE_DEFICIENTE` y `CORRECCION_SOLICITADA` | Despejar drenaje y comprobar que no entra agua. Inspeccionar unidades potencialmente afectadas; no declarar contaminación automáticamente. | [S05, §5.2.4.3](https://www.fao.org/4/x5065e/x5065E0a.htm). **Base de diseño:** corrección antes de autorizar continuidad en el almacén afectado. |
| R33 | `malla_ventana_danada = VERDADERO` o `abertura_ingreso_plagas = VERDADERO` | `BARRERA_ANTIPLAGAS_DEFICIENTE` y `CORRECCION_SOLICITADA` | Reparar la abertura e inspeccionar presencia de plagas. Activar R14 o R15 únicamente si aparecen sus evidencias propias. | [S02, §3.6.b](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf); [S05, §§5.2.3.2 y 5.2.4.3](https://www.fao.org/4/x5065e/x5065E0a.htm). **Base de diseño:** no inferir infestación de un acceso posible. |
| R34 | `agua_estancada_entorno = VERDADERO` o `residuos_o_maleza_entorno = VERDADERO` | `ENTORNO_NO_HIGIENICO` y `CORRECCION_SOLICITADA` | Limpiar y eliminar focos de agua/residuos; documentar verificación. No duplicar el control de limpieza interior R25. | [S02, §3.2.c](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf); [S05, §5.2.3.2](https://www.fao.org/4/x5065e/x5065E0a.htm). **Base de diseño:** estado separado del interior. |
| R35 | `sacos_usados_o_desechos_en_almacen = VERDADERO` o `residuos_de_proceso_sin_retirar = VERDADERO` | `MATERIAL_RESIDUAL_EN_ALMACEN` y `CORRECCION_SOLICITADA` | Retirar el material, limpiar y registrar inspección. No asumir plaga confirmada. | [S02, §3.2.e–f](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf); [S05, §5.2.3.2](https://www.fao.org/4/x5065e/x5065E0a.htm). **Base de diseño:** solicitud de reevaluación. |
| R36 | `humedad_por_agua_en_unidad = VERDADERO` | `UNIDAD_EXPUESTA_A_AGUA` y `CUARENTENA_SOLICITADA` | Aislar la unidad, medir de nuevo humedad y revisar deterioro. Abrir o mantener un episodio con la causa R36; el hallazgo no prueba micotoxinas. | [S02, §§3.1 y 3.3](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf); [S04, CXC 51-2003](https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXC+51-2003%2FCXC_051e.pdf). **Base de diseño:** cuarentena preventiva de la unidad mojada. |

#### F. Estiba y accesibilidad

| Regla | Condición SI | Hecho derivado ENTONCES | Actuación y relación con la base 2.0 | Fuentes |
|---|---|---|---|---|
| R37 | `paleta_danada_o_con_salientes = VERDADERO` | `PALETA_NO_APTA` y `CORRECCION_SOLICITADA` | Sustituir o reparar la paleta e inspeccionar si perforó un envase. R13 se activa solo si se observa daño de la barrera hermética. | [S02, §3.5](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf); [S05, §§5.2.3.2 y 5.2.4.1](https://www.fao.org/4/x5065e/x5065E0a.htm). **Base de diseño:** vinculación con R13. |
| R38 | `estiba_inestable = VERDADERO` o `altura_supera_limite_proveedor = VERDADERO` | `ESTIBA_INSEGURA` y `CORRECCION_SOLICITADA` | Reestibar y verificar estabilidad; registrar el límite del proveedor antes de comparar alturas. No inventar una altura universal. | [S02, §§3.4–3.5](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf); [S05, §5.2.4.1](https://www.fao.org/4/x5065e/x5065E0a.htm). **Base de diseño:** verificación documentada. |
| R39 | `pasillo_inspeccion_obstruido = VERDADERO` o, si hay estantes, `distancia_entre_estantes < 1,00 m` | `ACCESO_INSPECCION_INSUFICIENTE` y `CORRECCION_SOLICITADA` | Liberar acceso y medir nuevamente. Mantener R24 para distancias entre unidad, piso, pared y techo; esta regla cubre acceso entre estantes y pasillos. | [S02, §§3.4–3.5](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf); [S05, §5.2.4.1](https://www.fao.org/4/x5065e/x5065E0a.htm). **Base de diseño:** aplicación de 1 m solo a estantes. |

#### G. Trazabilidad y movimientos

| Regla | Condición SI | Hecho derivado ENTONCES | Actuación y relación con la base 2.0 | Fuentes |
|---|---|---|---|---|
| R40 | `identificacion_unidad_legible = FALSO` | `IDENTIDAD_DE_UNIDAD_NO_VERIFICABLE` y `CORRECCION_SOLICITADA` | Conciliar etiqueta, lote y registro antes de usar resultados anteriores o autorizar salida. No asignar por similitud una evaluación a otra unidad. | [S02, §§3.3 y 3.5](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf); [S05, §5.2.4.1](https://www.fao.org/4/x5065e/x5065E0a.htm). **Base de diseño:** bloqueo de reutilización de resultados por identidad incierta. |
| R41 | `registro_trazabilidad_completo = FALSO` | `TRAZABILIDAD_INCOMPLETA` y `CORRECCION_SOLICITADA` | Completar procedencia, lote, entrada, movimientos y destino aplicables. Una fecha de vencimiento ausente solo cuenta como pendiente cuando corresponde al producto. | [S02, §3.3](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf); [S05, §5.2.4.4](https://www.fao.org/4/x5065e/x5065E0a.htm). **Base de diseño:** lista mínima de campos exigibles. |
| R42 | `movimiento_sin_registro = VERDADERO` | `HISTORIAL_DE_UBICACION_INCIERTO` y `CORRECCION_SOLICITADA` | Reconstruir fecha, origen, destino y responsable; invalidar solo controles dependientes de la ubicación anterior. Si la exposición no puede reconstruirse, solicitar inspección actual. También puede activar R41, pero se consolida una sola solicitud de corrección con ambas causas. | [S02, §3.3](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf); [S05, §§5.2.3.2 y 5.2.4.4](https://www.fao.org/4/x5065e/x5065E0a.htm). **Base de diseño:** invalidación selectiva. |
| R43 | `contacto_con_unidad_en_cuarentena = VERDADERO` | `POSIBLE_CONTAMINACION_CRUZADA` y `CUARENTENA_SOLICITADA` | Abrir episodio también para la unidad expuesta y documentar contacto real, intervalo y superficie. No extender cuarentena a todo el almacén sin vínculo probado. | [S02, §3.3](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf); [S05, §5.2.3.2](https://www.fao.org/4/x5065e/x5065E0a.htm). **Base de diseño:** propagación limitada a contacto documentado. |
| R44 | Episodio de cuarentena abierto para la unidad y `separacion_cuarentena_verificada = FALSO` | `AISLAMIENTO_INSUFICIENTE` y `CORRECCION_SOLICITADA` | Separar, señalizar y registrar la verificación. Mantener cuarentena por episodio abierto; la corrección del aislamiento no cierra el episodio. La observación se comprueba después de crear el episodio, nunca como antecedente de la causa de cuarentena. | [S02, §3.3](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf); [S05, §5.2.3.2](https://www.fao.org/4/x5065e/x5065E0a.htm). **Base de diseño:** comprobación adicional sin cambiar prioridad R30. |
| R45 | `derrame_grano_en_piso = VERDADERO` | `DERRAME_DE_GRANO_REGISTRADO` y `CORRECCION_SOLICITADA` | Separar el grano derramado del lote identificado, registrar cantidad y evaluar limpieza/tamizado y aptitud técnica antes de cualquier reincorporación. El derrame no equivale automáticamente a contaminación animal. | [S02, §3.3](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf). **Base de diseño:** segregación y revisión previa. |
| R46 | `grano_derramado_reincorporado = VERDADERO` sin verificación documentada de limpieza, tamizado cuando sea posible y destino | `REINCORPORACION_NO_VERIFICADA` y `CUARENTENA_SOLICITADA` | Aislar la unidad mezclada, reconstruir la cantidad y pedir dictamen técnico. No considerar apto el grano solo porque se recogió del piso. | [S02, §3.3](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf). **Base de diseño:** cuarentena preventiva por pérdida de evidencia de aptitud. |
| R47 | Existe un lote anterior apto pendiente de salida y se programa salida de otro posterior del mismo producto sin motivo registrado | `ROTACION_NO_JUSTIFICADA` y `REVISION_DE_DESPACHO_SOLICITADA` | Revisar orden de salida y vida/fecha aplicable en el flujo de despacho. Esta alerta logística no altera la decisión de almacenamiento R30 ni el plazo sanitario de R27. No despachar el lote anterior si está en cuarentena, suspendido o vencido; un motivo válido puede justificar la excepción. | [S02, §3.3](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf); [S05, §5.2.3.2](https://www.fao.org/4/x5065e/x5065E0a.htm). **Base de diseño:** excepción registrada y revisión de despacho separada. |

#### H. Sustancias, plagas y vencimiento

| Regla | Condición SI | Hecho derivado ENTONCES | Actuación y relación con la base 2.0 | Fuentes |
|---|---|---|---|---|
| R48 | `alimentos_olor_incompatible_en_contacto = VERDADERO` | `RIESGO_TRANSFERENCIA_OLOR` y `CORRECCION_SOLICITADA` | Separar alimentos incompatibles e inspeccionar olor de la unidad. Activar R18 solo si se observa `olor_anormal` en el grano. | [S02, §3.5](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf). **Base de diseño:** separación entre riesgo de transferencia y deterioro observado. |
| R49 | `programa_control_plagas_documentado = FALSO` | `GESTION_PREVENTIVA_PLAGAS_INCOMPLETA` y `CORRECCION_SOLICITADA` | Registrar responsable, controles y prestador autorizado cuando aplique; no prescribir productos ni dosis desde el motor. No equivale a infestación confirmada. | [S02, §3.6.a](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf). **Base de diseño:** solicitud documental del prototipo. |
| R50 | `aplicacion_plaguicida_sin_registro_competente = VERDADERO` | `TRATAMIENTO_NO_VERIFICABLE` y `CUARENTENA_SOLICITADA` | Retener las unidades tratadas hasta revisar producto, responsable, dosis registrada y período de carencia aplicable. No inferir inocuidad ni recomendar consumo. | [S02, §3.6.a, c–e](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf). **Base de diseño:** cuarentena por falta de trazabilidad del tratamiento. |
| R51 | `exposicion_quimica_del_grano = VERDADERO` | `CONTACTO_QUIMICO_SOSPECHADO` y `CUARENTENA_SOLICITADA` | Segregar unidad y remitir a evaluación competente. No usar R26 como prueba de contacto: R26 cubre calidad del aire/presencia de sustancias en el almacén. | [S02, §§3.3 y 3.6.c–d](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf). **Base de diseño:** activación de R19 por exposición documentada. |
| R52 | `vencimiento_aplicable = VERDADERO` y `fecha_actual > fecha_vencimiento_producto` | `PRODUCTO_VENCIDO` y `SUSPENSION_SOLICITADA` | Bloquear ingreso o retirar de almacenamiento normal según fase; gestionar disposición mediante evaluación competente. El vencimiento comercial no se sustituye por la vida calculada de R29. | [S02, §3.3](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf). **Base de diseño:** traducción a suspensión en R30; no ordenar destrucción automática. |

### 12.3 Integración y pruebas

1. Capturar y validar hechos de la base 2.0 y de R31–R52. Ejecutar R01–R26 y R31–R43, R45–R46, R48–R52 hasta punto fijo. R47 se evalúa solo en despacho y produce aviso logístico; no participa en la aptitud del almacenamiento.
2. Consolidar las causas de cuarentena de R19, R36, R43, R46, R50 y R51 y abrir o mantener **un episodio por unidad y evento**, conservando todas las causas. Después comprobar R44 sobre ese episodio. Ninguna de estas reglas espera a R19 para transmitir su solicitud. Una corrección de R44 no cierra la cuarentena.
3. Calcular `riesgo_activo` a partir de observaciones y hallazgos independientes de R27 y R30. Incluir R31–R38, R39–R43, R45–R46, R48–R52 cuando apliquen, excepto R47 y el hecho derivado R44. Calcular luego historial/vida R28–R29, plazos de control, R27, `CONTROL_VIGENTE`, `requisitos_completos`, `condiciones_comunes_aptas` y `plazo_compatible`. Así R27 nunca determina retroactivamente su propio plazo.
4. Extender las condiciones comunes con comprobaciones aplicables de infraestructura, higiene exterior, estiba, trazabilidad, identificación y separación. Las condiciones adversas conocidas producen **una solicitud consolidada por tipo** y motivos separados; no duplicar tareas si R25/R35 o R41/R42 detectan un mismo problema. Un `FALSO` comprobado activa corrección; un requisito `DESCONOCIDO` activa `DATOS_PENDIENTES`. Una variable contextual solo se exige cuando corresponde; un evento excepcional requiere confirmación explícita de ausencia en el control aplicable.
5. Entregar a R30, **una sola vez y al final**, las solicitudes acumuladas: cuarentena R19/R36/R43/R46/R50/R51; suspensión R01/R23/R29/R52; corrección de las demás reglas aplicables; monitoreo de R16/R28 y la rama condicional original; datos pendientes de requisitos desconocidos. R30 conserva el orden CUARENTENA > SUSPENSIÓN > CORRECCIÓN > DATOS PENDIENTES > AUTORIZACIÓN. R47 no entra en ninguno de esos conjuntos.
6. Mantener vigencia de observaciones nuevas, corrección documentada, reconstrucción de hechos por evaluación y cierre técnico de cuarentenas. No añadir otra periodicidad que contradiga R27. El 1,00 m de R39 solo aplica entre estantes; las distancias de R24 permanecen intactas.
7. Añadir pruebas de prioridad y límites: filtración sin unidad mojada → corrección, no cuarentena; unidad mojada → cuarentena; malla rota sin insectos → corrección, no infestación; derrame aislado versus reincorporación no verificada; químico almacenado versus grano expuesto; vencimiento aplicable versus `NO_APLICA`; cuarentena + aislamiento corregido → cuarentena vigente hasta cierre competente; rotación injustificada → aviso de despacho sin cambiar R30.

**Casos de aceptación adicionales.** Se parte del caso base B de la versión 2.0, con los nuevos requisitos aplicables comprobados favorables. Cada fila cambia solo los hechos indicados; el motor debe conservar todas las causas aunque muestre una sola decisión.

| Caso | Variación | Resultado exigido |
|---|---|---|
| N01 | Filtración verdadera; inspección confirma unidad seca y sin deterioro. | R31 → `CORREGIR_Y_REEVALUAR`; sin cuarentena. |
| N02 | Humedad por agua observada en la unidad, aunque humedad instrumental anterior era ≤ 13 %. | R36 → `CUARENTENA`; invalidar la lectura anterior para la unidad mojada. |
| N03 | Malla rota, insectos vivos falsos e indicios falsos. | R33 → `CORREGIR_Y_REEVALUAR`; R14/R15 no disparan. |
| N04 | Identificación de unidad ilegible, pero unidad físicamente conforme. | R40 → `CORREGIR_Y_REEVALUAR`; no reutilizar evaluación ajena. |
| N05 | Movimiento sin registro y trazabilidad incompleta. | R41 y R42, una solicitud de corrección con dos motivos; controles dependientes de ubicación invalidados. |
| N06 | Unidad B contactó a unidad A durante el episodio de cuarentena de A. | R43 abre un episodio de B; `CUARENTENA` para B. Ninguna unidad C sin contacto documentado hereda esa cuarentena. |
| N07 | Episodio abierto y aislamiento sin verificar; luego aislamiento corregido. | R44 pide corrección auxiliar; la decisión permanece `CUARENTENA` hasta cierre técnico del episodio. |
| N08 | Derrame separado sin reincorporación frente a derrame reincorporado sin verificación. | Primer caso R45 → corrección; segundo R45/R46 → `CUARENTENA`. |
| N09 | Lote posterior programado primero sin justificación, condiciones de almacenamiento intactas. | R47 emite aviso de despacho; R30 conserva `AUTORIZAR_ALMACENAMIENTO`. |
| N10 | Químicos presentes en almacén sin exposición del grano frente a contacto químico documentado. | Primer caso R26 → corrección; segundo R51 → `CUARENTENA`. |
| N11 | Plaguicida aplicado sin registro competente, además de contacto químico documentado. | R50/R51 → un episodio por unidad/evento con ambas causas; una decisión `CUARENTENA`. |
| N12 | Fecha de vencimiento aplicable ya superada, fase INGRESO; después, fase SEGUIMIENTO. | R52 → `BLOQUEAR_INGRESO` y `RETIRAR_LOTE`, respectivamente. Con `NO_APLICA` justificado, R52 no dispara. |
| N13 | Falta observación obligatoria nueva, sin hallazgos adversos conocidos. | `SIN_CONCLUSION_AUTOMATICA`; ninguna ausencia se interpreta como favorable. |
| N14 | Coinciden R36, R52 y R31. | R30 elige solo `CUARENTENA`, muestra las tres causas y no activa recomendaciones incompatibles. |

### 12.4 Fuentes reutilizadas

- **S02.** Servicio Nacional de Sanidad Agraria (SENASA). *Guía sobre almacenamiento*, §§3.1–3.6. [Documento oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf).
- **S04.** Codex Alimentarius Commission. *Code of practice for the prevention and reduction of mycotoxin contamination in cereals* (CXC 51-2003). [Documento oficial](https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXC+51-2003%2FCXC_051e.pdf).
- **S05.** Food and Agriculture Organization of the United Nations. *Manual of the prevention of post-harvest grain losses: Central storage*, §§5.2.3–5.2.4. [Manual](https://www.fao.org/4/x5065e/x5065E0a.htm).

**Límite:** estas 22 reglas son candidatos lógicos derivados de apartados aún no expresados como producciones en la versión 2.0. No certifican calidad sanitaria ni aptitud para consumo. Deben ser revisadas con el responsable técnico del proyecto antes de integrarlas al catálogo ejecutable.
