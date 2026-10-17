-- ============================================================================
-- TechLoan — Sistema Web de Gestión de Reservas y Préstamos de Recursos
-- Tecnológicos.
--
-- Script de creación de la base de datos (SQLite3).
--
-- Uso:
--     python init_db.py                 # reconstruye database/techloan.db
--     python init_db.py ruta/otra.db    # reconstruye una base de datos alterna
--
-- Este script es idempotente: elimina las tablas existentes y las vuelve a
-- crear, por lo que puede ejecutarse tantas veces como sea necesario.
--
-- ADVERTENCIA: elimina los datos existentes de la base de datos de destino.
-- No ejecutarlo sobre la base de datos de trabajo sin respaldo previo.
--
-- NOTA: las fechas de las reservas y de los préstamos de prueba se calculan
-- respecto a la fecha de ejecución (date('now','localtime','+N days')), de modo
-- que los datos de demostración siempre quedan vigentes y nunca aparecen
-- vencidos durante la exposición.
--
-- Proyecto final de Programación III — IUTEPI.
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- Limpieza: se eliminan primero las tablas dependientes (hijas) y al final las
-- independientes (padres), para respetar las restricciones de clave foránea.
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS usuarios_ediciones;
DROP TABLE IF EXISTS edicion_configuracion;
DROP TABLE IF EXISTS edicion_versiones;
DROP TABLE IF EXISTS auditoria;
DROP TABLE IF EXISTS tokens_correo;
DROP TABLE IF EXISTS prestamos_equipos;
DROP TABLE IF EXISTS reservas;
DROP TABLE IF EXISTS secciones;
DROP TABLE IF EXISTS materias;
DROP TABLE IF EXISTS equipos;
DROP TABLE IF EXISTS categorias;
DROP TABLE IF EXISTS laboratorios;
DROP TABLE IF EXISTS prestatarios;
DROP TABLE IF EXISTS ediciones;
DROP TABLE IF EXISTS usuarios_sistema;

-- ============================================================================
-- 1. usuarios_sistema — Usuarios con credenciales (ADMINISTRADOR / OPERADOR)
-- ============================================================================
CREATE TABLE usuarios_sistema (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT         NOT NULL,
    apellido        TEXT         NOT NULL,
    username        TEXT         NOT NULL UNIQUE,
    email           TEXT         NOT NULL UNIQUE,
    -- La contraseña NUNCA se guarda en texto plano: se almacena su hash
    -- (Werkzeug scrypt). El campo se define VARCHAR(255) para cumplir el
    -- requisito de longitud de la indicación del profesor.
    password_hash   VARCHAR(255) NOT NULL,
    rol             TEXT         NOT NULL CHECK (rol IN ('ADMINISTRADOR', 'OPERADOR')),
    estado          TEXT         NOT NULL DEFAULT 'ACTIVO'
                                 CHECK (estado IN ('ACTIVO', 'INACTIVO')),
    -- Un usuario creado por un administrador ya es de confianza (1 por defecto).
    -- El que se registra por su cuenta nace en 0 y no puede entrar hasta abrir
    -- el enlace de confirmación que recibe por correo.
    email_confirmado INTEGER     NOT NULL DEFAULT 1
                                 CHECK (email_confirmado IN (0, 1)),
    fecha_registro  TEXT         NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 2. ediciones — Instancias personalizadas del sistema (multiedición)
-- ============================================================================
CREATE TABLE ediciones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT    NOT NULL,          -- "IUTEPI LABS"
    slug            TEXT    NOT NULL UNIQUE,   -- "iutepi-labs" (para URLs)
    descripcion     TEXT,
    estado          TEXT    NOT NULL DEFAULT 'ACTIVA'
                    CHECK (estado IN ('ACTIVA', 'ARCHIVADA', 'BORRADOR')),
    version_actual  INTEGER NOT NULL DEFAULT 1,
    fecha_creacion  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 3. edicion_versiones — Control de versiones/revisiones por edición
-- ============================================================================
CREATE TABLE edicion_versiones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    edicion_id      INTEGER NOT NULL,
    numero_version  INTEGER NOT NULL,          -- 1, 2, 3...
    nombre_version  TEXT,                      -- "Inicial", "Con secciones"...
    estado          TEXT    NOT NULL DEFAULT 'ACTIVA'
                    CHECK (estado IN ('ACTIVA', 'ARCHIVADA')),
    creado_por      INTEGER NOT NULL,          -- usuario_sistema_id
    notas_cambios   TEXT,                      -- qué cambió respecto a la anterior
    -- Estado completo de la edición en este momento (JSON).
    snapshot_json   TEXT    NOT NULL DEFAULT '{}',
    fecha_creacion  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (edicion_id) REFERENCES ediciones(id) ON DELETE CASCADE,
    FOREIGN KEY (creado_por) REFERENCES usuarios_sistema(id),
    UNIQUE (edicion_id, numero_version)
);

