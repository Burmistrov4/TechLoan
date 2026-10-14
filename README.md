# TechLoan

**Plataforma web de gestión de reservas y préstamos de recursos tecnológicos**

Aplicación web desarrollada con **Flask + SQLite3 + Jinja2 + HTML5 + CSS3 + JavaScript
Vanilla**, como proyecto final de la asignatura **Programación III** (IUTEPI).

Sin frameworks de frontend, sin servicios externos obligatorios y **funciona sin conexión
a internet**.

---

## 1. El problema que resuelve

En un centro de formación técnica los laboratorios y el equipamiento se comparten entre
docentes y grupos. Cuando eso se lleva en papel o por mensajería informal aparecen tres
problemas recurrentes:

1. **Doble reserva del mismo laboratorio**, porque no hay un registro único y consultable.
2. **Pérdida de trazabilidad de los equipos**: nadie sabe con certeza quién tiene un
   proyector, un switch o una laptop, ni desde cuándo.
3. **Ausencia de historial**: al no quedar registro, no se puede auditar qué se hizo,
   cuándo y quién lo autorizó.

**TechLoan** resuelve los tres:

- registra **prestatarios** (quienes reciben un espacio o un equipo);
- administra el **inventario** de laboratorios, categorías y equipos;
- gestiona **reservas por franja horaria**, **impidiendo solapamientos** y proponiendo
  alternativas cuando el horario está ocupado;
- gestiona **préstamos y devoluciones**, actualizando el estado del equipo de forma
  automática y avisando de los que llevan demasiado tiempo fuera;
- ofrece un **panel analítico** con indicadores y gráficos, y un **registro de auditoría**
  que responde a cualquier pregunta con nombre y fecha.

---

## 2. Tecnologías utilizadas

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12, Flask 3.1 |
| Base de datos | SQLite3 (librería nativa `sqlite3`), consultas parametrizadas |
| Plantillas | Jinja2 |
| Frontend | HTML5 semántico, CSS3 (responsive, sin frameworks), JavaScript Vanilla |
| Gráficos | SVG generado en el cliente, sin librerías |
| Iconografía | SVG en línea, sin dependencias ni peticiones de red |
| Seguridad | Werkzeug (`scrypt`), sesiones Flask, token CSRF, permisos por rol |
| Pruebas | Scripts de integración con el cliente de pruebas de Flask |

> **No** se utiliza React, Vue, Angular, Bootstrap ni Tailwind. Tampoco Chart.js, Three.js
> ni ninguna librería de animación: todo el movimiento y los gráficos son CSS y JavaScript
> escritos a mano. Esto mantiene el proyecto explicable y garantiza que funcione sin red.

---

## 3. Estructura del proyecto

