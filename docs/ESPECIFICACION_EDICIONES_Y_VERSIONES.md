# Especificación: Ediciones, versiones y peticiones del profesor Nelson

**Documento de traspaso para IA.** Está escrito para que otra IA (o desarrollador)
pueda implementar la ampliación sin haber visto el proyecto. Incluye el estado
actual, decisiones de diseño, modelo de datos, archivos a tocar y orden de trabajo.

Proyecto: **TechLoan** — Flask + SQLite3 + Jinja2 + HTML/CSS/JS Vanilla.
Desplegado en `lorodev.pythonanywhere.com`.

---

## 1. Contexto de negocio: ¿qué es una "edición"?

El landing de TechLoan tiene un plan "Avanzado — A medida" que menciona "varios
centros" e "informes a medida". El objetivo es hacer eso real: que el sistema
soporte **múltiples ediciones**, cada una siendo una instancia personalizada para
un profesor, escuela o centro.

**Ejemplo concreto:**
- **Edición base** (genérica): TechLoan tal como está hoy. Gestiona reservas y
  préstamos de equipos.
- **Edición "IUTEPI LABS"**: creada para las peticiones del profesor Nelson.
  Incluye secciones, semestres, asignación de horarios por materia, detección de
  choques de profesor, vista previa de rejilla semanal y exportación a PDF.

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

## 2. Estado actual verificado

### 2.1 Esquema de base de datos

9 tablas en `schema.sql` (ver archivo completo; el esquema está duplicado en
`app/database.py` con `CREATE TABLE IF NOT EXISTS`):

| Tabla | Propósito | ¿Necesita edicion_id? |
|---|---|---|
| `usuarios_sistema` | Login, roles, confirmación de correo | **NO** (usuarios globales) |
| `tokens_correo` | Tokens de un solo uso | **NO** (ligados a usuarios) |
| `prestatarios` | Personas que reservan/piden préstamo | **SÍ** (cada edición tiene sus profesores/estudiantes) |
| `categorias` | Clasificación de equipos | **NO** (compartidas) |
| `laboratorios` | Espacios físicos reservables | **SÍ** (cada edición define los suyos) |
| `equipos` | Recursos individuales prestables | **SÍ** (pero pueden heredarse de la edición base) |
| `reservas` | Reservas de laboratorios | **SÍ** |
| `prestamos_equipos` | Préstamos de equipos | **SÍ** |
| `auditoria` | Registro de actividad | **SÍ** (con `edicion_id` opcional para filtrar) |

**No existen**: `seccion`, `semestre`, `materia`, `periodo_academico`, `carrera`,
`escuela`. Las 49 apariciones de la palabra "sección" son prosa en español, no
columnas.

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

## 4. Modelo de datos: ediciones y versiones

### 4.1 Tabla maestra: ediciones

```sql
CREATE TABLE ediciones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre          TEXT    NOT NULL,          -- "IUTEPI LABS"
    slug            TEXT    NOT NULL UNIQUE,   -- "iutepl-labs" (para URLs)
    descripcion     TEXT,
    estado          TEXT    NOT NULL DEFAULT 'ACTIVA'
                    CHECK (estado IN ('ACTIVA', 'ARCHIVADA', 'BORRADOR')),
    -- La versión que se muestra por defecto cuando un usuario entra a esta edición.
    version_actual  INTEGER NOT NULL DEFAULT 1,
    fecha_creacion  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 Control de versiones: edicion_versiones

Cada edición puede tener múltiples "revisiones". Una revisión es una **copia
completa de la configuración y los datos** de esa edición en un momento dado.
Esto permite:
- Probar cambios sin romper la versión en producción.
- Volver a una versión anterior si algo falla.
- Comparar versiones.

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
    fecha_creacion  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (edicion_id) REFERENCES ediciones(id) ON DELETE CASCADE,
    FOREIGN KEY (creado_por) REFERENCES usuarios_sistema(id),
    UNIQUE (edicion_id, numero_version)
);
```

### 4.3 Configuración por edición y versión

Almacena preferencias que difieren entre ediciones: bloques horarios, periodo
académico, duración estándar, colores, etc.

```sql
CREATE TABLE edicion_configuracion (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    edicion_id  INTEGER NOT NULL,
    version_id  INTEGER NOT NULL,              -- a qué revisión aplica
    clave       TEXT    NOT NULL,              -- 'bloques_horarios'
    valor       TEXT,                          -- JSON: '["07:00-08:10",...]'
    FOREIGN KEY (edicion_id) REFERENCES ediciones(id) ON DELETE CASCADE,
    FOREIGN KEY (version_id) REFERENCES edicion_versiones(id) ON DELETE CASCADE,
    UNIQUE (edicion_id, version_id, clave)
);
```

### 4.4 Relación usuarios ↔ ediciones

Un usuario puede pertenecer a varias ediciones (p. ej. un operador que administra
IUTEPI LABS y también la edición base).

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

