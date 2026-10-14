"""Exporta la base de datos SQLite de TechLoan a un volcado compatible con MySQL.

Por qué existe este script
--------------------------
La aplicación usa **SQLite3** (lo exige el enunciado del proyecto). Un archivo
``.db`` de SQLite es un binario cuyo encabezado dice literalmente
``SQLite format 3``. **phpMyAdmin / MariaDB no pueden abrirlo**: son motores
distintos y por eso aparece el error::

    #1064 - You have an error in your SQL syntax ... near 'SQLite format 3'

Eso no es un fallo del proyecto: es lo esperado al subir un archivo de un motor
a otro. Para **revisar la base de datos real** se usa DB Browser for SQLite o la
línea de comandos ``sqlite3`` (ver ``docs/GUIA_BASE_DE_DATOS.md``).

Si de todos modos se quiere ver la información en phpMyAdmin, este script genera
un ``.sql`` con las MISMAS tablas, relaciones y datos, ya en sintaxis MySQL.

Uso::

    python exportar_a_mysql.py                     # -> database/techloan_mysql.sql
    python exportar_a_mysql.py ruta/salida.sql
"""

import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "techloan.db"
DESTINO_POR_DEFECTO = BASE_DIR / "database" / "techloan_mysql.sql"

# Tipos de SQLite -> tipos de MySQL.
_MAPA_TIPOS = {
    "INTEGER": "INT",
    "INT": "INT",
    "BIGINT": "BIGINT",
    "REAL": "DOUBLE",
    "DOUBLE": "DOUBLE",
    "FLOAT": "FLOAT",
    "NUMERIC": "DECIMAL(12,2)",
    "TEXT": "TEXT",
    "BLOB": "LONGBLOB",
}


def _tipo_mysql(tipo):
    """Traduce el tipo declarado en SQLite al equivalente de MySQL."""
    if not tipo:
        return "TEXT"
    base = tipo.strip().upper()
    # Conserva la longitud de VARCHAR(n)/CHAR(n).
    if base.startswith("VARCHAR") or base.startswith("CHAR"):
        return base
    # Quita cualquier sufijo de paréntesis (p. ej. DECIMAL(12,2) ya se contempla).
    raiz = base.split("(")[0].strip()
    return _MAPA_TIPOS.get(raiz, "TEXT")


def _esc(valor):
    """Escapa un valor de Python para incrustarlo en una sentencia MySQL."""
    if valor is None:
        return "NULL"
    if isinstance(valor, bool):
        return "1" if valor else "0"
    if isinstance(valor, (int, float)):
        return str(valor)
    if isinstance(valor, bytes):
        return "X'" + valor.hex() + "'"
    texto = str(valor)
    reemplazos = {
        "\\": "\\\\",
        "'": "\\'",
        "\0": "\\0",
        "\n": "\\n",
        "\r": "\\r",
        "\x1a": "\\Z",
    }
    for original, escapado in reemplazos.items():
        texto = texto.replace(original, escapado)
    return "'" + texto + "'"


def _tablas(conexion):
    return [
        fila["name"]
        for fila in conexion.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]


def _sql_de(conexion, tabla):
    fila = conexion.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tabla,)
    ).fetchone()
    return (fila["sql"] or "") if fila else ""


def _columnas_unicas(conexion, tabla):
    """Conjuntos de columnas con restricción UNIQUE (índices origin='u')."""
    unicas = []
    for indice in conexion.execute(f"PRAGMA index_list({tabla})").fetchall():
        if indice["origin"] == "u":
            cols = [
                info["name"]
                for info in conexion.execute(
                    f"PRAGMA index_info({indice['name']})"
                ).fetchall()
            ]
            if cols:
                unicas.append(cols)
    return unicas