```
Proyecto Final de Python/
│
├── run_server.py                         # Punto de entrada: inicia el servidor Flask
├── init_db.py                            # Inicializa la base de datos desde schema.sql
├── demostrar_seguridad.py                # Demuestra hash, validaciones e inyección SQL
├── exportar_a_mysql.py                   # Volcado MySQL opcional (para phpMyAdmin)
├── schema.sql                            # Tablas, índices y datos de prueba
├── requirements.txt                      # Dependencias (Flask, Werkzeug)
├── README.md                             # Este documento
│
├── database/
│   └── techloan.db                       # Base de datos SQLite3 (generada)
│
├── static/                               # Archivos estáticos
│   ├── favicon.svg                       # Icono de la aplicación
│   ├── css/
│   │   ├── estilos.css                   # Sistema de diseño + interfaz de la aplicación
│   │   └── landing.css                   # Portada pública y pantalla de acceso
│   ├── js/
│   │   ├── main.js                       # Interactividad de la aplicación
│   │   ├── graficos.js                   # Gráficos SVG dibujados en el cliente
│   │   ├── tutorial.js                   # Tutorial guiado (walkthrough) del panel
│   │   └── landing.js                    # Escenas 3D y animaciones de la portada
│   └── img/                              # Logotipo, iconos e ilustraciones
│
├── templates/                            # Plantillas HTML procesadas por Jinja2
│   ├── base.html                         # Documento base (head, tema, notificaciones)
│   ├── base_app.html                     # Shell de la aplicación (barra lateral + superior)
│   ├── base_publico.html                 # Shell de las páginas sin sesión
│   ├── landing.html                      # Portada pública
│   ├── index.html                        # Panel de inicio con gráficos
│   ├── perfil.html · ayuda.html          # Cuenta propia y guía de uso
│   ├── parciales/                        # Fragmentos reutilizables (iconos, listados, campos)
│   ├── auth/login.html                   # Formulario de acceso
│   ├── auth/registro.html                # Alta de cuenta
│   ├── auth/revisar_correo.html          # Aviso de correo enviado (y enlace en demo)
│   ├── auth/confirmar.html               # Resultado de la confirmación
│   ├── auth/reenviar.html                # Pedir un enlace nuevo
│   ├── prestatarios/ · laboratorios/ · categorias/ · equipos/ · usuarios/
│   ├── reservas/                         # Listado, formulario y comprobante
│   ├── prestamos/ · historial/ · auditoria/
│   └── errores/error.html
│
├── app/                                  # Código Python (arquitectura por capas)
│   ├── server.py                         # create_app(): blueprints, contexto y errores
│   ├── config.py                         # Configuración y parámetros de negocio
│   ├── database.py                       # Conexión SQLite3 (abrir/cerrar por operación)
│   ├── models/entities.py                # Clases de dominio (POO)
│   ├── services/                         # Lógica de negocio y validaciones
│   │   ├── auth_service.py               #   Autenticación y matriz de permisos
│   │   ├── usuario_service.py            #   Usuarios y cambio de contraseña
│   │   ├── prestatario_service.py
│   │   ├── laboratorio_service.py · categoria_service.py · equipo_service.py
│   │   ├── reservation_service.py        #   Reservas, solapamientos y sugerencias
│   │   ├── prestamo_equipo_service.py    #   Préstamos y devoluciones
│   │   ├── disponibilidad_service.py
│   │   ├── historial_service.py
│   │   ├── dashboard_service.py          #   Indicadores, tendencias y series de gráficos
│   │   ├── alertas_service.py            #   Avisos operativos
│   │   ├── auditoria_service.py          #   Registro de actividad
│   │   ├── registro_service.py           #   Alta con confirmación por correo
│   │   └── correo_service.py             #   Envío SMTP (con modo demostración)
│   ├── routes/
│   │   ├── web_common.py                 # Blueprint web, permisos, CSRF, listados y CSV
│   │   ├── web_auth_routes.py            # Portada, panel, acceso, registro y búsqueda
│   │   ├── web_crud_routes.py            # CRUD web de las entidades
│   │   ├── web_operations_routes.py      # Reservas, préstamos, historial
│   │   ├── web_extra_routes.py           # Perfil, guía de uso y auditoría
│   │   └── *_routes.py                   # API JSON (/api/...)
│   ├── security/permissions.py           # Revalidación de sesión y permisos
│   └── gui/                              # Interfaz Tkinter previa (prototipo, no prioritaria)
│
├── docs/
│   ├── MANUAL_DE_USUARIO.md              # Manual de uso completo
│   ├── GUIA_EXPOSICION.md                # Guion de la defensa
│   ├── GUIA_BASE_DE_DATOS.md             # Cómo abrir la BD (SQLite) y el caso phpMyAdmin
│   ├── DEMOSTRACION_SEGURIDAD.md         # Guion de la demo de hash/validaciones/SQLi
│   ├── capturas/                         # Evidencia visual de la verificación
│   └── PROJECT_CONTEXT/                  # Documentación de continuidad del proyecto
│
└── tests/                                # Pruebas automatizadas
    ├── test_web_phase6.py                # Integración de la capa web
    ├── test_registro_phase7.py           # Registro y confirmación por correo
    ├── smoke_test.py                     # Verificación rápida de extremo a extremo
    ├── test_crud_phase5.py · test_validations_phase5.py
    ├── test_security_phase5.py · test_overlap_phase5.py
    ├── test_roles_phase5.py · test_historial_phase4.py
    └── crud_test.py · security_test.py
```

### 3.1 Equivalencia con la estructura sugerida por el enunciado

