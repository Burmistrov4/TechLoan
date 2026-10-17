# Especificación: Ediciones, versiones, peticiones del profesor Nelson y Visor Técnico SQLite3

**Documento de traspaso para IA.** Escrito para que otra IA (o desarrollador)
pueda implementar la ampliación sin haber visto el proyecto. Incluye diagnóstico
real del estado actual, decisiones de diseño revisadas, modelo de datos,
archivos a tocar y orden de trabajo.

Proyecto: **TechLoan** — Flask + SQLite3 + Jinja2 + HTML/CSS/JS Vanilla.
Desplegado en `lorodev.pythonanywhere.com`.

---

## 0. Estado de implementación (actualizado 2026-10-17)

- **Fase 1 — Multi-edición, versiones con snapshot y Visor SQLite3: COMPLETADA**
  (commit local `eede99f`). Incluye `ediciones`, `edicion_versiones`
  (`snapshot_json`), `edicion_configuracion`, `usuarios_ediciones`, `edicion_id`
  en las tablas operativas con `UNIQUE (edicion_id, …)`, selector de edición
  (`POST /ediciones/cambiar` + context processor), `edicion_service`,
  `db_inspector_service` y migración idempotente (`_migrar`) con
  `PRAGMA index_list/index_info` + `legacy_alter_table=ON`.

- **Fase 2 — Secciones, materias, reservas semestrales y motor de choques:
  COMPLETADA** (pendiente de commit). Estado real:

  - **Tablas nuevas** `secciones` y `materias`
    (`UNIQUE (edicion_id, codigo_seccion, semestre, periodo_academico,
    carrera_o_escuela)` y `UNIQUE (edicion_id, codigo)` respectivamente).
    Regex de `codigo_seccion`: `^[A-Z0-9]{1,4}(-[A-Z0-9]{1,3})?$` (admite `SA`,
    `SB`, `SA-A`, `SAA`).
  - **Columnas finales de `reservas`** (Fase 2): `tipo_reserva`
    `TEXT NOT NULL DEFAULT 'PUNTUAL' CHECK (tipo_reserva IN ('PUNTUAL','SEMESTRAL'))`,
    `seccion_id` (FK opcional), `materia_id` (FK opcional), `dia_semana`
    `INTEGER CHECK (dia_semana BETWEEN 0 AND 5)` (**0=Lunes..5=Sábado**, con
    `date.weekday()`), `periodo_academico TEXT`, `cantidad_estudiantes INTEGER`.
    `fecha` se mantiene también en semestrales como referencia de inicio.
    Índices: `idx_reservas_seccion`, `idx_reservas_materia`,
    `idx_reservas_profesor_fecha (prestatario_id, dia_semana)`,
    `idx_reservas_lab_dia (laboratorio_id, dia_semana)`.
  - **Motor de choques** (`reservation_service.create_reservation`): compara
    siempre en **minutos** (`_a_minutos`, corrige `'9:30'` vs `'09:00'`).
    - Puntual↔Puntual: misma `fecha` + bloque solapado (mismo `laboratorio_id`).
    - Semestral↔Semestral: mismo `dia_semana` **y** mismo `periodo_academico`.
    - **Cruce Puntual↔Semestral**: si `date.weekday(fecha) == dia_semana` y
      comparten `periodo_academico` (mismo laboratorio → choque).
    - **Choque de profesor**: mismo `prestatario_id` en distinto `laboratorio_id`
      y franja solapada, **solo si `tipo = 'PROFESOR'`** (un estudiante en dos
      laboratorios a la misma hora sigue permitido).
    - **Capacidad**: `cantidad_estudiantes` (o `seccion.cantidad_estimada`) vs
      `laboratorios.capacidad`; si excede, `ReservaInvalida` expone `.sugerencias`
      = laboratorios de la edición con cupo suficiente.
    - **Bloques horarios**: `obtener_bloques_edicion()` lee
      `edicion_configuracion['bloques_horarios']` (JSON `"HH:MM-HH:MM"`) con
      fallback a bloques de 70 min (07:00–21:00). No rechaza por bloque: solo
      informa/sugiere (así no rompe las reservas de 45/70 min existentes).
  - **UI**: CRUD de `secciones`/`materias` (listados + formularios, menú lateral)
    y formulario de reserva con conmutador **Semestral/Puntual**, campos
    condicionales (día, periodo, sección, materia), cantidad y bloque de
    laboratorios alternativos. Filtro Jinja `nombre_dia` (0..6 → español).
  - **Snapshot/restore** de versiones incluye `secciones` y `materias`
    (preserva ids).
  - **Seed IUTEPI LABS (edicion_id=2)**: secciones `SA` 1.º, `SA` 2.º y `SA-A`;
    3 materias; laboratorios con capacidad 20/30/40; 1 asignación SEMESTRAL y 1
    reserva PUNTUAL de ejemplo.

