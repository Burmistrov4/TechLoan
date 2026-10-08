"""Inicializador de la base de datos de TechLoan.

Ejecuta ``schema.sql`` para reconstruir la base de datos SQLite3 desde cero:
crea las tablas, los índices y carga los datos iniciales y de prueba.

Uso::

    python init_db.py                  # reconstruye database/techloan.db
    python init_db.py /ruta/otra.db    # reconstruye una base de datos alterna

Se puede indicar otra ruta para probar la reconstrucción sobre una base de
datos temporal sin tocar la base de datos de trabajo.
"""

import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"
DEFAULT_DB_PATH = BASE_DIR / "database" / "techloan.db"

TABLAS = (
    "usuarios_sistema",
    "prestatarios",
    "categorias",
    "laboratorios",
    "equipos",
    "reservas",
    "prestamos_equipos",
)


def init_database(db_path: Path) -> None:
    """Reconstruye la base de datos indicada a partir de ``schema.sql``."""
    if not SCHEMA_PATH.exists():
        raise SystemExit(f"No se encontró el script SQL: {SCHEMA_PATH}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    sql = SCHEMA_PATH.read_text(encoding="utf-8")

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(sql)
        connection.commit()

        print(f"Base de datos reconstruida: {db_path}")
        print("-" * 46)
        for tabla in TABLAS:
            total = connection.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
            print(f"  {tabla:<22} {total:>4} registro(s)")

        integridad = connection.execute("PRAGMA integrity_check").fetchone()[0]
        print("-" * 46)
        print(f"  integrity_check: {integridad}")
    finally:
        connection.close()


def main() -> None:
    destino = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_DB_PATH
    init_database(destino)


if __name__ == "__main__":
    main()
