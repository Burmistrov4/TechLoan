# Cómo actualizar TechLoan en producción (PythonAnywhere)

Guía paso a paso para subir un cambio a `lorodev.pythonanywhere.com` **sin perder
datos, sin cerrar las sesiones abiertas y sin llevarse sorpresas**.

Está escrita para el caso real de este proyecto: en producción la aplicación usa
una base de datos SQLite que vive en `/home/lorodev/TechLoan/database/techloan.db`
y un archivo WSGI editado a mano en `/var/www/`.

---

## Lo que hay que entender antes de tocar nada

Tres piezas, y cada una se actualiza de forma distinta:

| Pieza | Dónde vive | Cómo se actualiza |
|---|---|---|
| **El código** | `/home/lorodev/TechLoan/` (clon de GitHub) | `git pull` |
| **La base de datos** | `/home/lorodev/TechLoan/database/techloan.db` | **no se toca salvo que haga falta** |
| **La configuración** | `/var/www/lorodev_pythonanywhere_com_wsgi.py` | a mano, y **no se regenera** |

### El archivo WSGI es sagrado

Ese archivo contiene, a mano, la clave de sesión y los datos de Gmail:

```python
os.environ["TECHLOAN_SECRET_KEY"] = "b77456227a68e…"
os.environ["TECHLOAN_URL_BASE"] = "https://lorodev.pythonanywhere.com"
os.environ["TECHLOAN_SMTP_HOST"] = "smtp.gmail.com"
…
```

Depende de `sys.path`, no del repositorio. El script
`deploy/desplegar_pythonanywhere.sh` lo **reescribe entero** si lo vuelves a
ejecutar, así que **hay que guardar una copia antes**:

```bash
cp /var/www/lorodev_pythonanywhere_com_wsgi.py ~/wsgi-respaldo.py
```

### La base de datos no se reconstruye

`init_db.py` **borra todas las tablas y las vuelve a crear** (es idempotente, no
incremental). Ejecutarlo en producción destruiría los usuarios registrados, las
reservas y los tokens de confirmación pendientes. El script de despliegue solo lo
ejecuta si el archivo no existe, así que mientras no se borre a mano, no hay
riesgo.

### Los cambios de esquema necesitan migración, no recreación

`app/database.py` crea las tablas con `CREATE TABLE IF NOT EXISTS`. Eso significa
que **una tabla nueva sí se crea** al arrancar, pero **una tabla que ya existe no
se modifica**: si se le añade una columna, la aplicación falla en producción con
`no such column`.

Regla práctica: si el cambio toca el esquema, hay que escribir la migración
(`ALTER TABLE … ADD COLUMN`) dentro de `_migrar()` en `app/database.py`, que se
ejecuta en cada arranque y es idempotente.

---

## Procedimiento normal (cambio de código o plantillas)

Son unos 3 minutos.

### 1. Respaldar

Siempre, antes de cualquier cosa:

```bash
cp ~/TechLoan/database/techloan.db ~/respaldo-techloan-$(date +%Y%m%d-%H%M).db
cp /var/www/lorodev_pythonanywhere_com_wsgi.py ~/wsgi-respaldo.py
```

### 2. Traer el código

```bash
cd ~/TechLoan
git pull origin main
```

### 3. Comprobar que arranca

```bash
.venv/bin/python -c "from app.server import create_app; create_app(); print('import OK')"
```

Si esto falla, **no sigas**: el error se vería en producción como un 500 sin
explicación. Lo que imprima dice exactamente qué falta.

### 4. Recargar

Pestaña **Web** → botón verde **Reload**.

> El servidor de PythonAnywhere necesita el reload para volver a importar la
> aplicación. Recargar la página en el navegador **no** sirve: seguiría viendo el
> código viejo.

### 5. Comprobar

```bash
curl https://lorodev.pythonanywhere.com/health
```

Debe devolver `{"ok":true,"service":"TechLoan","status":"running"}`.

Después entra en `https://lorodev.pythonanywhere.com` y prueba el cambio que
acabas de subir.

---

## Si algo sale mal: volver atrás

```bash
# 1. Quitar el código roto
cd ~/TechLoan
git log --oneline -5                      # mira el commit anterior al problema
git reset --hard <commit-bueno>

# 2. Restaurar la configuración
cp ~/wsgi-respaldo.py /var/www/lorodev_pythonanywhere_com_wsgi.py

# 3. Restaurar la base de datos SOLO si se corrompió
cp ~/respaldo-techloan-*.db ~/TechLoan/database/techloan.db
```

Y recargar en la pestaña Web.

> Antes de restaurar la base de datos, confirma que el problema es realmente de
> datos. Restaurar una copia vieja **pierde todo lo que se hizo después**.

---

## Si el cambio toca el esquema

Ejemplo: añadir la tabla `secciones`.

**1. Añadir la tabla en los dos sitios** (obligatorio en los dos):

- `schema.sql` — con su `DROP TABLE IF EXISTS secciones;` arriba, para que
  `init_db.py` pueda reconstruir la base desde cero.
- `app/database.py`, dentro de `init_database()` — porque es lo que se ejecuta en
  producción al arrancar.

**2. Añadir la migración** en `_migrar()` (`app/database.py`), por si la base de
producción ya existe:

```python
def _migrar(db):
    ...
    if "email_confirmado" not in _columnas(db, "usuarios_sistema"):
        db.execute("ALTER TABLE usuarios_sistema ADD COLUMN ...")
```

**3. Comprobar en local antes de subir**:

```bash
python init_db.py /tmp/prueba-esquema.db      # reconstruye desde cero
```

**4. Subir** con el procedimiento normal.

---

## Si el cambio toca `requirements.txt`

Las dependencias van al entorno virtual, que **no está en git**. Hay que
instalarlas en el servidor:

```bash
cd ~/TechLoan
.venv/bin/python -m pip install -r requirements.txt
```

Y recargar la web.

> **Cuidado con las librerías de PDF.** El plan gratuito de PythonAnywhere no
> tiene `apt` ni `sudo`: solo se pueden instalar paquetes de Python puro.
> `reportlab` y `fpdf2` funcionan; `weasyprint` y `wkhtmltopdf` **no**, porque
> necesitan bibliotecas del sistema.

---

## Comprobación final

Lista para repasar después de cada subida:

- [ ] `git pull` trajo el commit esperado (`git log --oneline -1`).
- [ ] El import de la aplicación funciona.
- [ ] `/health` responde 200.
- [ ] La portada y el acceso cargan.
- [ ] Entrar con `admin` y comprobar el panel.
- [ ] Probar el cambio concreto que se subió.
- [ ] El CSS y las imágenes cargan (si el panel se ve «desnudo», falta el mapeo
      de `/static/` en la pestaña Web).
- [ ] La base de datos sigue teniendo los usuarios previos
      (`python3 deploy/diagnostico_registro.py`).

---

## Registro de la configuración actual

A fecha de 2026-10-16, el WSGI de producción contiene:

```
RUTA              = /home/lorodev/TechLoan
TECHLOAN_URL_BASE = https://lorodev.pythonanywhere.com
TECHLOAN_SMTP_HOST/PORT/USER/FROM = smtp.gmail.com / 587 / lorenzoroca333@gmail.com
TECHLOAN_SMTP_TLS = (activo, STARTTLS)
```

La clave de sesión (`TECHLOAN_SECRET_KEY`) es distinta en cada entorno y **no
está en el repositorio**. Si se pierde, hay que generar otra
(`python3 -c "import secrets; print(secrets.token_hex(32))"`), con la consecuencia
de que **todas las sesiones abiertas se cierran**.
