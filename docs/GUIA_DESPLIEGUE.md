# Guía de despliegue de TechLoan

La aplicación es **Flask + SQLite3**. Antes de elegir plataforma, ten presente la
regla que manda sobre todas:

> **SQLite es un archivo.** Necesita un **disco persistente**. Casi todas las
> plataformas gratuitas tienen disco efímero: en cada reinicio o despliegue
> borran `database/techloan.db`. Si eso pasa, el profesor abriría una base vacía.

Arquitectura de un despliegue típico:

```
Navegador → HTTPS → nginx → gunicorn (WSGI) → Flask → SQLite en disco persistente
```

En local se sigue usando `python run_server.py` (servidor de desarrollo). En
producción **nunca** se usa el servidor de desarrollo: se usa **gunicorn** (o
waitress en Windows), a través de `wsgi.py`.

---

## 1. Opción recomendada: PythonAnywhere (plan gratuito)

Es la que mejor encaja con esta entrega: disco persistente (SQLite funciona tal
cual), despliegue de Flask sin Docker y URL `tuusuario.pythonanywhere.com`.

### Qué da y qué no da el plan gratuito

| Concepto | Plan gratuito («Beginner», 0 $) |
|---|---|
| URL | `tuusuario.pythonanywhere.com` (sin dominio propio) |
| Aplicaciones web | **1** |
| Disco | **512 MB** (el proyecto ocupa ~70 MB, sobra) |
| CPU | 100 s/día (de sobra para una demostración) |
| Internet saliente | **solo lista blanca** — pero `github.com` y `pypi.org` **sí** están, así que el clonado y la instalación funcionan |
| HTTPS | incluido |
| Base de datos | SQLite en tu disco, **persistente** (no se borra) |

### La regla que no se puede saltar: la versión de Python

> El intérprete del **entorno virtual** y el que elijas en la **pestaña Web**
> tienen que ser **exactamente el mismo**. Si no coinciden, PythonAnywhere
> recarga con el error *«virtualenv is not compatible with this Python version»*
> y la web no arranca.

Por eso el script **fija una versión** y te dice cuál marcar. Elige la más alta
disponible en tu cuenta (las versiones dependen de la *System image*):

| System image | Python disponibles |
|---|---|
| `innit` (actual) | 3.7, 3.8, 3.9, **3.10, 3.11, 3.12, 3.13** |
| `haggis` (antigua) | 2.7, 3.6, 3.7, 3.8, 3.9, 3.10 |

Puedes ver la tuya en **Account → System image** (y actualizarla a `innit`).

**Vía automatizada.** Abre una consola **Bash** en PythonAnywhere y ejecuta:

```bash
git clone https://github.com/Burmistrov4/TechLoan.git
bash TechLoan/deploy/desplegar_pythonanywhere.sh
```

Si tu cuenta no tuviera la última versión, pásala explícitamente:

```bash
PA_PYTHON=python3.10 bash TechLoan/deploy/desplegar_pythonanywhere.sh
```

El script clona el proyecto, crea el entorno virtual con **una versión fija**,
instala las dependencias, crea la base de datos (solo si no existe), **comprueba
que la aplicación se importa** (detecta errores antes de tocar el navegador) y
escribe el archivo WSGI. Al terminar imprime los valores exactos del **único paso
manual** que queda, ya con la versión de Python correcta incluida, **la clave de
sesión ya generada** y la URL de tu cuenta.

Detalles que el script resuelve por ti:

- Si el comando `python3.x` no está en el PATH de la consola, lo busca por **ruta
  absoluta**; si el módulo `venv` falla, usa el paquete **`virtualenv`**.
- La versión de Python del entorno virtual queda **fijada** y te dice cuál marcar.
- Genera una **clave de sesión aleatoria** lista para pegar (no la inventes tú).

> **Truco:** si ejecutas el script **otra vez** después de crear la aplicación web en
> la pestaña *Web*, ya podrá escribir el archivo WSGI en `/var/www/` por ti, y solo
> te quedará pulsar **Reload**.

**Pasos manuales** (si prefieres verlo todo):

1. Crea una cuenta en <https://www.pythonanywhere.com>.
2. Abre una consola **Bash** y trae el proyecto:
   ```bash
   git clone https://github.com/Burmistrov4/TechLoan.git
   cd TechLoan
   python3.13 -m venv .venv          # usa la MISMA versión del paso 3
   source .venv/bin/activate
   pip install -r requirements.txt
   python init_db.py          # crea la base de datos con los datos de prueba
   ```