- **Fase 3 — Rejilla semanal y vista previa en vivo: COMPLETADA** (pendiente de
  commit al cierre de esta sesión). Incluye `rejilla_service.construir(edicion_id)`
  (días 0..5 × bloques, ocupación proyectada de semestrales y puntuales),
  `ReservationService.estado_reserva(...)` (evaluación sin guardar),
  `DisponibilidadService.estado(...)`, endpoint `GET /reservas/rejilla-semanal`
  (filtrado por la edición de la sesión) y la previsualización en el formulario
  (`pintarRejillaSemanal` en `static/js/main.js`) con celda fantasma y semáforo.
  El **Visor SQLite3** ahora tiene enlace en el menú (Administración, solo
  administrador). Verificado con 17/17 suites y Playwright.

- **Fase 4 — PDF con fpdf2: PENDIENTE.**

---

## 1. Contexto de negocio: ¿qué es una "edición"?

El landing de TechLoan tiene un plan "Avanzado — A medida" que menciona "varios
centros" e "informes a medida". El objetivo es hacer eso real: que el sistema
soporte **múltiples ediciones**, cada una siendo una instancia personalizada para
un profesor, escuela o centro.

**Ejemplo concreto:**
- **Edición base** (genérica): TechLoan tal como está hoy. Gestiona reservas y
  préstamos de equipos. Slug: `base`. Nombre: "TechLoan Base".
- **Edición "IUTEPI LABS"**: creada para las peticiones del profesor Nelson.
  Incluye secciones, semestres, asignación de horarios por materia, detección de
  choques de profesor, vista previa de rejilla semanal y exportación a PDF.
  Slug: `iutepi-labs`. Nombre: "IUTEPI LABS".

Cada edición:
- Tiene su **propia landing/sección** en el sistema.
- Tiene **control de versiones/revisiones**: se puede hacer una "copia" de una
  edición (v1 → v2), probar cambios, y decidir si la nueva versión reemplaza a
  la anterior o se archiva.
- Tiene **datos aislados** (laboratorios, reservas, secciones) o compartidos
  (usuarios, categorías de equipo).
- Aparece en el **apartado correspondiente** del panel: un selector de edición
  en la barra superior, y cada módulo filtra automáticamente por la edición
  activa.

---

## 2. Estado actual verificado (sobre el código real)

### 2.1 Esquema de base de datos

9 tablas. El esquema está **duplicado**: `schema.sql` (reconstrucción completa)
y `app/database.py` (`CREATE TABLE IF NOT EXISTS` + `_migrar()`). Cualquier
cambio debe hacerse en **ambos**.

```sql
-- Hallazgos reales de schema.sql y app/database.py:
--
-- usuarios_sistema: password_hash VARCHAR(255) NOT NULL
--                   username UNIQUE, email UNIQUE
--
-- prestatarios:     cedula TEXT NOT NULL UNIQUE
-- laboratorios:     codigo TEXT NOT NULL UNIQUE
-- equipos:          codigo TEXT NOT NULL UNIQUE, serial TEXT UNIQUE
-- categorias:       nombre TEXT NOT NULL UNIQUE
-- reservas:         sin UNIQUE
-- prestamos_equipos: sin UNIQUE
-- auditoria:        sin UNIQUE
```

Las restricciones UNIQUE actuales son **globales** (no por edición). Esto es un
problema: si la edición "TechLoan Base" tiene `LAB-01`, la edición "IUTEPI LABS"
no puede tener `LAB-01`.

### 2.2 Reservas hoy

```sql
CREATE TABLE reservas (
    id, laboratorio_id, prestatario_id, usuario_sistema_id,
    fecha TEXT, hora_inicio TEXT, hora_fin TEXT,
    duracion_minutos INTEGER, estado TEXT, observaciones TEXT
);
```