`ADMINISTRADOR_EDICION` puede gestionar solo su edición (no crear usuarios
globales, no ver otras ediciones). `ADMINISTRADOR` global sigue viendo todo.

### 4.5 Datos filtrados por edición

Las siguientes tablas añaden `edicion_id` y `version_id`:

| Tabla | edicion_id | version_id | Notas |
|---|---|---|---|
| `prestatarios` | SÍ | NO | Cada edición tiene sus propios profesores/estudiantes |
| `laboratorios` | SÍ | NO | Capacidad, duración, etc. por edición |
| `equipos` | SÍ | NO | Pueden copiarse de la edición base al crear una nueva |
| `reservas` | SÍ | NO | Pertenece a la edición activa |
| `prestamos_equipos` | SÍ | NO | Pertenece a la edición activa |
| `auditoria` | opcional | NO | Para filtrar logs por edición |

**Tablas SIN edicion_id** (globales): `usuarios_sistema`, `tokens_correo`,
`categorias`, `ediciones`, `edicion_versiones`, `edicion_configuracion`,
`usuarios_ediciones`.

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
    UNIQUE (edicion_id, codigo_seccion, semestre, periodo_academico, carrera_o_escuela)
);
```

La unicidad es **compuesta y por edición**: `SA` en 1.er semestre de IUTEPI LABS
y `SA` en 1.er semestre de otra edición son diferentes filas.

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
    UNIQUE (edicion_id, codigo)
);
```

### 4.8 Ampliación de reservas

```sql
ALTER TABLE reservas ADD COLUMN edicion_id INTEGER;
ALTER TABLE reservas ADD COLUMN seccion_id INTEGER;
ALTER TABLE reservas ADD COLUMN materia_id INTEGER;
ALTER TABLE reservas ADD COLUMN cantidad_estudiantes INTEGER;
ALTER TABLE reservas ADD COLUMN periodo_academico TEXT;
```

Índices nuevos:
```sql
CREATE INDEX idx_reservas_edicion       ON reservas (edicion_id);
CREATE INDEX idx_reservas_seccion       ON reservas (seccion_id);
CREATE INDEX idx_reservas_profesor_fecha ON reservas (prestatario_id, fecha);
```

---

## 5. Flujo de trabajo: crear una edición

### 5.1 Desde cero (v1)

1. Administrador global crea la edición: nombre, slug, descripción.
2. Se crea automáticamente la versión 1 (vacia).
3. Se asignan usuarios a la edición con rol `ADMINISTRADOR_EDICION` u `OPERADOR`.
4. El administrador de edición configura: bloques horarios, periodo académico,
   duración estándar, etc.
5. Carga laboratorios, prestatarios (profesores), secciones, materias.
6. Empieza a crear reservas/asignaciones.

### 5.2 Nueva versión (v1 → v2)

1. El administrador de edición pulsa "Crear nueva versión".
2. El sistema copia TODA la configuración de `edicion_configuracion` de v1 a v2.
3. El sistema copia TODOS los datos (laboratorios, prestatarios, secciones,
   materias, reservas) de v1 a v2.
4. El administrador trabaja en v2 sin afectar v1.
5. Cuando v2 está lista, puede marcarse como `version_actual`.
6. v1 se archiva (sus datos se conservan para consulta histórica).

**Nota de implementación:** la copia de datos entre versiones puede hacerse con
`INSERT INTO ... SELECT ...` en SQLite. Las tablas con `version_id` se copian
automáticamente; las que solo tienen `edicion_id` necesitan una columna
`version_id` adicional o una tabla de "snapshot".

**Decisión de simplificación:** en la primera implementación, las tablas de datos
(`laboratorios`, `prestatarios`, `reservas`, etc.) solo llevan `edicion_id`. El
control de versiones se hace a nivel de **configuración** (`edicion_configuracion`)
y de **datos maestros** (laboratorios, secciones). Las reservas históricas se
conservan por su naturaleza (no se borran, solo cambian de estado). Si en el
futuro se necesita versionado completo de datos, se añade `version_id`.

---

## 6. Interfaz de usuario

### 6.1 Selector de edición

En `base_app.html`, junto al nombre del usuario, un desplegable:

```
[👤 Lorenzo Roca  ▼]  [📋 Edición: IUTEPI LABS  ▼]
```

El desplegable lista las ediciones a las que el usuario pertenece. Al cambiar,
se guarda en sesión (`session['edicion_id']`) y se recarga la página. Todas las
rutas CRUD filtran por `session['edicion_id']`.

### 6.2 Panel de ediciones (solo ADMINISTRADOR global)

Ruta: `/ediciones`
- Lista de ediciones con estado, versión actual, cantidad de usuarios.
- Botón "Crear edición".
- Botón "Gestionar usuarios" por edición.

### 6.3 Configuración de edición (ADMINISTRADOR_EDICION y global)

Ruta: `/ediciones/<slug>/configuracion`
- Periodo académico actual.
- Bloques horarios (lista editable).
- Duración estándar.
- Campos a medida (clave/valor dinámico).

