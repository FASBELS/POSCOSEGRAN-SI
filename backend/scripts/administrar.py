"""Aprovisionamiento explícito; requiere credencial de migraciones y motivo."""
import argparse
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from poscosegran.db.modelos import Usuario, UsuarioRol, AsignacionLote, AsignacionAlmacen

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--usuario", type=uuid.UUID, required=True, help="UUID sub de Supabase o usuario local")
parser.add_argument("--nombre")
parser.add_argument("--rol", choices=["PRODUCTOR", "TECNICO", "ADMINISTRADOR"])
parser.add_argument("--lote", type=uuid.UUID)
parser.add_argument("--almacen", type=uuid.UUID)
parser.add_argument("--responsable", type=uuid.UUID, help="Usuario administrador que autoriza la asignación")
parser.add_argument("--motivo", required=True)
args = parser.parse_args()
if not args.motivo.strip():
    parser.error("El motivo no puede estar vacío")
load_dotenv(Path(__file__).resolve().parents[1] / ".env")
url = os.environ.get("POSCOSEGRAN_BD_URL_MIGRACIONES")
if not url:
    parser.error("Defina POSCOSEGRAN_BD_URL_MIGRACIONES")
with Session(create_engine(url)) as db, db.begin():
    responsable = db.get(Usuario, args.responsable) if args.responsable else None
    if args.responsable and (responsable is None or not responsable.activo or not db.scalar(
        select(UsuarioRol).where(UsuarioRol.id_usuario == args.responsable, UsuarioRol.rol == "ADMINISTRADOR")
    )):
        parser.error("El responsable debe ser un administrador activo")
    usuario = db.get(Usuario, args.usuario)
    if usuario is None:
        if not args.nombre:
            parser.error("Un usuario nuevo requiere --nombre")
        usuario = Usuario(id=args.usuario, nombre=args.nombre)
        db.add(usuario)
        db.flush()
    if args.rol and not db.scalar(select(UsuarioRol).where(UsuarioRol.id_usuario==args.usuario, UsuarioRol.rol==args.rol)):
        db.add(UsuarioRol(id_usuario=args.usuario, rol=args.rol, otorgado_por=args.motivo))
        db.flush()
    if args.lote or args.almacen:
        if not args.responsable or not db.scalar(select(UsuarioRol).where(UsuarioRol.id_usuario==args.responsable, UsuarioRol.rol=='ADMINISTRADOR')):
            parser.error("Una asignación requiere --responsable con rol ADMINISTRADOR")
        if not db.scalar(select(UsuarioRol).where(UsuarioRol.id_usuario==args.usuario, UsuarioRol.rol=='TECNICO')):
            parser.error("El usuario debe tener rol TECNICO")
        for modelo, columna, identificador in ((AsignacionLote, 'id_lote', args.lote), (AsignacionAlmacen, 'id_almacen', args.almacen)):
            if identificador and not db.scalar(select(modelo).where(modelo.id_tecnico==args.usuario, getattr(modelo,columna)==identificador)):
                db.add(modelo(id_tecnico=args.usuario, creada_por=args.responsable, **{columna:identificador}))
    from poscosegran.seguridad.identidad import Identidad
    from poscosegran.servicios.auditoria import registrar
    actor = Identidad(id=args.responsable, roles=frozenset(db.scalars(
        select(UsuarioRol.rol).where(UsuarioRol.id_usuario == args.responsable)
    ))) if args.responsable else None
    registrar(db, actor,
              accion="aprovisionamiento_administrativo", recurso_tipo="usuario", recurso_id=args.usuario,
              metodo=None, ruta=None, estado_http=None, resumen={"procedimiento":"credencial_administrativa", "motivo":args.motivo,"rol":args.rol,
              "lote":str(args.lote) if args.lote else None,"almacen":str(args.almacen) if args.almacen else None})
print("Aprovisionamiento registrado.")
