# Backend POSCOSEGRAN

FastAPI, PostgreSQL y un sistema experto con motor de inferencia genérico: el conocimiento vive en `knowledge/base_conocimiento.yaml`.

La puesta en marcha integrada y las credenciales de desarrollo se documentan en [README principal](../README.md).

- [Arquitectura](../docs/ARQUITECTURA.md)
- [API](../docs/API.md)
- [Pruebas ejecutadas](../docs/PRUEBAS.md)
- [Arquitectura del sistema experto](../docs/ARQUITECTURA_SE.md)
- [Motor](../docs/MOTOR.md)
- [Instalacion y despliegue](../docs/INSTALACION_DESPLIEGUE.md)

Las migraciones se ejecutan mediante Alembic con credencial separada. La API nunca crea tablas al arrancar.
