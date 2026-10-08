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
DROP TABLE IF EXISTS auditoria;
DROP TABLE IF EXISTS tokens_correo;
DROP TABLE IF EXISTS prestamos_equipos;
DROP TABLE IF EXISTS reservas;
DROP TABLE IF EXISTS equipos;
DROP TABLE IF EXISTS categorias;
DROP TABLE IF EXISTS laboratorios;
DROP TABLE IF EXISTS prestatarios;
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
-- 2. prestatarios — Personas que reciben reservas o préstamos
--    (no necesitan cuenta en el sistema)
-- ============================================================================
CREATE TABLE prestatarios (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    cedula    TEXT NOT NULL UNIQUE,
    nombre    TEXT NOT NULL,
    apellido  TEXT NOT NULL,
    tipo      TEXT NOT NULL CHECK (tipo IN ('ESTUDIANTE', 'PROFESOR', 'EMPLEADO', 'OTRO')),
    telefono  TEXT,
    email     TEXT,
    estado    TEXT NOT NULL DEFAULT 'ACTIVO'
              CHECK (estado IN ('ACTIVO', 'INACTIVO'))
);

-- ============================================================================
-- 3. categorias — Clasificación de los equipos
-- ============================================================================
CREATE TABLE categorias (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre       TEXT NOT NULL UNIQUE,
    descripcion  TEXT
);

-- ============================================================================
-- 4. laboratorios — Espacios físicos reservables
-- ============================================================================
CREATE TABLE laboratorios (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo                    TEXT    NOT NULL UNIQUE,
    nombre                    TEXT    NOT NULL,
    ubicacion                 TEXT    NOT NULL,
    capacidad                 INTEGER NOT NULL CHECK (capacidad > 0),
    -- Duración estándar de una reserva: 70 minutos (1 h 10 min).
    duracion_estandar_minutos INTEGER NOT NULL DEFAULT 70
                              CHECK (duracion_estandar_minutos > 0),
    estado                    TEXT    NOT NULL DEFAULT 'DISPONIBLE'
                              CHECK (estado IN ('DISPONIBLE', 'MANTENIMIENTO', 'INACTIVO'))
);

-- ============================================================================
-- 5. equipos — Recursos individuales prestables
-- ============================================================================
CREATE TABLE equipos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo          TEXT NOT NULL UNIQUE,
    nombre          TEXT NOT NULL,
    categoria_id    INTEGER,
    marca           TEXT,
    modelo          TEXT,
    serial          TEXT UNIQUE,
    laboratorio_id  INTEGER,
    estado          TEXT NOT NULL DEFAULT 'DISPONIBLE'
                    CHECK (estado IN ('DISPONIBLE', 'PRESTADO', 'MANTENIMIENTO', 'DANADO', 'INACTIVO')),
    FOREIGN KEY (categoria_id)   REFERENCES categorias(id),
    FOREIGN KEY (laboratorio_id) REFERENCES laboratorios(id)
);

-- ============================================================================
-- 6. reservas — Reservas de laboratorios por franja horaria
--    Regla de negocio: un mismo laboratorio no puede tener dos reservas
--    (CONFIRMADA/ACTIVA) cuyos intervalos se superpongan.
-- ============================================================================
CREATE TABLE reservas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
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
    FOREIGN KEY (laboratorio_id)     REFERENCES laboratorios(id),
    FOREIGN KEY (prestatario_id)     REFERENCES prestatarios(id),
    FOREIGN KEY (usuario_sistema_id) REFERENCES usuarios_sistema(id)
);