- El "profesor" es un `prestatario` con `tipo='PROFESOR'`.
- **No hay bloques horarios**: `hora_inicio`/`hora_fin` son texto libre.
- **Choque solo por laboratorio** (`has_overlap`): no comprueba si un profesor
  está en dos sitios a la vez.
- **Capacidad no se valida**: `laboratorios.capacidad` existe pero nunca se
  compara con cantidad de estudiantes (no existe ese campo).
- El solapamiento compara horas como texto (`hora_inicio < ?`). Funciona con
  `HH:MM` con cero; se rompe con `9:00` frente a `09:00`.
- **No existe `dia_semana`**: las reservas son puntuales por fecha. El profesor
  Nelson necesita horarios semestrales ("todos los lunes de 7:00 a 8:10").

### 2.3 Exportación

`requirements.txt`: Flask, Werkzeug, gunicorn. **Sin librerías de PDF.**
Exportación actual = CSV (9 rutas). El "comprobante" es HTML con
`window.print()`.

### 2.4 Vista previa

Existe línea de tiempo de un solo día y un solo laboratorio:
`pintarLineaTiempo()` en `main.js`, con datos de `/reservas/disponibilidad`.
No es rejilla semanal, ni multi-laboratorio, ni por profesor.

### 2.5 Roles

Solo `ADMINISTRADOR` y `OPERADOR`. **No existe COORDINADOR.**
El mapa de permisos está en `app/services/auth_service.py` → `can()`.

---

## 3. Arquitectura y convenciones (respetarlas)

- Rutas no escriben SQL; usan servicios (`@staticmethod`) en `app/services/`.
- Consultas parametrizadas (`?`), nunca f-strings.
- Eliminaciones solo por POST; todo POST exige CSRF (`_csrf_token`).
- Vistas que heredan `base_app.html` exigen sesión (`@login_required`).
- Parámetros de negocio en `app/config.py`.
- Esquema duplicado: cambios en `schema.sql` Y `app/database.py` (`init_database()`
  + `_migrar()`). Las columnas nuevas necesitan migración en producción.
- Tests aislados con `tests/_tempdb.py` (`preparar()`); nunca tocar
  `database/techloan.db` real.
- Texto en español de Venezuela.

---

## 4. Modelo de datos: ediciones y versiones (CORREGIDO)

### 4.1 Tabla maestra: ediciones

```sql
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
```

### 4.2 Control de versiones: edicion_versiones (CORREGIDO)

**Decisión arquitectónica:** las tablas operativas (`laboratorios`, `prestatarios`,
`secciones`, `materias`, `reservas`) **solo llevan `edicion_id`** (no `version_id`).
Esto mantiene las consultas CRUD limpias y rápidas. El versionado se hace mediante
**snapshot JSON** en la tabla de versiones.

Cuando se crea una nueva versión, el servicio `edicion_service.py` serializa en
`snapshot_json` el estado completo de la edición. Al restaurar una versión, se
deserializa el snapshot y se reemplazan los datos operativos de forma transaccional.

```sql
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
    -- Incluye: configuración, laboratorios, secciones, materias, reservas.
    snapshot_json   TEXT    NOT NULL,
    fecha_creacion  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (edicion_id) REFERENCES ediciones(id) ON DELETE CASCADE,
    FOREIGN KEY (creado_por) REFERENCES usuarios_sistema(id),
    UNIQUE (edicion_id, numero_version)
);
```

**Formato del snapshot JSON:**
```json
{
  "configuracion": {"bloques_horarios": [...], "periodo_academico": "2026-2"},
  "laboratorios": [{"codigo": "LAB-01", "nombre": "...", ...}],
  "prestatarios": [...],
  "secciones": [...],
  "materias": [...],
  "reservas": [...]
}
```

### 4.3 Configuración por edición

Almacena preferencias que difieren entre ediciones: bloques horarios, periodo
académico, duración estándar, colores, etc. Se carga desde la versión activa
o se puede sobreescribir independientemente.

```sql
CREATE TABLE edicion_configuracion (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    edicion_id  INTEGER NOT NULL,
    clave       TEXT    NOT NULL,              -- 'bloques_horarios'
    valor       TEXT,                          -- JSON: '["07:00-08:10",...]'
    FOREIGN KEY (edicion_id) REFERENCES ediciones(id) ON DELETE CASCADE,
    UNIQUE (edicion_id, clave)
);
```