El PDF propone una arquitectura simplificada ("Se sugiere la siguiente arquitectura"). Se
respeta su intención y se conserva, además, la organización modular del proyecto:

| Elemento sugerido en el enunciado | Dónde está en este proyecto |
|---|---|
| `app.py` — Servidor principal de Flask | `run_server.py` (entrada) + `app/server.py` (`create_app`) |
| `database.db` — Archivo de la base de datos | `database/techloan.db` |
| `schema.sql` — Script de creación de tablas | `schema.sql` (raíz) |
| `static/css/estilos.css` | `static/css/estilos.css` |
| `static/js/main.js` | `static/js/main.js` |
| `templates/base.html` | `templates/base.html` |
| `templates/index.html` — Vista principal | `templates/index.html` (panel) + `templates/<entidad>/index.html` |
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

### 4.2 Crear y activar un entorno virtual

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

### 4.3 Instalar las dependencias

```bash
pip install -r requirements.txt
```

O de forma equivalente:

```bash
pip install flask
```

`requirements.txt` contiene únicamente:

```
Flask==3.1.2
Werkzeug==3.1.3
```

---

## 5. Inicializar la base de datos

El proyecto incluye `schema.sql`, que crea **todas las tablas, los índices y los datos de
prueba** (incluidos los usuarios del sistema y un registro de actividad inicial).

```bash
python init_db.py
```

Salida esperada:

```
Base de datos reconstruida: .../database/techloan.db
----------------------------------------------------------
  usuarios_sistema          2 registro(s)
  prestatarios              4 registro(s)
  categorias                3 registro(s)
  laboratorios              3 registro(s)
  equipos                   4 registro(s)
  reservas                  3 registro(s)
  prestamos_equipos         2 registro(s)
  auditoria                 5 registro(s)
----------------------------------------------------------
  integrity_check: ok

  Reservas de demostración (útiles para la exposición):
    LAB-01  2026-10-15  08:00-09:10  (70 min)
    ...
```

> **Importante:** `init_db.py` **elimina y vuelve a crear** las tablas del archivo de
> destino. No lo ejecutes sobre una base de datos con información real que quieras
> conservar. Para reconstruir un archivo distinto: `python init_db.py ruta/otra.db`.

Las fechas de los datos de prueba son **relativas al día de ejecución**
(`date('now','localtime','+N days')`), así que las reservas de demostración **nunca quedan
vencidas**.

### 5.1 ¿Por qué phpMyAdmin no abre `techloan.db`?

La base de datos es **SQLite3** (lo pide el enunciado), no MySQL. Un archivo `.db` de
SQLite empieza por el texto `SQLite format 3`; al subirlo a phpMyAdmin, MariaDB intenta
leerlo como SQL y responde:

```
#1064 - You have an error in your SQL syntax ... near 'SQLite format 3' at line 1
```

Es lo esperado al mezclar dos motores distintos, **no un fallo del proyecto**.

- Para **revisar** la base de datos real: **DB Browser for SQLite** o
  `python demostrar_seguridad.py`.
- Para **verla en phpMyAdmin** (opcional): `python exportar_a_mysql.py` genera
  `database/techloan_mysql.sql`, importable desde phpMyAdmin. La aplicación sigue
  trabajando con SQLite.

El detalle completo está en `docs/GUIA_BASE_DE_DATOS.md`.

---

## 6. Ejecutar el servidor

```bash
python run_server.py
```

Abre el navegador en **http://127.0.0.1:5000**.

Verás la **portada pública** del producto. Haz clic en *Iniciar sesión* o ve a `/login`. Una vez
dentro, `/` pasa a ser el panel de control.

---

## 7. Usuarios de prueba

Los crea `schema.sql` con la contraseña almacenada **como hash** (nunca en texto plano).

| Usuario | Contraseña | Rol | Alcance |
|---|---|---|---|
| `admin` | `Admin123!` | ADMINISTRADOR | Acceso total: CRUD de todo, usuarios, auditoría y eliminaciones |
| `operador` | `Operador123!` | OPERADOR | Operación diaria; **sin** usuarios, auditoría ni eliminaciones |

La diferencia es demostrable: al entrar como `operador` desaparecen del menú los módulos
*Usuarios* y *Auditoría*, y los botones *Eliminar*; las rutas correspondientes redirigen con
un aviso de permisos insuficientes.