-- ============================================================================
-- 7. prestamos_equipos — Préstamos individuales de equipos y sus devoluciones
--    Al prestar:  equipos.estado = 'PRESTADO'
--    Al devolver: equipos.estado = 'DISPONIBLE'
-- ============================================================================
CREATE TABLE prestamos_equipos (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
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
-- 8. auditoria — Registro de actividad (quién hizo qué y cuándo)
--
--    Nota de diseño: ``usuario_id`` NO tiene clave foránea a propósito. Un
--    registro de auditoría debe sobrevivir a la eliminación del usuario y
--    conservar su nombre como evidencia histórica. Por eso se guarda también
--    ``usuario_username`` de forma desnormalizada.
-- ============================================================================
CREATE TABLE auditoria (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
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
CREATE INDEX idx_prestamos_equipo_estado ON prestamos_equipos (equipo_id, estado);
CREATE INDEX idx_prestamos_prestatario   ON prestamos_equipos (prestatario_id);
CREATE INDEX idx_equipos_categoria       ON equipos (categoria_id);
CREATE INDEX idx_equipos_laboratorio     ON equipos (laboratorio_id);
CREATE INDEX idx_auditoria_fecha         ON auditoria (fecha);
CREATE INDEX idx_auditoria_entidad       ON auditoria (entidad, entidad_id);
CREATE INDEX idx_auditoria_usuario       ON auditoria (usuario_id);
CREATE INDEX idx_tokens_token            ON tokens_correo (token);
CREATE INDEX idx_tokens_usuario          ON tokens_correo (usuario_id, tipo);

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
-- Prestatarios (4 registros de prueba).
-- ---------------------------------------------------------------------------
INSERT INTO prestatarios (cedula, nombre, apellido, tipo, telefono, email, estado)
VALUES
    ('V-12345678', 'María',    'González', 'ESTUDIANTE', '0414-1111111', 'maria.gonzalez@correo.com',  'ACTIVO'),
    ('V-23456789', 'José',     'Tarazón',  'PROFESOR',   '0414-2222222', 'jose.tarazon@correo.com',    'ACTIVO'),
    ('V-34567890', 'Sleither', 'Vásquez',  'ESTUDIANTE', '0414-3333333', 'sleither.vasquez@correo.com','ACTIVO'),
    ('V-45678901', 'Adrián',   'Cedeño',   'EMPLEADO',   '0414-4444444', 'adrian.cedeno@correo.com',   'ACTIVO');

-- ---------------------------------------------------------------------------
-- Categorías de equipos (3 registros de prueba).
-- ---------------------------------------------------------------------------
INSERT INTO categorias (nombre, descripcion)
VALUES
    ('Computación', 'Equipos de cómputo, monitores y periféricos'),
    ('Audiovisual', 'Proyectores, cámaras y equipos de sonido'),
    ('Redes',       'Routers, switches y equipos de conectividad');

-- ---------------------------------------------------------------------------
-- Laboratorios (3 registros de prueba).
-- ---------------------------------------------------------------------------
INSERT INTO laboratorios
    (codigo, nombre, ubicacion, capacidad, duracion_estandar_minutos, estado)
VALUES
    ('LAB-01', 'Laboratorio de Informática 1', 'Edificio A - Planta Baja', 30, 70, 'DISPONIBLE'),
    ('LAB-02', 'Laboratorio de Redes',         'Edificio A - Planta Alta', 20, 90, 'DISPONIBLE'),
    ('LAB-03', 'Laboratorio de Electrónica',   'Edificio B - Planta Baja', 25, 70, 'MANTENIMIENTO');

-- ---------------------------------------------------------------------------
-- Equipos (4 registros de prueba).
-- EQ-003 aparece como PRESTADO porque tiene un préstamo ACTIVO más abajo:
-- los datos de prueba respetan la coherencia de estados del sistema.
-- ---------------------------------------------------------------------------
INSERT INTO equipos
    (codigo, nombre, categoria_id, marca, modelo, serial, laboratorio_id, estado)
VALUES
    ('EQ-001', 'Laptop Dell Latitude',     1, 'Dell',  'Latitude 3420',   'SN-DL-001', 1, 'DISPONIBLE'),
    ('EQ-002', 'Proyector Epson',          2, 'Epson', 'PowerLite X49',   'SN-EP-002', 2, 'DISPONIBLE'),
    ('EQ-003', 'Switch Cisco 24 puertos',  3, 'Cisco', 'Catalyst 2960',   'SN-CS-003', 2, 'PRESTADO'),
    ('EQ-004', 'Monitor LG 24 pulgadas',   1, 'LG',    '24MK430H-B',      'SN-LG-004', 1, 'DISPONIBLE');

-- ---------------------------------------------------------------------------
-- Reservas (3 registros de prueba).
--
-- Las fechas se calculan con date('now','localtime','+N days') para que las
-- reservas de demostración queden SIEMPRE en el futuro, sin importar cuándo se
-- ejecute este script. Así la demostración nunca muestra datos vencidos.
--
-- LAB-01 (en 7 días) tiene dos reservas ADYACENTES (08:00-09:10 y 09:10-10:20):
-- no se superponen, por lo que son válidas. Sirven para demostrar la regla de
-- solapamiento: una tercera reserva a las 08:30 sería rechazada, y una a las
-- 10:20 sería aceptada (adyacencia exacta).
-- ---------------------------------------------------------------------------
INSERT INTO reservas
    (laboratorio_id, prestatario_id, usuario_sistema_id, fecha, hora_inicio,
     hora_fin, duracion_minutos, estado, observaciones)
VALUES
    (1, 1, 1, date('now','localtime','+7 days'), '08:00', '09:10', 70, 'CONFIRMADA', 'Práctica de programación'),
    (1, 2, 1, date('now','localtime','+7 days'), '09:10', '10:20', 70, 'CONFIRMADA', 'Clase de bases de datos'),
    (2, 3, 2, date('now','localtime','+8 days'), '14:00', '15:30', 90, 'CONFIRMADA', 'Práctica de configuración de redes');

-- ---------------------------------------------------------------------------
-- Préstamos de equipos (2 registros de prueba: uno activo y uno devuelto).
--
-- El préstamo activo se registró ayer y el equipo EQ-003 sigue en estado
-- PRESTADO. El préstamo devuelto se cerró hace unas semanas, para que el
-- historial muestre una devolución con su fecha.
-- ---------------------------------------------------------------------------
INSERT INTO prestamos_equipos
    (equipo_id, prestatario_id, usuario_sistema_id, fecha_prestamo,
     fecha_devolucion, estado, observaciones)
VALUES
    (3, 3, 2, datetime('now','localtime','-1 day'),  NULL,                                    'ACTIVO',   'Préstamo para práctica de redes'),
    (2, 1, 1, datetime('now','localtime','-18 days'), datetime('now','localtime','-16 days'), 'DEVUELTO', 'Préstamo para exposición');

-- ---------------------------------------------------------------------------
-- Registro de actividad (5 registros de prueba).
-- Reflejan las operaciones que originaron los datos anteriores, para que la
-- página de auditoría muestre información real desde el primer arranque.
-- ---------------------------------------------------------------------------
INSERT INTO auditoria
    (usuario_id, usuario_username, accion, entidad, entidad_id, descripcion, direccion_ip, fecha)
VALUES
    (1, 'admin', 'CREAR', 'prestatario', 1, 'Alta del prestatario V-12345678 (María González)', '127.0.0.1', datetime('now','localtime','-20 days')),
    (1, 'admin', 'CREAR', 'laboratorio', 1, 'Alta del laboratorio LAB-01 (Laboratorio de Informática 1)', '127.0.0.1', datetime('now','localtime','-19 days')),
    (1, 'admin', 'CREAR', 'equipo', 2, 'Alta del equipo EQ-002 (Proyector Epson)', '127.0.0.1', datetime('now','localtime','-18 days')),
    (2, 'operador', 'DEVOLVER', 'prestamo', 2, 'Devolución del equipo EQ-002 (Proyector Epson)', '127.0.0.1', datetime('now','localtime','-16 days')),
    (2, 'operador', 'CREAR', 'prestamo', 1, 'Préstamo del equipo EQ-003 (Switch Cisco 24 puertos) a V-34567890', '127.0.0.1', datetime('now','localtime','-1 day'));
