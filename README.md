# TechLoan

**Sistema Web CRUD de Gestión de Reservas y Préstamos de Recursos Tecnológicos**

Aplicación web desarrollada con **Flask + SQLite3 + Jinja2 + HTML5 + CSS3 + JavaScript Vanilla**,
como proyecto final de la asignatura **Programación III** (IUTEPI).

---

## 1. Descripción del problema que resuelve

En un centro de formación técnica los laboratorios de informática, redes y electrónica se
comparten entre varios docentes y grupos de estudiantes. Cuando la asignación de esos espacios
y del equipamiento se lleva en papel o por mensajería informal aparecen tres problemas
recurrentes:

1. **Doble reserva del mismo laboratorio** en el mismo horario, porque no existe un registro
   único y consultable.
2. **Pérdida de trazabilidad de los equipos**: nadie sabe con certeza quién tiene prestado un
   proyector, un switch o una laptop, ni desde cuándo.
3. **Ausencia de historial**: al no quedar registro de las operaciones, no se puede auditar
   qué se hizo, cuándo y quién lo autorizó.

**TechLoan** resuelve estos problemas con una aplicación web que:

- registra **prestatarios** (personas que reciben un espacio o un equipo);
- administra el **inventario** de laboratorios, categorías y equipos;
- gestiona **reservas de laboratorios** por franja horaria, **impidiendo solapamientos**;
- gestiona **préstamos individuales de equipos** y sus **devoluciones**, actualizando el
  estado del equipo de forma automática;
- ofrece un **historial unificado** con filtros para auditar todas las operaciones.

---

## 2. Tecnologías utilizadas

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12, Flask 3.1 |
| Base de datos | SQLite3 (librería nativa `sqlite3`), consultas parametrizadas |
| Plantillas | Jinja2 |
| Frontend | HTML5 semántico, CSS3 (responsive, sin frameworks), JavaScript Vanilla |
| Seguridad | Werkzeug (`generate_password_hash` / `check_password_hash`), sesiones Flask, token CSRF |
| Pruebas | Scripts de integración en Python con el cliente de pruebas de Flask |

> No se utiliza React, Vue, Angular, Bootstrap ni Tailwind: el proyecto se mantiene
> deliberadamente en HTML, CSS y JavaScript puros, tal como exige el enunciado.

---

## 3. Estructura del proyecto

```
Proyecto Final de Python/
│
├── app.py equivalente → run_server.py    # Punto de entrada: inicia el servidor Flask
├── init_db.py                            # Inicializa la base de datos desde schema.sql
├── schema.sql                            # Script SQL: tablas, índices y datos de prueba
├── requirements.txt                      # Dependencias (Flask, Werkzeug)
├── README.md                             # Este documento
│
├── database/
│   └── techloan.db                       # Base de datos SQLite3 (generada)
│
├── static/                               # Archivos estáticos
│   ├── css/
│   │   └── estilos.css                   # Hoja de estilos personalizada y responsive
│   └── js/
│       └── main.js                       # Interactividad (Vanilla JS)
│
├── templates/                            # Plantillas HTML procesadas por Jinja2
│   ├── base.html                         # Plantilla base (navbar, mensajes, layout)
│   ├── index.html                        # Vista principal (panel de inicio)
│   ├── parciales/                        # Fragmentos reutilizables (formularios, mensajes)
│   ├── auth/login.html                   # Formulario de acceso
│   ├── prestatarios/                     # Listado + formulario
│   ├── laboratorios/
│   ├── categorias/
│   ├── equipos/
│   ├── usuarios/
│   ├── reservas/
│   ├── prestamos/
│   ├── historial/
│   └── errores/error.html
│
├── app/                                  # Código Python (arquitectura por capas)
│   ├── server.py                         # create_app(): registra blueprints y errores
│   ├── config.py                         # Configuración (ruta de BD, host, puerto)
│   ├── database.py                       # Conexión SQLite3 (abrir/cerrar por operación)
│   ├── models/entities.py                # Clases de dominio (POO)
│   ├── services/                         # Lógica de negocio y validaciones
│   │   ├── auth_service.py
│   │   ├── usuario_service.py
│   │   ├── prestatario_service.py
│   │   ├── laboratorio_service.py
│   │   ├── categoria_service.py
│   │   ├── equipo_service.py
│   │   ├── reservation_service.py        # Reservas + regla de solapamiento
│   │   ├── prestamo_equipo_service.py    # Préstamos y devoluciones
│   │   ├── disponibilidad_service.py
│   │   ├── historial_service.py
│   │   └── dashboard_service.py
│   ├── routes/
│   │   ├── web_common.py                 # Blueprint web, permisos, CSRF
│   │   ├── web_auth_routes.py            # /login, /logout, / (panel)
│   │   ├── web_crud_routes.py            # CRUD web de las entidades
│   │   ├── web_operations_routes.py      # Reservas, préstamos, historial
│   │   └── *_routes.py                   # API JSON (/api/...)
│   ├── security/permissions.py           # Revalidación de sesión y permisos por rol
│   └── gui/                              # Interfaz Tkinter previa (prototipo, no prioritaria)
│
└── tests/                                # Pruebas automatizadas
    ├── test_web_phase6.py                # Pruebas de integración de la capa web
    ├── smoke_test.py                     # Verificación rápida de extremo a extremo
    ├── test_crud_phase5.py
    ├── test_validations_phase5.py
    ├── test_security_phase5.py
    ├── test_overlap_phase5.py
    ├── test_roles_phase5.py
    └── test_historial_phase4.py
```

