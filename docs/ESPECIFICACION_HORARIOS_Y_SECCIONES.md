# Especificación de ampliación: secciones, semestres, asignación y PDF

**Documento de traspaso.** Está escrito para que otra IA (o un desarrollador)
pueda implementar la ampliación **sin necesidad de haber visto el proyecto**.
Incluye el diagnóstico del estado actual, las decisiones de diseño, los archivos
a tocar y el orden de trabajo.

Proyecto: **TechLoan** — sistema web de gestión de reservas y préstamos de
recursos tecnológicos. Flask + SQLite3 + Jinja2 + HTML/CSS/JS Vanilla.
Desplegado en `lorodev.pythonanywhere.com`.

---

## 1. Contexto de negocio

El **coordinador de laboratorios** recibe de las escuelas (Escuela de Sistemas y
Escuelas Generales) los horarios base de las materias y debe asignar a cada
profesor un laboratorio concreto según la materia y la cantidad de estudiantes de
la sección.

Hoy eso se hace a mano. El objetivo es que el sistema:

1. modele **secciones** y **semestres** correctamente,
2. detecte **choques** (mismo laboratorio, mismo día y bloque; o mismo profesor en
   dos sitios a la vez) y **valide la capacidad**,
3. muestre una **vista previa en vivo** antes de guardar,
4. exporte a **PDF** sin que el diseño se rompa.

---

## 2. Estado actual (verificado sobre el código)

### 2.1 Modelo de datos

`schema.sql` tiene **9 tablas**: `usuarios_sistema`, `tokens_correo`,
`prestatarios`, `categorias`, `laboratorios`, `equipos`, `reservas`,
`prestamos_equipos`, `auditoria`. Doce índices.

**No existen** (0 coincidencias en el código): `seccion`, `semestre`, `materia`,
`asignatura`, `periodo_academico`, `carrera`, `escuela`. Las 49 apariciones de la
palabra «sección» son prosa en español («titulo-seccion», «Busca secciones…»), no
columnas.

La única clasificación académica existente es `prestatarios.tipo`
(`ESTUDIANTE`/`PROFESOR`/`EMPLEADO`/`OTRO`), que describe a la **persona**, no a
la sección.

### 2.2 Reservas

```sql
CREATE TABLE reservas (
    id, laboratorio_id, prestatario_id, usuario_sistema_id,
    fecha TEXT,            -- AAAA-MM-DD
    hora_inicio TEXT,      -- HH:MM
    hora_fin TEXT,         -- HH:MM
    duracion_minutos INTEGER,
    estado TEXT,           -- CONFIRMADA | ACTIVA | FINALIZADA | CANCELADA
    observaciones TEXT,
    fecha_registro TEXT
);
```

- El «profesor» es un `prestatario` con `tipo='PROFESOR'`: reutilización
  semántica, no un campo propio.
- **No hay bloques horarios**: `hora_inicio`/`hora_fin` son texto libre. Solo
  existen `duracion_estandar_minutos` (70) por laboratorio y la franja
  `07:00–21:00` de `app/config.py` (`HORA_APERTURA`, `HORA_CIERRE`).
- **El choque se detecta solo por laboratorio** (`app/services/reservation_service.py`,
  métodos `has_overlap` y `create_reservation`, y también
  `app/services/disponibilidad_service.py`): comparan `laboratorio_id + fecha` con
  intersección horaria sobre estados `CONFIRMADA`/`ACTIVA`. **No hay ninguna
  comprobación de que un profesor esté en dos laboratorios a la vez.**
- **La capacidad no se valida al reservar**: `create_reservation` solo comprueba
  el `estado` del laboratorio; `laboratorios.capacidad` se valida al crear el
  laboratorio (1–1000) pero nunca se compara con nada, porque no existe el campo
  de cantidad de estudiantes.
- Fragilidad: el solapamiento compara horas **como texto**
  (`hora_inicio < ?`). Funciona con `HH:MM` con cero a la izquierda; se rompe con
  `9:00` frente a `09:00`.

### 2.3 Laboratorios

```sql
CREATE TABLE laboratorios (
    id, codigo UNIQUE, nombre, ubicacion,
    capacidad INTEGER CHECK (capacidad > 0),
    duracion_estandar_minutos INTEGER DEFAULT 70,
    estado TEXT  -- DISPONIBLE | MANTENIMIENTO | INACTIVO
);
```

