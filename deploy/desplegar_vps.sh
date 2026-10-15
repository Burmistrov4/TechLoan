#!/usr/bin/env bash
#
# Provisiona TechLoan en un VPS Ubuntu/Debian "limpio" en un solo comando.
#
#   sudo bash deploy/desplegar_vps.sh --dominio techloan.midominio.com --correo yo@correo.com
#   sudo bash deploy/desplegar_vps.sh                    # sin dominio: solo HTTP en la IP
#
# Hace, sin pasos intermedios:
#   1. instala los paquetes (python3, venv, pip, nginx, git, certbot)
#   2. clona el repo en /opt/techloan (o lo actualiza si ya existe)
#   3. crea el entorno virtual, instala las dependencias y ejecuta init_db
#      SOLO si la base de datos no existe (nunca la borra)
#   4. genera una clave de sesión aleatoria y el fichero de entorno
#   5. crea la unidad de systemd que ejecuta gunicorn sin privilegios
#   6. crea el sitio de nginx (archivos estáticos + proxy a gunicorn)
#   7. si hay dominio, obtiene el certificado TLS con Let's Encrypt y fuerza HTTPS
#   8. verifica /health y muestra el resumen
#
# No toca el cortafuegos: revísalo tú después si tienes uno activo.

set -euo pipefail

# ---------------------------------------------------------------------------
# Opciones
# ---------------------------------------------------------------------------
DOMINIO=""
CORREO=""
REPO="https://github.com/Burmistrov4/TechLoan.git"
RAMA="main"
DIR="/opt/techloan"
PUERTO="8000"
USUARIO="techloan"

while [ $# -gt 0 ]; do
  case "$1" in
    --dominio) DOMINIO="${2:-}"; shift 2 ;;
    --correo)  CORREO="${2:-}"; shift 2 ;;
    --repo)    REPO="${2:-}"; shift 2 ;;
    --rama)    RAMA="${2:-}"; shift 2 ;;
    --dir)     DIR="${2:-}"; shift 2 ;;
    --puerto)  PUERTO="${2:-}"; shift 2 ;;
    --usuario) USUARIO="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
    *) echo "Opción desconocida: $1" >&2; exit 2 ;;
  esac
done

ENTORNO="/etc/default/techloan"

# ---------------------------------------------------------------------------
# Comprobaciones previas
# ---------------------------------------------------------------------------
if [ "$(id -u)" -ne 0 ]; then
  echo "Este script debe ejecutarse como root:  sudo bash $0 ..." >&2
  exit 1
fi

if [ ! -f /etc/debian_version ]; then
  echo "Solo está probado en Debian/Ubuntu. En otro sistema, sigue docs/GUIA_DESPLIEGUE.md a mano." >&2
  exit 1
fi

separo() { echo "-------------------------------------------------------------"; }

if [ -n "$DOMINIO" ] && [ -z "$CORREO" ] && ! grep -q CERTBOT_EMAIL "$ENTORNO" 2>/dev/null; then
  echo "Si usas --dominio, pasa también --correo (lo exige Let's Encrypt para avisos)." >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 1. Paquetes
# ---------------------------------------------------------------------------
echo "==> Instalando paquetes del sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git curl ca-certificates nginx >/dev/null

# ---------------------------------------------------------------------------
# 2. Usuario y código
# ---------------------------------------------------------------------------
if ! id "$USUARIO" >/dev/null 2>&1; then
  useradd --system --home "$DIR" --shell /usr/sbin/nologin "$USUARIO"
  echo "==> Usuario de sistema creado: $USUARIO"
fi

mkdir -p "$DIR"

if [ -d "$DIR/.git" ]; then
  echo "==> Actualizando el repositorio existente"
  git -C "$DIR" fetch --quiet origin
  git -C "$DIR" checkout --quiet "$RAMA"
  git -C "$DIR" pull --quiet origin "$RAMA"
