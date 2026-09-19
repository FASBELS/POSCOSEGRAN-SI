"""Crea configuración y datos de desarrollo sin sobrescribir un entorno existente."""
import argparse
import os
import secrets
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from poscosegran.api.local import USUARIOS
from poscosegran.db.modelos import Usuario, UsuarioRol
from poscosegran.config import obtener_configuracion
from poscosegran.conocimiento.cargar import cargar

BACKEND = Path(__file__).resolve().parents[1]
os.chdir(BACKEND)
analizador = argparse.ArgumentParser(description=__doc__)
analizador.add_argument(
    "--contenedor",
    action="store_true",
    help="Usa solo variables del contenedor y no escribe archivos del host.",
)
argumentos = analizador.parse_args()
archivo = BACKEND / ".env"
if not argumentos.contenedor and not archivo.exists():
    archivo.write_text(
        "POSCOSEGRAN_ENTORNO=local\n"
        "POSCOSEGRAN_BD_URL_APP=postgresql+psycopg://poscosegran_app:local_app_2026@127.0.0.1:55432/poscosegran\n"
        "POSCOSEGRAN_BD_URL_MIGRACIONES=postgresql+psycopg://poscosegran_migraciones:local_migraciones_2026@127.0.0.1:55432/poscosegran\n"
        "POSCOSEGRAN_JWT_MODO=SECRETO_COMPARTIDO\nPOSCOSEGRAN_JWT_ALGORITMOS=HS256\n"
        f"POSCOSEGRAN_JWT_SECRETO={secrets.token_urlsafe(48)}\n"
        "POSCOSEGRAN_JWT_EMISOR=http://localhost/auth/v1\n"
        "POSCOSEGRAN_AUTH_LOCAL_HABILITADA=true\n"
        f"POSCOSEGRAN_AUTH_LOCAL_PASSWORD={secrets.token_urlsafe(16)}\n"
        "POSCOSEGRAN_CORS_ORIGENES=http://localhost:8443,http://127.0.0.1:8443\n"
        "POSCOSEGRAN_LIMITE_PETICIONES_POR_MINUTO=1000\n"
        "POSCOSEGRAN_LIMITE_PETICIONES_ESCRITURA_POR_MINUTO=300\n", encoding="utf-8")
if archivo.exists():
    load_dotenv(archivo)
if os.environ.get("POSCOSEGRAN_ENTORNO") != "local":
    raise SystemExit("Este script solo prepara el entorno local")
admin = create_engine(os.environ.get("POSCOSEGRAN_BD_URL_ADMIN_LOCAL",
    "postgresql+psycopg://postgres:revision_local_2026@127.0.0.1:55432/poscosegran"))
with admin.begin() as conn:
    for rol, password in (("poscosegran_app", "local_app_2026"),
                          ("poscosegran_migraciones", "local_migraciones_2026")):
        if not conn.scalar(text("SELECT 1 FROM pg_roles WHERE rolname=:rol"), {"rol": rol}):
            conn.exec_driver_sql(f"CREATE ROLE {rol} LOGIN PASSWORD '{password}'")
    conn.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS poscosegran AUTHORIZATION poscosegran_migraciones")
    conn.exec_driver_sql("GRANT CONNECT ON DATABASE poscosegran TO poscosegran_app, poscosegran_migraciones")
    conn.exec_driver_sql("GRANT USAGE ON SCHEMA poscosegran TO poscosegran_app")
    conn.exec_driver_sql("ALTER DEFAULT PRIVILEGES FOR ROLE poscosegran_migraciones IN SCHEMA poscosegran GRANT SELECT, INSERT, UPDATE ON TABLES TO poscosegran_app")
subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
with Session(admin) as db, db.begin():
    for nombre, identificador in USUARIOS.items():
        if db.get(Usuario, identificador) is None:
            db.add(Usuario(id=identificador, nombre=f"{nombre.capitalize()} local"))
            db.flush()
            db.add(UsuarioRol(id_usuario=identificador, rol=nombre.upper(), otorgado_por="preparar_local.py"))
# Carga administrativa: la API solo necesita leer el catálogo.
os.environ["POSCOSEGRAN_BD_URL_APP"] = str(admin.url.render_as_string(hide_password=False))
obtener_configuracion.cache_clear()
print(cargar(BACKEND.parent / "knowledge/catalogo.yaml", activar=True, notas="Desarrollo local"))
with admin.begin() as conn:
    conn.exec_driver_sql("GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA poscosegran TO poscosegran_app")
    conn.exec_driver_sql("GRANT DELETE ON poscosegran.borrador, poscosegran.idempotencia TO poscosegran_app")
    conn.exec_driver_sql("REVOKE INSERT, UPDATE ON poscosegran.usuario, poscosegran.usuario_rol, poscosegran.asignacion_lote, poscosegran.asignacion_almacen, poscosegran.version_conocimiento, poscosegran.regla, poscosegran.fuente FROM poscosegran_app")
frontend = BACKEND.parent / ".env.local"
if not argumentos.contenedor and not frontend.exists():
    frontend.write_text("VITE_AUTH_MODE=local\nVITE_API_URL=/api/v1\n", encoding="utf-8")
print("Entorno listo. Usuarios: productor / tecnico / administrador.")
if not argumentos.contenedor:
    print("Contraseña local: consulte POSCOSEGRAN_AUTH_LOCAL_PASSWORD en backend/.env.")