Sin vínculo a escuela ni a carrera, y sin «tipo» de laboratorio.

### 2.4 Exportación

`requirements.txt` solo tiene Flask, Werkzeug y gunicorn (este último con
`; sys_platform != "win32"`). **No hay ninguna librería de PDF.**

La exportación actual es **CSV**: `exportar_csv()` en
`app/routes/web_common.py` (separador `;`, BOM para Excel en español), usada por
9 rutas: `/prestatarios/exportar`, `/categorias/exportar`,
`/laboratorios/exportar`, `/equipos/exportar`, `/usuarios/exportar`,
`/auditoria/exportar`, `/reservas/exportar`, `/prestamos/exportar`,
`/historial/exportar`.

Lo más parecido a un PDF es `templates/reservas/comprobante.html`: un recibo HTML
que llama a `window.print()` (líneas 88-94). Depende del navegador del usuario,
no es un PDF generado en el servidor, y no hay rejilla semanal.

### 2.5 Vista previa

Existe una **línea de tiempo de un solo día y un solo laboratorio**:

- `templates/reservas/form.html` líneas 64-69 (contenedor `#linea-tiempo`).
- `static/js/main.js`, función `pintarLineaTiempo()` (~línea 436), que la dibuja
  con los datos de `GET /reservas/disponibilidad`.
- `ReservationService.sugerir_horarios()` (líneas 166-226) calcula huecos libres
  y propone franjas alternativas: **buena base para el motor de choques**.

No es rejilla semanal, ni multi-laboratorio, ni por profesor ni por sección.

### 2.6 Roles

Solo `ADMINISTRADOR` y `OPERADOR`, fijados en **dos sitios** que hay que mantener
sincronizados:

- `schema.sql` línea 54: `CHECK (rol IN ('ADMINISTRADOR', 'OPERADOR'))`.
- `app/services/auth_service.py`, método `can()` (líneas 58-82): mapa de permisos
  por rol (`reservas.read`, `reservas.write`, …).

**No existe el rol COORDINADOR** que describe el negocio.

---

## 3. Arquitectura y convenciones (respetarlas)

- **Las rutas no escriben SQL.** Usan los servicios de `app/services/`, que son
  **clases con `@staticmethod`** (`ReservationService`, `LaboratorioService`…).
- **Consultas parametrizadas siempre** (`?`), nunca f-strings.
- **Eliminaciones solo por POST**, y todo POST web exige token CSRF
  (`@web_bp.before_request` → `_verify_csrf`). El campo se llama **`_csrf_token`**.
- **Cualquier vista que renderice una plantilla que hereda `base_app.html` debe
  exigir sesión** (`@login_required` o `@permission_required`): ese shell accede a
  `usuario_actual`, que es `None` sin sesión y da 500, no 302.
- Los parámetros de negocio (franja horaria, duración, umbral de saturación,
  filas por página) viven en `app/config.py`.
- **El esquema está duplicado a propósito** (trampa importante): `schema.sql` para
  reconstruir desde cero (`init_db.py`) y `app/database.py` con
  `CREATE TABLE IF NOT EXISTS` para producción. Un cambio de esquema debe
  hacerse **en los dos**, y las columnas nuevas necesitan además una migración en
  `_migrar()`.
- Las pruebas se aíslan con `tests/_tempdb.py` (`preparar()`) o redirigiendo
  `app.database.DATABASE_PATH`; nunca deben tocar `database/techloan.db`.
- Texto de interfaz en **español de Venezuela** («haz clic», «celular»).

---

## 4. Requisitos y decisiones de diseño

### 4.1 Secciones y semestres (prioridad alta)

**Problema que se quiere evitar:** en sistemas anteriores el código de sección se
definió como clave única global, así que no podía existir `SA` en 1.er semestre y
`SA` en 2.º semestre a la vez; el usuario tenía que inventar `SA1`, `SA2`, `SA3`.

**Solución:** el código de sección **no** es único por sí solo. La unicidad es
**compuesta**:

```
UNIQUE (codigo_seccion, semestre, periodo_academico, carrera_o_escuela)
```