> **Estas credenciales no se muestran en la aplicación.** La pantalla de acceso solo indica
> dónde encontrarlas, porque dejar contraseñas a la vista —aunque sean de prueba— es una mala
> práctica. Además, cualquier persona puede **crear su propia cuenta** desde `/registro`: se
> da de alta como *operador* y confirma su correo antes de poder entrar (ver §8.5).

---

## 8. Funcionalidades

### 8.1 CRUD completo (35 % de la rúbrica)

Para cada entidad, las cuatro operaciones con formularios, validación en cliente y
servidor, mensajes de resultado y confirmación JavaScript antes de eliminar:

| Entidad | Rutas |
|---|---|
| **Prestatarios** | `/prestatarios`, `/prestatarios/crear`, `/prestatarios/<id>/editar`, `/prestatarios/<id>/eliminar` |
| Categorías | `/categorias`, `/categorias/crear`, `/categorias/<id>/editar`, `/categorias/<id>/eliminar` |
| Laboratorios | `/laboratorios`, `/laboratorios/crear`, `/laboratorios/<id>/editar`, `/laboratorios/<id>/eliminar` |
| Equipos | `/equipos`, `/equipos/crear`, `/equipos/<id>/editar`, `/equipos/<id>/eliminar` |
| Usuarios del sistema | `/usuarios`, `/usuarios/crear`, `/usuarios/<id>/editar`, `/usuarios/<id>/eliminar` |

Además, la entidad principal expone las **rutas limpias del enunciado**:

| Ruta | Acción |
|---|---|
| `/` | Vista principal: portada pública para visitantes, panel para usuarios con sesión |
| `/crear` | Formulario de inserción de un prestatario |
| `/editar/<id>` | Formulario de modificación precargado |
| `/eliminar/<id>` | Eliminación (por `POST`, con confirmación JavaScript) |

### 8.2 Capacidades de producto

Además del CRUD básico, la aplicación incorpora lo que se espera de una herramienta
profesional:

**Panel analítico.** Seis indicadores con variación respecto a la semana anterior, tres
gráficos (reservas por día, inventario por estado, ocupación por laboratorio), próximas
reservas y actividad reciente. Los gráficos son SVG dibujados en el cliente: se adaptan al
tema, se imprimen con calidad y no dependen de ninguna librería.

**Búsqueda global (Ctrl+K).** Una paleta de comandos que encuentra secciones, acciones y
**registros concretos** (prestatarios, equipos, laboratorios y reservas), respetando los
permisos del rol.

**Listados profesionales.** En todos los listados: búsqueda en vivo con retardo, ordenación
por cualquier columna, paginación y **exportación a CSV** que respeta el filtro activo y se
abre en Excel sin ajustes.

**Sugerencias inteligentes de horario.** Cuando una reserva choca con otra, el sistema no se
limita a rechazarla: calcula los huecos reales de la jornada y ofrece las franjas libres más
cercanas, aplicables con un clic.

**Alertas operativas.** Préstamos con más de 7 días sin devolver (destacados en rojo, con
los días transcurridos y un botón para devolverlos), reservas programadas para hoy y
laboratorios con alta ocupación.

**Registro de auditoría.** Cada acción queda anotada con su autor, fecha, detalle e IP:
altas, modificaciones, bajas, préstamos, devoluciones, cancelaciones, accesos y
exportaciones. Con filtros y exportación. El registro **sobrevive a la eliminación del
usuario**, conservando su nombre como evidencia.

**Comprobante imprimible.** Cada reserva genera un documento con folio, listo para imprimir
o guardar en PDF.

**Perfil propio.** Cada usuario puede cambiar su contraseña, con la actual como comprobación
de identidad.

**Tema claro y oscuro.** Conmutador en la barra superior, con la preferencia recordada y sin
destello al cargar. Los gráficos se redibujan al cambiar.

**Tutorial guiado.** La primera vez que un usuario entra al panel arranca solo un recorrido
de 8 pasos que va señalando cada parte de la interfaz (menú, búsqueda, tema, alertas, panel y
cuenta) con una tarjeta explicativa. Se puede saltar, repetir desde el menú de usuario o
desde la guía de uso, y no vuelve a aparecer una vez visto. Es navegable con teclado
(`←`, `→`, `Esc`).

