-- Ejecutar DESPUES de alembic upgrade head como propietario/administrador.
GRANT USAGE ON SCHEMA poscosegran TO poscosegran_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA poscosegran TO poscosegran_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA poscosegran TO poscosegran_app;
GRANT DELETE ON poscosegran.borrador, poscosegran.idempotencia TO poscosegran_app;
REVOKE INSERT, UPDATE ON poscosegran.usuario, poscosegran.usuario_rol,
  poscosegran.asignacion_lote, poscosegran.asignacion_almacen,
  poscosegran.version_conocimiento, poscosegran.regla, poscosegran.fuente
  FROM poscosegran_app;
