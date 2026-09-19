# Motor de inferencia

Etapa 7. Encadenamiento hacia adelante sobre la base 2.0, determinista y sin
estado compartido entre evaluaciones.

## Forma

El motor es una función pura: recibe una `Instantanea` y devuelve un
`Resultado`. No abre la base de datos ni el reloj del sistema. Eso permite
ejecutar los 40 casos de aceptación sin PostgreSQL y garantiza que el resultado
dependa solo de los hechos declarados, no del orden en que llegaron.

```
poscosegran/dominio/
  valores.py         lógica de tres estados y acceso a datos
  campos.py          campos capturables con su tipo, unidad y paso
  parametros.py      parámetros de la sección 3.1
  tablas.py          tabla de tiempo y selección determinista
  comprobaciones.py  hechos favorables explícitos de la sección 3.2
  reglas.py          R01–R26 declarativas
  tiempo.py          vida consumida, proyección y plazo compatible
  resolucion.py      riesgo, plazos de control, R27–R29
  motor.py           ciclo de la sección 8 y tabla R30
  catalogo.py        fuentes y naturaleza del fundamento por regla
```

No hay `eval` ni un lenguaje de reglas propio: cada antecedente es código Python
que se lee junto a su fila de la sección 4.

## Lógica de tres estados

`VERDADERO`, `FALSO`, `DESCONOCIDO` y `NO_APLICA`. En una conjunción un falso
basta para obtener falso; si no hay falsos y falta información, el resultado es
desconocido. Negar un desconocido devuelve desconocido.

Esa aritmética es lo que impide el error que la versión 1.0 cometía: un dato que
no se tomó nunca se lee como condición favorable. `Tri.__bool__` lanza
`TypeError` a propósito, para que un `if comprobacion:` distraído no convierta un
desconocido en verdadero.

## Ciclo

1. Validar: unidades, dominios, fechas no futuras y contradicciones de la sección
   2.3. Un dato fuera de dominio se conserva como inválido, produce corrección y
   no participa en comparaciones.
2. Construir las comprobaciones auxiliares: `medicion_confirmada`,
   `integridad_hermetica_verificada` y la temperatura aplicable.
3. Ejecutar R01–R26 hasta punto fijo. El recorrido se repite completo para que un
   hecho tardío active una regla ya evaluada: es lo que permite que R20 dispare
   R19 aunque R19 se haya evaluado antes. Si en una pasada no aparece ningún
   hallazgo nuevo, termina; si no converge en doce pasadas, falla en voz alta en
   lugar de devolver un resultado a medias.
4. Calcular el historial de vida y aplicar R28–R29, después el riesgo activo.
5. Calcular los plazos de control de la sección 5 y aplicar R27.
6. Consolidar las cinco solicitudes de la sección 7.1.
7. Resolver R30 una sola vez con la tabla ordenada.

La refracción funciona por hallazgo: registrar dos veces el mismo hecho no
duplica motivos ni tareas.

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
