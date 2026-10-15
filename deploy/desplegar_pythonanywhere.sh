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
  # El usuario lo forzó a mano.
  if command -v "$PA_PYTHON" >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v "$PA_PYTHON")"
  elif [ -x "$PA_PYTHON" ]; then
    PYTHON_BIN="$PA_PYTHON"
  else
    echo "PA_PYTHON=$PA_PYTHON no existe en esta cuenta." >&2
    exit 1
  fi
else
  # 1) Como comando en el PATH (lo habitual en PythonAnywhere).
  for candidato in python3.13 python3.12 python3.11 python3.10 python3.9 python3 python; do
    if command -v "$candidato" >/dev/null 2>&1; then
      PYTHON_BIN="$(command -v "$candidato")"
      break
    fi
  done
  # 2) Por ruta absoluta, por si el comando no está en el PATH de la consola.
  if [ -z "$PYTHON_BIN" ]; then
    for ver in 13 12 11 10 9; do
      for prefijo in /usr/bin /usr/local/bin /opt/python3.$ver/bin; do
        if [ -x "$prefijo/python3.$ver" ]; then
          PYTHON_BIN="$prefijo/python3.$ver"
          break 2
        fi
      done
    done
  fi
fi

if [ -z "$PYTHON_BIN" ]; then
  echo "No encuentro ningún intérprete de Python 3 en esta cuenta." >&2
  echo "Los que veo disponibles:" >&2
  ls -1 /usr/bin/python3* /usr/local/bin/python3* 2>/dev/null >&2 || true
  echo "Pásalo a mano: PA_PYTHON=/usr/bin/python3.10 bash deploy/desplegar_pythonanywhere.sh" >&2
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
  # Plan A: el módulo venv de la biblioteca estándar.
  # Plan B: el paquete "virtualenv", que funciona aunque venv/pip falle
  #         (pasa en algunas cuentas de PythonAnywhere).
  if ! "$PYTHON_BIN" -m venv "$PROYECTO/.venv" 2>/dev/null; then
    echo "    'python -m venv' falló; pruebo con el paquete virtualenv..."
    rm -rf "$PROYECTO/.venv"
    "$PYTHON_BIN" -m pip install --quiet --user virtualenv \
      || "$PYTHON_BIN" -m pip install --quiet virtualenv
    "$PYTHON_BIN" -m virtualenv -p "$PYTHON_BIN" "$PROYECTO/.venv" \
      || "$PYTHON_BIN" -m virtualenv "$PROYECTO/.venv"
  fi
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

# --- 7. Archivo WSGI (aquí van las variables de entorno) ---------------------
# IMPORTANTE: PythonAnywhere NO tiene una sección "Environment variables" en la
# pestaña Web. La forma oficial de definirlas es el archivo WSGI, y tienen que
# asignarse ANTES del import, porque app/config.py lee os.environ en cuanto se
# importa (SECRET_KEY y URL_BASE son constantes de módulo).
WSGI="/var/www/${USER_PA}_pythonanywhere_com_wsgi.py"
RESPALDO="$PROYECTO/deploy/_wsgi_generado.py"

# Reutilizar la clave si ya existe: regenerarla cerraría la sesión de todos.
CLAVE=""
if [ -n "${TECHLOAN_SECRET_KEY:-}" ]; then
  CLAVE="$TECHLOAN_SECRET_KEY"
  echo "==> Uso la clave de sesión que pasaste en TECHLOAN_SECRET_KEY."
elif [ -f "$WSGI" ]; then
  CLAVE="$(grep -oP 'TECHLOAN_SECRET_KEY", *"\K[^"]+' "$WSGI" 2>/dev/null | head -1 || true)"
  [ -n "$CLAVE" ] && echo "==> Reutilizo la clave de sesión que ya estaba en el WSGI."