**Subsecciones:** deben admitirse `SA-A`, `SA-B`, `SA-C` (y sus variantes sin
guion `SAA`, `SAB`, `SAC`) cuando en un mismo semestre se habilitan secciones
adicionales. El campo `codigo_seccion` admite letras, dígitos, guion y guion bajo.

**Modelo propuesto:**

```sql
CREATE TABLE secciones (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_seccion      TEXT NOT NULL,          -- SA, SB, SA-A, SAA...
    semestre            INTEGER NOT NULL CHECK (semestre BETWEEN 1 AND 10),
    periodo_academico   TEXT NOT NULL,          -- p. ej. '2026-2'
    carrera_o_escuela   TEXT NOT NULL,
    cantidad_estimada   INTEGER,                -- estudiantes previstos
    estado              TEXT NOT NULL DEFAULT 'ACTIVA',
    UNIQUE (codigo_seccion, semestre, periodo_academico, carrera_o_escuela)
);
```

### 4.2 Motor de asignación y detección de choques

Campos que debe llevar cada asignación/reserva:

> Profesor · Materia · Escuela/Carrera · Semestre · Sección · Cantidad de
> estudiantes · Día · Bloque horario · Laboratorio asignado

**Validaciones automáticas:**

1. **Capacidad:** si `cantidad_de_estudiantes > laboratorios.capacidad`, avisar o
   filtrar ese laboratorio de las opciones.
2. **Choque de laboratorio:** misma combinación laboratorio + día + bloque para
   dos asignaciones distintas.
3. **Choque de profesor:** mismo profesor asignado a dos laboratorios en el mismo
   día y bloque. **Esto hoy no existe y hay que añadirlo.**

**Bloques horarios:** se recomienda modelarlos como entidad o como lista fija en
`app/config.py` (p. ej. `BLOQUES = [("07:00","08:10"), ("08:10","09:20"), …]`), en
lugar de validar horas libres. El sistema ya trabaja con la duración estándar de
70 minutos, así que los bloques encajan sin cambiar el modelo de `reservas`.

**Nota sobre horas:** si se conservan `hora_inicio`/`hora_fin` como texto, conviene
normalizar a `HH:MM` con cero a la izquierda y comparar convirtiendo a minutos
(`_a_minutos()` ya existe en `reservation_service.py`), en vez de comparar cadenas.

### 4.3 Vista previa interactiva

Requisito: **ver el horario antes de guardar**, en pantalla, actualizándose
mientras se cargan las asignaciones. Debe permitirse elegir la vista:

- por laboratorio,
- por semestre/sección,
- por profesor.

**Recomendación de implementación:** reutilizar el patrón existente
(`GET /reservas/disponibilidad` → `pintarLineaTiempo` en `main.js`), ampliándolo a
una rejilla semanal servida como JSON. No hace falta ninguna librería: basta una
tabla HTML construida en JS. Es el mismo camino que ya funciona, con más
dimensiones.

### 4.4 Exportación a PDF

**Restricción dura del entorno:** el plan gratuito de PythonAnywhere **no tiene
`apt` ni `sudo`** y solo permite instalar paquetes de Python. Cualquier librería
que necesite bibliotecas del sistema queda descartada.

| Librería | ¿Sirve en PythonAnywhere gratuito? | Notas |
|---|---|---|
| **fpdf2** | **Sí** | Python puro. API simple. Se le pueden pasar fuentes TTF propias. |
| **reportlab** | **Sí** | Python puro, el estándar. Más verboso, control total. |
| **xhtml2pdf** | Sí, con límites | Renderiza HTML. **No soporta flexbox ni grid**: hay que maquetar con tablas y estilos en línea. |
| weasyprint | **No** | Necesita cairo y pango del sistema. |
| wkhtmltopdf | **No** | Necesita un binario externo. |

**Decisión que hay que tomar:** si el PDF debe «coincidir fielmente con la vista
previa», hay dos caminos honestos:

- **(A) Dibujar el PDF a mano** con fpdf2 o reportlab: control total del diseño,
  pero la maquetación se hace dos veces (una para la pantalla, otra para el PDF).
- **(B) xhtml2pdf** reutilizando la misma plantilla HTML: menos código duplicado,
  pero el CSS tiene que ser de 2005 (tablas, estilos en línea).