### 4.4 Relación usuarios ↔ ediciones

Un usuario puede pertenecer a varias ediciones.

```sql
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
```

`ADMINISTRADOR_EDICION` puede gestionar solo su edición. `ADMINISTRADOR` global
sigue viendo todo.

### 4.5 Datos filtrados por edición (UNIQUE compuesta)

Las siguientes tablas añaden `edicion_id`. Las restricciones UNIQUE globales se
convierten en **UNIQUE compuestas por edición**:

| Tabla | Cambio en UNIQUE |
|---|---|
| `prestatarios` | `UNIQUE (edicion_id, cedula)` (antes: `cedula UNIQUE` global) |
| `laboratorios` | `UNIQUE (edicion_id, codigo)` (antes: `codigo UNIQUE` global) |
| `equipos` | `UNIQUE (edicion_id, codigo)`; `UNIQUE (edicion_id, serial)` |
| `secciones` | `UNIQUE (edicion_id, codigo_seccion, semestre, periodo_academico, carrera_o_escuela)` |
| `materias` | `UNIQUE (edicion_id, codigo)` |

**Nota:** `categorias` y `usuarios_sistema` siguen siendo globales (sin `edicion_id`).
Los usuarios globales se asocian a ediciones mediante `usuarios_ediciones`.

```sql
ALTER TABLE prestatarios ADD COLUMN edicion_id INTEGER;
ALTER TABLE laboratorios ADD COLUMN edicion_id INTEGER;
ALTER TABLE equipos      ADD COLUMN edicion_id INTEGER;
ALTER TABLE reservas     ADD COLUMN edicion_id INTEGER;
ALTER TABLE prestamos_equipos ADD COLUMN edicion_id INTEGER;
ALTER TABLE auditoria    ADD COLUMN edicion_id INTEGER;
```

Índices nuevos:
```sql
CREATE INDEX idx_prestatarios_edicion ON prestatarios (edicion_id);
CREATE INDEX idx_laboratorios_edicion ON laboratorios (edicion_id);
CREATE INDEX idx_equipos_edicion      ON equipos (edicion_id);
CREATE INDEX idx_reservas_edicion     ON reservas (edicion_id);
CREATE INDEX idx_prestamos_edicion    ON prestamos_equipos (edicion_id);
CREATE INDEX idx_auditoria_edicion    ON auditoria (edicion_id);
```

### 4.6 Secciones y semestres (petición del profesor Nelson)

```sql
CREATE TABLE secciones (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    edicion_id          INTEGER NOT NULL,
    codigo_seccion      TEXT    NOT NULL,          -- SA, SB, SA-A, SAA...
    semestre            INTEGER NOT NULL CHECK (semestre BETWEEN 1 AND 10),
    periodo_academico   TEXT    NOT NULL,          -- '2026-2'
    carrera_o_escuela   TEXT    NOT NULL,
    cantidad_estimada   INTEGER,                   -- estudiantes previstos
    estado              TEXT    NOT NULL DEFAULT 'ACTIVA',
    FOREIGN KEY (edicion_id) REFERENCES ediciones(id) ON DELETE CASCADE,
    UNIQUE (edicion_id, codigo_seccion, semestre, periodo_academico, carrera_o_escuela)
);
```

### 4.7 Materias (asignaturas)

```sql
CREATE TABLE materias (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    edicion_id      INTEGER NOT NULL,
    codigo          TEXT    NOT NULL,          -- p. ej. 'MAT-101'
    nombre          TEXT    NOT NULL,
    escuela         TEXT,
    semestre        INTEGER,
    estado          TEXT    NOT NULL DEFAULT 'ACTIVA',
    FOREIGN KEY (edicion_id) REFERENCES ediciones(id) ON DELETE CASCADE,
    UNIQUE (edicion_id, codigo)
);
```

### 4.8 Ampliación de reservas (día de semana + bloques horarios)

```sql
ALTER TABLE reservas ADD COLUMN edicion_id INTEGER;
ALTER TABLE reservas ADD COLUMN seccion_id INTEGER;
ALTER TABLE reservas ADD COLUMN materia_id INTEGER;
ALTER TABLE reservas ADD COLUMN cantidad_estudiantes INTEGER;
ALTER TABLE reservas ADD COLUMN periodo_academico TEXT;
ALTER TABLE reservas ADD COLUMN dia_semana INTEGER;  -- 0=Lunes, 5=Sábado
```