fi
if [ -z "$CLAVE" ]; then
  if command -v openssl >/dev/null 2>&1; then
    CLAVE="$(openssl rand -hex 32 2>/dev/null || true)"
  fi
  [ -n "$CLAVE" ] || CLAVE="$("$PYTHON_BIN" -c 'import secrets; print(secrets.token_hex(32))' 2>/dev/null || true)"
  echo "==> Clave de sesión nueva generada."
fi

cat > "$RESPALDO" <<EOF
# -*- coding: utf-8 -*-
# Archivo WSGI de TechLoan. Generado por deploy/desplegar_pythonanywhere.sh
#
# En PythonAnywhere las variables de entorno se definen AQUÍ: la pestaña Web no
# tiene una sección para ellas. Van ANTES del import de la aplicación, porque
# app/config.py lee os.environ en el momento de importarse.
import os
import sys

RUTA = "$PROYECTO"
if RUTA not in sys.path:
    sys.path.insert(0, RUTA)

os.environ.setdefault("TECHLOAN_SECRET_KEY", "$CLAVE")
os.environ.setdefault("TECHLOAN_URL_BASE", "https://$USER_PA.pythonanywhere.com")

# --- Correo real (opcional) --------------------------------------------------
# Sin esto la aplicación funciona en MODO DEMOSTRACIÓN: guarda el correo en
# database/buzon/ y muestra el enlace de confirmación en pantalla (perfecto para
# la defensa). Si consigues un servidor SMTP que responda, descomenta y rellena:
#
# os.environ.setdefault("TECHLOAN_SMTP_HOST", "smtp.gmail.com")
# os.environ.setdefault("TECHLOAN_SMTP_PORT", "587")
# os.environ.setdefault("TECHLOAN_SMTP_USER", "tucorreo@gmail.com")
# os.environ.setdefault("TECHLOAN_SMTP_PASSWORD", "contrasena-de-aplicacion")
# os.environ.setdefault("TECHLOAN_SMTP_FROM", "tucorreo@gmail.com")

from app.server import create_app

application = create_app()
EOF

if [ -w "$(dirname "$WSGI")" ]; then
  cp "$RESPALDO" "$WSGI"
  echo "==> Archivo WSGI escrito en $WSGI (con las variables dentro)."
  PASO_WSGI="ya está escrito y con las variables; solo revísalo"
else
  echo "==> Todavía no existe /var/www: crea antes la aplicación web (paso 1)."
  PASO_WSGI="abre el enlace y pega el contenido de $RESPALDO"
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
     (ahí dentro van la clave de sesión y la URL; NO existe una sección
      "Environment variables" en PythonAnywhere: eso es lo que hay que usar).
  4. En "Static files", añade (opcional, acelera las imágenes y el CSS):
       URL:  /static/
       Path: $PROYECTO/static/
  5. Pulsa el botón verde "Reload".

Después comprueba:
  Salud: https://$USER_PA.pythonanywhere.com/health
  App:   https://$USER_PA.pythonanywhere.com/

Sobre el correo: sin SMTP configurado la aplicación entra en MODO DEMOSTRACIÓN,
guarda el mensaje en database/buzon/ y muestra el enlace en pantalla. El plan
gratuito bloquea el SMTP saliente, así que para la defensa el modo demostración
es lo más seguro (no depende de internet ni de una cuenta de correo).

Notas del plan gratuito:
  - Internet saliente limitado a una lista blanca (github.com y pypi.org sí
    están, por eso este script funciona).
  - El dominio es $USER_PA.pythonanywhere.com (sin dominio propio).
  - 512 MB de disco: el proyecto ocupa unos 70 MB, de sobra.
  - La web se desactiva si no entras en 3 meses: pulsa "Run until 1 month from
    today" en la pestaña Web de vez en cuando.

TRUCO: si vuelves a ejecutar este script DESPUÉS de crear la aplicación web, ya
podrá escribir el archivo WSGI por ti (paso 3) y solo tendrás que pulsar Reload.
================================================================
EOF