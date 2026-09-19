# POSCOSEGRAN: propuesta de 30 reglas para la base de conocimiento

**Fecha de investigación:** 8 de septiembre de 2026  
**Ámbito:** almacenamiento poscosecha de maíz chulpi seco por pequeños productores de la sierra sur del Perú  
**Propósito:** servir como especificación inicial, trazable y verificable para un prototipo de sistema experto con encadenamiento hacia adelante.

## 1. Respuesta ejecutiva

Las reglas siguientes forman una base de conocimiento conectada. Los datos del lote y del almacén ingresan como hechos iniciales; varias reglas producen hechos intermedios, y estos activan conclusiones terminales como `AUTORIZAR_ALMACENAMIENTO`, `BLOQUEAR_INGRESO`, `CUARENTENA` o `RETIRAR_LOTE`.

La investigación no encontró umbrales de almacenamiento validados específicamente para maíz chulpi. Por ello, los límites numéricos se transfieren de evidencia oficial o experimental sobre maíz en general, maíz amarillo duro o maíz morado peruano. Esta transferencia es técnicamente razonable para un prototipo, pero debe validarse con un especialista y con lotes locales de chulpi antes de convertirla en una recomendación productiva definitiva.

Se adopta una política conservadora:

- `13 %` de humedad en base húmeda es el objetivo general para almacenamiento prolongado.
- Más de `14 %` bloquea el ingreso al almacenamiento normal del prototipo.
- El `15,5 %` del Codex es un máximo de calidad comercial del maíz para consumo; no se usa como límite de almacenamiento seguro.
- Temperatura del almacén menor de `25 °C` y humedad relativa menor de `60 %` constituyen la condición ambiental base recomendada por SENASA para maíz amarillo duro.
- La aireación se decide por equilibrio higroscópico y solo se aplica a sistemas no herméticos.
- Un recipiente hermético debe permanecer sellado; abrirlo o ventilarlo elimina la condición que controla los insectos.

## 2. Modelo de inferencia propuesto

### 2.1 Hechos iniciales mínimos

| Grupo | Variables sugeridas | Tipo / unidad |
|---|---|---|
| Identificación | `id_lote`, `fecha_ingreso`, `procedencia`, `variedad`, `uso_final` | texto / fecha |
| Grano | `humedad_grano`, `actividad_agua`, `temperatura_grano`, `temperatura_grano_previa`, `metodo_humedad`, `temperatura_muestra` | %, aw, °C, categoría |
| Ambiente | `temperatura_ambiente`, `hr_ambiente`, `lluvia_o_niebla`, `humedad_equilibrio_maiz` | °C, %, booleano, % |
| Almacenamiento | `tipo_almacenamiento`, `sello_integro`, `bolsa_abierta`, `perforacion_recipiente`, `cierre_seguro`, `dias_almacenados`, `plazo_previsto`, `clima_calido` | categoría / booleano / días |
| Plagas y deterioro | `insectos_vivos`, `granos_perforados`, `polvillo`, `signos_roedores_aves`, `moho_visible`, `olor_anormal`, `condensacion`, `germinacion` | booleanos |
| Calidad física | `suciedad_origen_animal`, `heces_visibles`, `granos_defectuosos`, `granos_enfermos`, `granos_quebrados`, `materia_organica_extrana`, `materia_inorganica_extrana` | % masa / booleano |
| Recipiente y local | `recipiente_limpio`, `recipiente_seco`, `material_grado_alimentario`, `recipiente_resistente`, `distancia_piso`, `distancia_pared`, `distancia_techo` | booleanos / m |
| Higiene y control | `dias_desde_limpieza_general`, `limpieza_previa_nuevo_lote`, `limpieza_diaria`, `polvo_humo_gases_vapores`, `quimicos_combustibles_en_almacen`, `dias_desde_inspeccion`, `nivel_riesgo`, `inspeccion_exterior_pendiente` | días / categorías / booleanos |
| Tiempo seguro | `vida_consumida`, `tiempo_seguro_tabla` | fracción 0–1 / días |

Todos los hechos negativos deben registrarse expresamente, por ejemplo `insectos_vivos = FALSO`. La ausencia de un dato no debe interpretarse como una condición segura.

### 2.2 Conclusiones terminales y prioridad

Cuando se disparen varias reglas, el motor debe aplicar esta prioridad:

1. `CUARENTENA` por contaminación, plagas o deterioro.
2. `BLOQUEAR_INGRESO` o `RETIRAR_LOTE` por humedad, vida agotada o estructura no apta.
3. `CORREGIR_Y_REEVALUAR` por ventilación, limpieza, estiba o medición insuficiente.
4. `AUTORIZAR_CON_MONITOREO`.
5. `AUTORIZAR_ALMACENAMIENTO`.

Entre reglas de igual prioridad se recomienda: regla más específica, luego mayor severidad y finalmente primera regla registrada. Debe aplicarse **refracción**: una regla no vuelve a dispararse mientras no cambie alguno de sus antecedentes.