3. Pestaña **Web** → **Add a new web app** → **Manual configuration** →
   **Python 3.13** (exactamente la del paso 2).
4. En **Virtualenv**, escribe la ruta: `/home/TU_USUARIO/TechLoan/.venv`.
5. En **WSGI configuration file**: en el script automático ya queda escrito en
   `/var/www/TU_USUARIO_pythonanywhere_com_wsgi.py`. A mano, borra el contenido y
   pega lo de `deploy/_wsgi_generado.py` (o `deploy/pythonanywhere_wsgi.py`
   ajustando `USUARIO`).
6. En **Static files**, mapea (opcional pero recomendado, para que nginx sirva el
   CSS y las imágenes sin pasar por Python):
   - URL `/static/` → `/home/TU_USUARIO/TechLoan/static/`
7. Pulsa **Reload**.

> ⚠️ **PythonAnywhere NO tiene una sección «Environment variables» en la pestaña
> Web.** Es un error frecuente: el paso aparece en muchas guías, pero ahí no
> existe. Las variables se definen **dentro del archivo WSGI**, y tienen que
> quedar **antes** del `from app.server import create_app`, porque
> `app/config.py` lee `os.environ` en el momento de importarse (`SECRET_KEY` y
> `URL_BASE` son constantes de módulo). Si las pones después, la aplicación
> arranca en silencio con la clave por defecto `CAMBIAR_EN_PRODUCCION`, que está
> publicada en este repositorio público. El script ya genera el WSGI con esa
> forma correcta:
>
> ```python
> import os, sys
> RUTA = "/home/TU_USUARIO/TechLoan"
> if RUTA not in sys.path:
>     sys.path.insert(0, RUTA)
>
> os.environ.setdefault("TECHLOAN_SECRET_KEY", "<clave aleatoria>")
> os.environ.setdefault("TECHLOAN_URL_BASE", "https://TU_USUARIO.pythonanywhere.com")
>
> from app.server import create_app
> application = create_app()
> ```
>
> Si vuelves a ejecutar `deploy/desplegar_pythonanywhere.sh` con la aplicación web
> ya creada, **reutiliza la clave que ya estaba** (no la regenera, para no cerrar
> las sesiones abiertas) y escribe el WSGI por ti.

> **Si sale «Something went wrong» (error 502/504):** mira **Web → Error log**.
> Las dos causas casi siempre son (a) la versión de Python del entorno virtual no
> coincide con la de la pestaña Web, o (b) una ruta mal escrita en el WSGI.

---

## 1.b Correo: modo demostración o SMTP real

**El correo de confirmación no llega porque no hay servidor de correo
configurado.** No es un fallo: es el comportamiento previsto. La aplicación
detecta que no hay `TECHLOAN_SMTP_HOST` y entra en **modo demostración**:

- guarda el mensaje en `database/buzon/` (dentro del proyecto), y
- muestra el enlace *«Confirmar mi cuenta ahora»* **en pantalla**.

Es decir, **el registro funciona igual** y puedes completar el flujo entero sin
correo. Para una defensa es lo más seguro: no depende de internet ni de que un
servidor externo responda ese día.

### ¿Se puede enviar correo de verdad con `lorenzoroca333@gmail.com`?

Primero **mídelo**, no lo supongas. En la consola Bash de PythonAnywhere:

```bash
cd ~/TechLoan
python3 deploy/diagnostico_correo.py
```

Ese script no envía nada ni pide contraseñas: solo comprueba si el servidor
puede abrir el puerto 587. Si responde `[FALLA] TCP`, el plan gratuito está
bloqueando la salida SMTP y el modo demostración es tu opción (y está bien).

Si responde `[OK]`, entonces configura Gmail así:

1. Activa la **verificación en dos pasos** en la cuenta de Google.
2. Crea una **contraseña de aplicación** en
   <https://myaccount.google.com/apppasswords> (16 caracteres). La contraseña
   normal de Gmail **no** sirve para SMTP. Google solo la muestra **una vez**:
   si la perdiste, genera otra (la anterior queda inutilizada).
