"""Plantilla del archivo WSGI para PythonAnywhere.

En PythonAnywhere el archivo WSGI se edita desde la pestaña **Web** del panel,
en «WSGI configuration file». Pega este contenido y ajusta ``USUARIO``.

El script ``deploy/desplegar_pythonanywhere.sh`` genera esta misma versión ya
rellenada en ``deploy/_wsgi_generado.py`` (y la copia a ``/var/www`` si puede).

**Recuerda:** la versión de Python del entorno virtual y la que elijas en la
pestaña Web tienen que ser la misma, o la web no arranca.

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
