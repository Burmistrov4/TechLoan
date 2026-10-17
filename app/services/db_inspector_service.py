"""Inspector de base de datos de solo lectura para administradores.

Permite auditar la estructura de SQLite3, verificar el hashing de contraseñas
y previsualizar tablas sin permitir SQL arbitrario.
"""

import json
from app.database import get_connection


def _tablas_reales(db):
    """Devuelve la lista blanca de tablas obtenida dinámicamente de sqlite_master."""
    return {
        r["name"]
        for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    }


def _tiene_columna(db, tabla, columna):
    """Verifica si una tabla tiene una columna concreta."""
    return any(
        c["name"] == columna
        for c in db.execute(f"PRAGMA table_info({tabla})").fetchall()
    )


def _enmascarar_tokens(filas):
    """Oculta la columna 'token' mostrando solo los primeros 8 caracteres."""
    resultado = []
    for fila in filas:
        copia = dict(fila)
        if "token" in copia and copia["token"]:
            copia["token"] = copia["token"][:8] + "..."
        resultado.append(copia)
    return resultado


class DBInspectorService:
    @staticmethod
    def listar_tablas():
        with get_connection() as db:
            filas = db.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            return [dict(f) for f in filas]

    @staticmethod
    def contar_registros(tabla):
        with get_connection() as db:
            if tabla not in _tablas_reales(db):
                raise ValueError(f"Tabla '{tabla}' no existe.")
            return db.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]

    @staticmethod
    def previsualizar(tabla, limite=50, edicion_id=None):
        with get_connection() as db:
            if tabla not in _tablas_reales(db):
                raise ValueError(f"Tabla '{tabla}' no existe.")

            cols = [c["name"] for c in db.execute(f"PRAGMA table_info({tabla})").fetchall()]
            if not cols:
                return {"columnas": [], "filas": []}

            tiene_edicion = _tiene_columna(db, tabla, "edicion_id")
            if edicion_id is not None and tiene_edicion:
                filas = db.execute(
                    f"SELECT {', '.join(cols)} FROM {tabla} WHERE edicion_id = ? LIMIT ?",
                    (edicion_id, limite),
                ).fetchall()
            else:
                filas = db.execute(
                    f"SELECT {', '.join(cols)} FROM {tabla} LIMIT ?", (limite,)
                ).fetchall()

            resultado = [dict(f) for f in filas]
            if tabla == "tokens_correo":
                resultado = _enmascarar_tokens(resultado)

            return {"columnas": cols, "filas": resultado}

    @staticmethod
    def obtener_usuarios_con_hash():
        with get_connection() as db:
            filas = db.execute(
                """SELECT id, nombre, apellido, email, rol, password_hash
                     FROM usuarios_sistema ORDER BY id"""
            ).fetchall()
            return [dict(f) for f in filas]

    @staticmethod
    def desglosar_hash(password_hash):
        """Parsea un hash de Werkzeug y devuelve sus componentes.

        Formato esperado: metodo$parametros$salt$hash  o  metodo:parametros$salt$hash
        Ejemplo scrypt: scrypt:32768:8:1$salt$hash
        """
        if not password_hash:
            return None

        partes = password_hash.split("$")
        if len(partes) < 3:
            return {"error": "Formato de hash no reconocido", "raw": password_hash}

        # scrypt:32768:8:1$salt$hash -> metodo_param = "scrypt:32768:8:1"
        metodo_param = partes[0]
        salt = partes[1] if len(partes) >= 2 else ""
        hash_val = "$".join(partes[2:])  # por si el hash contiene $

        metodo = metodo_param.split(":")[0] if ":" in metodo_param else metodo_param
        parametros = metodo_param[len(metodo) + 1 :] if ":" in metodo_param else ""

        return {
            "algoritmo": metodo,
            "parametros": parametros,
            "salt": salt,
            "hash": hash_val,
            "raw": password_hash,
        }

    @staticmethod
    def generar_hash_demo(password):
        """Genera un hash de demostración con Werkzeug para mostrar
        que el salt es aleatorio y cada generación produce un hash distinto."""
        from werkzeug.security import generate_password_hash

        return generate_password_hash(password)