Recomendación: **(A) con fpdf2** si el PDF es un documento formal para imprimir,
porque la coincidencia exacta con la vista previa se consigue definiendo **una
sola función de datos** (la rejilla) y dos renderizadores sobre ella.

**Documentos a exportar:**

1. Horario maestro de cada laboratorio.
2. Comprobante de reserva/horario por sección.

Encabezados exigidos: Periodo Académico, Laboratorio, Semestre, Sección, Materia,
Profesor y Bloques Horarios.

---

## 5. Archivos a modificar, en orden

### Fase 1 — Secciones y semestres

| Archivo | Cambio |
|---|---|
| `schema.sql` | `DROP TABLE IF EXISTS secciones;` arriba + `CREATE TABLE secciones` |
| `app/database.py` | Reflejar el `CREATE TABLE` dentro de `init_database()` |
| `app/database.py` → `_migrar()` | Si la cola de producción ya existe, `ALTER TABLE` |
| `app/models/entities.py` | `@dataclass Seccion` |
| `app/services/seccion_service.py` | **nuevo**, con el patrón de los servicios existentes |
| `app/routes/web_crud_routes.py` | Rutas CRUD copiando el patrón de `prestatarios` |
| `app/services/auth_service.py` → `can()` | Permisos `secciones.read/write/delete` |
| `templates/secciones/{form,index}.html` | **nuevos** |
| `tests/test_secciones.py` | **nuevo**, aislado con `_tempdb.preparar()` |
| `schema.sql` | Datos de demostración coherentes con las fechas relativas |

### Fase 2 — Ampliar reservas

| Archivo | Cambio |
|---|---|
| `schema.sql` + `app/database.py` | Columnas nuevas en `reservas`: `materia`, `seccion_id`, `cantidad_estudiantes`, `periodo_academico`, `profesor_id` (o reutilizar `prestatario`) |
| `schema.sql` (índices) | `idx_reservas_seccion`, `idx_reservas_profesor_fecha` |
| `app/services/reservation_service.py` | Choque de profesor + validación de capacidad |
| `app/services/disponibilidad_service.py` | Reflejar las mismas validaciones |

### Fase 3 — Vista previa

| Archivo | Cambio |
|---|---|
| `app/routes/web_operations_routes.py` | Ruta JSON de rejilla semanal |
| `static/js/main.js` | Ampliar `pintarLineaTiempo` a rejilla por laboratorio / sección / profesor |
| `templates/reservas/form.html` | Contenedor de la rejilla |

### Fase 4 — PDF

| Archivo | Cambio |
|---|---|
| `requirements.txt` | Añadir `fpdf2` (puro Python) |
| `app/services/pdf_service.py` | **nuevo**: genera los dos documentos |
| `app/routes/web_*_routes.py` | Rutas de descarga `/reservas/<id>/pdf`, `/laboratorios/<id>/horario-pdf` |
| `app/services/auditoria_service.py` | Registrar la acción `EXPORTAR` |

---

## 6. Reglas de trabajo acordadas

1. **Inspeccionar antes de escribir.** Leer el estado real del código, los modelos
   y las plantillas.
2. **Planificación iterativa.** Fases pequeñas y seguras, con aprobación explícita
   antes de aplicar cambios.
3. **No hacer `git commit` ni `git push`** sin confirmación previa.
4. **Compatibilidad con PythonAnywhere.** Toda librería sugerida (sobre todo para
   PDF) debe ser Python puro, sin dependencias del sistema.

---

## 7. Cómo verificar

```bash
# Desde la raíz del proyecto
PYTHONPATH=. .venv/bin/python tests/test_registro_phase7.py
PYTHONPATH=. .venv/bin/python tests/test_registro_smtp.py
PYTHONPATH=. .venv/bin/python tests/test_overlap_phase5.py
PYTHONPATH=. .venv/bin/python tests/test_validations_phase5.py
```

En el servidor, antes de recargar:

```bash
cd ~/TechLoan
.venv/bin/python -c "from app.server import create_app; create_app(); print('import OK')"
```

Y para diagnosticar el ciclo de registro en producción:

```bash
python3 deploy/diagnostico_registro.py
```

La guía completa de actualización a producción está en
`docs/ACTUALIZAR_EN_PRODUCCION.md`.
