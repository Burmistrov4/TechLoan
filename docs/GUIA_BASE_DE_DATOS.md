# Guía de la base de datos de TechLoan

Esta guía responde a dos preguntas concretas:

1. **¿Por qué phpMyAdmin no puede abrir `techloan.db`?** (error `#1064 … 'SQLite format 3'`).
2. **¿Cómo reviso la base de datos y demuestro que las contraseñas se guardan con hash?**

---

## 1. La base de datos es SQLite3, no MySQL

El enunciado del proyecto pide **Flask y SQLite3**, así que la aplicación usa
**SQLite3** (`import sqlite3` de la librería estándar). El archivo
`database/techloan.db` es un archivo **SQLite**, no un volcado de MySQL.

Los dos motores son incompatibles:

| | SQLite3 (lo que usa TechLoan) | MySQL / MariaDB (lo que espera phpMyAdmin) |
|---|---|---|
| Formato del archivo | binario propio | texto SQL |
| Encabezado | `SQLite format 3` | — |
| Se abre con | DB Browser for SQLite, `sqlite3` | phpMyAdmin, Workbench |
| Servidor | no (archivo local) | sí (servicio) |

Cuando subes un `.db` de SQLite a phpMyAdmin, MariaDB intenta leerlo como SQL,
se topa con el encabezado binario `SQLite format 3` y responde:

```
#1064 - You have an error in your SQL syntax ... near 'SQLite format 3' at line 1
```

**Eso no es un error del proyecto ni de la base de datos.** Es exactamente lo que
debe pasar cuando se mezclan dos motores distintos. La forma correcta de revisar
la base de datos es con una herramienta de SQLite.

---

## 2. Cómo abrir la base de datos (recomendado)

### Opción A — DB Browser for SQLite (interfaz gráfica, sin instalar nada más)

1. Abre **DB Browser for SQLite** (gratis, multiplataforma: <https://sqlitebrowser.org>).
2. **Abrir base de datos** → elige `database/techloan.db`.
3. Pestaña **Datos** → tabla `usuarios_sistema`.

Verás la columna **`password_hash`** con valores como:

```
scrypt:32768:8:1$LNEik1DgfqIB2lLs$1482d433e425642e2694bb056a9f4ceac53…
```

Eso es un **hash scrypt** generado por Werkzeug: nunca la contraseña en claro.

### Opción B — Línea de comandos `sqlite3`

```bash
sqlite3 database/techloan.db
sqlite> .headers on
sqlite> .mode column
sqlite> SELECT username, rol, substr(password_hash,1,40) AS hash, length(password_hash) AS largo
   ...>   FROM usuarios_sistema;
```

### Opción C — El script de demostración (para la exposición)

```bash
python demostrar_seguridad.py
```

Muestra, en un minuto y sin abrir nada más, las tres cosas que se suelen pedir:
el hash de las contraseñas, las validaciones del servidor y por qué la inyección
SQL no funciona. Detalle en `docs/DEMOSTRACION_SEGURIDAD.md`.

---

## 3. Qué revisar en la tabla `usuarios_sistema`

| Columna | Qué demuestra |
|---|---|
| `password_hash VARCHAR(255)` | La contraseña se guarda como **hash**, en una columna de **255 caracteres** (el hash scrypt ocupa 162; sobra margen). |
| `rol` | Solo `ADMINISTRADOR` u `OPERADOR` (restricción `CHECK`). |
| `email_confirmado` | 1 = cuenta activada; 0 = registro pendiente de confirmar por correo. |

La columna se declara así en `schema.sql`:

```sql
password_hash   VARCHAR(255) NOT NULL,
```

Y el valor **nunca** se guarda en claro: se calcula con
`werkzeug.security.generate_password_hash()` (método **scrypt**) al crear o
cambiar la contraseña, y se verifica con `check_password_hash()`. El campo
`password_hash` tampoco viaja nunca en la sesión ni en la API.

---

## 4. (Opcional) Ver la información en phpMyAdmin

Si de todas formas se quiere revisar la información en phpMyAdmin, el proyecto
incluye un exportador que genera un volcado **en sintaxis MySQL** con las mismas
tablas, relaciones y datos:

```bash
python exportar_a_mysql.py
# -> database/techloan_mysql.sql
```

Luego, en phpMyAdmin: **Importar** → elegir `techloan_mysql.sql` → **Continuar**.

> **Importante:** ese `.sql` es **solo para mirar los datos** en MySQL. La
> aplicación sigue trabajando con `database/techloan.db` (SQLite), que es lo que
> pide el enunciado. No hay que cambiar nada en el proyecto.

---

## 5. Resumen de archivos de base de datos

| Archivo | Qué es |
|---|---|
| `schema.sql` | Script de creación (tablas, índices y datos de prueba). Fuente de verdad. |
| `database/techloan.db` | Base de datos SQLite que usa la aplicación. |
| `init_db.py` | Reconstruye `techloan.db` desde `schema.sql`. |
| `database/techloan_mysql.sql` | Volcado MySQL opcional (lo genera `exportar_a_mysql.py`). |
| `database/buzon/` | Correos en modo demostración (no hay SMTP configurado). |