### 6.4 Landing por edición

Ruta pública: `/e/<slug>`
- Muestra nombre, descripción, periodo académico, estadísticas de la edición
  (cantidad de laboratorios, reservas activas, etc.).
- Enlace al login (al entrar, se redirige a la edición correspondiente).

---

## 7. Motor de asignación y choques (peticiones del profesor Nelson)

### 7.1 Campos de una asignación/reserva ampliada

- Profesor (`prestatario_id`, tipo PROFESOR)
- Materia (`materia_id`)
- Escuela/Carrera (de la sección o de la materia)
- Semestre + Sección (`seccion_id`)
- Cantidad de estudiantes (`cantidad_estudiantes`)
- Día + Bloque horario (`fecha`, `hora_inicio`, `hora_fin`)
- Laboratorio asignado (`laboratorio_id`)

### 7.2 Validaciones automáticas

1. **Capacidad:** si `cantidad_estudiantes > laboratorios.capacidad`, rechazar
   o mostrar advertencia.
2. **Choque de laboratorio:** mismo `laboratorio_id + fecha + bloque` para dos
   asignaciones `CONFIRMADA`/`ACTIVA`.
3. **Choque de profesor:** mismo `prestatario_id + fecha + bloque` para dos
   asignaciones distintas. **Esto hoy no existe.**

### 7.3 Bloques horarios

Modelar como lista en `app/config.py` o como entidad:
```python
BLOQUES = [
    ("07:00", "08:10"),
    ("08:10", "09:20"),
    # ...
]
```
La duración estándar de 70 minutos encaja. El selector de hora en el formulario
pasa de ser un `<input type="time">` libre a un `<select>` con bloques fijos.

### 7.4 Normalización de horas

Convertir `hora_inicio`/`hora_fin` a minutos (`_a_minutos()` ya existe en
`reservation_service.py`) antes de comparar, en vez de comparar cadenas.

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

### Fase 1 — Esqueleto de ediciones

| Archivo | Cambio |
|---|---|
| `schema.sql` | `DROP TABLE IF EXISTS` para tablas nuevas + `CREATE TABLE ediciones`, `edicion_versiones`, `edicion_configuracion`, `usuarios_ediciones` |
| `schema.sql` | `ALTER TABLE` (o nuevas columnas) en `prestatarios`, `laboratorios`, `equipos`, `reservas`, `prestamos_equipos`, `auditoria` para añadir `edicion_id` |
| `app/database.py` | Reflejar TODO en `init_database()` y `_migrar()` |
| `app/models/entities.py` | `@dataclass Edicion`, `EdicionVersion`, `EdicionConfig`, `UsuarioEdicion`, `Seccion`, `Materia` |
| `app/services/edicion_service.py` | **nuevo**: CRUD de ediciones, crear versión, cambiar versión activa |
| `app/services/seccion_service.py` | **nuevo**: CRUD de secciones (filtrado por edición) |
| `app/services/materia_service.py` | **nuevo**: CRUD de materias (filtrado por edición) |
| `app/routes/web_ediciones_routes.py` | **nuevo**: rutas `/ediciones`, `/ediciones/<slug>`, `/ediciones/<slug>/configuracion` |
| `app/routes/web_crud_routes.py` | Añadir filtro `edicion_id` en todas las consultas de listado |
| `templates/ediciones/index.html` | **nuevo** |
| `templates/ediciones/configuracion.html` | **nuevo** |
| `templates/parciales/selector_edicion.html` | **nuevo**: macro del desplegable |
| `templates/base_app.html` | Incluir el selector de edición en la barra superior |
| `app/services/auth_service.py` | Añadir permisos `ediciones.read/write/delete`, `configuracion.read/write` |

### Fase 2 — Secciones, materias y ampliación de reservas

| Archivo | Cambio |
|---|---|
| `schema.sql` + `app/database.py` | `CREATE TABLE secciones`, `CREATE TABLE materias` |
| `app/services/reservation_service.py` | Choque de profesor + validación de capacidad + filtro por edición |
| `app/services/disponibilidad_service.py` | Reflejar las mismas validaciones |
| `app/routes/web_crud_routes.py` | Rutas CRUD para secciones y materias |
| `templates/secciones/{form,index}.html` | **nuevos** |
| `templates/materias/{form,index}.html` | **nuevos** |
| `templates/reservas/form.html` | Añadir select de sección, materia, cantidad de estudiantes |

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
3. **No hacer `git commit` ni `git push`** sin confirmación previa.
4. **PythonAnywhere compatible.** Todo paquete nuevo debe ser Python puro.
5. **Las ediciones base existen desde el inicio.** Al crear la tabla `ediciones`,
   se inserta automáticamente la edición "TechLoan Base" (slug: `base`) con
   `id=1`. Todas las filas existentes en producción se asignan a `edicion_id=1`
   en la migración `_migrar()`.

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
