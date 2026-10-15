#!/usr/bin/env bash
#
# Prepara TechLoan en una consola Bash de PythonAnywhere en un solo comando.
#
#   bash deploy/desplegar_pythonanywhere.sh
#
# Hace: clonar el repo, crear el entorno virtual, instalar las dependencias,
# crear la base de datos (solo si no existe) y escribir el archivo WSGI con tu
# usuario. Al final imprime los valores exactos del ÚNICO paso manual que queda
# (la pestaña Web de PythonAnywhere: virtualenv, estáticos, variables, recarga).

set -euo pipefail

# Normalmente el usuario está en $USER en la consola de PythonAnywhere.
USER_PA="${PA_USER:-${USER:-}}"

if [ -z "$USER_PA" ]; then
  echo "No detecto tu usuario de PythonAnywhere." >&2
  echo "Ejecútalo en la consola Bash de PythonAnywhere, o pasa PA_USER=tu_usuario." >&2
  exit 1
fi

HOME_DIR="${TECHLOAN_HOME_DIR:-/home/$USER_PA}"
PROYECTO="$HOME_DIR/TechLoan"

echo "==> Clonando o actualizando el repositorio"
if [ -d "$PROYECTO/.git" ]; then
  git -C "$PROYECTO" pull --quiet origin main
  echo "    actualizado."
else
  git clone --quiet --branch main \
    https://github.com/Burmistrov4/TechLoan.git "$PROYECTO"
  echo "    clonado en $PROYECTO."
fi

echo "==> Entorno virtual y dependencias"
if [ ! -d "$PROYECTO/.venv" ]; then
  "$(command -v python3 || command -v python)" -m venv "$PROYECTO/.venv"
fi
# PythonAnywhere es Linux: .venv/bin. En Windows (MSYS) sería .venv/Scripts; se
# admite ambos solo para poder probar el script localmente.
VENV_BIN="$PROYECTO/.venv/bin"; [ -d "$VENV_BIN" ] || VENV_BIN="$PROYECTO/.venv/Scripts"
# En Windows, pip no puede actualizarse llamando al exe; "python -m pip" sí.
"$VENV_BIN/python" -m pip install --quiet --upgrade pip || true
"$VENV_BIN/python" -m pip install --quiet -r "$PROYECTO/requirements.txt"

echo "==> Base de datos"
if [ -f "$PROYECTO/database/techloan.db" ]; then
  echo "    la base de datos ya existe: NO se reconstruye."
else
  "$VENV_BIN/python" "$PROYECTO/init_db.py" | tail -10
fi

# --- Archivo WSGI de PythonAnywhere -----------------------------------------
WSGI="/var/www/${USER_PA}_pythonanywhere_com_wsgi.py"
PLANTILLA="$(mktemp)"
cat > "$PLANTILLA" <<EOF
# -*- coding: utf-8 -*-
# Archivo WSGI de TechLoan. Generado por deploy/desplegar_pythonanywhere.sh.
import sys

RUTA = "$PROYECTO"
if RUTA not in sys.path:
    sys.path.insert(0, RUTA)

from app.server import create_app

application = create_app()
EOF

if [ -w "$(dirname "$WSGI")" ]; then
  cp "$PLANTILLA" "$WSGI"
  echo "==> Archivo WSGI escrito en $WSGI"
  PASO_WSGI="(el archivo WSGI ya está escrito; solo revísalo)"
else
  echo "==> No pude escribir $WSGI; lo dejo en $PLANTILLA"
  PASO_WSGI="(copia el contenido de $PLANTILLA y pégalo aquí)"
fi

cat <<EOF

================================================================
Queda UN paso manual: la pestaña "Web" de PythonAnywhere.

  1. Añade la aplicación: pestaña Web -> "Add a new web app"
     -> "Manual configuration" -> elige la versión de Python.
  2. En "Virtualenv", escribe:
       $PROYECTO/.venv
  3. En "Static files", añade:
       URL:  /static/
       Path: $PROYECTO/static/
  4. En "WSGI configuration file" $PASO_WSGI
  5. En "Environment variables", añade:
       TECHLOAN_SECRET_KEY = una cadena aleatoria larga
       TECHLOAN_URL_BASE   = https://$USER_PA.pythonanywhere.com
  6. Pulsa "Reload".

Después:
  Salud: https://$USER_PA.pythonanywhere.com/health
  App:   https://$USER_PA.pythonanywhere.com/

Nota del plan gratuito: bloquea el internet saliente, así que el correo de
confirmación entra en modo demostración (se guarda en database/buzon/ y el
enlace aparece en pantalla). Es exactamente lo que necesitas para la defensa.
================================================================
EOF