def _definicion_tabla(conexion, tabla):
    """Construye la sentencia CREATE TABLE en sintaxis MySQL."""
    info = conexion.execute(f"PRAGMA table_info({tabla})").fetchall()
    sql_original = _sql_de(conexion, tabla).upper()
    autoincremento = "AUTOINCREMENT" in sql_original
    unicas = {tuple(cols) for cols in _columnas_unicas(conexion, tabla)}
    cols_indexadas = {c for cols in unicas for c in cols}

    lineas = []
    for col in info:
        tipo = _tipo_mysql(col["type"])
        default = col["dflt_value"]
        # Dos ajustes que MySQL exige y SQLite no:
        #   - DEFAULT CURRENT_TIMESTAMP solo vale en DATETIME, no en TEXT.
        #   - UNIQUE sobre TEXT necesita longitud de clave: se usa VARCHAR(191).
        if tipo == "TEXT" and default is not None and "CURRENT_TIMESTAMP" in str(default).upper():
            tipo = "DATETIME"
        elif tipo == "TEXT" and col["name"] in cols_indexadas:
            tipo = "VARCHAR(191)"

        partes = [f"  `{col['name']}`", tipo]
        if col["pk"]:
            partes.append("NOT NULL")
            if autoincremento and col["type"].strip().upper() in ("INTEGER", "INT"):
                partes.append("AUTO_INCREMENT")
            partes.append("PRIMARY KEY")
        else:
            if col["notnull"]:
                partes.append("NOT NULL")
            if default is not None:
                partes.append(f"DEFAULT {default}")
        lineas.append(" ".join(partes))

    for cols in sorted(unicas):
        nombres = ", ".join(f"`{c}`" for c in cols)
        lineas.append(f"  UNIQUE ({nombres})")

    for fk in conexion.execute(f"PRAGMA foreign_key_list({tabla})").fetchall():
        lineas.append(
            f"  FOREIGN KEY (`{fk['from']}`) REFERENCES `{fk['table']}` (`{fk['to']}`)"
        )

    cuerpo = ",\n".join(lineas)
    return (
        f"DROP TABLE IF EXISTS `{tabla}`;\n"
        f"CREATE TABLE `{tabla}` (\n{cuerpo}\n) "
        f"ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
    )


def _inserts(conexion, tabla):
    filas = conexion.execute(f"SELECT * FROM `{tabla}`").fetchall()
    if not filas:
        return []
    columnas = list(filas[0].keys())
    lista_cols = ", ".join(f"`{c}`" for c in columnas)
    sentencias = []
    for fila in filas:
        valores = ", ".join(_esc(fila[c]) for c in columnas)
        sentencias.append(f"INSERT INTO `{tabla}` ({lista_cols}) VALUES ({valores});")
    return sentencias


def exportar(origen=DB_PATH, destino=DESTINO_POR_DEFECTO):
    origen = Path(origen)
    if not origen.exists():
        raise SystemExit(
            f"No existe la base de datos {origen}. Ejecuta primero: python init_db.py"
        )

    conexion = sqlite3.connect(origen)
    conexion.row_factory = sqlite3.Row

    partes = [
        "-- Volcado MySQL generado por exportar_a_mysql.py",
        f"-- Origen: {origen.name} (SQLite3)",
        "-- La aplicación usa SQLite; este archivo es solo para revisarlo en MySQL.",
        "",
        "SET NAMES utf8mb4;",
        "SET FOREIGN_KEY_CHECKS = 0;",
        "CREATE DATABASE IF NOT EXISTS `techloan` "
        "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        "USE `techloan`;",
        "",
    ]

    tablas = _tablas(conexion)
    total_filas = 0
    for tabla in tablas:
        partes.append(f"-- ---------- {tabla} ----------")
        partes.append(_definicion_tabla(conexion, tabla))
        sentencias = _inserts(conexion, tabla)
        partes.extend(sentencias)
        total_filas += len(sentencias)
        partes.append("")

    partes.append("SET FOREIGN_KEY_CHECKS = 1;")
    partes.append("")

    conexion.close()

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(partes), encoding="utf-8")

    print(f"Volcado MySQL generado: {destino}")
    print(f"  Tablas: {len(tablas)}")
    print(f"  Sentencias INSERT: {total_filas}")
    print()
    print("Para verlo en phpMyAdmin: Importar -> elegir este archivo .sql")
    return destino


def main():
    destino = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DESTINO_POR_DEFECTO
    exportar(DB_PATH, destino)


if __name__ == "__main__":
    main()
