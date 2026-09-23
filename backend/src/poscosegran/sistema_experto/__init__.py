"""Sistema experto POSCOSEGRAN, organizado según su arquitectura clásica.

    base_conocimiento  Representación del conocimiento: reglas, parámetros,
                       tablas y resolución, leídos de un archivo versionado.
    base_hechos        Hechos del caso: observaciones iniciales y hechos
                       inferidos durante la evaluación.
    lenguaje           Evaluador del lenguaje de condiciones, en lógica de
                       tres estados.
    calculos           Procedimientos de cálculo que las reglas invocan por
                       nombre, configurados desde la base de conocimiento.
    motor              Motor de inferencia genérico: encadenamiento hacia
                       adelante por etapas y resolución por prioridad.
    explicacion        Módulo de explicación: cómo, por qué no y por qué se
                       pregunta.
    adquisicion        Módulo de adquisición: propuesta, validación e impacto
                       de nuevas versiones de la base de conocimiento.

El motor no contiene ningún umbral, regla ni prioridad del dominio.
"""
