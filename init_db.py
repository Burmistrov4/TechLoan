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
        print("-" * 58)
        for tabla in TABLAS:
            total = connection.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
            print(f"  {tabla:<22} {total:>4} registro(s)")

        integridad = connection.execute("PRAGMA integrity_check").fetchone()[0]
        print("-" * 58)
        print(f"  integrity_check: {integridad}")

        _mostrar_datos_demostracion(connection)
    finally:
        connection.close()


def _mostrar_datos_demostracion(connection: sqlite3.Connection) -> None:
    """Imprime las fechas de las reservas de prueba.

    Las fechas de ``schema.sql`` son relativas a la fecha de ejecución, así que
    conviene saber exactamente cuáles quedaron cargadas para ensayar la
    demostración (sobre todo el ejemplo de solapamiento).
    """
    filas = connection.execute(
        """SELECT l.codigo, r.fecha, r.hora_inicio, r.hora_fin, r.duracion_minutos
           FROM reservas r JOIN laboratorios l ON l.id = r.laboratorio_id
           ORDER BY r.fecha, r.hora_inicio"""
    ).fetchall()
    if not filas:
        return

    print()
    print("  Reservas de demostración (útiles para la exposición):")
    for fila in filas:
        print(
            f"    {fila['codigo']}  {fila['fecha']}  "
            f"{fila['hora_inicio']}-{fila['hora_fin']}  ({fila['duracion_minutos']} min)"
        )
    print("    Sugerencia: intenta reservar LAB-01 el mismo día a las 08:30")
    print("    (debe rechazarse por solapamiento) y a las 10:20 (debe aceptarse).")


def main() -> None:
    destino = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_DB_PATH
    init_database(destino)


if __name__ == "__main__":
    main()
