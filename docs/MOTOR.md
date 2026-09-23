# Motor de inferencia

Encadenamiento hacia adelante sobre la base 2.0, determinista y sin estado
compartido entre evaluaciones. Motor 0.8.0: genérico, con la base como datos.

## Forma

Desde la versión 0.8.0 el motor es **genérico**: no contiene reglas, umbrales ni
prioridades del dominio. Interpreta la base de conocimiento que recibe. La
arquitectura completa, con el diagrama de componentes, está en
[`ARQUITECTURA_SE.md`](ARQUITECTURA_SE.md).

```
knowledge/
  base_conocimiento.yaml  reglas SI–ENTONCES, parámetros, definiciones, tabla,
                          datos exigibles, resolución R30 y restricciones
  catalogo.yaml           texto documental de cada regla (transcrito del documento 2.0)
  casos_referencia.json   242 casos congelados: regresión e impacto de cambios

poscosegran/sistema_experto/
  base_conocimiento.py    carga, validación, consulta y huella de la base
  base_hechos.py          hechos iniciales, hechos inferidos y traza
  lenguaje.py             evaluador de condiciones en lógica de tres estados
  calculos.py             procedimientos invocables: tiempo, tabla, plazos, fechas
  motor.py                ciclo reconocer–actuar y resolución por prioridad
  explicacion.py          ¿cómo?, ¿por qué no?, ¿por qué se pide?
  adquisicion.py          propuesta, validación e impacto de nuevas versiones
  serializacion.py        hechos iniciales a JSON y de vuelta

poscosegran/dominio/
  valores.py, campos.py, hechos.py   tipos del dominio y lógica de tres estados
  motor.py                           punto de entrada: evaluar(instantánea, base)
```

El motor es una función pura: recibe una `Instantanea` y una `BaseConocimiento` y
devuelve un `Resultado`. No abre la base de datos ni el reloj del sistema. En
producción el servicio pasa la versión activa guardada en la base de datos; en las
pruebas se usa la de los archivos de `knowledge/`.

No hay `eval`: el lenguaje de condiciones es cerrado y cada operador tiene una
implementación explícita.

## Lógica de tres estados

`VERDADERO`, `FALSO`, `DESCONOCIDO` y `NO_APLICA`. En una conjunción un falso
basta para obtener falso; si no hay falsos y falta información, el resultado es
desconocido. Negar un desconocido devuelve desconocido.

Esa aritmética es lo que impide el error que la versión 1.0 cometía: un dato que
no se tomó nunca se lee como condición favorable. `Tri.__bool__` lanza
`TypeError` a propósito, para que un `if comprobacion:` distraído no convierta un
desconocido en verdadero.

## Ciclo

Las etapas se declaran en la base (`etapas:`); el motor las recorre en orden:

1. **Validación.** Datos inválidos o vencidos, contradicciones de la sección 2.3 y
   las detectadas al consolidar el historial.
2. **Encadenamiento.** R01–R26 hasta punto fijo. Un hecho tardío activa una regla
   ya evaluada: R20 dispara R19 en la pasada siguiente.
3. **Tiempo.** Vida consumida y proyectada, R29 y después R28.
4. **Control.** Plazos de la sección 5, acortados con riesgo activo o desconocido, y R27.
5. **Consolidación.** Solicitudes de la sección 7.1: plazo incompatible, estimación
   hermética, banda condicional, incidencias abiertas, plan de monitoreo ausente,
   fase desconocida con suspensión.

Después se calculan los datos exigibles que siguen desconocidos y se resuelve R30
una sola vez.

**Refracción.** Cada regla de producción se dispara como mucho una vez por
evaluación. Toda pasada que no alcanza el punto fijo dispara al menos una regla
nueva, así que cada etapa termina en, como mucho, tantas pasadas como reglas tiene.

**Traza.** Cada disparo registra orden, etapa, pasada, regla, conclusión,
solicitudes y soportes: las condiciones concretas que lo hicieron verdadero. El
módulo de explicación la usa para responder "¿cómo?".

## Decisión

R30 recorre las nueve ramas de arriba abajo y se queda con la primera aplicable.
Las filas inferiores no emiten una segunda decisión, pero **todos los motivos se
conservan**: la prioridad determina la actuación principal, no borra las causas.
Un lote con moho y humedad de 15 % devuelve `CUARENTENA` y sigue mostrando la
causa de suspensión.

Dos reglas de contexto que no están en la tabla pero sí en el texto de la
sección 7.3: con la fase sin definir y una suspensión pendiente se devuelve
`CORREGIR_Y_REEVALUAR`, y una cuarentena prevalece aunque la fase se desconozca.

## Tiempo

`vida_consumida` es una fracción acumulada del tiempo de referencia del modelo.
No es inocuidad ni fecha de caducidad, y la interfaz no debe presentarla como
un porcentaje de seguridad.

Un tramo del historial sin condiciones documentadas deja el total desconocido.
`vida_minima_documentada` suma solo lo conocido y sirve como límite inferior: se
muestra, pero no autoriza. Un lote con pasado desconocido no arranca en cero.

La selección de celda sigue el procedimiento de la sección 6.1: fila de humedad
mayor o igual a la observada, columna de temperatura mayor o igual, avanzando a
una columna más cálida si la celda no tiene duración publicada. Fuera de la
tabla el cálculo queda no disponible: no se recorta una lectura de 30 °C a
26,67 °C ni se interpola entre celdas. Toda sustitución se declara en
`estimaciones_y_sustituciones`.

En hermético sin sensor interno se permite el escenario de planificación de la
sección 6.2, etiquetado `ESTIMACION_HERMETICA`. Exige barrera íntegra, control
exterior vigente y plan de monitoreo, y nunca se presenta como una medición
interna recién tomada.

## Casos de aceptación

`tests/casos/test_aceptacion.py` implementa C01–C40 sobre el caso base B, más
las invariantes de la sección 9. **Se ejecutaron y pasan los 65 asertos**, con el
intérprete disponible en el entorno de construcción. La revisión integrada
posterior también ejecutó PostgreSQL, HTTP y navegador: consultar
[PRUEBAS.md](PRUEBAS.md) para los resultados actuales y sus límites.

Un caso mereció una lectura atenta: C35 dice "autorizar según datos internos".
Sin sensor interno declarado, el motor aplica el escenario de planificación y
pide plan de monitoreo, así que el caso solo se cumple cuando el recipiente
tiene sensor. El comportamiento del motor es el que pide la sección 6.2; lo que
había que precisar era el supuesto del caso.
