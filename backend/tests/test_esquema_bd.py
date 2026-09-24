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


def test_evaluacion_no_se_puede_modificar(motor) -> None:  
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


def test_clima_calido_exige_fundamento(motor) -> None:  
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


def test_observacion_aportada_exige_fecha_y_metodo(motor) -> None:  
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


def _unidad(conexion: sa.Connection) -> uuid.UUID:
    """Crea una unidad propia de la prueba, con todo lo que exigen sus claves ajenas."""
    propietario = _usuario(conexion, "productora de prueba")
    sufijo = uuid.uuid4().hex[:12]
    almacen, lote, recipiente, unidad = (uuid.uuid4() for _ in range(4))
    conexion.execute(
        sa.text(
            "INSERT INTO poscosegran.almacen (id, id_propietario, nombre, ubicacion) "
            "VALUES (:id, :p, :nombre, 'Prueba')"
        ),
        {"id": almacen, "p": propietario, "nombre": f"Almacén {sufijo}"},
    )
    conexion.execute(
        sa.text(
            "INSERT INTO poscosegran.lote (id, id_propietario, codigo, variedad, uso_final) "
            "VALUES (:id, :p, :codigo, 'MAIZ_CHULPI', 'ALIMENTACION')"
        ),
        {"id": lote, "p": propietario, "codigo": f"L-{sufijo}"},
    )
    conexion.execute(
        sa.text("INSERT INTO poscosegran.recipiente (id, nombre) VALUES (:id, :nombre)"),
        {"id": recipiente, "nombre": f"Costal {sufijo}"},
    )
    conexion.execute(
        sa.text(
            "INSERT INTO poscosegran.unidad "
            "(id, id_lote, id_almacen, id_recipiente, nombre_recipiente, tipo_almacenamiento) "
            "VALUES (:id, :lote, :almacen, :recipiente, :nombre, 'NO_HERMETICO')"
        ),
        {
            "id": unidad, "lote": lote, "almacen": almacen,
            "recipiente": recipiente, "nombre": f"Costal {sufijo}",
        },
    )
    return unidad


def test_solo_una_incidencia_abierta_por_tipo(motor) -> None:  
    """El índice parcial impide dos incidencias abiertas del mismo tipo en una unidad.

    La prueba crea su propia unidad y revierte al terminar. Tomar una unidad
    cualquiera de la base hacía que fallara el *primer* INSERT en cuanto una
    ejecución anterior —o el uso normal de la aplicación— ya hubiera dejado una
    cuarentena abierta sobre ella.
    """
    with motor.connect() as conexion:
        transaccion = conexion.begin()
        try:
            unidad = _unidad(conexion)
            insercion = sa.text(
                "INSERT INTO poscosegran.incidencia (id_unidad, tipo, estado, causas) "
                "VALUES (:u, 'CUARENTENA', 'ABIERTA', ARRAY['prueba'])"
            )
            conexion.execute(insercion, {"u": unidad})
            with pytest.raises(sa.exc.IntegrityError):
                conexion.execute(insercion, {"u": unidad})
        finally:
            transaccion.rollback()


def test_historial_no_se_borra(motor) -> None:  
    with motor.begin() as conexion:
        registro = conexion.execute(sa.text("SELECT id FROM poscosegran.evento LIMIT 1")).first()
        if registro is None:
            pytest.skip("no hay eventos registrados todavía")
        with pytest.raises(sa.exc.DatabaseError):
            conexion.execute(
                sa.text("DELETE FROM poscosegran.evento WHERE id = :id"), {"id": registro[0]}
            )


def test_la_credencial_de_aplicacion_no_puede_crear_tablas(motor) -> None:  
    """Comprobación del reparto de privilegios de sql/roles_privilegios.sql."""
    with motor.begin() as conexion:
        rol = conexion.execute(sa.text("SELECT current_user")).scalar_one()
        if rol != "poscosegran_app":
            pytest.skip("la URL de pruebas no usa la credencial de aplicación")
        with pytest.raises(sa.exc.ProgrammingError):
            conexion.execute(sa.text("CREATE TABLE poscosegran.prueba_privilegios (id int)"))
