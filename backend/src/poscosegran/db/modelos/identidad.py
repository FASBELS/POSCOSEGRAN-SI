"""Usuarios, roles y asignaciones técnicas.

El identificador de usuario es el 'sub' del proveedor de identidad. No se guardan
credenciales, contraseñas ni tokens en esta base.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from ..base import AHORA, Base, columna_id, enum_texto, fk_uuid
from ..enums import ROL


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = columna_id()
    nombre: Mapped[str] = mapped_column(sa.Text)
    activo: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default=sa.true())
    creado_en: Mapped[datetime] = mapped_column(server_default=AHORA)

    __table_args__ = (sa.CheckConstraint("length(btrim(nombre)) > 0", name="nombre_no_vacio"),)


class UsuarioRol(Base):
    """Un usuario puede acumular roles. ADMINISTRADOR no implica TECNICO."""

    __tablename__ = "usuario_rol"

    id: Mapped[uuid.UUID] = columna_id()
    id_usuario: Mapped[uuid.UUID] = fk_uuid("usuario.id", index=True)
    rol: Mapped[str] = mapped_column(enum_texto("rol", ROL))
    otorgado_en: Mapped[datetime] = mapped_column(server_default=AHORA)
    otorgado_por: Mapped[str] = mapped_column(
        sa.Text, comment="Procedimiento administrativo documentado que originó el rol."
    )

    __table_args__ = (sa.UniqueConstraint("id_usuario", "rol"),)


class AsignacionAlmacen(Base):
    """Habilita a un técnico sobre todas las unidades de un almacén."""

    __tablename__ = "asignacion_almacen"

    id: Mapped[uuid.UUID] = columna_id()
    id_tecnico: Mapped[uuid.UUID] = fk_uuid("usuario.id", index=True)
    id_almacen: Mapped[uuid.UUID] = fk_uuid("almacen.id", index=True)
    vigente: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default=sa.true())
    creada_en: Mapped[datetime] = mapped_column(server_default=AHORA)
    creada_por: Mapped[uuid.UUID] = fk_uuid("usuario.id")

    __table_args__ = (sa.UniqueConstraint("id_tecnico", "id_almacen"),)


class AsignacionLote(Base):
    """Habilita a un técnico sobre las unidades de un lote concreto."""

    __tablename__ = "asignacion_lote"

    id: Mapped[uuid.UUID] = columna_id()
    id_tecnico: Mapped[uuid.UUID] = fk_uuid("usuario.id", index=True)
    id_lote: Mapped[uuid.UUID] = fk_uuid("lote.id", index=True)
    vigente: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default=sa.true())
    creada_en: Mapped[datetime] = mapped_column(server_default=AHORA)
    creada_por: Mapped[uuid.UUID] = fk_uuid("usuario.id")

    __table_args__ = (sa.UniqueConstraint("id_tecnico", "id_lote"),)
