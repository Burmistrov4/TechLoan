#!/usr/bin/env bash
#
# Prepara TechLoan en una consola Bash de PythonAnywhere en un solo comando.
#
#   bash deploy/desplegar_pythonanywhere.sh
#
# Hace: clonar el repo, crear el entorno virtual, instalar las dependencias,
# crear la base de datos (solo si no existe), comprobar que la aplicación se
# importa y escribir el archivo WSGI con tu usuario. Al final imprime los valores
# exactos del ÚNICO paso manual que queda (la pestaña Web).
#
# Opciones:
#   PA_USER=tuusuario        tu usuario de PythonAnywhere (si no lo detecta)
#   PA_PYTHON=python3.13     versión con la que crear el entorno virtual
#
# IMPORTANTE: la versión de Python del entorno virtual TIENE que ser la misma
# que elijas en la pestaña Web. PythonAnywhere falla con "virtualenv is not
# compatible with this Python version" si no coinciden. Este script fija una
# versión y te dice exactamente cuál marcar.

set -euo pipefail

# --- 1. Identificar al usuario ----------------------------------------------
USER_PA="${PA_USER:-${USER:-}}"

if [ -z "$USER_PA" ]; then
  echo "No detecto tu usuario de PythonAnywhere." >&2
  echo "Ejecútalo en la consola Bash de PythonAnywhere, o pasa PA_USER=tu_usuario." >&2
  exit 1
fi

HOME_DIR="${TECHLOAN_HOME_DIR:-/home/$USER_PA}"
PROYECTO="$HOME_DIR/TechLoan"

echo "==> Usuario: $USER_PA"

# --- 2. Clonar o actualizar el repositorio ----------------------------------
echo "==> Clonando o actualizando el repositorio"
if [ -d "$PROYECTO/.git" ]; then
  git -C "$PROYECTO" pull --quiet origin main
  echo "    actualizado en $PROYECTO."
else
  git clone --quiet --branch main \
    https://github.com/Burmistrov4/TechLoan.git "$PROYECTO"
  echo "    clonado en $PROYECTO."
fi

# --- 3. Elegir la versión de Python -----------------------------------------
# Se prueban de la más nueva a la más antigua y se usa la primera que exista.
# Así el entorno virtual queda atado a una versión concreta y sabemos qué
# marcar en la pestaña Web.
PYTHON_BIN=""
if [ -n "${PA_PYTHON:-}" ]; then
  if command -v "$PA_PYTHON" >/dev/null 2>&1; then
    PYTHON_BIN="$PA_PYTHON"
  else
    echo "PA_PYTHON=$PA_PYTHON no existe en esta cuenta." >&2
    exit 1
  fi
else
  for candidato in python3.13 python3.12 python3.11 python3.10 python3.9 python3 python; do
    if command -v "$candidato" >/dev/null 2>&1; then
      PYTHON_BIN="$candidato"
      break
    fi
  done
fi

if [ -z "$PYTHON_BIN" ]; then
  echo "No encuentro ningún intérprete de Python 3 en esta cuenta." >&2
  exit 1
fi

PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
echo "==> Python elegido: $PYTHON_BIN (versión $PY_VERSION)"

# --- 4. Entorno virtual y dependencias --------------------------------------
echo "==> Entorno virtual y dependencias"
if [ -d "$PROYECTO/.venv" ]; then
  # Si el entorno existe pero es de otra versión, se rehace para evitar el
  # desajuste con la pestaña Web.
  VENV_PY="$PROYECTO/.venv/bin/python"
  if [ -x "$VENV_PY" ]; then
    VENV_VERSION="$("$VENV_PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "?")"
    if [ "$VENV_VERSION" != "$PY_VERSION" ]; then
      echo "    el entorno virtual era de Python $VENV_VERSION; lo rehago con $PY_VERSION."
      rm -rf "$PROYECTO/.venv"
    fi
  fi
fi

if [ ! -d "$PROYECTO/.venv" ]; then
  "$PYTHON_BIN" -m venv "$PROYECTO/.venv"
fi

