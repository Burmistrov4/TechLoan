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

            CREATE TABLE IF NOT EXISTS ediciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                descripcion TEXT,
                estado TEXT NOT NULL DEFAULT 'ACTIVA'
                    CHECK (estado IN ('ACTIVA', 'ARCHIVADA', 'BORRADOR')),
                version_actual INTEGER NOT NULL DEFAULT 1,
                fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS edicion_versiones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edicion_id INTEGER NOT NULL,
                numero_version INTEGER NOT NULL,
                nombre_version TEXT,
                estado TEXT NOT NULL DEFAULT 'ACTIVA'
                    CHECK (estado IN ('ACTIVA', 'ARCHIVADA')),
                creado_por INTEGER NOT NULL,
                notas_cambios TEXT,
                snapshot_json TEXT NOT NULL DEFAULT '{}',
                fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (edicion_id) REFERENCES ediciones(id) ON DELETE CASCADE,
                FOREIGN KEY (creado_por) REFERENCES usuarios_sistema(id),
                UNIQUE (edicion_id, numero_version)
            );

            CREATE TABLE IF NOT EXISTS edicion_configuracion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edicion_id INTEGER NOT NULL,
                clave TEXT NOT NULL,
                valor TEXT,
                FOREIGN KEY (edicion_id) REFERENCES ediciones(id) ON DELETE CASCADE,
                UNIQUE (edicion_id, clave)
            );

            CREATE TABLE IF NOT EXISTS usuarios_ediciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_sistema_id INTEGER NOT NULL,
                edicion_id INTEGER NOT NULL,
                rol_en_edicion TEXT NOT NULL DEFAULT 'OPERADOR'
                    CHECK (rol_en_edicion IN ('ADMINISTRADOR_EDICION', 'OPERADOR')),
                fecha_union TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_sistema_id) REFERENCES usuarios_sistema(id) ON DELETE CASCADE,
                FOREIGN KEY (edicion_id) REFERENCES ediciones(id) ON DELETE CASCADE,
                UNIQUE (usuario_sistema_id, edicion_id)
            );

            -- Secciones y materias por edición (Fase 2).
            CREATE TABLE IF NOT EXISTS secciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edicion_id INTEGER NOT NULL DEFAULT 1,
                codigo_seccion TEXT NOT NULL,
                semestre INTEGER NOT NULL CHECK (semestre BETWEEN 1 AND 10),
                periodo_academico TEXT NOT NULL,
                carrera_o_escuela TEXT NOT NULL DEFAULT '',
                cantidad_estimada INTEGER CHECK (cantidad_estimada IS NULL OR cantidad_estimada >= 0),
                estado TEXT NOT NULL DEFAULT 'ACTIVA'
                    CHECK (estado IN ('ACTIVA', 'INACTIVA')),
                fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (edicion_id) REFERENCES ediciones(id) ON DELETE CASCADE,
                UNIQUE (edicion_id, codigo_seccion, semestre, periodo_academico, carrera_o_escuela)
            );

            CREATE TABLE IF NOT EXISTS materias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edicion_id INTEGER NOT NULL DEFAULT 1,
                codigo TEXT NOT NULL,
                nombre TEXT NOT NULL,
                escuela TEXT NOT NULL DEFAULT '',
                semestre INTEGER CHECK (semestre IS NULL OR semestre BETWEEN 1 AND 10),
                estado TEXT NOT NULL DEFAULT 'ACTIVA'
                    CHECK (estado IN ('ACTIVA', 'INACTIVA')),
                fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (edicion_id) REFERENCES ediciones(id) ON DELETE CASCADE,
                UNIQUE (edicion_id, codigo)
            );

            CREATE INDEX IF NOT EXISTS idx_secciones_edicion ON secciones (edicion_id);
            CREATE INDEX IF NOT EXISTS idx_materias_edicion  ON materias  (edicion_id);

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
                edicion_id INTEGER NOT NULL DEFAULT 1,
                cedula TEXT NOT NULL,
                nombre TEXT NOT NULL,
                apellido TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK (tipo IN ('ESTUDIANTE', 'PROFESOR', 'EMPLEADO', 'OTRO')),
                telefono TEXT,
                email TEXT,
                estado TEXT NOT NULL DEFAULT 'ACTIVO'
                    CHECK (estado IN ('ACTIVO', 'INACTIVO')),
                UNIQUE (edicion_id, cedula)
            );

            CREATE TABLE IF NOT EXISTS laboratorios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edicion_id INTEGER NOT NULL DEFAULT 1,
                codigo TEXT NOT NULL,
                nombre TEXT NOT NULL,
                ubicacion TEXT NOT NULL,
                capacidad INTEGER NOT NULL CHECK (capacidad > 0),
                duracion_estandar_minutos INTEGER NOT NULL DEFAULT 70
                    CHECK (duracion_estandar_minutos > 0),
                estado TEXT NOT NULL DEFAULT 'DISPONIBLE'
                    CHECK (estado IN ('DISPONIBLE', 'MANTENIMIENTO', 'INACTIVO')),
                UNIQUE (edicion_id, codigo)
            );

            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                descripcion TEXT
            );

            CREATE TABLE IF NOT EXISTS equipos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edicion_id INTEGER NOT NULL DEFAULT 1,
                codigo TEXT NOT NULL,
                nombre TEXT NOT NULL,
                categoria_id INTEGER,
                marca TEXT,
                modelo TEXT,
                serial TEXT,
                laboratorio_id INTEGER,
                estado TEXT NOT NULL DEFAULT 'DISPONIBLE'
                    CHECK (estado IN ('DISPONIBLE', 'PRESTADO', 'MANTENIMIENTO', 'DANADO', 'INACTIVO')),
                FOREIGN KEY (categoria_id) REFERENCES categorias(id),
                FOREIGN KEY (laboratorio_id) REFERENCES laboratorios(id),
                UNIQUE (edicion_id, codigo),
                UNIQUE (edicion_id, serial)
            );

            CREATE TABLE IF NOT EXISTS reservas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edicion_id INTEGER NOT NULL DEFAULT 1,
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
                tipo_reserva TEXT NOT NULL DEFAULT 'PUNTUAL'
                    CHECK (tipo_reserva IN ('PUNTUAL', 'SEMESTRAL')),
                seccion_id INTEGER,
                materia_id INTEGER,
                dia_semana INTEGER
                    CHECK (dia_semana IS NULL OR dia_semana BETWEEN 0 AND 5),
                periodo_academico TEXT,
                cantidad_estudiantes INTEGER
                    CHECK (cantidad_estudiantes IS NULL OR cantidad_estudiantes >= 0),
                FOREIGN KEY (laboratorio_id) REFERENCES laboratorios(id),
                FOREIGN KEY (prestatario_id) REFERENCES prestatarios(id),
                FOREIGN KEY (usuario_sistema_id) REFERENCES usuarios_sistema(id),
                FOREIGN KEY (seccion_id) REFERENCES secciones(id),
                FOREIGN KEY (materia_id) REFERENCES materias(id)
            );

            CREATE TABLE IF NOT EXISTS prestamos_equipos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edicion_id INTEGER NOT NULL DEFAULT 1,
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
                edicion_id INTEGER,
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
            -- Los índices por edición se crean en _migrar(), DESPUÉS de añadir la
            -- columna edicion_id: en una base antigua ese ALTER aún no corrió y
            -- crear aquí el índice fallaría con «no such column: edicion_id».
            """
        )
        _migrar(db)


def _columnas(db, tabla):
    """Nombres de las columnas de una tabla (vacío si la tabla no existe)."""
    return {fila["name"] for fila in db.execute(f"PRAGMA table_info({tabla})").fetchall()}


def _tiene_unica_compuesta(db, tabla, columna1, columna2):
    """Verifica si ya existe una restricción UNIQUE compuesta ``(col1, col2)``.

    Una restricción ``UNIQUE (a, b)`` de nivel de tabla se materializa como un
    **autoíndice** sin sentencia SQL propia (``sql`` es NULL en ``sqlite_master``),
    por lo que no se puede localizar consultando ``sql``. Se inspeccionan los
    índices con ``PRAGMA index_list``/``index_info`` y se comprueba que alguno
    sea UNIQUE y empiece exactamente por esas dos columnas, en ese orden.
    """
    try:
        for indice in db.execute(f"PRAGMA index_list({tabla})").fetchall():
            if not indice["unique"]:
                continue
            columnas = [
                info["name"]
                for info in db.execute(
                    f"PRAGMA index_info({indice['name']})"
                ).fetchall()
            ]
            if columnas[:2] == [columna1, columna2]:
                return True
    except Exception:
        pass
    return False


def _recrear_tabla_unica_compuesta(db, tabla, create_sql):
    """Recrea una tabla para cambiar su restricción UNIQUE de global a compuesta.

    SQLite no permite ``ALTER TABLE DROP CONSTRAINT``, así que hay que:
    1. Renombrar la tabla original.
    2. Crear la nueva tabla con la restricción correcta.
    3. Copiar los datos.
    4. Borrar la tabla original.

    Trampa medida: a partir de SQLite 3.25, ``ALTER TABLE … RENAME`` reescribe
    también las claves foráneas **de otras tablas** para que apunten al nombre
    nuevo (``prestatarios_old``). Si luego se borra esa tabla, ``reservas`` y
    ``prestamos_equipos`` quedan apuntando a una tabla inexistente. Con
    ``PRAGMA legacy_alter_table = ON`` el RENAME solo renombra la tabla y deja
    intactas las referencias, de modo que tras crear la nueva y borrar la vieja
    todo vuelve a resolverse contra el nombre original.

    Requisitos: ``foreign_keys = OFF`` **y** ``legacy_alter_table = ON`` antes
    de llamarla, ambos aplicados fuera de una transacción abierta.
    """
    temp = f"{tabla}_old"
    db.execute(f"ALTER TABLE {tabla} RENAME TO {temp}")
    db.executescript(create_sql)
    # Copiar columnas comunes (la nueva tabla tiene edicion_id, la vieja puede no)
    cols_nueva = _columnas(db, tabla)
    cols_vieja = _columnas(db, temp)
    cols_comunes = ", ".join(cols_nueva & cols_vieja)
    db.execute(f"INSERT INTO {tabla} ({cols_comunes}) SELECT {cols_comunes} FROM {temp}")
    db.execute(f"DROP TABLE {temp}")


def _migrar(db):
    """Pone al día una base de datos creada con una versión anterior.

    ``CREATE TABLE IF NOT EXISTS`` no toca una tabla que ya existe, así que los
    cambios de esquema posteriores hay que aplicarlos a mano. Es idempotente: se
    puede ejecutar en cada arranque sin efectos secundarios.
    """
    # --- 1. email_confirmado (migración histórica) ---
    if "email_confirmado" not in _columnas(db, "usuarios_sistema"):
        db.execute(
            "ALTER TABLE usuarios_sistema ADD COLUMN email_confirmado "
            "INTEGER NOT NULL DEFAULT 1 CHECK (email_confirmado IN (0, 1))"
        )

    # --- 2. edicion_id en tablas operativas ---
    for tabla in ("prestatarios", "laboratorios", "equipos", "reservas",
                  "prestamos_equipos", "auditoria"):
        if "edicion_id" not in _columnas(db, tabla):
            db.execute(f"ALTER TABLE {tabla} ADD COLUMN edicion_id INTEGER NOT NULL DEFAULT 1")

    # --- 2b. Índices por edición (las columnas ya existen tras el paso 2) ---
    for tabla, indice in (
        ("prestatarios", "idx_prestatarios_edicion"),
        ("laboratorios", "idx_laboratorios_edicion"),
        ("equipos", "idx_equipos_edicion"),
        ("reservas", "idx_reservas_edicion"),
        ("prestamos_equipos", "idx_prestamos_edicion"),
        ("auditoria", "idx_auditoria_edicion"),
    ):
        db.execute(f"CREATE INDEX IF NOT EXISTS {indice} ON {tabla} (edicion_id)")

    # --- 2c. Columnas de horarios en reservas (Fase 2) ---
    # ALTER TABLE ADD COLUMN es idempotente por chequeo de _columnas. tipo_reserva
    # es NOT NULL, por lo que necesita DEFAULT para no romper las filas existentes.
    columnas_reservas = (
        ("tipo_reserva", "TEXT NOT NULL DEFAULT 'PUNTUAL' "
                         "CHECK (tipo_reserva IN ('PUNTUAL', 'SEMESTRAL'))"),
        ("seccion_id", "INTEGER"),
        ("materia_id", "INTEGER"),
        ("dia_semana", "INTEGER CHECK (dia_semana IS NULL OR dia_semana BETWEEN 0 AND 5)"),
        ("periodo_academico", "TEXT"),
        ("cantidad_estudiantes", "INTEGER CHECK (cantidad_estudiantes IS NULL OR cantidad_estudiantes >= 0)"),
    )
    cols_reservas = _columnas(db, "reservas")
    for columna, definicion in columnas_reservas:
        if columna not in cols_reservas:
            db.execute(f"ALTER TABLE reservas ADD COLUMN {columna} {definicion}")

    # Índices de la Fase 2 (las columnas ya existen tras el paso anterior).
    for indice, definicion in (
        ("idx_reservas_seccion", "reservas (seccion_id)"),
        ("idx_reservas_materia", "reservas (materia_id)"),
        ("idx_reservas_profesor_fecha", "reservas (prestatario_id, dia_semana)"),
        ("idx_reservas_lab_dia", "reservas (laboratorio_id, dia_semana)"),
    ):
        db.execute(f"CREATE INDEX IF NOT EXISTS {indice} ON {definicion}")

    # --- 3. Seed de ediciones base e IUTEPI LABS ---
    if db.execute("SELECT COUNT(*) FROM ediciones").fetchone()[0] == 0:
        db.execute(
            "INSERT INTO ediciones (nombre, slug, descripcion, estado, version_actual) VALUES "
            "('TechLoan Base', 'base', 'Edición genérica del sistema de gestión de laboratorios.', 'ACTIVA', 1),"
            "('IUTEPI LABS', 'iutepi-labs', 'Edición a medida para gestión de horarios y secciones de laboratorios IUTEPI.', 'ACTIVA', 1)"
        )

    # --- 4. Seed de versiones iniciales ---
    # Solo si existe al menos un usuario ADMINISTRADOR: ``creado_por`` es
    # NOT NULL y apunta a usuarios_sistema. En una base recién creada por
    # init_db.py los usuarios ya existen; si por alguna razón no los hay,
    # omitimos este paso en vez de romper el arranque con un error de FK.
    if db.execute("SELECT COUNT(*) FROM edicion_versiones").fetchone()[0] == 0:
        admin = db.execute(
            "SELECT id FROM usuarios_sistema WHERE rol='ADMINISTRADOR' ORDER BY id LIMIT 1"
        ).fetchone()
        if admin:
            admin_id = admin["id"]
            db.execute(
                "INSERT INTO edicion_versiones "
                "(edicion_id, numero_version, nombre_version, estado, creado_por, notas_cambios, snapshot_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?), (?, ?, ?, ?, ?, ?, ?)",
                (1, 1, 'Inicial', 'ACTIVA', admin_id, 'Versión base del sistema.', '{}',
                 2, 1, 'Inicial', 'ACTIVA', admin_id, 'Versión inicial de IUTEPI LABS.', '{}')
            )

    # --- 5. Asignar usuarios a ediciones ---
    if db.execute("SELECT COUNT(*) FROM usuarios_ediciones").fetchone()[0] == 0:
        # Asume que admin=1 y operador=2 existen (seed histórico)
        try:
            db.execute(
                "INSERT INTO usuarios_ediciones (usuario_sistema_id, edicion_id, rol_en_edicion) VALUES "
                "(1, 1, 'ADMINISTRADOR_EDICION'), (1, 2, 'ADMINISTRADOR_EDICION'),"
                "(2, 1, 'OPERADOR'), (2, 2, 'OPERADOR')"
            )
        except Exception:
            # Si los usuarios no existen (BD vacía o tests), ignorar silenciosamente
            pass

    # --- 6. Cambiar UNIQUE globales a compuestas por edición ---
    # Solo recrear si la tabla aún no tiene la restricción compuesta. El chequeo
    # usa index_list/index_info, así que en una base ya creada desde schema.sql
    # (con UNIQUE (edicion_id, …)) este bloque no hace nada.
    # Los PRAGMA hay que aplicarlos FUERA de una transacción abierta: las
    # sentencias anteriores abrieron una y, si no, SQLite los ignora en silencio.
    db.commit()
    db.execute("PRAGMA legacy_alter_table = ON")
    db.execute("PRAGMA foreign_keys = OFF")

    if not _tiene_unica_compuesta(db, "prestatarios", "edicion_id", "cedula"):
        _recrear_tabla_unica_compuesta(db, "prestatarios", """
            CREATE TABLE prestatarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edicion_id INTEGER NOT NULL DEFAULT 1,
                cedula TEXT NOT NULL,
                nombre TEXT NOT NULL,
                apellido TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK (tipo IN ('ESTUDIANTE', 'PROFESOR', 'EMPLEADO', 'OTRO')),
                telefono TEXT,
                email TEXT,
                estado TEXT NOT NULL DEFAULT 'ACTIVO'
                    CHECK (estado IN ('ACTIVO', 'INACTIVO')),
                UNIQUE (edicion_id, cedula)
            );
        """)

    if not _tiene_unica_compuesta(db, "laboratorios", "edicion_id", "codigo"):
        _recrear_tabla_unica_compuesta(db, "laboratorios", """
            CREATE TABLE laboratorios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edicion_id INTEGER NOT NULL DEFAULT 1,
                codigo TEXT NOT NULL,
                nombre TEXT NOT NULL,
                ubicacion TEXT NOT NULL,
                capacidad INTEGER NOT NULL CHECK (capacidad > 0),
                duracion_estandar_minutos INTEGER NOT NULL DEFAULT 70
                    CHECK (duracion_estandar_minutos > 0),
                estado TEXT NOT NULL DEFAULT 'DISPONIBLE'
                    CHECK (estado IN ('DISPONIBLE', 'MANTENIMIENTO', 'INACTIVO')),
                UNIQUE (edicion_id, codigo)
            );
        """)

    # equipos tiene DOS restricciones compuestas
    tiene_codigo = _tiene_unica_compuesta(db, "equipos", "edicion_id", "codigo")
    tiene_serial = _tiene_unica_compuesta(db, "equipos", "edicion_id", "serial")
    if not tiene_codigo or not tiene_serial:
        _recrear_tabla_unica_compuesta(db, "equipos", """
            CREATE TABLE equipos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                edicion_id INTEGER NOT NULL DEFAULT 1,
                codigo TEXT NOT NULL,
                nombre TEXT NOT NULL,
                categoria_id INTEGER,
                marca TEXT,
                modelo TEXT,
                serial TEXT,
                laboratorio_id INTEGER,
                estado TEXT NOT NULL DEFAULT 'DISPONIBLE'
                    CHECK (estado IN ('DISPONIBLE', 'PRESTADO', 'MANTENIMIENTO', 'DANADO', 'INACTIVO')),
                FOREIGN KEY (categoria_id) REFERENCES categorias(id),
                FOREIGN KEY (laboratorio_id) REFERENCES laboratorios(id),
                UNIQUE (edicion_id, codigo),
                UNIQUE (edicion_id, serial)
            );
        """)

    # Restaurar los PRAGMA. Se commitea primero para cerrar la transacción que
    # abrieron las recreaciones: así los PRAGMA vuelven a surtir efecto (si se
    # dejan a mitad de una transacción, SQLite los ignora en silencio).
    db.commit()
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA legacy_alter_table = OFF")
