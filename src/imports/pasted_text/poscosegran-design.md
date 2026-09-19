Actúa como Diseñador UX/UI Principal y Motion Designer especializado en dashboards modernos de Next.js y aplicaciones agroindustriales accesibles (WCAG AA).

Diseña la interfaz de usuario completa y definitiva del SISTEMA FINAL PRODUCTIVO "POSCOSEGRAN", una plataforma web profesional construida bajo los patrones de arquitectura visual de Next.js (App Router), React, Tailwind CSS y componentes tipo shadcn/ui, orientada a la gestión y evaluación del almacenamiento poscosecha de maíz chulpi en el sur del Perú.

IMPORTANTE: Diseña el SISTEMA FINAL TERMINADO. Muestra datos reales, acabados pulidos y estado productivo. No incluyas avisos de "modo demo", "mock", "sin backend" ni alertas de simulación.

SISTEMA DE DISEÑO, TOKENS Y MOTION (Next.js + shadcn/ui + Framer Motion / GSAP):
- Layout base: Arquitectura típica de Next.js App Router con Sidebar lateral colapsable, Topbar global y área de contenido modular.
- Paleta cromática:
  * Fondo general: Marfil cálido (#FBF9F4) para mitigar fatiga visual en campo.
  * Superficies y Cards: Blanco puro (#FFFFFF) con bordes delgados de 1px (#E2DDD5).
  * Color Primario de Marca: Verde bosque profundo (#1B3B2B) para navegación activa y botones primarios.
  * Color de Acento: Amarillo Maíz Chulpi (#E5A93C) para estados activos, indicadores de foco y badges secundarios.
  * Estados semánticos (con Icono + Texto): Autorizado/Vigente (#2E7D32), Monitoreo/Observación (#ED6C02), Cuarentena/Crítico (#D32F2F), Informativo (#0288D1).
- Tipografía y ergonomía táctil: Inter o Roboto. Tamaño base 16px. Todos los controles interactivos (botones, inputs, conmutadores) con altura táctil mínima de 44px.
- Pautas de Motion (Framer Motion / GSAP): Microinteracciones táctiles en botones (scale 0.98 al click), transiciones suaves con easing en el stepper del wizard, animación fluida en barras de progreso y acordeones desplegables suaves.

DISTRIBUCIÓN DEL LIENZO (Genera en formato Desktop 1440px los siguientes 5 módulos continuos y coherentes):

1. LAYOUT GLOBAL NEXT.JS Y DASHBOARD PRINCIPAL (/dashboard):
- Sidebar lateral: Logo "POSCOSEGRAN", navegación con iconos (Inicio, Evaluaciones, Unidades/Lotes, Seguimiento, Base de Conocimiento R01–R30, Configuración).
- Topbar: Selector de rol activo en pastilla [PRODUCTOR | TÉCNICO | ADMINISTRADOR], reloj en zona "America/Lima", notificaciones y perfil de usuario.
- Fila de 4 KPI Cards:
  * "Unidades en Almacén" (18 lotes registrados)
  * "Controles Próximos (7 días)" (3 alertas ámbar pendientes)
  * "Lotes Autorizados" (14 vigentes en verde)
  * "Lotes en Cuarentena" (1 crítico en rojo terracota)
- Botón principal de acción en verde profundo: "+ Evaluar Nueva Unidad".
- Tabla de Monitoreo: Columnas para Código de Lote, Tipo de Recipiente (Bolsa PICS / Silo metálico), Humedad actual (12.5% b.h.), Última Inspección, Estado de Vigencia (Badges: "VIGENTE", "POR VENCER", "CUARENTENA") y Botón de acción rápida.

2. WIZARD DE EVALUACIÓN GUIADA PASO A PASO (/evaluar/[id]):
- Stepper horizontal animado con 6 pasos: P1 Identificación, P2 Mediciones, P3 Inspección Biológica, P4 Recipiente y Almacén, P5 Historial y Plan, P6 Revisión Final.
- Controles de formulario especializados:
  * Inputs numéricos con unidad visible integrada: Humedad del grano ("12.8 % b.h."), Temperatura del grano ("18.5 °C"), Humedad relativa del almacén ("55 % HR"). Compatibilidad visual para punto o coma.
  * Selector segmentado tri-estado horizontal obligatorio para síntomas: [ Sí ] [ No ] [ No se sabe ] (diseño neutro en gris claro, ninguno preseleccionado) para: "Moho visible", "Insectos vivos/gorgojos", "Granos perforados" y "Heces de roedores/aves".
  * Tarjetas de selección con icono para Recipiente: "Bolsa Hermética PICS", "Silo Metálico", "Costal Tradicional".
  * Callout informativo con borde ámbar: "Almacenamiento Hermético PICS verificado: No requiere apertura rutinaria para muestreo interno".
  * Barra de acciones fija al pie: Botón "Guardar borrador" (outline) y botón "Continuar a Inspección" (verde primario).

3. PANTALLA DE RESULTADO Y DICTAMEN TÉCNICO EXPLICABLE (/evaluaciones/[id]/resultado):
- Hero Banner de Decisión: Card destacada con badge de estado oficial ("ESTADO: CUARENTENA PREVENTIVA" en rojo terracota o "AUTORIZADO CON MONITOREO" en ámbar), con fecha y técnico asignado.
- Barra de Cálculo Temporal: "Vida de referencia consumida: 45 de 180 días (25% acumulado)", con nota explicativa: "Fracción del modelo de referencia NDSU, no constituye porcentaje de inocuidad".
- Panel de Explicabilidad en 3 Bloques:
  * "Motivos del Dictamen": Valores medidos vs umbrales seguros (ej. "Humedad registrada 14.8% supera límite base de 13.0% b.h.").
  * "Reglas de Inferencia Activadas": Badges de reglas con cita a fuentes oficiales ([R01 Límite de Humedad - SENASA S01], [R18 Deterioro Fúngico - Codex Alimentarius S04], [Resolución R30.1]).
  * "Acciones Correctivas Obligatorias": Lista numerada de tareas para el productor (1. Aislar inmediatamente el lote, 2. Solicitar inspección técnica formal, 3. Prohibir mezcla con grano sano).
- Acciones secundarias: Botones para "Exportar Dictamen en PDF" y "Programar Próximo Control".

4. TIMELINE DE SEGUIMIENTO HISTÓRICO INMUTABLE (/seguimiento/[id]):
- Línea de tiempo vertical con nodos cronológicos detallando:
  * Evento de Ingreso y sellado hermético documentado.
  * Inspección quincenal de control exterior completada.
  * Registro de Incidencia técnica por aumento térmico (+2 °C detectados).
  * Dictamen de Resolución emitido y firmado por el Técnico de zona.

5. CATÁLOGO DEL SISTEMA EXPERTO Y BASE DE CONOCIMIENTO (/conocimiento):
- Buscador y filtros por categoría: Humedad, Ambiente, Plagas, Hermeticidad, Calidad Física.
- Tarjetas interactivas para las 30 Reglas del Sistema (R01 a R29 y Ramas de Decisión R30.1 a R30.9). Cada tarjeta despliega: Condición SI (Antecedente), Consecuente ENTONCES, Fundamento Técnico y Referencia Oficial (SENASA BPA S01/S02, FAO S03/S05/S09, Codex Alimentarius S04, Purdue University PICS S06, NDSU S07/S08).

Aplica Auto-Layout estricto en todos los componentes, espaciados regulares en escala de 8px (8, 16, 24, 32px), sombras sutiles y diseño de alto contraste con estética profesional de Next.js.