-- ============================================================================
-- 4. edicion_configuracion — Preferencias por edición
-- ============================================================================
CREATE TABLE edicion_configuracion (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    edicion_id  INTEGER NOT NULL,
    clave       TEXT    NOT NULL,              -- 'bloques_horarios'
    valor       TEXT,                          -- JSON: '["07:00-08:10",...]'
    FOREIGN KEY (edicion_id) REFERENCES ediciones(id) ON DELETE CASCADE,
    UNIQUE (edicion_id, clave)
);

-- ============================================================================
-- 5. usuarios_ediciones — Relación usuarios ↔ ediciones
-- ============================================================================
CREATE TABLE usuarios_ediciones (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_sistema_id  INTEGER NOT NULL,
    edicion_id          INTEGER NOT NULL,
    rol_en_edicion      TEXT    NOT NULL DEFAULT 'OPERADOR'
                    CHECK (rol_en_edicion IN ('ADMINISTRADOR_EDICION', 'OPERADOR')),
    fecha_union         TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_sistema_id) REFERENCES usuarios_sistema(id) ON DELETE CASCADE,
    FOREIGN KEY (edicion_id)         REFERENCES ediciones(id)        ON DELETE CASCADE,
    UNIQUE (usuario_sistema_id, edicion_id)
);

-- ============================================================================
-- 5b. secciones — Secciones académicas por edición (petición del prof. Nelson)
--     La misma sección (p.ej. «SA») puede existir en varios semestres, periodos
--     o escuelas sin colisionar gracias a la UNIQUE compuesta.
-- ============================================================================
CREATE TABLE secciones (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    edicion_id        INTEGER NOT NULL DEFAULT 1,
    codigo_seccion    TEXT    NOT NULL,          -- «SA», «SB», «SA-A», «SAA»
    semestre          INTEGER NOT NULL CHECK (semestre BETWEEN 1 AND 10),
    periodo_academico TEXT    NOT NULL,          -- «2026-2»
    carrera_o_escuela TEXT    NOT NULL DEFAULT '',
    cantidad_estimada INTEGER CHECK (cantidad_estimada IS NULL OR cantidad_estimada >= 0),
    estado            TEXT    NOT NULL DEFAULT 'ACTIVA'
                      CHECK (estado IN ('ACTIVA', 'INACTIVA')),
    fecha_creacion    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (edicion_id) REFERENCES ediciones(id) ON DELETE CASCADE,
    UNIQUE (edicion_id, codigo_seccion, semestre, periodo_academico, carrera_o_escuela)
);

-- ============================================================================
-- 5c. materias — Materias por edición
-- ============================================================================
CREATE TABLE materias (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    edicion_id     INTEGER NOT NULL DEFAULT 1,
    codigo         TEXT    NOT NULL,             -- «SIS-101»
    nombre         TEXT    NOT NULL,
    escuela        TEXT    NOT NULL DEFAULT '',
    semestre       INTEGER CHECK (semestre IS NULL OR semestre BETWEEN 1 AND 10),
    estado         TEXT    NOT NULL DEFAULT 'ACTIVA'
                   CHECK (estado IN ('ACTIVA', 'INACTIVA')),
    fecha_creacion TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (edicion_id) REFERENCES ediciones(id) ON DELETE CASCADE,
    UNIQUE (edicion_id, codigo)
);

CREATE INDEX idx_secciones_edicion ON secciones (edicion_id);
CREATE INDEX idx_materias_edicion  ON materias  (edicion_id);