**Escenas 3D interactivas.** La portada no usa ilustraciones planas: la composición del héroe
—un tablero con indicadores, gráficos y la agenda del día— y los objetos de cada módulo son
**geometría real construida con CSS 3D** (`transform-style: preserve-3d`), sin WebGL ni
librerías. La escena se inclina siguiendo el puntero y se puede **girar arrastrando**, y los
objetos de los módulos se funden entre sí al cambiar de pestaña.

**Aplicación instalable.** Manifiesto web y favicon propios: se puede añadir a la pantalla
de inicio.

### 8.3 Operaciones de negocio

**Reservas de laboratorios** (`/reservas`)

- Selección de laboratorio, prestatario, fecha, hora de inicio y duración.
- Duración **estándar de 70 minutos**, tomada del laboratorio, o **personalizada**.
- Cálculo de la **hora de finalización** en vivo (manipulación del DOM).
- **Línea de tiempo del día** que muestra de un vistazo qué franjas están ocupadas.
- Comprobación de disponibilidad con `fetch()` a `/reservas/disponibilidad`.
- **Rechazo de solapamientos** con mensaje claro y **alternativas sugeridas**.
- Cancelación de reservas con liberación inmediata de la franja.
- Comprobante imprimible por reserva.

**Préstamos de equipos** (`/prestamos`)

- Selección de un equipo **DISPONIBLE** y de un prestatario.
- Al registrar el préstamo, el equipo pasa a **PRESTADO**.
- Un equipo con préstamo activo no puede volver a prestarse.
- Días transcurridos visibles en cada fila, con los vencidos destacados.

**Devoluciones**

- Desde el listado de préstamos activos, con confirmación previa.
- El equipo vuelve a **DISPONIBLE** y se registra la fecha.

**Historial** (`/historial`)

- Vista unificada de reservas, préstamos y devoluciones.
- Filtros por tipo, estado, prestatario, recurso y rango de fechas.
- Exportación a CSV del resultado filtrado.

### 8.4 Reglas de negocio garantizadas

**Solapamiento de reservas.** Dos reservas del mismo laboratorio y fecha se consideran
solapadas si se cumple:

```
hora_inicio_existente < hora_fin_nueva   AND   hora_fin_existente > hora_inicio_nueva
```

| Caso | Franjas | Resultado |
|---|---|---|
| Adyacentes | 08:00–09:10 y 09:10–10:20 | **Permitido** |
| Solapadas | 08:00–09:10 y 09:09–10:19 | **Rechazado** |

Solo bloquean las reservas `CONFIRMADA` o `ACTIVA`: una reserva `CANCELADA` o `FINALIZADA`
libera la franja.

**Estados de los equipos.** `DISPONIBLE → PRESTADO` al prestar; `PRESTADO → DISPONIBLE` al
devolver.

### 8.5 Registro de usuarios con confirmación por correo

Cualquiera puede crear su cuenta desde `/registro` sin que intervenga un administrador. El
flujo garantiza que la cuenta pertenece a quien dice:

| Paso | Qué ocurre |
|---|---|
| 1. Alta | Se valida el formulario y se crea el usuario con `email_confirmado = 0` |
| 2. Rol | El autoregistro crea siempre un **OPERADOR**: nadie se concede privilegios |
| 3. Token | Se emite un token aleatorio (`secrets`), de **un solo uso** y con caducidad (24 h por defecto) |
| 4. Correo | Se envía el enlace `http://…/confirmar/<token>` |
| 5. Activación | Al abrir el enlace, la cuenta pasa a confirmada y el token queda inservible |
| 6. Acceso | Ya se puede entrar con el **usuario o con el correo** |

Si el enlace caduca o se pierde, `/reenviar` emite uno nuevo e invalida el anterior.

**Sin confirmar no se entra**, y el mensaje de error lo explica. Ese aviso solo se muestra a
quien ya acertó la contraseña, así que no revela si una cuenta existe.

#### Configurar el correo saliente