# PythonAnywhere es Linux: .venv/bin. En Windows (MSYS) sería .venv/Scripts; se
# admite ambos solo para poder probar el script localmente.
VENV_BIN="$PROYECTO/.venv/bin"; [ -d "$VENV_BIN" ] || VENV_BIN="$PROYECTO/.venv/Scripts"
# En Windows, pip no puede actualizarse llamando al exe; "python -m pip" sí.
"$VENV_BIN/python" -m pip install --quiet --upgrade pip || true
"$VENV_BIN/python" -m pip install --quiet -r "$PROYECTO/requirements.txt"
echo "    dependencias instaladas."

# --- 5. Base de datos --------------------------------------------------------
echo "==> Base de datos"
if [ -f "$PROYECTO/database/techloan.db" ]; then
  echo "    ya existe: NO se reconstruye (no se pierden datos)."
else
  ( cd "$PROYECTO" && "$VENV_BIN/python" init_db.py | tail -8 )
fi

# --- 6. Prueba de humo: ¿la aplicación se importa? ---------------------------
# Detecta errores de importación ANTES de recargar la web (si no, el navegador
# muestra un 500 sin explicación).
echo "==> Comprobando que la aplicación se importa"
if ( cd "$PROYECTO" && TECHLOAN_SECRET_KEY=comprobacion \
      "$VENV_BIN/python" -c 'from app.server import create_app; create_app(); print("    import correcto.")' ); then
  :
else
  echo "    ¡ATENCIÓN! La aplicación NO se importa. Revisa el error de arriba" >&2
  echo "    antes de configurar la pestaña Web." >&2
  exit 1
fi

# --- 7. Archivo WSGI ---------------------------------------------------------
WSGI="/var/www/${USER_PA}_pythonanywhere_com_wsgi.py"
RESPALDO="$PROYECTO/deploy/_wsgi_generado.py"

cat > "$RESPALDO" <<EOF
# -*- coding: utf-8 -*-
# Archivo WSGI de TechLoan. Generado por deploy/desplegar_pythonanywhere.sh
# Pega este contenido en "WSGI configuration file" de la pestaña Web.
import sys

RUTA = "$PROYECTO"
if RUTA not in sys.path:
    sys.path.insert(0, RUTA)

from app.server import create_app

application = create_app()
EOF

if [ -w "$(dirname "$WSGI")" ]; then
  cp "$RESPALDO" "$WSGI"
  echo "==> Archivo WSGI escrito en $WSGI"
  PASO_WSGI="ya está escrito; solo revísalo"
else
  echo "==> Todavía no existe la carpeta /var/www: crea antes la aplicación web."
  PASO_WSGI="pega el contenido de $RESPALDO"
fi

# --- 8. Instrucciones finales ------------------------------------------------
cat <<EOF

================================================================
Queda UN paso manual: la pestaña "Web" de PythonAnywhere.

  1. Pestaña "Web" -> "Add a new web app"
     -> "Manual configuration" -> elige **Python $PY_VERSION**
     (tiene que ser $PY_VERSION, la misma del entorno virtual).
  2. En "Virtualenv", escribe:
       $PROYECTO/.venv
  3. En "WSGI configuration file": $PASO_WSGI
  4. En "Static files", añade (opcional, acelera las imágenes y el CSS):
       URL:  /static/
       Path: $PROYECTO/static/
  5. En "Environment variables", añade:
       TECHLOAN_SECRET_KEY = (una cadena aleatoria larga)
       TECHLOAN_URL_BASE   = https://$USER_PA.pythonanywhere.com
  6. Pulsa el botón verde "Reload".

Después comprueba:
  Salud: https://$USER_PA.pythonanywhere.com/health
  App:   https://$USER_PA.pythonanywhere.com/

Notas del plan gratuito:
  - Bloquea el internet saliente salvo una lista blanca (github.com y pypi.org
    sí están permitidos, por eso este script funciona).
  - Sin SMTP configurado, el correo de confirmación entra en modo demostración:
    se guarda en database/buzon/ y el enlace aparece en pantalla.
  - El dominio es $USER_PA.pythonanywhere.com (el plan gratuito no admite
    dominio propio). 512 MB de disco: el proyecto ocupa unos 70 MB, de sobra.
================================================================
EOF