else
  echo "==> Clonando el repositorio en $DIR"
  rm -rf "${DIR:?}"/*
  git clone --quiet --branch "$RAMA" "$REPO" "$DIR"
fi

# ---------------------------------------------------------------------------
# 3. Entorno virtual y base de datos
# ---------------------------------------------------------------------------
echo "==> Instalando dependencias de Python"
[ -x "$DIR/.venv/bin/python" ] || python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install --quiet --upgrade pip
"$DIR/.venv/bin/pip" install --quiet -r "$DIR/requirements.txt"

if [ -f "$DIR/database/techloan.db" ]; then
  echo "==> Ya existe la base de datos: NO se reconstruye (no se pierden datos)"
else
  echo "==> Creando la base de datos desde schema.sql"
  "$DIR/.venv/bin/python" "$DIR/init_db.py" | tail -15
fi

# ---------------------------------------------------------------------------
# 4. Variables de entorno (systemd usa /etc/default/techloan)
# ---------------------------------------------------------------------------
EXISTENTE_SECRET="$(grep -E '^TECHLOAN_SECRET_KEY=' "$ENTORNO" 2>/dev/null | cut -d= -f2- || true)"
if [ -z "$EXISTENTE_SECRET" ]; then
  NUEVO_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
else
  NUEVO_SECRET="$EXISTENTE_SECRET"   # no regenerar: invalidaría las sesiones abiertas
fi

if [ -n "$DOMINIO" ]; then
  URL_BASE="https://$DOMINIO"
else
  URL_BASE="http://$(curl -s --max-time 5 https://api.ipify.org || echo 'la-ip-de-tu-servidor')"
fi

umask 077
cat > "$ENTORNO" <<EOF
# Gestión de sesiones. Cadena aleatoria larga. NO la compartas.
TECHLOAN_SECRET_KEY=$NUEVO_SECRET
# URL pública con la que se construyen los enlaces de confirmación por correo.
TECHLOAN_URL_BASE=$URL_BASE
# gunicorn escucha solo en local; nginx es quien recibe el tráfico de internet.
TECHLOAN_HOST=127.0.0.1
TECHLOAN_PORT=$PUERTO
EOF
chmod 600 "$ENTORNO"
echo "==> Fichero de entorno escrito: $ENTORNO"

chown -R "$USUARIO":"$USUARIO" "$DIR"
# La base de datos y el buzón deben poder escribir el usuario que ejecuta la app.
chmod 775 "$DIR/database" 2>/dev/null || true

# ---------------------------------------------------------------------------
# 5. Unidad de systemd
# ---------------------------------------------------------------------------
UNIDAD="/etc/systemd/system/techloan.service"
echo "==> Creando la unidad de systemd: $UNIDAD"
cat > "$UNIDAD" <<EOF
[Unit]
Description=TechLoan (Flask + SQLite3)
After=network.target

[Service]
Type=simple
User=$USUARIO
Group=$USUARIO
WorkingDirectory=$DIR
EnvironmentFile=$ENTORNO
ExecStart=$DIR/.venv/bin/gunicorn wsgi:app --bind 127.0.0.1:\${TECHLOAN_PORT} --workers 2 --timeout 60
Restart=always
RestartSec=3
# Endurecimiento mínimo: sin escalada y sistema de ficheros de solo lectura salvo /tmp.
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable techloan >/dev/null 2>&1 || true
systemctl restart techloan

# ---------------------------------------------------------------------------
# 6. nginx
# ---------------------------------------------------------------------------
SITIO="/etc/nginx/sites-available/techloan"
echo "==> Creando el sitio de nginx: $SITIO"

if [ -n "$DOMINIO" ]; then
  SERVIDORES="server_name $DOMINIO;"
else
  SERVIDORES="server_name _;"
fi

cat > "$SITIO" <<EOF
server {
  listen 80;
  listen [::]:80;
  $SERVIDORES

  # Logs separados: facilitan ver qué pasa sin mezclarlos con otros sitios.
  access_log /var/log/nginx/techloan.access.log;
  error_log  /var/log/nginx/techloan.error.log;

  client_max_body_size 8m;

  # Archivos estáticos los sirve nginx directamente (más rápido que Flask).
  location /static/ {
    alias $DIR/static/;
    expires 7d;
    access_log off;
  }

  # No hace falta una regla para el favicon ni para el manifiesto:
  #   - el favicon y los iconos cuelgan de /static/ (los cubre el bloque anterior)
  #   - /manifest.json lo genera Flask, así que pasa al proxy de abajo

  location / {
    proxy_pass http://127.0.0.1:$PUERTO;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_connect_timeout 30s;
    proxy_read_timeout 60s;
  }
}
EOF

ln -sfn "$SITIO" /etc/nginx/sites-enabled/techloan
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# ---------------------------------------------------------------------------
# 7. TLS con Let's Encrypt
# ---------------------------------------------------------------------------
if [ -n "$DOMINIO" ]; then
  echo "==> Solicitando certificado TLS para $DOMINIO"
  apt-get install -y -qq certbot python3-certbot-nginx >/dev/null
  if certbot --nginx -d "$DOMINIO" --non-interactive --agree-tos \
       -m "$CORREO" --redirect; then
    echo "==> Certificado TLS instalado"
  else
    echo "==> ATENCIÓN: no se pudo obtener el certificado."
    echo "    Comprueba que el dominio $DOMINIO apunta a la IP de este servidor"
    echo "    y que el puerto 80 está abierto. Reinténtalo con:"
    echo "      sudo certbot --nginx -d $DOMINIO"
  fi
fi

# ---------------------------------------------------------------------------
# 8. Verificación
# ---------------------------------------------------------------------------
separo
echo "Verificando..."
for _ in $(seq 1 15); do
  if curl -fsS --max-time 3 "http://127.0.0.1:$PUERTO/health" >/dev/null 2>&1; then
    echo "  /health responde OK"
    break
  fi
  sleep 2
done

systemctl --no-pager --full status techloan | head -6 || true

separo
echo "DESPLIEGUE COMPLETADO"
if [ -n "$DOMINIO" ]; then
  echo "  URL:    https://$DOMINIO"
  echo "  Salud:  https://$DOMINIO/health"
else
  IP="$(curl -s --max-time 5 https://api.ipify.org || echo '<IP-de-tu-servidor>')"
  echo "  URL:    http://$IP"
  echo "  Salud:  http://$IP/health"
fi
echo "  Código: $DIR"
separo
cat <<EOF
Comandos útiles:
  sudo systemctl status techloan       estado del servicio
  sudo journalctl -u techloan -f       logs en vivo
  sudo tail -f /var/log/nginx/techloan.error.log   logs de nginx
  sudo certbot renew --dry-run         comprobar la renovación automática

Recuerda abrir en el cortafuegos los puertos 80 y 443.
EOF