El único módulo que necesita hablar con el exterior es este. Se configura por variables de
entorno; si no se define ninguna, la aplicación entra en **modo demostración**.

| Variable | Para qué |
|---|---|
| `TECHLOAN_SMTP_HOST` | Servidor SMTP (p. ej. `smtp.gmail.com`) |
| `TECHLOAN_SMTP_PORT` | Puerto (por defecto `587`, con STARTTLS) |
| `TECHLOAN_SMTP_USER` | Usuario de la cuenta |
| `TECHLOAN_SMTP_PASSWORD` | Contraseña o *contraseña de aplicación* |
| `TECHLOAN_SMTP_FROM` | Remitente (por defecto, el usuario) |
| `TECHLOAN_SMTP_TLS` | `0` para desactivar STARTTLS |
| `TECHLOAN_URL_BASE` | Dirección pública con la que se construyen los enlaces |
| `TECHLOAN_HORAS_TOKEN` | Horas de validez del enlace (24 por defecto) |

```bash
# Ejemplo en Windows (PowerShell)
$env:TECHLOAN_SMTP_HOST = "smtp.gmail.com"
$env:TECHLOAN_SMTP_USER = "micorreo@gmail.com"
$env:TECHLOAN_SMTP_PASSWORD = "clave-de-aplicacion"
python run_server.py
```

**Modo demostración (sin SMTP).** No se envía nada: el mensaje se guarda en
`database/buzon/` y el enlace de confirmación se muestra en pantalla tras el registro. Es lo
que permite enseñar el flujo completo en la defensa sin internet ni cuenta de correo, y
también si el envío real falla.

### 8.6 Listados enriquecidos: hasta cuándo y qué tan ocupado

Los listados de **Equipos** y **Laboratorios** no se quedan en el estado: dicen
**para cuándo** y **cómo viene la demanda**, para que la decisión se tome sin abrir cada
registro.

En `/equipos`, cada fila muestra una columna **Situación del préstamo**:

- **PRESTADO** → quién lo tiene, desde cuándo (con los días transcurridos), la **fecha
  límite de devolución** calculada a partir de `DIAS_PRESTAMO_LIMITE` (7 días por defecto)
  y un distintivo de color:
  - verde "Vence el DD/MM" cuando aún faltan días,
  - amarillo "Vence mañana" / "Vence hoy" según corresponda,
  - rojo "Vencido hace N días" cuando se pasó del plazo.
  Incluye el teléfono del prestatario para poder contactarlo y un botón **Devolver** en la
  misma fila.
- **DISPONIBLE** → "Disponible para prestar".
- Otros estados → trazo neutro.

En `/laboratorios`, cada fila muestra una columna **Ocupación**:

- **Ocupado ahora** (reserva en curso) / **Reservado hoy** (la próxima es hoy) /
  **Próxima reserva** (en días siguientes), con la fecha, la franja horaria
  `HH:MM–HH:MM` y el nombre del prestatario.
- Cuando hay más reservas dentro de los próximos 7 días, se añade "N reservas en los
  próximos 7 días" como señal de saturación.
- Si está libre ahora: "Libre ahora · N reservas esta semana" o
  "Libre, sin reservas próximas".

Los datos los calculan `PrestamoEquipoService.prestamos_activos_por_equipo()` y
`ReservationService.proximas_reservas_por_laboratorio()` en una sola consulta cada uno, de
modo que añadir la columna no ralentiza el listado.

---

## 9. Seguridad implementada

| Riesgo | Mitigación |
|---|---|
| Inyección SQL | **Todas** las consultas usan parámetros (`?`). No se concatena entrada del usuario. |
| Contraseñas en texto plano | Se almacenan como **hash Werkzeug** (`scrypt`), en un campo `VARCHAR(255)`. |
| Exposición de hashes | Los servicios nunca seleccionan ni devuelven `password_hash`. |
| Falsificación de identidad | El usuario que registra una operación se toma **siempre de la sesión**, nunca de un campo del formulario. |
| Escalada de privilegios | No existe registro público. Solo un ADMINISTRADOR crea usuarios y asigna roles. |
| CSRF | Todos los `POST` web exigen un token CSRF de sesión; sin él responden `400`. |
| Acciones destructivas por URL | Las eliminaciones usan exclusivamente `POST`; un `GET` a `/eliminar/<id>` responde `405`. |
| Acceso sin sesión | Cada ruta comprueba sesión y permisos; el rol y el estado del usuario se **revalidan contra la base de datos en cada petición**. |
| Fuga de información en errores | Manejadores propios para `400`, `403`, `404` y `500`: nunca se muestra una traza. |
| Validación solo en el cliente | La validación de HTML5 y JavaScript es una mejora de usabilidad; la **definitiva** se ejecuta en el servidor. |
| Pérdida de rastro | Registro de auditoría con autor, fecha, detalle e IP, independiente del ciclo de vida del usuario. |

