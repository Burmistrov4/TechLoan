"""Aísla las pruebas en una base de datos temporal.

Los scripts de prueba **nunca** deben escribir en ``database/techloan.db``: si lo
hacen, la base de datos que se entrega y que revisa el profesor acaba con
usuarios y registros de prueba (por ejemplo ``security_admin`` o ``CRUD-*``).

Importar este módulo y llamar a :func:`preparar` antes de usar cualquier
servicio redirige ``app.database.DATABASE_PATH`` a un archivo temporal y carga
el esquema (``schema.sql``) con sus datos de demostración.

Uso::

    import _tempdb
    _tempdb.preparar("test_crud.db")
"""

import sys
import tempfile
from pathlib import Path

_BASE = Path(__file__).resolve().parent.parent
if str(_BASE) not in sys.path:
    sys.path.insert(0, str(_BASE))

import app.database as database  # noqa: E402
from init_db import init_database as _cargar_esquema  # noqa: E402


def preparar(nombre="techloan_test.db"):
    """Redirige la base de datos a un archivo temporal y carga el esquema.

    Devuelve la ruta del archivo temporal creado.
    """
    ruta = Path(tempfile.mkdtemp(prefix="techloan_test_")) / nombre
    database.DATABASE_PATH = ruta
    _cargar_esquema(ruta)
    return ruta