Si ninguna conclusión terminal se dispara —por ejemplo, cuando la humedad queda en la banda condicional de 13–14 % y faltan datos para calcular el tiempo seguro— el sistema debe devolver `SIN_CONCLUSION_AUTOMATICA`, solicitar los hechos faltantes y derivar a revisión experta. Nunca debe autorizar por omisión.

## 3. Base de conocimiento: 30 reglas

### A. Humedad y aptitud inicial del lote

| ID | Regla SI–ENTONCES | Variables | Umbral | Acción esperada del sistema | Justificación y aplicabilidad a chulpi | Fuente principal en APA 7 + URL |
|---|---|---|---|---|---|---|
| R01 | **SI** `humedad_grano > 14` **ENTONCES** `HUMEDAD_NO_APTA` y `BLOQUEAR_INGRESO`. | `humedad_grano` | `> 14 % b.h.` | Bloquear el almacenamiento normal; indicar secado, nueva medición y reevaluación. | SENASA fija 14 % como máximo de calidad para maíz amarillo duro y recomienda recogerlo con 12–13 %. Se usa 14 % como límite conservador de admisión. Es transferido a chulpi y requiere validación varietal. | Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro* (pp. 30–31). [PDF oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf). |
| R02 | **SI** `13 < humedad_grano ≤ 14` **ENTONCES** `HUMEDAD_CONDICIONAL`. | `humedad_grano`, `plazo_previsto`, `clima_calido` | Banda `>13 %` y `≤14 %` | No emitir autorización plena; calcular el tiempo seguro y solicitar revisión experta para almacenamiento corto. Para plazo prolongado o clima cálido, ordenar secado hasta `≤13 %`. | La banda cumple el máximo local de calidad, pero supera el objetivo conservador de almacenamiento prolongado. Evita tratar un valor comercialmente aceptable como universalmente seguro. | Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro* (pp. 30–31). [PDF oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf). |
| R03 | **SI** `humedad_grano ≤ 13` **Y** `medicion_confirmada = VERDADERO` **ENTONCES** `HUMEDAD_APTA_BASE`. | `humedad_grano`, `medicion_confirmada` | `≤13 % b.h.` | Registrar condición favorable; continuar evaluando ambiente, plagas, recipiente y tiempo. | Coincide con el rango 12–13 % recomendado por SENASA y con el valor conservador de FAO para maíz en almacenamiento prolongado en regiones cálidas. No autoriza por sí solo. | Food and Agriculture Organization of the United Nations. (s. f.). *Agricultural engineering in development: Storage*. [Capítulo de almacenamiento](https://www.fao.org/4/t0522e/T0522E09.htm). |
| R04 | **SI** `actividad_agua ≥ 0.70` **O**, si no se mide aw, `temperatura_grano ≈ 25 °C` **Y** `humedad_grano ≥ 14.2` **ENTONCES** `RIESGO_FUNGICO_HIDRICO`. | `actividad_agua`, `temperatura_grano`, `humedad_grano` | `aw ≥0.70`; aproximación para maíz a 25 °C: `14.2 %` corresponde a aw `0.70` | Generar alerta de mohos; bloquear almacenamiento prolongado y pedir secado o análisis. | Codex indica que el crecimiento fúngico se inhibe por debajo de aw 0,70. El 14,2 % es una equivalencia orientativa a 25 °C y cambia con variedad, tamaño del grano, calidad y temperatura; en chulpi debe calibrarse. | Codex Alimentarius Commission. (2017). *Code of practice for the prevention and reduction of mycotoxin contamination in cereals* (CXC 51-2003, párrs. 37–39). [PDF FAO/WHO](https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXC+51-2003%2FCXC_051e.pdf). |
| R05 | **SI** `metodo_humedad = ESTIMACION_INDIRECTA` **O** `temperatura_muestra < 4.4 °C` **ENTONCES** `MEDICION_HUMEDAD_NO_CONFIRMADA`. | `metodo_humedad`, `temperatura_muestra` | Medición indirecta; muestra `<4.4 °C` (`40 °F`) | Pedir una medición independiente; si la muestra está fría, templarla en una bolsa sellada antes de medir. No autorizar con un dato no confirmado. | NDSU advierte diferencias de 1,0–1,5 puntos porcentuales en estimaciones indirectas y lecturas inexactas de muestras frías. Es muy pertinente en zonas altoandinas. | Hellevang, K., & Proulx, R. (2026, 27 de febrero). *Proper grain storage crucial in late winter and spring*. North Dakota State University Extension. [Artículo](https://www.ag.ndsu.edu/news/newsreleases/2026/february/proper-grain-storage-crucial-in-late-winter-and-spring). |

### B. Ambiente de conservación y aireación

| ID | Regla SI–ENTONCES | Variables | Umbral | Acción esperada del sistema | Justificación y aplicabilidad a chulpi | Fuente principal en APA 7 + URL |
|---|---|---|---|---|---|---|
| R06 | **SI** `temperatura_ambiente < 25` **Y** `hr_ambiente < 60` **ENTONCES** `AMBIENTE_BASE_APTO`. | `temperatura_ambiente`, `hr_ambiente` | `<25 °C` y `<60 % HR` | Registrar ambiente favorable; continuar con las demás comprobaciones. | Son las condiciones óptimas publicadas por SENASA para maíz amarillo duro. Se adoptan como referencia inicial para chulpi, sin afirmar equivalencia varietal absoluta. | Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro* (p. 31). [PDF oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf). |
| R07 | **SI** `hr_ambiente ≥ 60` **Y** `tipo_almacenamiento = NO_HERMETICO` **ENTONCES** `RIESGO_REHUMEDECIMIENTO`. | `hr_ambiente`, `tipo_almacenamiento` | `≥60 % HR` | Emitir alerta; impedir una autorización plena y evaluar cierre o ventilación controlada mediante R10–R11. | SENASA exige menos de 60 % para evitar mohos. En sacos permeables el grano intercambia humedad con el aire. Para chulpi seco, el rehumedecimiento puede comprometer estabilidad y calidad para cancha. | Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro* (p. 31). [PDF oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf). |
| R08 | **SI** `temperatura_ambiente ≥ 25` **O** `temperatura_grano ≥ 25` **ENTONCES** `RIESGO_TERMICO`. | `temperatura_ambiente`, `temperatura_grano` | `≥25 °C` | Aumentar frecuencia de inspección, recalcular tiempo seguro y recomendar enfriamiento pasivo o aireación favorable si corresponde. | SENASA recomienda menos de 25 °C. El calor acelera respiración, insectos y deterioro; la respuesta depende de humedad y tipo de recipiente. | Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro* (p. 31). [PDF oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf). |
| R09 | **SI** `temperatura_grano - temperatura_grano_previa ≥ 2` **ENTONCES** `PUNTO_CALIENTE_SOSPECHADO`. | `temperatura_grano`, `temperatura_grano_previa`, `horas_entre_lecturas` | Aumento `≥2 °C`; Codex señala `2–3 °C` | Generar alerta prioritaria; solicitar muestreo en varios puntos y búsqueda de insectos, humedad y moho. | Un aumento de 2–3 °C puede indicar actividad microbiana o insectos. No diagnostica la causa; dispara inspección. Aplicable a cualquier maíz, incluido chulpi. | Codex Alimentarius Commission. (2017). *Code of practice for the prevention and reduction of mycotoxin contamination in cereals* (CXC 51-2003, párr. 39). [PDF FAO/WHO](https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXC+51-2003%2FCXC_051e.pdf). |
| R10 | **SI** `tipo_almacenamiento = NO_HERMETICO` **Y** `humedad_grano > humedad_equilibrio_maiz` **Y** `hr_ambiente < 70` **Y** `lluvia_o_niebla = FALSO` **ENTONCES** `AIREACION_FAVORABLE`. | `tipo_almacenamiento`, `humedad_grano`, `humedad_equilibrio_maiz`, `hr_ambiente`, `lluvia_o_niebla` | Humedad real mayor que la humedad de equilibrio; aire exterior seco | Recomendar abrir ventilación o accionar el sistema disponible; registrar inicio y comprobar después la humedad. | El aire puede secar el grano cuando su humedad de equilibrio es menor que la humedad actual. La tabla de equilibrio debe configurarse para maíz y temperatura. Es transferible a chulpi con calibración. | Food and Agriculture Organization of the United Nations. (s. f.). *Manual of the prevention of post-harvest grain losses: Central storage* (sección 5.2.4.2). [Manual FAO](https://www.fao.org/4/x5065e/x5065E0a.htm). |
| R11 | **SI** `tipo_almacenamiento = NO_HERMETICO` **Y** (`humedad_grano ≤ humedad_equilibrio_maiz` **O** `hr_ambiente ≥ 70` **O** `lluvia_o_niebla = VERDADERO`) **ENTONCES** `AIREACION_DESFAVORABLE`. | Mismas variables de R10 | Aire capaz de rehumedecer; `HR ≥70 %`; lluvia o niebla | Recomendar cerrar aberturas o detener ventilación; volver a evaluar cuando cambie el aire exterior. | Ventilar con aire húmedo puede aumentar condensación y actividad de agua. La regla evita que “airear” sea una recomendación automática. | Food and Agriculture Organization of the United Nations. (s. f.). *Manual of the prevention of post-harvest grain losses: Central storage* (sección 5.2.4.2). [Manual FAO](https://www.fao.org/4/x5065e/x5065E0a.htm). |
| R12 | **SI** `tipo_almacenamiento = HERMETICO` **Y** `humedad_grano ≤ 13` **Y** `sello_integro = VERDADERO` **ENTONCES** `PROTECCION_HERMETICA_ACTIVA`. | `tipo_almacenamiento`, `humedad_grano`, `sello_integro` | `≤13 %`; sello íntegro | Ordenar mantener el recipiente cerrado, sin aireación; programar inspección exterior mensual. | PICS requiere grano seco y sellado. Un ensayo de nueve meses en Arequipa con maíz morado mostró menos de 1 % de pérdida de peso en PICS frente a cerca de 20 % en polipropileno; es evidencia peruana cercana, pero no específica de chulpi. | Purdue Extension. (2015). *A guide on the use of PICS bags* (E-265-W). [PDF](https://extension.entm.purdue.edu/publications/E-265.pdf). Evidencia peruana complementaria: Coronel-Rojas, K., Baributsa, D., Zanabria-Gálvez, S. J., Díaz-Valderrama, J. R., & Casa-Coila, V. H. (2025). *Insects, 16*(12), 1240. [https://doi.org/10.3390/insects16121240](https://doi.org/10.3390/insects16121240). |
| R13 | **SI** `tipo_almacenamiento = HERMETICO` **Y** (`sello_integro = FALSO` **O** `perforacion_recipiente = VERDADERO` **O** `bolsa_abierta_sin_resellar = VERDADERO`) **ENTONCES** `HERMETICIDAD_COMPROMETIDA`. | `sello_integro`, `perforacion_recipiente`, `bolsa_abierta_sin_resellar` | Cualquier daño o cierre incompleto | Bloquear la condición “hermética”; reparar de forma compatible o trasvasar a un recipiente apto. Si se abrió para retirar grano, expulsar aire y resellar inmediatamente. | La eficacia depende de conservar la barrera. La inspección mensual y el resellado inmediato son prácticas operativas de PICS. Directamente útil para pequeños productores de chulpi. | Purdue Extension. (2015). *A guide on the use of PICS bags* (E-265-W). [PDF](https://extension.entm.purdue.edu/publications/E-265.pdf). |

### C. Plagas, deterioro y cuarentena

| ID | Regla SI–ENTONCES | Variables | Umbral | Acción esperada del sistema | Justificación y aplicabilidad a chulpi | Fuente principal en APA 7 + URL |
|---|---|---|---|---|---|---|
| R14 | **SI** `insectos_vivos = VERDADERO` **ENTONCES** `INFESTACION_CONFIRMADA`. | `insectos_vivos` | Presencia de al menos un insecto vivo en la muestra o inspección | Emitir alerta de plagas y activar R19. No identificar especie ni prescribir plaguicida. | Codex exige maíz libre de insectos vivos. La presencia es una evidencia observable y compatible con el alcance manual del prototipo. | Food and Agriculture Organization of the United Nations & World Health Organization. (2026). *Standard for maize (corn)* (CXS 153-1985, amended 2026). [Documento oficial](https://openknowledge.fao.org/handle/20.500.14283/ce0295en). |
| R15 | **SI** `granos_perforados = VERDADERO` **O** `polvillo_inusual = VERDADERO` **O** `exuvias_larvas = VERDADERO` **O** `ruido_alimentacion = VERDADERO` **ENTONCES** `INFESTACION_SOSPECHADA`. | Indicadores visuales y auditivos | Cualquier indicio presente | Aumentar muestreo, inspeccionar costuras y grietas y activar R19 si se confirma daño del lote. | Varias plagas se desarrollan dentro del grano y pueden no observarse como adultos. Es aplicable a chulpi sin requerir reconocimiento taxonómico. | Food and Agriculture Organization of the United Nations. (s. f.). *Manual of the prevention of post-harvest grain losses: Central storage* (sección 5.2.4.3). [Manual FAO](https://www.fao.org/4/x5065e/x5065E0a.htm). |
| R16 | **SI** `tipo_almacenamiento = NO_HERMETICO` **Y** `15 ≤ temperatura_grano ≤ 35` **ENTONCES** `AMBIENTE_FAVORABLE_A_INSECTOS`. | `tipo_almacenamiento`, `temperatura_grano` | `15–35 °C` | Elevar frecuencia de inspección y priorizar medidas físicas: secado, limpieza, enfriamiento apropiado o almacenamiento hermético. | FAO señala que los insectos de productos almacenados pueden vivir y reproducirse aproximadamente entre 15 y 35 °C. Es una regla de riesgo, no prueba de infestación. | Food and Agriculture Organization of the United Nations. (s. f.). *Agricultural engineering in development: Storage*. [Capítulo de almacenamiento](https://www.fao.org/4/t0522e/T0522E09.htm). |
| R17 | **SI** `heces_roedores_aves = VERDADERO` **O** `huellas = VERDADERO` **O** `bolsa_roida = VERDADERO` **O** `grano_derramado_por_plaga = VERDADERO` **ENTONCES** `CONTAMINACION_BIOLOGICA_SOSPECHADA`. | Signos de roedores y aves | Cualquier signo presente | Aislar los recipientes afectados, inspeccionar el entorno, impedir mezcla y activar R19. | Roedores y aves dañan envases y contaminan el grano. SENASA exige prevención y FAO recomienda buscar estos rastros. Aplicación directa a chulpi. | Servicio Nacional de Sanidad Agraria. (s. f.). *Guía sobre almacenamiento* (secciones 3.2–3.5). [PDF oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf). |
| R18 | **SI** `moho_visible = VERDADERO` **O** `olor_mohoso_anormal = VERDADERO` **O** `condensacion = VERDADERO` **O** `germinacion = VERDADERO` **ENTONCES** `DETERIORO_SOSPECHADO`. | Indicadores sensoriales y visuales | Cualquier indicador presente | Bloquear consumo y almacenamiento normal; activar R19 y recomendar evaluación técnica o análisis de micotoxinas cuando corresponda. | El olor puede aparecer antes que los cambios visibles. El sistema no declara que el lote sea inocuo ni cuantifica micotoxinas; detecta una condición que exige separación. | Codex Alimentarius Commission. (2017). *Code of practice for the prevention and reduction of mycotoxin contamination in cereals* (CXC 51-2003, párrs. 38–39). [PDF FAO/WHO](https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXC+51-2003%2FCXC_051e.pdf). |
| R19 | **SI** `INFESTACION_CONFIRMADA` **O** `CONTAMINACION_BIOLOGICA_SOSPECHADA` **O** `CONTAMINACION_BIOLOGICA_CONFIRMADA` **O** `DETERIORO_SOSPECHADO` **ENTONCES** `CUARENTENA`. | Hechos derivados de R14, R17, R18 y R20 | Al menos uno verdadero | Separar físicamente el lote, prohibir mezcla con grano sano, conservar trazabilidad y remitir a responsable técnico. | Codex indica separar las porciones aparentemente afectadas y evitar mezclarlas, porque una pequeña cantidad contaminada puede comprometer el resto. Es una conclusión terminal de máxima prioridad. | Codex Alimentarius Commission. (2017). *Code of practice for the prevention and reduction of mycotoxin contamination in cereals* (CXC 51-2003, párr. 39). [PDF FAO/WHO](https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXC+51-2003%2FCXC_051e.pdf). |

### D. Calidad física, recipiente, estiba e higiene

| ID | Regla SI–ENTONCES | Variables | Umbral | Acción esperada del sistema | Justificación y aplicabilidad a chulpi | Fuente principal en APA 7 + URL |
|---|---|---|---|---|---|---|
| R20 | **SI** `suciedad_origen_animal > 0.1` **O** `heces_visibles = VERDADERO` **ENTONCES** `CONTAMINACION_BIOLOGICA_CONFIRMADA`. | `suciedad_origen_animal`, `heces_visibles` | `>0.1 % m/m` o presencia fecal visible | Activar R19; impedir autorización para consumo directo y derivar a evaluación sanitaria. | Codex fija 0,1 % como máximo de suciedad de origen animal; SENASA pide separar mazorcas con restos fecales. El límite Codex cubre maíz dentado o cristalino y debe validarse para la clasificación comercial de chulpi. | Food and Agriculture Organization of the United Nations & World Health Organization. (2026). *Standard for maize (corn)* (CXS 153-1985, amended 2026). [Documento oficial](https://openknowledge.fao.org/handle/20.500.14283/ce0295en). |
| R21 | **SI** `granos_defectuosos > 7` **O** `granos_enfermos > 0.5` **ENTONCES** `LOTE_NO_CONFORME_POR_DEFECTOS`. | `granos_defectuosos`, `granos_enfermos` | Defectuosos `>7 %`; enfermos `>0.5 %` | Separar, registrar no conformidad y solicitar evaluación antes del almacenamiento o uso. | Los defectos favorecen deterioro y reducen calidad. Son límites comerciales Codex, no umbrales chulpi validados; deben usarse como cribado provisional. | Food and Agriculture Organization of the United Nations & World Health Organization. (2026). *Standard for maize (corn)* (CXS 153-1985, amended 2026). [Documento oficial](https://openknowledge.fao.org/handle/20.500.14283/ce0295en). |
| R22 | **SI** `granos_quebrados > 6` **O** `materia_organica_extrana > 1.5` **O** `materia_inorganica_extrana > 0.5` **ENTONCES** `LOTE_REQUIERE_LIMPIEZA_Y_CLASIFICACION`. | Porcentajes de quebrados y materias extrañas | `6 %`, `1.5 %` y `0.5 % m/m`, respectivamente | Impedir autorización; limpiar o clasificar y volver a medir. Si no puede corregirse, separar el lote. | Quebrados, polvo y materias extrañas crean refugios y dificultan el flujo de aire. Los límites son Codex para maíz comercial y constituyen una referencia provisional para chulpi. | Food and Agriculture Organization of the United Nations & World Health Organization. (2026). *Standard for maize (corn)* (CXS 153-1985, amended 2026). [Documento oficial](https://openknowledge.fao.org/handle/20.500.14283/ce0295en). |
| R23 | **SI** `recipiente_limpio = FALSO` **O** `recipiente_seco = FALSO` **O** `material_grado_alimentario = FALSO` **O** `recipiente_resistente = FALSO` **O** `cierre_seguro = FALSO` **ENTONCES** `RECIPIENTE_NO_APTO`. | Condición y material del recipiente | Cualquier requisito incumplido | Bloquear llenado; limpiar, secar, reparar o reemplazar. | Codex exige sacos limpios, secos, resistentes y de material no tóxico; el envase no debe transmitir olor o sabor. Es directamente aplicable a chulpi destinado a cancha. | Food and Agriculture Organization of the United Nations & World Health Organization. (2026). *Standard for maize (corn)* (CXS 153-1985, sección 6). [Documento oficial](https://openknowledge.fao.org/handle/20.500.14283/ce0295en). |
| R24 | **SI** `distancia_piso < 0.15` **O** `distancia_pared < 0.50` **O** `distancia_techo < 1.00` **ENTONCES** `ESTIBA_NO_APTA`. | `distancia_piso`, `distancia_pared`, `distancia_techo` | Piso `<0.15 m`; pared/columna `<0.50 m`; techo/viga `<1.00 m` | Pedir reubicar la estiba antes de autorizar; mantener pasillos de inspección. | Las separaciones facilitan limpieza, aireación e inspección y reducen humedad y acceso de plagas. Son requisitos nacionales para alimentos agropecuarios almacenados. | Servicio Nacional de Sanidad Agraria. (s. f.). *Guía sobre almacenamiento* (sección 3.5). [PDF oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf). |
| R25 | **SI** `dias_desde_limpieza_general > 30` **O** (`nuevo_lote = VERDADERO` **Y** `limpieza_previa_nuevo_lote = FALSO`) **O** `limpieza_diaria = FALSO` **ENTONCES** `ALMACEN_NO_HIGIENICO`. | Registro de limpieza | General al menos mensual; antes de nuevo lote; área de trabajo diaria | Bloquear ingreso o movimiento del lote hasta limpiar y registrar la actividad. | SENASA exige limpieza general mensual, limpieza con el almacén vacío antes de una nueva carga y limpieza diaria del área de trabajo. Aplicación directa. | Servicio Nacional de Sanidad Agraria. (s. f.). *Guía sobre almacenamiento* (sección 3.2). [PDF oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf). |
| R26 | **SI** `polvo_humo_gases_vapores = VERDADERO` **O** `quimicos_combustibles_en_almacen = VERDADERO` **ENTONCES** `CALIDAD_AIRE_INADECUADA`. | Observación de contaminantes y almacenamiento incompatible | Cualquier presencia | Bloquear ingreso; retirar la fuente, ventilar el local vacío cuando proceda y reevaluar antes de almacenar alimento. | El prototipo puede evaluar calidad del aire con una lista de observación, sin sensores de gases. SENASA exige reducir polvo, fibras, humo, gases y vapores y mantener químicos y combustibles fuera del almacén. | Servicio Nacional de Sanidad Agraria. (s. f.). *Guía sobre almacenamiento* (secciones 3.1–3.2). [PDF oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2014/12/GUIA-ALMACENAMIENTO.pdf). |

### E. Seguimiento, tiempo seguro y decisión final

| ID | Regla SI–ENTONCES | Variables | Umbral | Acción esperada del sistema | Justificación y aplicabilidad a chulpi | Fuente principal en APA 7 + URL |
|---|---|---|---|---|---|---|
| R27 | **SI** (`riesgo_activo = VERDADERO` **Y** `dias_desde_inspeccion > 7`) **O** (`riesgo_activo = FALSO` **Y** `dias_desde_inspeccion > 14`) **O** (`tipo_almacenamiento = HERMETICO` **Y** `dias_desde_inspeccion_exterior > 30`) **ENTONCES** `CONTROL_ATRASADO`. | Fechas de inspección y estado de riesgo | 7 días con riesgo; 14 días normal; 30 días para exterior de PICS | Crear tarea de inspección; suspender autorización automática hasta registrar temperatura, humedad, plagas, olor y estado del recipiente. | FAO recomienda muestreo semanal o quincenal; Purdue indica inspección exterior mensual de PICS. En chulpi, la periodicidad debe ajustarse tras el piloto. | Food and Agriculture Organization of the United Nations. (s. f.). *Manual of the prevention of post-harvest grain losses: Central storage* (sección 5.2.4.3). [Manual FAO](https://www.fao.org/4/x5065e/x5065E0a.htm). |
| R28 | **SI** `0.80 ≤ vida_consumida < 1.00` **ENTONCES** `VIDA_SEGURA_PROXIMA_AL_LIMITE`. | `vida_consumida` | `80–<100 %` | Emitir alerta preventiva; aumentar inspección y planificar uso, acondicionamiento o retiro. | El tiempo permisible depende conjuntamente de humedad y temperatura y es acumulativo. El 80 % es un punto de decisión conservador diseñado para el sistema, no un umbral biológico publicado. | North Dakota State University Extension. (s. f.). *Allowable storage time for cereal grains, malting barley and soybeans*. Recuperado el 8 de septiembre de 2026 de [NDSU Agriculture](https://www.ndsu.edu/agriculture/ag-hub/allowable-storage-time-cereal-grains-malting-barley-and-soybeans). |
| R29 | **SI** `vida_consumida ≥ 1.00` **O** (`clima_calido = VERDADERO` **Y** `tipo_almacenamiento = NO_HERMETICO` **Y** `dias_almacenados ≥ 90`) **ENTONCES** `RETIRAR_LOTE`. | `vida_consumida`, `clima_calido`, `tipo_almacenamiento`, `dias_almacenados` | `≥100 %` de vida estimada; o `≥90 días` en clima cálido no hermético | Emitir alerta crítica; suspender continuidad, inspeccionar y priorizar uso o salida según evaluación técnica. | NDSU trata la vida como acumulativa; SENASA recomienda no superar tres meses en climas cálidos. Para chulpi de sierra, `clima_calido` debe configurarse por zona, no inferirse solo por calendario. | Servicio Nacional de Sanidad Agraria. (2020). *Guía para la implementación de buenas prácticas agrícolas para el cultivo de maíz amarillo duro* (p. 31). [PDF oficial](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf). |
| R30 | **SI** `HUMEDAD_APTA_BASE` **Y** `AMBIENTE_BASE_APTO` **Y** `RECIPIENTE_APTO` **Y** `ESTIBA_APTA` **Y** `ALMACEN_HIGIENICO` **Y** `CALIDAD_AIRE_ADECUADA` **Y** `CALIDAD_FISICA_CONFORME` **Y** `SIN_EVIDENCIA_DE_PLAGAS` **Y** `CONTROL_VIGENTE` **Y** `vida_consumida < 0.80` **ENTONCES** `AUTORIZAR_ALMACENAMIENTO`. | Hechos derivados y confirmaciones explícitas | Todos los antecedentes verdaderos | Autorizar y mostrar la explicación completa: hechos usados, reglas disparadas, umbral de cada regla, fuente y próxima fecha de control. | Es la conclusión terminal favorable. Exigir todos los antecedentes evita que la ausencia de datos se interprete como seguridad. La autorización sigue siendo provisional hasta validar la base con especialista y casos reales de chulpi. | Síntesis basada en Codex Alimentarius Commission. (2017). *CXC 51-2003* [PDF](https://www.fao.org/fao-who-codexalimentarius/sh-proxy/en/?lnk=1&url=https%3A%2F%2Fworkspace.fao.org%2Fsites%2Fcodex%2FStandards%2FCXC+51-2003%2FCXC_051e.pdf) y Servicio Nacional de Sanidad Agraria. (2020). *Guía BPA para maíz amarillo duro* [PDF](https://www.senasa.gob.pe/senasa/descargasarchivos/2020/07/Guia-BPA-MAIZ-AMARILLO-DURO.pdf). |

## 4. Cálculo de la vida de almacenamiento

La variable `vida_consumida` debe sumar la fracción gastada en cada intervalo entre mediciones:

```text
vida_consumida = Σ (dias_del_intervalo / tiempo_seguro_tabla[humedad, temperatura])
```

Ejemplo: si un lote permanece 20 días en una condición cuyo tiempo permisible es 100 días, consume `0.20`. Si luego pasa 30 días en una condición cuyo tiempo permisible es 60 días, consume `0.50` adicional; el total es `0.70`.

La tabla actual de NDSU es aproximada, está construida para cereales comerciales y no ha sido validada para chulpi. Para el prototipo se debe seleccionar de forma conservadora la fila de humedad igual o inmediatamente superior y la columna de temperatura igual o inmediatamente superior. Algunos puntos publicados para cereal/maíz son:

| Humedad | 10 °C | 15.6 °C | 21.1 °C | 26.7 °C |
|---:|---:|---:|---:|---:|
| 14 % | sin valor numérico | sin valor numérico | 200 días | 140 días |
| 15 % | sin valor numérico | 240 días | 125 días | 70 días |
| 16 % | 230 días | 120 días | 70 días | 40 días |
| 17 % | 130 días | 75 días | 45 días | 20 días |
| 18 % | 90 días | 50 días | 30 días | 15 días |
| 19 % | 70 días | 35 días | 20 días | 10 días |
| 20 % | 50 días | 25 días | 14 días | 7 días |

Estos valores apoyan alertas y priorización; no reemplazan la validación local. La aireación puede mantener o reducir temperatura, pero no reinicia el tiempo de vida ya consumido.

## 5. Encadenamientos de ejemplo

### Caso 1: lote húmedo

```text
humedad_grano = 14.8 %
→ R01 dispara HUMEDAD_NO_APTA
→ conclusión terminal: BLOQUEAR_INGRESO
```

### Caso 2: indicios de deterioro

```text
olor_mohoso_anormal = VERDADERO
→ R18 dispara DETERIORO_SOSPECHADO
→ R19 dispara CUARENTENA
```

### Caso 3: aireación correcta

```text
tipo_almacenamiento = NO_HERMETICO
humedad_grano > humedad_equilibrio_maiz
hr_ambiente < 70 %
lluvia_o_niebla = FALSO
→ R10 dispara AIREACION_FAVORABLE
```

### Caso 4: almacenamiento hermético

```text
tipo_almacenamiento = HERMETICO
humedad_grano = 12.5 %
sello_integro = VERDADERO
→ R12 dispara PROTECCION_HERMETICA_ACTIVA
→ mantener sellado; no ejecutar R10 ni R11
```

## 6. Reglas de implementación

- Cada medición debe guardar valor, unidad, fecha, método y responsable.
- Los porcentajes de humedad se registran en base húmeda (`% b.h.`).
- Los hechos positivos usados por R30 (`RECIPIENTE_APTO`, `ESTIBA_APTA`, `ALMACEN_HIGIENICO`, `CALIDAD_AIRE_ADECUADA`, `CALIDAD_FISICA_CONFORME`, `SIN_EVIDENCIA_DE_PLAGAS` y `CONTROL_VIGENTE`) solo se insertan tras completar sus listas de comprobación. No se deducen por la mera ausencia de una alerta.
- Las reglas R10 y R11 requieren una tabla de humedad de equilibrio para maíz por temperatura y HR; no debe usarse una constante única.
- Las reglas de aireación no se ejecutan sobre recipientes herméticos cerrados.
- Las reglas R20–R22 son cribados de calidad comercial. No sustituyen un análisis de inocuidad.
- El sistema no debe recomendar ingredientes activos ni dosis de plaguicidas. Ante infestación, deriva a personal autorizado y conserva la trazabilidad.
- `clima_calido` debe ser un parámetro territorial validado por un especialista; no debe deducirse solamente de una lectura aislada.
- Toda conclusión debe mostrar una explicación del tipo: “Se disparó R09 porque la temperatura aumentó 2,4 °C; Codex indica que un aumento de 2–3 °C puede señalar actividad microbiana o de insectos”.

## 7. Validación propuesta

Antes de usar las reglas en campo:

1. Revisar los 30 antecedentes y consecuentes con un especialista en poscosecha de granos.
2. Confirmar con INIA, SENASA o un laboratorio universitario los límites de humedad y calidad específicos para chulpi destinado a cancha.
3. Ejecutar casos de prueba con valores frontera: 13 %, 14 %, 25 °C, 60 % HR, aumento térmico de 2 °C y 80/100 % de vida consumida.
4. Comparar las conclusiones del sistema con el especialista y registrar acuerdo, falso positivo, falso negativo y regla causante.
5. Ajustar umbrales mediante configuración, sin modificar el motor de inferencia.

## 8. Limitaciones y desacuerdos de la evidencia

- No se localizó un estándar abierto que establezca límites poscosecha exclusivos para maíz chulpi.
- El máximo Codex de 15,5 % corresponde a calidad del maíz para consumo y permite límites menores según clima y duración. SENASA publica 14 % como máximo de calidad para maíz amarillo duro y 12–13 % tras secado. Por eso el prototipo usa el criterio nacional más conservador.
- Los tiempos de NDSU proceden de condiciones y cultivos comerciales distintos de la sierra peruana. Se usan para modelar el carácter acumulativo del riesgo y deben recalibrarse.
- El estudio peruano de bolsas PICS evaluó maíz morado, no chulpi. Sustenta la tecnología hermética en Arequipa, pero no prueba que conserve todas las propiedades de expansión o textura de la cancha chulpi.
- El olor, el moho visible y los insectos permiten clasificar riesgo, pero no demuestran ausencia o concentración de micotoxinas. Un lote sospechoso requiere evaluación competente.

## 9. Referencias complementarias

- Díaz-Valderrama, J. R., Njoroge, A. W., Macedo-Valdivia, D., Orihuela-Ordóñez, N., Smith, B. W., Casa-Coila, V. H., Ramírez-Calderón, N., Zanabria-Gálvez, S. J., Woloshuk, C., & Baributsa, D. (2020). Postharvest practices, challenges and opportunities for grain producers in Arequipa, Peru. *PLOS ONE, 15*(11), e0240857. [https://doi.org/10.1371/journal.pone.0240857](https://doi.org/10.1371/journal.pone.0240857).
- Ileleji, K. (2020, 13 de abril). *Managing grain in the spring*. Purdue University Extension. [https://extension.purdue.edu/news/2020/04/Managing-Grain-in-the-Spring.html](https://extension.purdue.edu/news/2020/04/Managing-Grain-in-the-Spring.html).
- Yewle, N. R., Stroshine, R. L., Ambrose, R. P. K., & Baributsa, D. (2024). Hermetic bags: A short-term solution to preserve high-moisture maize during grain drying. *Foods, 13*(5), 760. [https://doi.org/10.3390/foods13050760](https://doi.org/10.3390/foods13050760).

## 10. Criterio de cierre de la investigación

Se detuvo la búsqueda cuando los factores principales —humedad, temperatura, HR, aireación, plagas, hermeticidad, deterioro, higiene, calidad física, monitoreo y tiempo— quedaron respaldados por una fuente oficial o por evidencia científica abierta, y cuando las diferencias entre límite comercial, límite de almacenamiento y aplicabilidad a chulpi quedaron explícitamente delimitadas. Nuevas búsquedas generales aportaban fuentes repetidas sin resolver la brecha varietal; esa brecha requiere validación experimental o experta local.