### 9.1 Cómo demostrarlo en la defensa

```bash
python demostrar_seguridad.py
```

Reúne, en un minuto y **sin modificar la base de datos**, las tres comprobaciones que
suelen pedirse:

1. las contraseñas se guardan como **hash scrypt** en `password_hash VARCHAR(255)`
   (162 caracteres, nunca en claro);
2. las **validaciones** del servidor rechazan datos inválidos;
3. la **inyección SQL** no funciona: las consultas van parametrizadas.

Guion completo y preguntas previsibles en `docs/DEMOSTRACION_SEGURIDAD.md`.

---

## 10. Interfaz, diseño y accesibilidad

**HTML5 semántico.** `header`, `nav`, `main`, `section`, `article`, `table`, `caption`,
`form`, `label`, `output` y `details`, con `lang="es"` y `meta viewport`.

**CSS3 propio**, sin frameworks, con un sistema de diseño basado en variables: tokens de
color, tipografía, espaciado, radios y sombras, y **dos temas completos** (claro y oscuro)
que comparten estructura. Enfoque *mobile-first* con puntos de ruptura en **375 px**
(celular), **768 px** (tablet) y **1280 px** (escritorio). En pantallas pequeñas las tablas se
transforman en tarjetas apiladas mediante CSS, sin duplicar el HTML.

**JavaScript Vanilla** (`static/js/`), organizado en módulos comentados:

| Archivo | Responsabilidad |
|---|---|
| `main.js` | Tema, barra lateral, menús, notificaciones, paleta de comandos, confirmaciones, validación, búsqueda con retardo, línea de tiempo y sugerencias, contadores animados |
| `graficos.js` | Gráficos de barras, anillo y barras horizontales en SVG, con colores tomados del tema |
| `landing.js` | Escena 3D con paralaje de ratón, revelado al desplazar, pestañas de módulos |

**Accesibilidad.** Enlace «saltar al contenido», foco visible en todos los controles,
`aria-label` en los botones de icono, `aria-live` en las notificaciones y los resultados
dinámicos, roles ARIA en la paleta de comandos y en las pestañas, contraste cuidado y
respeto por `prefers-reduced-motion`.

**Portada pública.** Presentación del producto con escena 3D en CSS (`perspective` +
`preserve-3d`), animaciones al desplazar, secciones de características, módulos, seguridad,
planes y preguntas frecuentes. Todo con CSS y JavaScript propios.

---

## 11. Ejecutar las pruebas

Todas se ejecutan desde la raíz del proyecto y necesitan `PYTHONPATH=.` para que el paquete
`app` sea importable.

> **Aislamiento:** cada prueba trabaja sobre una **base de datos temporal**
> (`tests/_tempdb.py`), así que **nunca** alteran `database/techloan.db`. Se puede correr
> la suite entera sin miedo a contaminar la base de datos que se entrega.

### 11.1 Verificación rápida

```bash
PYTHONPATH=. python tests/smoke_test.py
```

Comprueba el esquema, las claves foráneas, el hash de contraseñas, la regla de solapamiento,
las sugerencias de horario, la auditoría y el arranque de la aplicación web.

### 11.2 Pruebas de integración de la capa web

```bash
PYTHONPATH=. python tests/test_web_phase6.py
```

Cubre autenticación, CSRF, portada pública, búsqueda global, listados con búsqueda/orden/
paginación/CSV, el ciclo CRUD completo por HTTP, reservas y solapamientos, sugerencias,
préstamos y devoluciones, historial, auditoría, perfil, comprobante, permisos por rol,
archivos estáticos y la ausencia de errores 500. **Se ejecuta sobre una base de datos
temporal**, por lo que no altera `database/techloan.db`.