3. En el editor de PythonAnywhere, deja el archivo **con esta forma completa**
   (copia y pega, cambiando solo TU_USUARIO, TU_CORREO y TU_CLAVE):

```python
# -*- coding: utf-8 -*-
import os
import sys

RUTA = "/home/TU_USUARIO/TechLoan"
if RUTA not in sys.path:
    sys.path.insert(0, RUTA)

# --- Estas líneas van ANTES del import: config.py lee os.environ al importarse ---
os.environ["TECHLOAN_SECRET_KEY"] = "la-clave-que-ya-tenias"
os.environ["TECHLOAN_URL_BASE"] = "https://TU_USUARIO.pythonanywhere.com"

# --- Correo real con Gmail ---
os.environ["TECHLOAN_SMTP_HOST"] = "smtp.gmail.com"
os.environ["TECHLOAN_SMTP_PORT"] = "587"
os.environ["TECHLOAN_SMTP_USER"] = "TU_CORREO@gmail.com"
os.environ["TECHLOAN_SMTP_PASSWORD"] = "tucclavede16letras"
os.environ["TECHLOAN_SMTP_FROM"] = "TU_CORREO@gmail.com"

from app.server import create_app

application = create_app()
```

Detalles que hacen fallar:

- La contraseña de aplicación de Google se muestra con espacios
  (`abcd efgh ijkl mnop`). **Quítale los espacios** antes de pegarla.
- Las cinco líneas nuevas tienen que quedar **por debajo** de `TECHLOAN_URL_BASE`
  y **por encima** de `from app.server import create_app`. Si quedan debajo, la
  app no las ve.
- **Comprueba la URL**: si `TECHLOAN_URL_BASE` no es exactamente
  `https://TU_USUARIO.pythonanywhere.com`, el enlace del correo apuntará a un
  dominio que no existe y el usuario no podrá confirmar la cuenta.
- Las variables son de tipo texto; el puerto en `"587"` entre comillas está bien
  (la app lo convierte).

4. Pulsa **Save** en el editor.
5. Ve a la pestaña **Web** y pulsa el botón verde **Reload**.
6. Registra una cuenta de prueba y revisa la bandeja (y el **spam**: Gmail a
   veces tarda unos segundos o manda el primer correo a no deseados).

> Aunque el SMTP falle, el registro **no se rompe**: `correo_service.py` atrapa
> la excepción, deja copia en `database/buzon/` y el enlace sigue apareciendo en
> pantalla. Por eso probarlo no tiene riesgo.

> ⚠️ **No vuelvas a ejecutar `desplegar_pythonanywhere.sh` después de haber editado
> el WSGV a mano**: regeneraría el archivo y perdería las líneas de SMTP que
> escribiste (el script las deja comentadas). El script solo reutiliza la
> `TECHLOAN_SECRET_KEY`; el resto lo reescribe entero. Si necesitas volver a
> ejecutarlo, guarda antes una copia de tus líneas SMTP.

---

## 2. Opción con Docker (Fly.io, Render, Railway, VPS…)

El proyecto incluye `Dockerfile` y `wsgi.py`, así que sirve para cualquier
plataforma que acepte contenedores.

```bash
docker build -t techloan .
docker run -p 8000:8000 \
  -e TECHLOAN_SECRET_KEY=una-clave-larga \
  -e TECHLOAN_URL_BASE=https://tu-dominio \
  -v techloan_data:/app/database \
  techloan
```

**El volumen (`-v ...:/app/database`) no es opcional**: sin él, la base de datos
se pierde al recrear el contenedor. En Fly.io se declara un *volume*; en Render,
un *Disk* (el disco persistente es de pago, ~7 USD/mes).

El contenedor crea la base de datos solo si no existe (`[ -f database/techloan.db ]
|| python init_db.py`), así que no la borra en cada arranque.

---

## 3. Opción VPS (nginx + gunicorn + systemd)

Para algo más "de verdad" y barato a largo plazo (Oracle Cloud Always Free,
Hetzner ~4 €/mes…). En Ubuntu/Debian limpio, todo se monta con **un solo comando**
(como root):

```bash
# Con dominio (también configura TLS con Let's Encrypt):
sudo bash <(curl -fsSL https://raw.githubusercontent.com/Burmistrov4/TechLoan/main/deploy/desplegar_vps.sh) \
     --dominio techloan.tudominio.com --correo tu@correo.com

# Sin dominio (solo HTTP en la IP del VPS):
sudo bash deploy/desplegar_vps.sh
```

