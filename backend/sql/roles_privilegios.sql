-- Roles de base de datos para POSCOSEGRAN.
-- Se ejecuta una vez, con un superusuario, antes de la primera migración.
-- Sustituya las contraseñas por valores generados; no las guarde en el repositorio.

-- 1. Rol de migraciones: dueño del esquema, con privilegios DDL.
CREATE ROLE poscosegran_migraciones LOGIN PASSWORD 'CAMBIAR_MIGRACIONES';

-- 2. Rol de aplicación: lee y escribe datos, nunca altera la estructura.
CREATE ROLE poscosegran_app LOGIN PASSWORD 'CAMBIAR_APP';

-- 3. Esquema privado. No se expone a través de ninguna Data API.
CREATE SCHEMA IF NOT EXISTS poscosegran AUTHORIZATION poscosegran_migraciones;

-- 4. Nadie obtiene permisos por defecto.
REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA poscosegran FROM PUBLIC;
REVOKE ALL ON DATABASE poscosegran FROM PUBLIC;
GRANT CONNECT ON DATABASE poscosegran TO poscosegran_app, poscosegran_migraciones;

-- 5. La aplicación entra al esquema pero no crea objetos en él.
GRANT USAGE ON SCHEMA poscosegran TO poscosegran_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA poscosegran TO poscosegran_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA poscosegran TO poscosegran_app;

-- DELETE se concede solo donde la aplicación lo necesita: borradores caducados
-- y claves de idempotencia vencidas. El historial no se borra nunca.
-- Las tablas aún no existen: ejecutar permisos_aplicacion.sql tras migrar.

-- 6. Las tablas futuras heredan el mismo criterio.
ALTER DEFAULT PRIVILEGES FOR ROLE poscosegran_migraciones IN SCHEMA poscosegran
  GRANT SELECT, INSERT, UPDATE ON TABLES TO poscosegran_app;
ALTER DEFAULT PRIVILEGES FOR ROLE poscosegran_migraciones IN SCHEMA poscosegran
  GRANT USAGE, SELECT ON SEQUENCES TO poscosegran_app;

-- 7. Comprobación rápida de que la aplicación no puede crear tablas:
--    SET ROLE poscosegran_app;
--    CREATE TABLE poscosegran.prueba (id int);  -- debe fallar con 42501
--    RESET ROLE;