-- ============================================================================
-- TOKENS DE UN SOLO USO (confirmación de cuenta y recuperación de contraseña)
-- ----------------------------------------------------------------------------
-- El token se guarda en claro a propósito: es un valor aleatorio de un solo uso
-- con caducidad, y así el administrador puede auditar qué enlaces se emitieron.
-- Nunca da acceso por sí mismo: solo confirma la titularidad del correo.
-- ============================================================================
CREATE TABLE tokens_correo (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id        INTEGER NOT NULL,
    token             TEXT    NOT NULL UNIQUE,
    tipo              TEXT    NOT NULL DEFAULT 'CONFIRMACION'
                              CHECK (tipo IN ('CONFIRMACION', 'RECUPERACION')),
    usado             INTEGER NOT NULL DEFAULT 0 CHECK (usado IN (0, 1)),
    fecha_creacion    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_expiracion  TEXT    NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios_sistema(id) ON DELETE CASCADE
);

-- ============================================================================
-- 6. prestatarios — Personas que reciben reservas o préstamos
--    (no necesitan cuenta en el sistema)
-- ============================================================================
CREATE TABLE prestatarios (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    edicion_id INTEGER NOT NULL DEFAULT 1,
    cedula    TEXT NOT NULL,
    nombre    TEXT NOT NULL,
    apellido  TEXT NOT NULL,
    tipo      TEXT NOT NULL CHECK (tipo IN ('ESTUDIANTE', 'PROFESOR', 'EMPLEADO', 'OTRO')),
    telefono  TEXT,
    email     TEXT,
    estado    TEXT NOT NULL DEFAULT 'ACTIVO'
              CHECK (estado IN ('ACTIVO', 'INACTIVO')),
    UNIQUE (edicion_id, cedula)
);

-- ============================================================================
-- 7. categorias — Clasificación de los equipos (GLOBAL, sin edicion_id)
-- ============================================================================
CREATE TABLE categorias (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre       TEXT NOT NULL UNIQUE,
    descripcion  TEXT
);

-- ============================================================================
-- 8. laboratorios — Espacios físicos reservables
-- ============================================================================
CREATE TABLE laboratorios (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    edicion_id                INTEGER NOT NULL DEFAULT 1,
    codigo                    TEXT    NOT NULL,
    nombre                    TEXT    NOT NULL,
    ubicacion                 TEXT    NOT NULL,
    capacidad                 INTEGER NOT NULL CHECK (capacidad > 0),
    -- Duración estándar de una reserva: 70 minutos (1 h 10 min).
    duracion_estandar_minutos INTEGER NOT NULL DEFAULT 70
                              CHECK (duracion_estandar_minutos > 0),
    estado                    TEXT    NOT NULL DEFAULT 'DISPONIBLE'
                              CHECK (estado IN ('DISPONIBLE', 'MANTENIMIENTO', 'INACTIVO')),
    UNIQUE (edicion_id, codigo)
);

-- ============================================================================
-- 9. equipos — Recursos individuales prestables
-- ============================================================================
CREATE TABLE equipos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    edicion_id      INTEGER NOT NULL DEFAULT 1,
    codigo          TEXT NOT NULL,
    nombre          TEXT NOT NULL,
    categoria_id    INTEGER,
    marca           TEXT,
    modelo          TEXT,
    serial          TEXT,
    laboratorio_id  INTEGER,
    estado          TEXT NOT NULL DEFAULT 'DISPONIBLE'
                    CHECK (estado IN ('DISPONIBLE', 'PRESTADO', 'MANTENIMIENTO', 'DANADO', 'INACTIVO')),
    FOREIGN KEY (categoria_id)   REFERENCES categorias(id),
    FOREIGN KEY (laboratorio_id) REFERENCES laboratorios(id),
    UNIQUE (edicion_id, codigo),
    UNIQUE (edicion_id, serial)
);