Índices nuevos:
```sql
CREATE INDEX idx_reservas_seccion       ON reservas (seccion_id);
CREATE INDEX idx_reservas_profesor_fecha ON reservas (prestatario_id, fecha);
CREATE INDEX idx_reservas_dia_semana    ON reservas (edicion_id, dia_semana, hora_inicio);
```

**Bloques horarios:** se modelan como lista en `app/config.py` o como entidad:
```python
BLOQUES = [
    ("07:00", "08:10"),
    ("08:10", "09:20"),
    # ...
]
```
El selector de hora pasa de `<input type="time">` libre a `<select>` con bloques
fijos. La duración estándar de 70 minutos encaja.

---

## 5. Visor Técnico SQLite3 y Auditoría de Contraseñas (NUEVO — Requerimiento del Profesor)

Ruta protegida (solo `ADMINISTRADOR`): `/sistema/visor-sqlite`

Servicio de solo lectura: `app/services/db_inspector_service.py`

### 5.1 Pestaña 1 — Verificación de Cifrado/Hashing de Contraseñas

Muestra los registros reales de `usuarios_sistema`:
- `id`, `nombre`, `email`, `rol`
- **Valor crudo de `password_hash`**

**Desglose visual automático** de cada hash Werkzeug:
- **Algoritmo:** `scrypt` (o `pbkdf2:sha256` si se cambia en el futuro)
- **Parámetros/Iteraciones:** `32768:8:1` (cost, blockSize, parallelization)
- **Salt:** la parte entre `$`
- **Hash criptográfico:** la parte final después del último `$`

**Probador en vivo:**
- Campo de texto: el profesor escribe una contraseña de prueba.
- Botón "Generar hash": muestra cómo Werkzeug produce un hash **diferente cada
  vez** gracias al salt aleatorio.
- Mensaje explicativo: "El hash cambia en cada generación porque el salt es
  aleatorio. Esto confirma que es irreversible: no se puede recuperar la
  contraseña original a partir del hash."

### 5.2 Pestaña 2 — Explorador de Tablas SQLite3

- Lista todas las tablas reales consultando `sqlite_master`.
- Muestra el DDL (`CREATE TABLE ...`) de cada tabla.
- Muestra la cantidad de registros (`SELECT COUNT(*)`).
- Permite previsualizar las últimas 50 filas.
- Filtro opcional por `edicion_id` (si la tabla lo tiene).

**Seguridad estricta:**
- Solo lectura (`SELECT` parametrizado).
- Lista blanca de tablas obtenida dinámicamente de `sqlite_master` (no hardcodeada).
- **Sin formulario de SQL arbitrario**.
- Ocultar columna `token` de `tokens_correo` (mostrar `substr(token,1,8)||'...'`).

---

## 6. Flujo de trabajo: crear una edición

### 6.1 Desde cero (v1)

1. Administrador global crea la edición: nombre, slug, descripción.
2. Se crea automáticamente la versión 1 con `snapshot_json = '{}'`. Se marca como
   `version_actual = 1`.
3. Se asignan usuarios a la edición con rol `ADMINISTRADOR_EDICION` u `OPERADOR`.
4. El administrador de edición configura: bloques horarios, periodo académico,
   duración estándar, etc.
5. Carga laboratorios, prestatarios (profesores), secciones, materias.
6. Empieza a crear reservas/asignaciones.
7. Cuando quiere guardar un punto de control, crea una nueva versión:
   el sistema serializa todo el estado actual en `snapshot_json`.

### 6.2 Restaurar una versión anterior

1. El administrador de edición selecciona una versión archivada.
2. El sistema deserializa `snapshot_json`.
3. En una transacción:
   - Borra los datos operativos actuales de la edición (laboratorios,
     prestatarios, secciones, materias, reservas).
   - Inserta los datos del snapshot.
   - Actualiza `version_actual` en `ediciones`.
4. La edición ahora refleja el estado de esa versión.

---

## 7. Motor de asignación y choques (peticiones del profesor Nelson)

### 7.1 Campos de una asignación/reserva ampliada

