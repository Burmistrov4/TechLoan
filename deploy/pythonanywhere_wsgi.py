"""Plantilla del archivo WSGI para PythonAnywhere.

En PythonAnywhere el archivo WSGI se edita desde la pestaña **Web** del panel,
en «WSGI configuration file». Pega este contenido y ajusta ``USUARIO``.

Este archivo NO se ejecuta en local; es solo una plantilla de referencia.
"""

import sys

# --- Ajusta estas dos líneas -------------------------------------------------
USUARIO = "tu_usuario"  # tu nombre de usuario de PythonAnywhere
RUTA = f"/home/{USUARIO}/TechLoan"

if RUTA not in sys.path:
    sys.path.insert(0, RUTA)

# --- No toques a partir de aquí ----------------------------------------------
from app.server import create_app  # noqa: E402

application = create_app()