El script instala los paquetes, clona el proyecto, crea la unidad de systemd, el
sitio de nginx y, si diste un dominio, el certificado TLS. Al final te muestra la
URL y los comandos útiles (`journalctl -u techloan -f`, etc.). Es **idempotente**:
si lo vuelves a ejecutar, actualiza el código y **no** borra la base de datos.

Si prefieres ver y pegar las piezas a mano, la siguiente sección las detalla.

### Montaje manual del VPS

```bash
sudo apt install python3-venv nginx
git clone https://github.com/Burmistrov4/TechLoan.git /opt/techloan
cd /opt/techloan && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python init_db.py
```

**Servicio systemd** (`/etc/systemd/system/techloan.service`):

```ini
[Unit]
Description=TechLoan
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/techloan
Environment="TECHLOAN_SECRET_KEY=una-clave-larga"
Environment="TECHLOAN_URL_BASE=https://tu-dominio"
ExecStart=/opt/techloan/.venv/bin/gunicorn wsgi:app --bind 127.0.0.1:8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now techloan
```

**nginx** (`/etc/nginx/sites-available/techloan`): `proxy_pass` a
`http://127.0.0.1:8000`, sirviendo `/static/` directamente desde
`/opt/techloan/static/`, y certificado TLS con `certbot`. Así la base SQLite vive
en el disco del VPS y puedes tener copia local como respaldo.

---

## 4. Variables de entorno

| Variable | Para qué | ¿Obligatoria? |
|---|---|---|
| `TECHLOAN_SECRET_KEY` | Firma la sesión. Cámbiala por una aleatoria larga. | Sí, en producción |
| `TECHLOAN_URL_BASE` | Enlaces de confirmación por correo | Sí, si hay registro por correo |
| `TECHLOAN_PORT` / `PORT` | Puerto de escucha (la mayoría de plataformas inyectan `PORT`) | La define la plataforma |
| `TECHLOAN_HOST` | Interfaz de escucha (por defecto `127.0.0.1` en local) | No |
| `TECHLOAN_SMTP_*` | Envío real de correo (si no, modo demostración) | No |
| `TECHLOAN_HORAS_TOKEN` | Validez del enlace de confirmación (24 h) | No |

Copia `.env.example` como referencia.

---

## 5. Lista de comprobación antes de publicar

- [ ] `TECHLOAN_SECRET_KEY` cambiada (no dejar `CAMBIAR_EN_PRODUCCION`).
- [ ] La **versión de Python** del entorno virtual coincide con la de la pestaña Web.
- [ ] `TECHLOAN_URL_BASE` con la URL real.
- [ ] Base de datos creada en el servidor (`init_db.py`, lo hace el script).
- [ ] El disco **persiste** entre despliegues (probar: recargar y ver que los
      datos siguen).
- [ ] `/health` responde `200`.
- [ ] Entrar con un usuario real y crear un registro; recargar y comprobar que
      sigue ahí.
- [ ] Se ve el **CSS** (si el panel sale «desnudo», falta el mapeo de `/static/`).

### Cómo se verificó esta guía

El despliegue se ensayó de punta a punta antes de publicarla: se generó el
entorno virtual, se cargó el **archivo WSGI** con un servidor WSGI real y se
pidieron las páginas contra él. Resultado:

| Comprobación | Resultado |
|---|---|
| `/health` | `200` + `{"ok":true,...}` |
| Portada, `/login`, `/registro` | `200` |
| Rutas protegidas sin sesión | `302` → `/login` (correcto) |
| Estáticos (`estilos.css`, `landing.css`, `favicon.svg`) | `200`, con su *content-type* |
| Las **12** páginas del panel, con sesión iniciada | `200` |
| Listados enriquecidos y fechas `DD/MM/YYYY` | presentes en el HTML |
| Rutas registradas en la aplicación | 78 |

---

## 6. Lo que NO sirve para este proyecto

**Vercel, Netlify, Heroku (free), AWS Lambda, Cloud Run** y demás *serverless*:
no tienen disco persistente y no ejecutan un proceso WSGI de larga duración.
SQLite se reiniciaría y la app no arranca tal cual. La entrega pide SQLite3, así
que la plataforma tiene que conservar el archivo.