-- ============================================================================
-- 10. reservas — Reservas de laboratorios por franja horaria
--     Regla de negocio: un mismo laboratorio no puede tener dos reservas
--     (CONFIRMADA/ACTIVA) cuyos intervalos se superpongan.
-- ============================================================================
CREATE TABLE reservas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    edicion_id          INTEGER NOT NULL DEFAULT 1,
    laboratorio_id      INTEGER NOT NULL,
    prestatario_id      INTEGER NOT NULL,
    -- Usuario del sistema que registró la reserva (se toma de la sesión,
    -- nunca del formulario enviado por el navegador).
    usuario_sistema_id  INTEGER NOT NULL,
    fecha               TEXT    NOT NULL,          -- AAAA-MM-DD
    hora_inicio         TEXT    NOT NULL,          -- HH:MM
    hora_fin            TEXT    NOT NULL,          -- HH:MM
    duracion_minutos    INTEGER NOT NULL CHECK (duracion_minutos > 0),
    estado              TEXT    NOT NULL DEFAULT 'CONFIRMADA'
                        CHECK (estado IN ('CONFIRMADA', 'ACTIVA', 'FINALIZADA', 'CANCELADA')),
    observaciones       TEXT,
    fecha_registro      TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- --- Multi-edición: secciones, materias y horarios (Fase 2) ---
    tipo_reserva        TEXT    NOT NULL DEFAULT 'PUNTUAL'
                        CHECK (tipo_reserva IN ('PUNTUAL', 'SEMESTRAL')),
    seccion_id          INTEGER,                    -- FK opcional a secciones
    materia_id          INTEGER,                    -- FK opcional a materias
    dia_semana          INTEGER                    -- 0=Lunes..5=Sábado (semestral)
                        CHECK (dia_semana IS NULL OR dia_semana BETWEEN 0 AND 5),
    periodo_academico   TEXT,                       -- «2026-2»
    cantidad_estudiantes INTEGER
                        CHECK (cantidad_estudiantes IS NULL OR cantidad_estudiantes >= 0),
    FOREIGN KEY (laboratorio_id)     REFERENCES laboratorios(id),
    FOREIGN KEY (prestatario_id)     REFERENCES prestatarios(id),
    FOREIGN KEY (usuario_sistema_id) REFERENCES usuarios_sistema(id),
    FOREIGN KEY (seccion_id)         REFERENCES secciones(id),
    FOREIGN KEY (materia_id)         REFERENCES materias(id)
);

-- ============================================================================
-- 11. prestamos_equipos — Préstamos individuales de equipos y sus devoluciones
--     Al prestar:  equipos.estado = 'PRESTADO'
--     Al devolver: equipos.estado = 'DISPONIBLE'
-- ============================================================================
CREATE TABLE prestamos_equipos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    edicion_id          INTEGER NOT NULL DEFAULT 1,
    equipo_id           INTEGER NOT NULL,
    prestatario_id      INTEGER NOT NULL,
    usuario_sistema_id  INTEGER NOT NULL,
    fecha_prestamo      TEXT    NOT NULL,
    fecha_devolucion    TEXT,
    estado              TEXT    NOT NULL DEFAULT 'ACTIVO'
                        CHECK (estado IN ('ACTIVO', 'DEVUELTO', 'CANCELADO')),
    observaciones       TEXT,
    FOREIGN KEY (equipo_id)          REFERENCES equipos(id),
    FOREIGN KEY (prestatario_id)     REFERENCES prestatarios(id),
    FOREIGN KEY (usuario_sistema_id) REFERENCES usuarios_sistema(id)
);

