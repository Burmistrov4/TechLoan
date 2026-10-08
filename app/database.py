import sqlite3
from contextlib import contextmanager

from app.config import DATABASE_PATH


@contextmanager
def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_database():
    with get_connection() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS usuarios_sistema (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                apellido TEXT NOT NULL,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                rol TEXT NOT NULL CHECK (rol IN ('ADMINISTRADOR', 'OPERADOR')),
                estado TEXT NOT NULL DEFAULT 'ACTIVO'
                    CHECK (estado IN ('ACTIVO', 'INACTIVO')),
                email_confirmado INTEGER NOT NULL DEFAULT 1
                    CHECK (email_confirmado IN (0, 1)),
                fecha_registro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            -- Tokens de un solo uso para confirmar la cuenta o recuperar la
            -- contraseña. Caducan y se marcan como usados; nunca dan acceso.
            CREATE TABLE IF NOT EXISTS tokens_correo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                tipo TEXT NOT NULL DEFAULT 'CONFIRMACION'
                    CHECK (tipo IN ('CONFIRMACION', 'RECUPERACION')),
                usado INTEGER NOT NULL DEFAULT 0 CHECK (usado IN (0, 1)),
                fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                fecha_expiracion TEXT NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios_sistema(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS prestatarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cedula TEXT NOT NULL UNIQUE,
                nombre TEXT NOT NULL,
                apellido TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK (tipo IN ('ESTUDIANTE', 'PROFESOR', 'EMPLEADO', 'OTRO')),
                telefono TEXT,
                email TEXT,
                estado TEXT NOT NULL DEFAULT 'ACTIVO'
                    CHECK (estado IN ('ACTIVO', 'INACTIVO'))
            );

            CREATE TABLE IF NOT EXISTS laboratorios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT NOT NULL UNIQUE,
                nombre TEXT NOT NULL,
                ubicacion TEXT NOT NULL,
                capacidad INTEGER NOT NULL CHECK (capacidad > 0),
                duracion_estandar_minutos INTEGER NOT NULL DEFAULT 70
                    CHECK (duracion_estandar_minutos > 0),
                estado TEXT NOT NULL DEFAULT 'DISPONIBLE'
                    CHECK (estado IN ('DISPONIBLE', 'MANTENIMIENTO', 'INACTIVO'))
            );

            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                descripcion TEXT
            );

            CREATE TABLE IF NOT EXISTS equipos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT NOT NULL UNIQUE,
                nombre TEXT NOT NULL,
                categoria_id INTEGER,
                marca TEXT,
                modelo TEXT,
                serial TEXT UNIQUE,
                laboratorio_id INTEGER,
                estado TEXT NOT NULL DEFAULT 'DISPONIBLE'
                    CHECK (estado IN ('DISPONIBLE', 'PRESTADO', 'MANTENIMIENTO', 'DANADO', 'INACTIVO')),
                FOREIGN KEY (categoria_id) REFERENCES categorias(id),
                FOREIGN KEY (laboratorio_id) REFERENCES laboratorios(id)
            );

            CREATE TABLE IF NOT EXISTS reservas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                laboratorio_id INTEGER NOT NULL,
                prestatario_id INTEGER NOT NULL,
                usuario_sistema_id INTEGER NOT NULL,
                fecha TEXT NOT NULL,
                hora_inicio TEXT NOT NULL,
                hora_fin TEXT NOT NULL,
                duracion_minutos INTEGER NOT NULL CHECK (duracion_minutos > 0),
                estado TEXT NOT NULL DEFAULT 'CONFIRMADA'
                    CHECK (estado IN ('CONFIRMADA', 'ACTIVA', 'FINALIZADA', 'CANCELADA')),
                observaciones TEXT,
                fecha_registro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (laboratorio_id) REFERENCES laboratorios(id),
                FOREIGN KEY (prestatario_id) REFERENCES prestatarios(id),
                FOREIGN KEY (usuario_sistema_id) REFERENCES usuarios_sistema(id)
            );

            CREATE TABLE IF NOT EXISTS prestamos_equipos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipo_id INTEGER NOT NULL,
                prestatario_id INTEGER NOT NULL,
                usuario_sistema_id INTEGER NOT NULL,
                fecha_prestamo TEXT NOT NULL,
                fecha_devolucion TEXT,
                estado TEXT NOT NULL DEFAULT 'ACTIVO'
                    CHECK (estado IN ('ACTIVO', 'DEVUELTO', 'CANCELADO')),
                observaciones TEXT,
                FOREIGN KEY (equipo_id) REFERENCES equipos(id),
                FOREIGN KEY (prestatario_id) REFERENCES prestatarios(id),
                FOREIGN KEY (usuario_sistema_id) REFERENCES usuarios_sistema(id)
            );

            -- Registro de actividad. ``usuario_id`` no lleva clave foránea a
            -- propósito: la auditoría debe sobrevivir a la baja del usuario.
            CREATE TABLE IF NOT EXISTS auditoria (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                usuario_username TEXT NOT NULL,
                accion TEXT NOT NULL
                    CHECK (accion IN ('CREAR', 'ACTUALIZAR', 'ELIMINAR', 'DEVOLVER',
                                      'CANCELAR', 'ACCEDER', 'SALIR', 'EXPORTAR')),
                entidad TEXT NOT NULL,
                entidad_id INTEGER,
                descripcion TEXT NOT NULL,
                direccion_ip TEXT,
                fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_auditoria_fecha ON auditoria (fecha);
            CREATE INDEX IF NOT EXISTS idx_auditoria_entidad ON auditoria (entidad, entidad_id);
            CREATE INDEX IF NOT EXISTS idx_auditoria_usuario ON auditoria (usuario_id);
            CREATE INDEX IF NOT EXISTS idx_tokens_token ON tokens_correo (token);
            CREATE INDEX IF NOT EXISTS idx_tokens_usuario ON tokens_correo (usuario_id, tipo);
            """
        )
        _migrar(db)


def _columnas(db, tabla):
    """Nombres de las columnas de una tabla (vacío si la tabla no existe)."""
    return {fila["name"] for fila in db.execute(f"PRAGMA table_info({tabla})").fetchall()}


def _migrar(db):
    """Pone al día una base de datos creada con una versión anterior.

    ``CREATE TABLE IF NOT EXISTS`` no toca una tabla que ya existe, así que los
    cambios de esquema posteriores hay que aplicarlos a mano. Es idempotente: se
    puede ejecutar en cada arranque sin efectos secundarios.
    """
    if "email_confirmado" not in _columnas(db, "usuarios_sistema"):
        # Las cuentas que ya existían se consideran confirmadas: se dieron de
        # alta cuando el registro por correo todavía no existía.
        db.execute(
            "ALTER TABLE usuarios_sistema ADD COLUMN email_confirmado "
            "INTEGER NOT NULL DEFAULT 1 CHECK (email_confirmado IN (0, 1))"
        )
