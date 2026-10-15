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

**Vía automatizada.** Abre una consola **Bash** en PythonAnywhere y ejecuta:

```bash
git clone https://github.com/Burmistrov4/TechLoan.git
bash TechLoan/deploy/desplegar_pythonanywhere.sh
```

Ese script clona el proyecto, crea el entorno virtual, instala las dependencias,
crea la base de datos y escribe el archivo WSGI con tu usuario. Al terminar te
imprime los valores exactos del **único paso manual** que queda (la pestaña Web).
Si prefieres hacerlo a mano, estos son los pasos:

**Pasos manuales:**

1. Crea una cuenta en <https://www.pythonanywhere.com>.
2. Abre una consola **Bash** y trae el proyecto:
   ```bash
   git clone https://github.com/Burmistrov4/TechLoan.git
   cd TechLoan
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   python init_db.py          # crea la base de datos con los datos de prueba
   ```
3. Pestaña **Web** → **Add a new web app** → **Manual configuration** →
   **Python 3.10** (o la versión que ofrezca).
4. En **Virtualenv**, escribe la ruta: `/home/TU_USUARIO/TechLoan/.venv`.
5. En **WSGI configuration file**, borra el contenido y pega lo de
   `deploy/pythonanywhere_wsgi.py` (ajustando `USUARIO`).
6. En **Static files**, mapea:
   - URL `/static/` → `/home/TU_USUARIO/TechLoan/static/`
7. **Environment variables** (botón *Add*):
   - `TECHLOAN_SECRET_KEY` = una cadena aleatoria larga
   - `TECHLOAN_URL_BASE` = `https://TU_USUARIO.pythonanywhere.com`
8. Pulsa **Reload**.

> **Aviso del plan gratuito:** bloquea internet saliente salvo una lista blanca,
> así que el correo SMTP no se envía. La aplicación entra en **modo demostración**
> (guarda el mensaje en `database/buzon/` y muestra el enlace en pantalla), que es
> justo lo que se necesita para enseñar el flujo sin correo real.

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
- [ ] `TECHLOAN_URL_BASE` con la URL real.
- [ ] Base de datos creada en el servidor: `python init_db.py`.
- [ ] El disco **persiste** entre despliegues (probar: reiniciar y ver que los
      datos siguen).
- [ ] Entrar con un usuario real y crear un registro; recargar y comprobar que
      sigue ahí.
- [ ] `/health` responde `200`.

---

## 6. Lo que NO sirve para este proyecto

**Vercel, Netlify, Heroku (free), AWS Lambda, Cloud Run** y demás *serverless*:
no tienen disco persistente y no ejecutan un proceso WSGI de larga duración.
SQLite se reiniciaría y la app no arranca tal cual. La entrega pide SQLite3, así
que la plataforma tiene que conservar el archivo.