---

### 3.1 Equivalencia con la estructura sugerida por el enunciado

El PDF propone una arquitectura de directorios simplificada ("Se sugiere la siguiente
arquitectura"). Se respeta su intención y se conserva, además, la organización modular del
proyecto. Correspondencia directa:

| Elemento sugerido en el enunciado | Dónde está en este proyecto |
|---|---|
| `app.py` — Servidor principal de Flask | `run_server.py` (punto de entrada) + `app/server.py` (`create_app`) |
| `database.db` — Archivo de la base de datos | `database/techloan.db` |
| `schema.sql` — Script de creación de tablas | `schema.sql` (raíz) |
| `static/css/estilos.css` | `static/css/estilos.css` |
| `static/js/main.js` | `static/js/main.js` |
| `templates/base.html` | `templates/base.html` |
| `templates/index.html` — Vista principal | `templates/index.html` (panel) + `templates/<entidad>/index.html` (listados) |
| `templates/crear.html` — Formulario de inserción | `templates/<entidad>/form.html` (modo alta) |
| `templates/editar.html` — Formulario de modificación | `templates/<entidad>/form.html` (modo edición) |
| Rutas `/`, `/crear`, `/editar/<id>`, `/eliminar/<id>` | Implementadas literalmente para Prestatarios |

La lógica de negocio no vive en `app.py`: está repartida en `app/services/`, de modo que la
misma regla se comparte entre las rutas web y la API JSON, y no puede divergir.

---

## 4. Instalación paso a paso

### 4.1 Requisitos previos

- Python 3.10 o superior (probado con Python 3.12).
- `pip` disponible.

### 4.2 Arranque portable (recomendado)

El proyecto **no depende de rutas absolutas de Python**. El archivo `start.py` detecta Python,
crea un entorno virtual local `.venv` si no existe, instala las dependencias y levanta Flask.
**No es necesario activar el entorno virtual manualmente.**

Solo se necesita **Python 3.10 o superior** instalado y disponible en el PATH.

**Windows — doble clic:**
```text
iniciar.bat
```

**Windows — PowerShell:**
```powershell
.\iniciar.ps1
```

**Linux / macOS:**
```bash
./iniciar.sh
```

También puede ejecutarse directamente:
```bash
python start.py
```

El lanzador calcula todas las rutas desde la carpeta del proyecto, por lo que funciona aunque
la carpeta esté en otra unidad, tenga otro nombre o contenga espacios.

> **Importante:** no copies la carpeta `.venv` de otra PC. Un entorno virtual contiene
> referencias internas a la máquina donde fue creado. Al copiar el proyecto a otra PC,
> elimina `.venv` y ejecuta `iniciar.bat` (o el lanzador correspondiente); se reconstruirá
> automáticamente.

### 4.3 Creación manual del entorno virtual (opcional)

**Windows (PowerShell / CMD):**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4.4 Instalar las dependencias

```bash
pip install -r requirements.txt
```

O de forma equivalente:

```bash
pip install flask
```

`requirements.txt` contiene:

```
Flask==3.1.2
Werkzeug==3.1.3
```

---

## 5. Inicializar la base de datos

El proyecto incluye `schema.sql`, que crea **todas las tablas, los índices y los datos de
prueba** (incluidos los usuarios del sistema).

```bash
python init_db.py
```

Salida esperada:

```
Base de datos reconstruida: .../database/techloan.db
----------------------------------------------
  usuarios_sistema          2 registro(s)
  prestatarios              4 registro(s)
  categorias                3 registro(s)
  laboratorios              3 registro(s)
  equipos                   4 registro(s)
  reservas                  3 registro(s)
  prestamos_equipos         2 registro(s)
----------------------------------------------
  integrity_check: ok
```

> **Importante:** `init_db.py` **elimina y vuelve a crear** las tablas del archivo de destino.
> No lo ejecutes sobre una base de datos con información real que quieras conservar.
> Para reconstruir un archivo distinto (por ejemplo, una copia de prueba):
>
> ```bash
> python init_db.py ruta/a/otra_base.db
> ```

También puedes cargar el script manualmente con el cliente de SQLite:

```bash
sqlite3 database/techloan.db < schema.sql
```

---

## 6. Ejecutar el servidor

Para un equipo nuevo se recomienda usar el lanzador portable:

**Windows:**
```text
iniciar.bat
```

**PowerShell:**
```powershell
.\\iniciar.ps1
```

**Linux / macOS:**
```bash
./iniciar.sh
```

El lanzador crea o reutiliza el `.venv` local, instala las dependencias y ejecuta
`run_server.py`. Si la base de datos todavía no existe, también ejecuta `init_db.py`.

La ejecución manual sigue disponible:

```bash
python run_server.py
```

Salida esperada:

```
 * Running on http://127.0.0.1:5000
```

Abre el navegador en:

**http://127.0.0.1:5000**

Serás redirigido al formulario de acceso (`/login`).

---

## 7. Usuarios de prueba

Los usuarios los crea `schema.sql` con la contraseña almacenada **como hash** (nunca en texto plano).

| Usuario | Contraseña | Rol | Alcance |
|---|---|---|---|
| `admin` | `Admin123!` | ADMINISTRADOR | Acceso total: CRUD de todas las entidades, usuarios y eliminaciones |
| `operador` | `Operador123!` | OPERADOR | Gestión de prestatarios y operaciones; **sin** acceso a usuarios ni a eliminaciones |

La diferencia entre ambos roles es demostrable: al entrar como `operador` desaparecen del menú
el módulo **Usuarios** y los botones **Eliminar**, y las rutas correspondientes redirigen con un
aviso de permisos insuficientes.

---

## 8. Funcionalidades

### 8.1 CRUD completo (35 % de la rúbrica)

Para cada entidad se implementan las cuatro operaciones con formularios, validación en cliente
y servidor, mensajes de resultado y confirmación JavaScript antes de eliminar:

| Entidad | Rutas |
|---|---|
| **Prestatarios** | `/prestatarios`, `/prestatarios/crear`, `/prestatarios/<id>/editar`, `/prestatarios/<id>/eliminar` |
| Categorías | `/categorias`, `/categorias/crear`, `/categorias/<id>/editar`, `/categorias/<id>/eliminar` |
| Laboratorios | `/laboratorios`, `/laboratorios/crear`, `/laboratorios/<id>/editar`, `/laboratorios/<id>/eliminar` |
| Equipos | `/equipos`, `/equipos/crear`, `/equipos/<id>/editar`, `/equipos/<id>/eliminar` |
| Usuarios del sistema | `/usuarios`, `/usuarios/crear`, `/usuarios/<id>/editar`, `/usuarios/<id>/eliminar` |

Además, la entidad principal del caso de estudio expone las **rutas limpias sugeridas por el
enunciado**:

| Ruta | Acción |
|---|---|
| `/` | Vista principal (panel con el listado y los indicadores) |
| `/crear` | Formulario de inserción de un prestatario |
| `/editar/<id>` | Formulario de modificación precargado |
| `/eliminar/<id>` | Eliminación (por `POST`, con confirmación JavaScript) |

### 8.2 Operaciones de negocio

**Reservas de laboratorios** (`/reservas`)

- Selección de laboratorio, prestatario, fecha, hora de inicio y duración.
- Duración **estándar de 70 minutos** (1 h 10 min), tomada automáticamente de la duración
  configurada para el laboratorio, o **personalizada** por el usuario.
- Cálculo de la **hora de finalización** en tiempo real (manipulación del DOM).
- Comprobación de disponibilidad en vivo mediante `fetch()` a `/reservas/disponibilidad`.
- **Rechazo de solapamientos**: si otro usuario ya reservó ese laboratorio en una franja que se
  cruza, el sistema muestra un error amigable y no guarda la reserva.
- Cancelación de reservas.

**Préstamos de equipos** (`/prestamos`)

- Selección de un equipo **DISPONIBLE** y de un prestatario.
- Al registrar el préstamo, el equipo pasa automáticamente a **PRESTADO**.
- Un equipo con préstamo activo no puede volver a prestarse.

**Devoluciones**

- Desde el listado de préstamos activos, con confirmación previa.
- El equipo vuelve a **DISPONIBLE** y se registra la fecha de devolución.

**Historial** (`/historial`)

- Vista unificada de reservas, préstamos y devoluciones.
- Filtros por tipo de operación, estado, prestatario, recurso (código o nombre) y rango de fechas.

### 8.3 Reglas de negocio garantizadas

**Solapamiento de reservas.** Dos reservas del mismo laboratorio y fecha se consideran
solapadas si se cumple:

```
hora_inicio_existente < hora_fin_nueva   AND   hora_fin_existente > hora_inicio_nueva
```

Por tanto:

| Caso | Franjas | Resultado |
|---|---|---|
| Adyacentes | 08:00–09:10 y 09:10–10:20 | **Permitido** |
| Solapadas | 08:00–09:10 y 09:09–10:19 | **Rechazado** |

Solo bloquean las reservas en estado `CONFIRMADA` o `ACTIVA`: una reserva `CANCELADA` o
`FINALIZADA` libera la franja.

**Estados de los equipos.** `DISPONIBLE → PRESTADO` al prestar; `PRESTADO → DISPONIBLE` al
devolver.

---

## 9. Seguridad implementada

| Riesgo | Mitigación |
|---|---|
| Inyección SQL | **Todas** las consultas usan parámetros (`?`). No se concatena entrada del usuario en SQL. |
| Contraseñas en texto plano | Se almacenan como **hash Werkzeug** (`scrypt`), en un campo `VARCHAR(255)`. |
| Exposición de hashes | Los servicios de usuario nunca seleccionan ni devuelven `password_hash` en los listados ni en la sesión. |
| Falsificación de identidad del operador | El usuario que registra una reserva o un préstamo se toma **siempre de la sesión del servidor**, nunca de un campo enviado por el navegador. |
| Escalada de privilegios | El registro público no existe en la web; solo un ADMINISTRADOR puede crear usuarios y asignar roles. |
| CSRF | Todos los `POST` web exigen un token CSRF de sesión; sin token válido responden `400`. |
| Acciones destructivas por URL | Las eliminaciones usan exclusivamente `POST`; un `GET` a `/eliminar/<id>` responde `405`. |
| Acceso sin sesión | Cada ruta comprueba sesión y permisos; el rol y el estado del usuario se **revalidan contra la base de datos en cada petición**. |
| Fuga de información en errores | Manejadores de error propios para `400`, `403`, `404` y `500`: nunca se muestra una traza al usuario. |
| Validación solo en el cliente | La validación de HTML5 y JavaScript es una mejora de usabilidad; la validación **definitiva** se ejecuta en el servidor antes de tocar la base de datos. |

---

## 10. Interfaz, diseño responsive y JavaScript

**HTML5 semántico.** Se utilizan `header`, `nav`, `main`, `section`, `article`, `table`,
`caption`, `form`, `label` y `output`, con `lang="es"` y `meta viewport`.

**CSS3 propio** (`static/css/estilos.css`), sin frameworks. Enfoque *mobile-first* con
breakpoints en **375 px** (móvil), **768 px** (tablet) y **1280 px** (escritorio). Incluye
navbar, formularios, botones, insignias de estado, mensajes flash, estados vacíos, foco visible
y un contraste de color razonable. En pantallas pequeñas las tablas se transforman en tarjetas
apiladas mediante CSS, sin duplicar el HTML.

**JavaScript Vanilla** (`static/js/main.js`), organizado en módulos comentados:

1. Menú de navegación móvil (con `aria-expanded`).
2. Cierre de mensajes flash.
3. **Confirmación antes de eliminar**, cancelar y devolver (`window.confirm`).
4. Validación en el cliente con realimentación visual (clase `.invalido`).
5. **Cálculo en vivo de la hora de finalización** de una reserva (manipulación del DOM).
6. **`fetch()`** al endpoint `/reservas/disponibilidad` para avisar de solapamientos antes de
   enviar el formulario.
7. Protección contra el doble envío.

---

## 11. Ejecutar las pruebas

Todas las pruebas se ejecutan desde la raíz del proyecto y necesitan `PYTHONPATH=.` para que el
paquete `app` sea importable.

### 11.1 Verificación rápida (smoke test)

```bash
PYTHONPATH=. python tests/smoke_test.py
```

Comprueba el esquema, las claves foráneas, el hash de contraseñas, la regla de solapamiento y el
arranque de la aplicación web.

### 11.2 Pruebas de integración de la capa web

```bash
PYTHONPATH=. python tests/test_web_phase6.py
```

Cubre autenticación, CSRF, el ciclo CRUD completo por HTTP de todas las entidades, reservas y
solapamientos, préstamos y devoluciones, historial, permisos por rol, archivos estáticos y la
ausencia de errores 500. **Se ejecuta sobre una base de datos temporal**, por lo que no altera
`database/techloan.db`.

### 11.3 Regresión del backend

```bash
PYTHONPATH=. python tests/test_crud_phase5.py
PYTHONPATH=. python tests/test_validations_phase5.py
PYTHONPATH=. python tests/test_security_phase5.py
PYTHONPATH=. python tests/test_overlap_phase5.py
PYTHONPATH=. python tests/test_roles_phase5.py
PYTHONPATH=. python tests/test_historial_phase4.py
```

---

## 12. Flujo sugerido para la exposición

1. `python init_db.py` → mostrar la reconstrucción de la base de datos desde `schema.sql`.
2. `python run_server.py` → abrir `http://127.0.0.1:5000`.
3. Iniciar sesión como `admin` → mostrar el panel con indicadores.
4. **Prestatarios**: crear, listar, editar y **eliminar con confirmación JavaScript**.
5. **Categorías / Laboratorios / Equipos**: crear un laboratorio y un equipo relacionándolos.
6. **Reservas**: crear una reserva de 70 minutos y mostrar la hora de finalización calculada.
7. **Solapamiento**: intentar una segunda reserva en la misma franja → el sistema la rechaza.
   Mostrar también que una franja **adyacente** sí se acepta.
8. **Préstamos**: prestar un equipo y mostrar que pasa a **PRESTADO**.
9. **Devolución**: devolverlo y mostrar que vuelve a **DISPONIBLE**.
10. **Historial**: mostrar la vista unificada y aplicar un filtro.
11. **Roles**: cerrar sesión, entrar como `operador` y mostrar la restricción administrativa.
12. Mostrar `schema.sql`, `README.md` y ejecutar las pruebas.

---

## 13. Arquitectura

```
Navegador (HTML5 + CSS3 + JavaScript Vanilla)
        │  HTTP (GET / POST)
        ▼
Flask  ──►  Rutas web (Jinja2)  ──┐
        └─►  API JSON (/api/...)  ─┤
                                   ▼
                        Servicios POO (validación + reglas de negocio)
                                   │
                                   ▼
                        SQLite3 (consultas parametrizadas)
```

Las dos capas de entrada (web y API JSON) comparten exactamente los mismos servicios, de modo
que las reglas de negocio y las validaciones son únicas y no pueden divergir.

---

*Proyecto final de Programación III — IUTEPI.*
