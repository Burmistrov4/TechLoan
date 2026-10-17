"""Migración idempotente a la restricción UNIQUE compuesta por edición.

Construye una base de datos con el esquema **anterior** a la Fase 1 (unicidad
GLOBAL, sin ``edicion_id``) y con datos que tienen claves foráneas que apuntan a
las tablas que la migración debe recrear (``prestatarios``, ``laboratorios``,
``equipos``). Después ejecuta el ``init_database()`` real y comprueba que:

- las tablas pasan a tener UNIQUE ``(edicion_id, …)``;
- los datos se conservan con los mismos id;
- no quedan claves foráneas colgando (``PRAGMA foreign_key_check`` vacío);
- ``integrity_check`` sigue en ``ok``;
- se puede borrar una fila hija y luego su padre (las FKs funcionan).

Este es el camino de actualización real en producción, donde la base existente no
fue creada con ``schema.sql`` actual.

Uso::

    PYTHONPATH=. python tests/test_migracion_edicion.py
"""

import os
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import app.database as database  # noqa: E402

RUTA = os.path.join(tempfile.mkdtemp(prefix="techloan_migracion_"), "old.db")
database.DATABASE_PATH = RUTA

# Esquema PRE-Fase 1 de las tablas afectadas: unicidad global, sin edicion_id.
ESQUEMA_VIEJO = """
DROP TABLE IF EXISTS auditoria;
DROP TABLE IF EXISTS prestamos_equipos;
DROP TABLE IF EXISTS reservas;
DROP TABLE IF EXISTS equipos;
DROP TABLE IF EXISTS categorias;
DROP TABLE IF EXISTS laboratorios;
DROP TABLE IF EXISTS prestatarios;
DROP TABLE IF EXISTS usuarios_sistema;

CREATE TABLE usuarios_sistema (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL, apellido TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE, email TEXT NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    rol TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'ACTIVO',
    email_confirmado INTEGER NOT NULL DEFAULT 1,
    fecha_registro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE categorias (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL UNIQUE, descripcion TEXT);
CREATE TABLE prestatarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cedula TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL, apellido TEXT NOT NULL,
    tipo TEXT NOT NULL, telefono TEXT, email TEXT,
    estado TEXT NOT NULL DEFAULT 'ACTIVO'
);
CREATE TABLE laboratorios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL, ubicacion TEXT NOT NULL,
    capacidad INTEGER NOT NULL, duracion_estandar_minutos INTEGER NOT NULL DEFAULT 70,
    estado TEXT NOT NULL DEFAULT 'DISPONIBLE'
);
CREATE TABLE equipos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL,
    categoria_id INTEGER, marca TEXT, modelo TEXT, serial TEXT UNIQUE,
    laboratorio_id INTEGER, estado TEXT NOT NULL DEFAULT 'DISPONIBLE',
    FOREIGN KEY (categoria_id) REFERENCES categorias(id),
    FOREIGN KEY (laboratorio_id) REFERENCES laboratorios(id)
);
CREATE TABLE reservas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    laboratorio_id INTEGER NOT NULL, prestatario_id INTEGER NOT NULL,
    usuario_sistema_id INTEGER NOT NULL, fecha TEXT NOT NULL,
    hora_inicio TEXT NOT NULL, hora_fin TEXT NOT NULL,
    duracion_minutos INTEGER NOT NULL, estado TEXT NOT NULL DEFAULT 'CONFIRMADA',
    observaciones TEXT, fecha_registro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (laboratorio_id) REFERENCES laboratorios(id),
    FOREIGN KEY (prestatario_id) REFERENCES prestatarios(id),
    FOREIGN KEY (usuario_sistema_id) REFERENCES usuarios_sistema(id)
);
CREATE TABLE prestamos_equipos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipo_id INTEGER NOT NULL, prestatario_id INTEGER NOT NULL,
    usuario_sistema_id INTEGER NOT NULL, fecha_prestamo TEXT NOT NULL,
    fecha_devolucion TEXT, estado TEXT NOT NULL DEFAULT 'ACTIVO', observaciones TEXT,
    FOREIGN KEY (equipo_id) REFERENCES equipos(id),
    FOREIGN KEY (prestatario_id) REFERENCES prestatarios(id),
    FOREIGN KEY (usuario_sistema_id) REFERENCES usuarios_sistema(id)
);
CREATE TABLE auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER, usuario_username TEXT NOT NULL,
    accion TEXT NOT NULL, entidad TEXT NOT NULL, entidad_id INTEGER,
    descripcion TEXT NOT NULL, direccion_ip TEXT,
    fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def _abrir():
    import sqlite3
    conn = sqlite3.connect(RUTA)
    conn.row_factory = sqlite3.Row
    return conn


def main():
    import sqlite3

    # 1. Crear la base "vieja" con datos que apuntan a las tablas a recrear.
    conn = _abrir()
    conn.executescript(ESQUEMA_VIEJO)
    conn.execute(
        "INSERT INTO usuarios_sistema (nombre,apellido,username,email,password_hash,rol) "
        "VALUES ('Admin','','admin','admin@x.local','scrypt:x','ADMINISTRADOR')"
    )
    conn.execute("INSERT INTO categorias (nombre) VALUES ('Computación')")
    conn.execute(
        "INSERT INTO prestatarios (cedula,nombre,apellido,tipo) VALUES ('V-1','Ana','Paz','ESTUDIANTE')"
    )
    conn.execute(
        "INSERT INTO laboratorios (codigo,nombre,ubicacion,capacidad) VALUES ('LAB-1','Lab','A',10)"
    )
    conn.execute(
        "INSERT INTO equipos (codigo,nombre,categoria_id,laboratorio_id,serial) "
        "VALUES ('EQ-1','Laptop',1,1,'SN-1')"
    )
    conn.execute(
        "INSERT INTO reservas (laboratorio_id,prestatario_id,usuario_sistema_id,fecha,"
        "hora_inicio,hora_fin,duracion_minutos,estado) VALUES (1,1,1,'2026-12-01','08:00','09:10',70,'CONFIRMADA')"
    )
    conn.commit()
    # Ids originales (deben conservarse).
    id_prestatario = conn.execute("SELECT id FROM prestatarios").fetchone()["id"]
    id_reserva = conn.execute("SELECT id FROM reservas").fetchone()["id"]
    conn.close()

    # 2. Ejecutar la migración real (CREATE IF NOT EXISTS + _migrar con recreación).
    database.init_database()

    # 3. Verificar que la recreación dejó las claves foráneas intactas.
    conn = _abrir()
    conn.execute("PRAGMA foreign_keys = ON")

    assert conn.execute("PRAGMA foreign_key_check").fetchall() == [], \
        "No debe quedar ninguna clave foránea colgando tras la migración"
    assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok", \
        "La integridad de la base debe conservarse"

    with database.get_connection() as db:
        assert database._tiene_unica_compuesta(db, "prestatarios", "edicion_id", "cedula"), \
            "prestatarios debe terminar con UNIQUE (edicion_id, cedula)"
        assert database._tiene_unica_compuesta(db, "laboratorios", "edicion_id", "codigo"), \
            "laboratorios debe terminar con UNIQUE (edicion_id, codigo)"
        assert database._tiene_unica_compuesta(db, "equipos", "edicion_id", "codigo"), \
            "equipos debe terminar con UNIQUE (edicion_id, codigo)"
        assert database._tiene_unica_compuesta(db, "equipos", "edicion_id", "serial"), \
            "equipos debe terminar con UNIQUE (edicion_id, serial)"

    # Los datos se conservan con el mismo id.
    assert conn.execute(
        "SELECT id FROM prestatarios WHERE cedula='V-1'"
    ).fetchone()["id"] == id_prestatario, "El id del prestatario debe conservarse"
    assert conn.execute(
        "SELECT id FROM reservas WHERE id=?", (id_reserva,)
    ).fetchone() is not None, "La reserva debe conservarse"

    # Las FKs funcionan de verdad: se puede borrar la hija y luego el padre.
    conn.execute("DELETE FROM reservas WHERE id=?", (id_reserva,))
    conn.execute("DELETE FROM prestatarios WHERE id=?", (id_prestatario,))
    conn.commit()

    # Y la unicidad ahora es por edición: se admiten ediciones distintas.
    conn.execute(
        "INSERT INTO prestatarios (edicion_id,cedula,nombre,apellido,tipo) "
        "VALUES (1,'V-ED','A','B','ESTUDIANTE')"
    )
    conn.execute(
        "INSERT INTO prestatarios (edicion_id,cedula,nombre,apellido,tipo) "
        "VALUES (2,'V-ED','A','B','ESTUDIANTE')"
    )
    conn.commit()
    try:
        conn.execute(
            "INSERT INTO prestatarios (edicion_id,cedula,nombre,apellido,tipo) "
            "VALUES (1,'V-ED','C','D','ESTUDIANTE')"
        )
        conn.commit()
        raise AssertionError("Duplicar la cédula en la misma edición debe fallar")
    except sqlite3.IntegrityError:
        conn.rollback()

    conn.close()
    print("MIGRACION_EDICION_OK")


if __name__ == "__main__":
    main()
