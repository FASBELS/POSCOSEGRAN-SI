# Backend POSCOSEGRAN

FastAPI, PostgreSQL y un sistema experto con motor de inferencia genérico: el conocimiento vive en `knowledge/base_conocimiento.yaml`.

La puesta en marcha integrada y las credenciales de desarrollo están en el [README principal](../README.md). La base de conocimiento que utiliza el motor está en [`knowledge/base_conocimiento.yaml`](../knowledge/base_conocimiento.yaml); su especificación está en [`knowledge/POSCOSEGRAN_52_reglas_base_conocimiento_integrada.md`](../knowledge/POSCOSEGRAN_52_reglas_base_conocimiento_integrada.md).

Con el backend en ejecución, la API interactiva está disponible en `/documentacion`.

Las migraciones se ejecutan mediante Alembic con credencial separada. La API nunca crea tablas al arrancar.