- Profesor (`prestatario_id`, tipo PROFESOR)
- Materia (`materia_id`)
- Escuela/Carrera (de la sección o de la materia)
- Semestre + Sección (`seccion_id`)
- Cantidad de estudiantes (`cantidad_estudiantes`)
- Día de semana (`dia_semana`: 0=Lunes, 5=Sábado) + Bloque horario
- Laboratorio asignado (`laboratorio_id`)
- Periodo académico (`periodo_academico`)

### 7.2 Validaciones automáticas (CORREGIDO)

1. **Capacidad:** si `cantidad_estudiantes > laboratorios.capacidad`, rechazar
   o mostrar advertencia clara.
2. **Choque de laboratorio:** mismo `laboratorio_id + dia_semana + bloque` para
   dos asignaciones `CONFIRMADA`/`ACTIVA`.
3. **Choque de profesor:** mismo `prestatario_id + dia_semana + bloque` para dos
   asignaciones distintas. **Esto hoy no existe y hay que añadirlo.**

### 7.3 Normalización de horas

Convertir `hora_inicio`/`hora_fin` a minutos (`_a_minutos()` ya existe en
`reservation_service.py`) antes de comparar, en vez de comparar cadenas.
Asegurar formato `HH:MM` con cero a la izquierda.

---

## 8. Vista previa interactiva

Requisito: ver el horario antes de guardar, actualizándose en vivo.

**Vistas disponibles:**
- Por laboratorio (rejilla semanal: días × bloques).
- Por semestre/sección.
- Por profesor.

**Implementación:** reutilizar `GET /reservas/disponibilidad` → servir JSON con
la rejilla completa → `main.js` construye tabla HTML. No se necesita librería
externa.

---

## 9. Exportación a PDF

### 9.1 Restricción del entorno

PythonAnywhere gratuito: sin `apt`, sin `sudo`. Solo paquetes Python puros.

| Librería | ¿Viable? | Notas |
|---|---|---|
| **fpdf2** | **Sí** | Python puro. API simple. Fuentes TTF propias. |
| **reportlab** | **Sí** | Estándar. Verboso, control total. |
| **xhtml2pdf** | Sí, con límites | No soporta flexbox/grid. Solo tablas y estilos en línea. |
| weasyprint | **No** | Necesita cairo/pango del sistema. |
| wkhtmltopdf | **No** | Necesita binario externo. |

**Decisión: fpdf2.** Se añade a `requirements.txt`.

### 9.2 Documentos a exportar

1. **Horario maestro** de cada laboratorio (rejilla semanal).
2. **Comprobante** de reserva/horario por sección.

Encabezados exigidos: Periodo Académico, Laboratorio, Semestre, Sección, Materia,
Profesor, Bloques Horarios.

---

## 10. Archivos a modificar, en orden

### Fase 1 — Esqueleto de ediciones + Visor Técnico SQLite3

| Archivo | Cambio |
|---|---|
| `schema.sql` | `DROP TABLE IF EXISTS` para tablas nuevas + `CREATE TABLE ediciones`, `edicion_versiones` (con `snapshot_json`), `edicion_configuracion`, `usuarios_ediciones` |
| `schema.sql` | `ALTER TABLE` en `prestatarios`, `laboratorios`, `equipos`, `reservas`, `prestamos_equipos`, `auditoria` para añadir `edicion_id`; cambiar UNIQUE globales a compuestas por edición |
| `schema.sql` | Insertar edición base: `INSERT INTO ediciones (nombre, slug, estado, version_actual) VALUES ('TechLoan Base', 'base', 'ACTIVA', 1)` |
| `app/database.py` | Reflejar TODO en `init_database()` y `_migrar()`; migración: asignar `edicion_id = 1` a filas existentes |
| `app/models/entities.py` | `@dataclass Edicion`, `EdicionVersion`, `EdicionConfig`, `UsuarioEdicion` |
| `app/services/edicion_service.py` | **nuevo**: CRUD de ediciones, crear versión (serializar snapshot), restaurar versión (deserializar), cambiar versión activa |
| `app/services/db_inspector_service.py` | **nuevo**: solo lectura, lista tablas desde `sqlite_master`, desglose de hash Werkzeug, probador en vivo |
| `app/routes/web_ediciones_routes.py` | **nuevo**: `/ediciones`, `/ediciones/<slug>`, `/ediciones/<slug>/configuracion` |
| `app/routes/web_inspector_routes.py` | **nuevo**: `/sistema/visor-sqlite` (solo ADMINISTRADOR) |
| `app/routes/web_crud_routes.py` | Añadir filtro `edicion_id` en todas las consultas de listado |
| `templates/ediciones/index.html` | **nuevo** |
| `templates/ediciones/configuracion.html` | **nuevo** |
| `templates/sistema/visor_sqlite.html` | **nuevo**: dos pestañas (hash de contraseñas + explorador de tablas) |
| `templates/parciales/selector_edicion.html` | **nuevo**: macro del desplegable |
| `templates/base_app.html` | Incluir el selector de edición en la barra superior |
| `app/services/auth_service.py` | Añadir permisos `ediciones.read/write/delete`, `configuracion.read/write`, `sistema.inspector` |
| `tests/test_ediciones.py` | **nuevo** |
| `tests/test_db_inspector.py` | **nuevo** |

