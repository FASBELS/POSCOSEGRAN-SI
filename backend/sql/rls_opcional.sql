-- Seguridad a nivel de fila: DEFENSA EN PROFUNDIDAD, NO LA AUTORIZACIÓN PRINCIPAL.
--
-- La autorización real la aplica la capa de permisos de la aplicación
-- (poscosegran.seguridad.permisos), porque el pool de SQLAlchemy comparte
-- conexiones entre usuarios: una política que dependa solo de la conexión no
-- identifica a nadie por sí misma. Estas políticas leen la variable de sesión
-- 'poscosegran.id_usuario', que la aplicación fija con SET LOCAL dentro de cada
-- transacción (ver db/sesion.py). Si esa variable falta, no se ve nada.
--
-- No se aplica automáticamente en las migraciones: actívelo solo después de
-- comprobar que todas las rutas fijan la variable. Ejecutar como propietario.

ALTER TABLE poscosegran.lote ENABLE ROW LEVEL SECURITY;
ALTER TABLE poscosegran.almacen ENABLE ROW LEVEL SECURITY;
ALTER TABLE poscosegran.unidad ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION poscosegran.usuario_actual() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT NULLIF(current_setting('poscosegran.id_usuario', true), '')::uuid;
$$;

CREATE POLICY lote_propio ON poscosegran.lote
  USING (
    id_propietario = poscosegran.usuario_actual()
    OR EXISTS (
      SELECT 1 FROM poscosegran.asignacion_lote a
      WHERE a.id_lote = lote.id
        AND a.id_tecnico = poscosegran.usuario_actual()
        AND a.vigente
    )
  );

CREATE POLICY almacen_propio ON poscosegran.almacen
  USING (
    id_propietario = poscosegran.usuario_actual()
    OR EXISTS (
      SELECT 1 FROM poscosegran.asignacion_almacen a
      WHERE a.id_almacen = almacen.id
        AND a.id_tecnico = poscosegran.usuario_actual()
        AND a.vigente
    )
  );

CREATE POLICY unidad_accesible ON poscosegran.unidad
  USING (
    EXISTS (SELECT 1 FROM poscosegran.lote l WHERE l.id = unidad.id_lote)
    AND EXISTS (SELECT 1 FROM poscosegran.almacen al WHERE al.id = unidad.id_almacen)
  );

-- Para revertir:
--   DROP POLICY ... ; ALTER TABLE ... DISABLE ROW LEVEL SECURITY;
