"""Pruebas contra PostgreSQL real. Requieren POSCOSEGRAN_BD_URL_PRUEBAS migrada."""

from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa

pytestmark = pytest.mark.bd


def _usuario(conexion: sa.Connection, nombre: str) -> uuid.UUID:
    identificador = uuid.uuid4()
    conexion.execute(
        sa.text(
            "INSERT INTO poscosegran.usuario (id, nombre) VALUES (:id, :nombre)"
        ),
        {"id": identificador, "nombre": nombre},
    )
    return identificador


def test_evaluacion_no_se_puede_modificar(motor) -> None:  # type: ignore[no-untyped-def]
    """Editar una evaluación debe fallar: se corrige emitiendo otra."""
    with motor.begin() as conexion:
        existe = conexion.execute(
            sa.text("SELECT id FROM poscosegran.evaluacion LIMIT 1")
        ).first()
        if existe is None:
            pytest.skip("no hay evaluaciones registradas todavía")
        with pytest.raises(sa.exc.DatabaseError):
            conexion.execute(
                sa.text(
                    "UPDATE poscosegran.evaluacion SET decision_final = 'AUTORIZAR_ALMACENAMIENTO' "
                    "WHERE id = :id"
                ),
                {"id": existe[0]},
            )


def test_clima_calido_exige_fundamento(motor) -> None:  # type: ignore[no-untyped-def]
    with motor.begin() as conexion:
        propietario = _usuario(conexion, "productora de prueba")
        with pytest.raises(sa.exc.IntegrityError):
            conexion.execute(
                sa.text(
                    "INSERT INTO poscosegran.almacen "
                    "(id_propietario, nombre, ubicacion, clima_calido, fundamento_clima) "
                    "VALUES (:p, 'Almacén', 'Sierra sur', true, NULL)"
                ),
                {"p": propietario},
            )


def test_observacion_aportada_exige_fecha_y_metodo(motor) -> None:  # type: ignore[no-untyped-def]
    """Un número sin procedimiento ni fecha no es una observación válida."""
    with motor.begin() as conexion:
        unidad = conexion.execute(sa.text("SELECT id FROM poscosegran.unidad LIMIT 1")).first()
        if unidad is None:
            pytest.skip("no hay unidades registradas todavía")
        responsable = _usuario(conexion, "responsable de prueba")
        with pytest.raises(sa.exc.IntegrityError):
            conexion.execute(
                sa.text(
                    "INSERT INTO poscosegran.observacion "
                    "(id_unidad, campo, captura, unidad_dato, valor_numero, aplicabilidad, "
                    " estado_dato, procedencia, id_responsable) "
                    "VALUES (:u, 'humedad_grano', 'APORTADO', 'PCT_BH', 12.5, 'APLICA', "
                    " 'VALIDO', 'ACTUAL', :r)"
                ),
                {"u": unidad[0], "r": responsable},
            )


def test_solo_una_incidencia_abierta_por_tipo(motor) -> None:  # type: ignore[no-untyped-def]
    with motor.begin() as conexion:
        unidad = conexion.execute(sa.text("SELECT id FROM poscosegran.unidad LIMIT 1")).first()
        if unidad is None:
            pytest.skip("no hay unidades registradas todavía")
        insercion = sa.text(
            "INSERT INTO poscosegran.incidencia (id_unidad, tipo, estado, causas) "
            "VALUES (:u, 'CUARENTENA', 'ABIERTA', ARRAY['prueba'])"
        )
        conexion.execute(insercion, {"u": unidad[0]})
        with pytest.raises(sa.exc.IntegrityError):
            conexion.execute(insercion, {"u": unidad[0]})


def test_historial_no_se_borra(motor) -> None:  # type: ignore[no-untyped-def]
    with motor.begin() as conexion:
        registro = conexion.execute(sa.text("SELECT id FROM poscosegran.evento LIMIT 1")).first()
        if registro is None:
            pytest.skip("no hay eventos registrados todavía")
        with pytest.raises(sa.exc.DatabaseError):
            conexion.execute(
                sa.text("DELETE FROM poscosegran.evento WHERE id = :id"), {"id": registro[0]}
            )


def test_la_credencial_de_aplicacion_no_puede_crear_tablas(motor) -> None:  # type: ignore[no-untyped-def]
    """Comprobación del reparto de privilegios de sql/roles_privilegios.sql."""
    with motor.begin() as conexion:
        rol = conexion.execute(sa.text("SELECT current_user")).scalar_one()
        if rol != "poscosegran_app":
            pytest.skip("la URL de pruebas no usa la credencial de aplicación")
        with pytest.raises(sa.exc.ProgrammingError):
            conexion.execute(sa.text("CREATE TABLE poscosegran.prueba_privilegios (id int)"))