### Fase 2 — Secciones, materias y ampliación de reservas

| Archivo | Cambio |
|---|---|
| `schema.sql` + `app/database.py` | `CREATE TABLE secciones`, `CREATE TABLE materias`; `ALTER TABLE reservas` (seccion_id, materia_id, cantidad_estudiantes, periodo_academico, dia_semana) |
| `app/services/reservation_service.py` | Choque de profesor + validación de capacidad + filtro por edición + normalización `_a_minutos()` |
| `app/services/disponibilidad_service.py` | Reflejar las mismas validaciones |
| `app/routes/web_crud_routes.py` | Rutas CRUD para secciones y materias |
| `templates/secciones/{form,index}.html` | **nuevos** |
| `templates/materias/{form,index}.html` | **nuevos** |
| `templates/reservas/form.html` | Añadir select de sección, materia, cantidad de estudiantes, día de semana, bloque horario |

### Fase 3 — Vista previa (rejilla semanal)

| Archivo | Cambio |
|---|---|
| `app/routes/web_operations_routes.py` | Ruta JSON `/ediciones/<slug>/rejilla` que devuelve la semana completa |
| `static/js/main.js` | Nueva función `pintarRejillaSemanal()`; ampliar `pintarLineaTiempo` |
| `templates/reservas/form.html` | Contenedor de la rejilla semanal |

### Fase 4 — PDF

| Archivo | Cambio |
|---|---|
| `requirements.txt` | Añadir `fpdf2` |
| `app/services/pdf_service.py` | **nuevo**: `horario_maestro_pdf()`, `comprobante_seccion_pdf()` |
| `app/routes/web_*_routes.py` | Rutas de descarga `/ediciones/<slug>/horario-pdf`, `/reservas/<id>/pdf` |
| `app/services/auditoria_service.py` | Acción `EXPORTAR` con `edicion_id` |

---

## 11. Reglas de trabajo

1. **Inspeccionar antes de escribir.** Leer el código real.
2. **Fases pequeñas y seguras.** Aprobación explícita antes de aplicar.
3. **NO hacer `git commit` ni `git push`** sin confirmación previa.
4. **PythonAnywhere compatible.** Todo paquete nuevo debe ser Python puro.
5. **La edición base existe desde el inicio.** Al crear `ediciones`, se inserta
   automáticamente la edición "TechLoan Base" (slug: `base`) con `id=1`. Todas
   las filas existentes en producción se asignan a `edicion_id=1` en la migración
   `_migrar()`.
6. **Las UNIQUE globales se convierten en compuestas por edición.** Verificar que
   la migración en `_migrar()` maneje correctamente la eliminación de índices
   UNIQUE antiguos y la creación de los nuevos compuestos (SQLite no permite
   `ALTER TABLE DROP CONSTRAINT`; puede requerir recrear la tabla).

---

## 12. Cómo verificar

```bash
# Local
PYTHONPATH=. .venv/bin/python tests/test_registro_phase7.py
PYTHONPATH=. .venv/bin/python tests/test_registro_smtp.py

# En PythonAnywhere, antes de recargar
.venv/bin/python -c "from app.server import create_app; create_app(); print('import OK')"

# Diagnóstico
python3 deploy/diagnostico_registro.py
```

La guía de actualización a producción está en `docs/ACTUALIZAR_EN_PRODUCCION.md`.