### 11.3 Pruebas del registro con confirmación por correo

```bash
PYTHONPATH=. python tests/test_registro_phase7.py
```

Cubre el alta, la emisión del token, la confirmación desde el enlace, el acceso con el
correo, el rechazo mientras la cuenta no está confirmada, las validaciones del formulario,
los duplicados, el token inválido, el caducado, el reutilizado y el reenvío. Usa una base de
datos y un buzón temporales.

### 11.4 Regresión del backend

```bash
PYTHONPATH=. python tests/test_crud_phase5.py
PYTHONPATH=. python tests/test_validations_phase5.py
PYTHONPATH=. python tests/test_security_phase5.py
PYTHONPATH=. python tests/test_overlap_phase5.py
PYTHONPATH=. python tests/test_roles_phase5.py
PYTHONPATH=. python tests/test_historial_phase4.py
```

---

## 12. Documentación adicional

| Documento | Contenido |
|---|---|
| `docs/MANUAL_DE_USUARIO.md` | Manual de uso completo: tareas paso a paso, atajos, reglas, roles, solución de problemas y glosario |
| `docs/GUIA_EXPOSICION.md` | Guion de la defensa: recorrido, plan de contingencia y preguntas previsibles |
| `docs/GUIA_BASE_DE_DATOS.md` | Cómo abrir la base de datos SQLite y por qué phpMyAdmin da error `#1064` |
| `docs/DEMOSTRACION_SEGURIDAD.md` | Guion de un minuto: hash de contraseñas, validaciones e inyección SQL |
| `docs/PROJECT_CONTEXT/` | Estado del proyecto, decisiones, criterios de aceptación y registro de trabajo |
| `docs/capturas/` | Evidencia visual de la verificación en navegador real |

La propia aplicación incluye una **Guía de uso** en el menú lateral, con la misma
información resumida y accesible sin salir del sistema.

---

## 13. Flujo sugerido para la exposición

1. `python init_db.py` → mostrar la reconstrucción de la base de datos desde `schema.sql`.
2. `python run_server.py` → abrir `http://127.0.0.1:5000` y mostrar la **portada pública**.
3. Iniciar sesión como `admin` → **panel** con indicadores y gráficos.
4. **Prestatarios**: crear, listar, buscar, ordenar, editar y **eliminar con confirmación**.
5. **Catálogos**: crear categoría, laboratorio y equipo relacionándolos.
6. **Reservas**: mostrar la línea de tiempo del día y crear una reserva de 70 minutos.
7. **Solapamiento**: intentar una reserva en una franja ocupada → rechazo + **alternativas**;
   demostrar que una franja **adyacente** sí se acepta.
8. **Comprobante**: abrir el comprobante imprimible de la reserva.
9. **Préstamos**: prestar un equipo → estado **PRESTADO**; devolverlo → **DISPONIBLE**.
10. **Historial**: vista unificada y filtros; exportar a CSV.
11. **Auditoría**: mostrar el rastro de todo lo anterior.
12. **Roles**: entrar como `operador` y mostrar la restricción administrativa.
13. **Búsqueda global**: `Ctrl`+`K` y encontrar un registro concreto.
14. **Tema oscuro** y **responsive** (375 / 768 / 1280 px).
15. Mostrar `schema.sql`, `README.md` y ejecutar las pruebas.
16. **Listados enriquecidos**: abrir `/equipos` y señalar la columna "Situación del
    préstamo" (prestado a quién, desde cuándo y cuándo vence, con el botón *Devolver*);
    abrir `/laboratorios` y señalar la columna "Ocupación" (próxima reserva, horario y
    demanda de la semana).
17. **Seguridad en vivo**: `python demostrar_seguridad.py` → hash de las contraseñas,
    validaciones y por qué la inyección SQL no funciona.

---

## 14. Arquitectura

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

Las dos capas de entrada (web y API JSON) comparten exactamente los mismos servicios, de
modo que las reglas de negocio y las validaciones son únicas y no pueden divergir.

---

*Proyecto final de Programación III — IUTEPI.*