-- ============================================================================
-- 12. auditoria — Registro de actividad (quién hizo qué y cuándo)
--
--    Nota de diseño: ``usuario_id`` NO tiene clave foránea a propósito. Un
--    registro de auditoría debe sobrevivir a la eliminación del usuario y
--    conservar su nombre como evidencia histórica. Por eso se guarda también
--    ``usuario_username`` de forma desnormalizada.
-- ============================================================================
CREATE TABLE auditoria (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    edicion_id        INTEGER,
    usuario_id        INTEGER,
    usuario_username  TEXT NOT NULL,
    accion            TEXT NOT NULL
                      CHECK (accion IN ('CREAR', 'ACTUALIZAR', 'ELIMINAR', 'DEVOLVER',
                                        'CANCELAR', 'ACCEDER', 'SALIR', 'EXPORTAR')),
    entidad           TEXT NOT NULL,
    entidad_id        INTEGER,
    descripcion       TEXT NOT NULL,
    direccion_ip      TEXT,
    fecha             TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- Índices — Aceleran las consultas más frecuentes (listados, búsqueda de
-- solapamientos, préstamos activos y filtros del historial).
-- ============================================================================
CREATE INDEX idx_reservas_lab_fecha      ON reservas (laboratorio_id, fecha);
CREATE INDEX idx_reservas_prestatario    ON reservas (prestatario_id);
CREATE INDEX idx_reservas_usuario        ON reservas (usuario_sistema_id);
-- Índices de la Fase 2: choques por sección, materia, profesor y laboratorio
CREATE INDEX idx_reservas_seccion        ON reservas (seccion_id);
CREATE INDEX idx_reservas_materia        ON reservas (materia_id);
CREATE INDEX idx_reservas_profesor_fecha ON reservas (prestatario_id, dia_semana);
CREATE INDEX idx_reservas_lab_dia        ON reservas (laboratorio_id, dia_semana);
CREATE INDEX idx_prestamos_equipo_estado ON prestamos_equipos (equipo_id, estado);
CREATE INDEX idx_prestamos_prestatario   ON prestamos_equipos (prestatario_id);
CREATE INDEX idx_equipos_categoria       ON equipos (categoria_id);
CREATE INDEX idx_equipos_laboratorio     ON equipos (laboratorio_id);
CREATE INDEX idx_auditoria_fecha         ON auditoria (fecha);
CREATE INDEX idx_auditoria_entidad       ON auditoria (entidad, entidad_id);
CREATE INDEX idx_auditoria_usuario       ON auditoria (usuario_id);
CREATE INDEX idx_tokens_token            ON tokens_correo (token);
CREATE INDEX idx_tokens_usuario          ON tokens_correo (usuario_id, tipo);
-- Índices por edición (nuevos)
CREATE INDEX idx_prestatarios_edicion    ON prestatarios (edicion_id);
CREATE INDEX idx_laboratorios_edicion    ON laboratorios (edicion_id);
CREATE INDEX idx_equipos_edicion         ON equipos (edicion_id);
CREATE INDEX idx_reservas_edicion        ON reservas (edicion_id);
CREATE INDEX idx_prestamos_edicion       ON prestamos_equipos (edicion_id);
CREATE INDEX idx_auditoria_edicion       ON auditoria (edicion_id);

-- ============================================================================
-- DATOS INICIALES Y DE PRUEBA
-- ============================================================================

-- ---------------------------------------------------------------------------
-- Usuarios del sistema.
-- Las contraseñas están almacenadas como hash (nunca en texto plano).
--
--   Usuario     Contraseña        Rol
--   ---------   ---------------   -------------
--   admin       Admin123!         ADMINISTRADOR
--   operador    Operador123!      OPERADOR
-- ---------------------------------------------------------------------------
INSERT INTO usuarios_sistema
    (nombre, apellido, username, email, password_hash, rol, estado)
VALUES
    ('Lorenzo', 'Roca', 'admin', 'admin@techloan.local',
     'scrypt:32768:8:1$LNEik1DgfqIB2lLs$1482d433e425642e2694bb056a9f4ceac5326cb11f6d2cade34d028d8b1d16d2687a77513068cfb9c5084160ffc6ad0d63b5eed4fbd932b29cd406c0e01a2735',
     'ADMINISTRADOR', 'ACTIVO'),
    ('Ana', 'Pérez', 'operador', 'operador@techloan.local',
     'scrypt:32768:8:1$BZlaJYBFh8ZhWvt3$cfe5ab53161141e2223714a3edb1b647a1259e8e3f93fe8ebe5aef5fc322e34d3ace52fd00093058a24f7c926dd27132b5d15a9c67d80e1e109146a281da1383',
     'OPERADOR', 'ACTIVO');

-- ---------------------------------------------------------------------------
-- Ediciones iniciales.
-- ---------------------------------------------------------------------------
INSERT INTO ediciones (nombre, slug, descripcion, estado, version_actual)
VALUES
    ('TechLoan Base', 'base', 'Edición genérica del sistema de gestión de laboratorios.', 'ACTIVA', 1),
    ('IUTEPI LABS', 'iutepi-labs', 'Edición a medida para gestión de horarios y secciones de laboratorios IUTEPI.', 'ACTIVA', 1);

-- ---------------------------------------------------------------------------
-- Versiones iniciales de cada edición.
-- ---------------------------------------------------------------------------
INSERT INTO edicion_versiones (edicion_id, numero_version, nombre_version, estado, creado_por, notas_cambios, snapshot_json)
VALUES
    (1, 1, 'Inicial', 'ACTIVA', 1, 'Versión base del sistema.', '{}'),
    (2, 1, 'Inicial', 'ACTIVA', 1, 'Versión inicial de IUTEPI LABS.', '{}');

-- ---------------------------------------------------------------------------
-- Asignar usuarios a ediciones.
-- ---------------------------------------------------------------------------
INSERT INTO usuarios_ediciones (usuario_sistema_id, edicion_id, rol_en_edicion)
VALUES
    (1, 1, 'ADMINISTRADOR_EDICION'),
    (1, 2, 'ADMINISTRADOR_EDICION'),
    (2, 1, 'OPERADOR'),
    (2, 2, 'OPERADOR');

-- ---------------------------------------------------------------------------
-- Prestatarios (4 registros de prueba, edición 1).
-- ---------------------------------------------------------------------------
INSERT INTO prestatarios (edicion_id, cedula, nombre, apellido, tipo, telefono, email, estado)
VALUES
    (1, 'V-12345678', 'María',    'González', 'ESTUDIANTE', '0414-1111111', 'maria.gonzalez@correo.com',  'ACTIVO'),
    (1, 'V-23456789', 'José',     'Tarazón',  'PROFESOR',   '0414-2222222', 'jose.tarazon@correo.com',    'ACTIVO'),
    (1, 'V-34567890', 'Sleither', 'Vásquez',  'ESTUDIANTE', '0414-3333333', 'sleither.vasquez@correo.com','ACTIVO'),
    (1, 'V-45678901', 'Adrián',   'Cedeño',   'EMPLEADO',   '0414-4444444', 'adrian.cedeno@correo.com',   'ACTIVO');

-- ---------------------------------------------------------------------------
-- Categorías de equipos (3 registros de prueba, GLOBAL).
-- ---------------------------------------------------------------------------
INSERT INTO categorias (nombre, descripcion)
VALUES
    ('Computación', 'Equipos de cómputo, monitores y periféricos'),
    ('Audiovisual', 'Proyectores, cámaras y equipos de sonido'),
    ('Redes',       'Routers, switches y equipos de conectividad');

-- ---------------------------------------------------------------------------
-- Laboratorios (3 registros de prueba, edición 1).
-- ---------------------------------------------------------------------------
INSERT INTO laboratorios
    (edicion_id, codigo, nombre, ubicacion, capacidad, duracion_estandar_minutos, estado)
VALUES
    (1, 'LAB-01', 'Laboratorio de Informática 1', 'Edificio A - Planta Baja', 30, 70, 'DISPONIBLE'),
    (1, 'LAB-02', 'Laboratorio de Redes',         'Edificio A - Planta Alta', 20, 90, 'DISPONIBLE'),
    (1, 'LAB-03', 'Laboratorio de Electrónica',   'Edificio B - Planta Baja', 25, 70, 'MANTENIMIENTO');

-- ---------------------------------------------------------------------------
-- Equipos (4 registros de prueba, edición 1).
-- EQ-003 aparece como PRESTADO porque tiene un préstamo ACTIVO más abajo.
-- ---------------------------------------------------------------------------
INSERT INTO equipos
    (edicion_id, codigo, nombre, categoria_id, marca, modelo, serial, laboratorio_id, estado)
VALUES
    (1, 'EQ-001', 'Laptop Dell Latitude',     1, 'Dell',  'Latitude 3420',   'SN-DL-001', 1, 'DISPONIBLE'),
    (1, 'EQ-002', 'Proyector Epson',          2, 'Epson', 'PowerLite X49',   'SN-EP-002', 2, 'DISPONIBLE'),
    (1, 'EQ-003', 'Switch Cisco 24 puertos',  3, 'Cisco', 'Catalyst 2960',   'SN-CS-003', 2, 'PRESTADO'),
    (1, 'EQ-004', 'Monitor LG 24 pulgadas',   1, 'LG',    '24MK430H-B',      'SN-LG-004', 1, 'DISPONIBLE');

-- ---------------------------------------------------------------------------
-- Reservas (3 registros de prueba, edición 1).
--
-- Las fechas se calculan con date('now','localtime','+N days') para que las
-- reservas de demostración queden SIEMPRE en el futuro.
-- ---------------------------------------------------------------------------
INSERT INTO reservas
    (edicion_id, laboratorio_id, prestatario_id, usuario_sistema_id, fecha, hora_inicio,
     hora_fin, duracion_minutos, estado, observaciones)
VALUES
    (1, 1, 1, 1, date('now','localtime','+7 days'), '08:00', '09:10', 70, 'CONFIRMADA', 'Práctica de programación'),
    (1, 1, 2, 1, date('now','localtime','+7 days'), '09:10', '10:20', 70, 'CONFIRMADA', 'Clase de bases de datos'),
    (1, 2, 3, 2, date('now','localtime','+8 days'), '14:00', '15:30', 90, 'CONFIRMADA', 'Práctica de configuración de redes');

-- ---------------------------------------------------------------------------
-- Préstamos de equipos (2 registros de prueba, edición 1).
-- ---------------------------------------------------------------------------
INSERT INTO prestamos_equipos
    (edicion_id, equipo_id, prestatario_id, usuario_sistema_id, fecha_prestamo,
     fecha_devolucion, estado, observaciones)
VALUES
    (1, 3, 3, 2, datetime('now','localtime','-1 day'),  NULL,                                    'ACTIVO',   'Préstamo para práctica de redes'),
    (1, 2, 1, 1, datetime('now','localtime','-18 days'), datetime('now','localtime','-16 days'), 'DEVUELTO', 'Préstamo para exposición');

-- ---------------------------------------------------------------------------
-- Registro de actividad (5 registros de prueba, edición 1).
-- ---------------------------------------------------------------------------
INSERT INTO auditoria
    (edicion_id, usuario_id, usuario_username, accion, entidad, entidad_id, descripcion, direccion_ip, fecha)
VALUES
    (1, 1, 'admin', 'CREAR', 'prestatario', 1, 'Alta del prestatario V-12345678 (María González)', '127.0.0.1', datetime('now','localtime','-20 days')),
    (1, 1, 'admin', 'CREAR', 'laboratorio', 1, 'Alta del laboratorio LAB-01 (Laboratorio de Informática 1)', '127.0.0.1', datetime('now','localtime','-19 days')),
    (1, 1, 'admin', 'CREAR', 'equipo', 2, 'Alta del equipo EQ-002 (Proyector Epson)', '127.0.0.1', datetime('now','localtime','-18 days')),
    (1, 2, 'operador', 'DEVOLVER', 'prestamo', 2, 'Devolución del equipo EQ-002 (Proyector Epson)', '127.0.0.1', datetime('now','localtime','-16 days')),
    (1, 2, 'operador', 'CREAR', 'prestamo', 1, 'Préstamo del equipo EQ-003 (Switch Cisco 24 puertos) a V-34567890', '127.0.0.1', datetime('now','localtime','-1 day'));

-- ============================================================================
-- DATOS DE DEMOSTRACIÓN DE LA EDICIÓN «IUTEPI LABS» (edicion_id = 2)
--
-- Pensados para que el profesor Nelson pruebe el horario semestral de inmediato:
-- secciones, materias y laboratorios con distinta capacidad, más una asignación
-- SEMESTRAL (clase regular) y una reserva PUNTUAL (evaluación). Los id se
-- resuelven por subconsulta para no depender del orden de AUTOINCREMENT.
-- ============================================================================

-- Profesores de la edición IUTEPI LABS.
INSERT INTO prestatarios
    (edicion_id, cedula, nombre, apellido, tipo, telefono, email, estado)
VALUES
    (2, 'V-10000001', 'Nelson', 'Mendoza', 'PROFESOR', '0414-1000001', 'nelson.mendoza@iutepi.edu', 'ACTIVO'),
    (2, 'V-10000002', 'Carla',  'Duarte',   'PROFESOR', '0414-1000002', 'carla.duarte@iutepi.edu',   'ACTIVO');

-- Laboratorios de la edición IUTEPI LABS con capacidades 20, 30 y 40.
-- Reusan los códigos «LAB-*» de la edición base: con el UNIQUE por edición ya
-- no colisionan (demuestra el aislamiento entre ediciones).
INSERT INTO laboratorios
    (edicion_id, codigo, nombre, ubicacion, capacidad, duracion_estandar_minutos, estado)
VALUES
    (2, 'LAB-01', 'Laboratorio de Sistemas I',      'Edificio IUTEPI - PB', 20, 70, 'DISPONIBLE'),
    (2, 'LAB-02', 'Laboratorio de Redes IUTEPI',    'Edificio IUTEPI - PA', 30, 70, 'DISPONIBLE'),
    (2, 'LAB-03', 'Laboratorio de Cómputo General', 'Edificio IUTEPI - P2', 40, 70, 'DISPONIBLE');

-- Secciones: «SA» en 1.º y 2.º semestre (ya no chocan) + subsección «SA-A».
INSERT INTO secciones
    (edicion_id, codigo_seccion, semestre, periodo_academico, carrera_o_escuela, cantidad_estimada, estado)
VALUES
    (2, 'SA',   1, '2026-2', 'Escuela de Sistemas', 25, 'ACTIVA'),
    (2, 'SA',   2, '2026-2', 'Escuela de Sistemas', 18, 'ACTIVA'),
    (2, 'SA-A', 1, '2026-2', 'Escuela de Sistemas', 12, 'ACTIVA');

-- Materias de Escuela de Sistemas y Escuelas Generales.
INSERT INTO materias
    (edicion_id, codigo, nombre, escuela, semestre, estado)
VALUES
    (2, 'SIS-101', 'Programación I',    'Escuela de Sistemas',   1, 'ACTIVA'),
    (2, 'SIS-204', 'Bases de Datos',    'Escuela de Sistemas',   2, 'ACTIVA'),
    (2, 'GEN-110', 'Matemática General','Escuelas Generales',    1, 'ACTIVA');

-- Asignación SEMESTRAL: clase regular de Programación I (sección SA, 1.er semestre),
-- todos los lunes (dia_semana=0) de 07:00 a 09:10 en LAB-01 (capacidad 20, 25 estudiantes
-- de referencia de la sección; el control de capacidad se valida al crear/editar).
INSERT INTO reservas
    (edicion_id, tipo_reserva, laboratorio_id, prestatario_id, usuario_sistema_id,
     fecha, dia_semana, periodo_academico, seccion_id, materia_id, cantidad_estudiantes,
     hora_inicio, hora_fin, duracion_minutos, estado, observaciones)
VALUES
    (2, 'SEMESTRAL',
     (SELECT id FROM laboratorios WHERE edicion_id=2 AND codigo='LAB-01'),
     (SELECT id FROM prestatarios WHERE edicion_id=2 AND cedula='V-10000001'), 1,
     date('now','localtime','+0 days'), 0, '2026-2',
     (SELECT id FROM secciones WHERE edicion_id=2 AND codigo_seccion='SA' AND semestre=1),
     (SELECT id FROM materias  WHERE edicion_id=2 AND codigo='SIS-101'),
     25, '07:00', '09:10', 140, 'CONFIRMADA', 'Clase semestral de Programación I (SA)');

-- Reserva PUNTUAL: evaluación en LAB-02, dentro del mismo periodo.
INSERT INTO reservas
    (edicion_id, tipo_reserva, laboratorio_id, prestatario_id, usuario_sistema_id,
     fecha, dia_semana, periodo_academico, seccion_id, materia_id, cantidad_estudiantes,
     hora_inicio, hora_fin, duracion_minutos, estado, observaciones)
VALUES
    (2, 'PUNTUAL',
     (SELECT id FROM laboratorios WHERE edicion_id=2 AND codigo='LAB-02'),
     (SELECT id FROM prestatarios WHERE edicion_id=2 AND cedula='V-10000002'), 1,
     date('now','localtime','+30 days'), NULL, '2026-2',
     NULL, NULL, 30, '14:00', '16:00', 120, 'CONFIRMADA', 'Evaluación puntual (LAB-02)');
