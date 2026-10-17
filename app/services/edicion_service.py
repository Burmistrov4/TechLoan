import json
from app.database import get_connection
from app.models.entities import Edicion, EdicionVersion, EdicionConfig


class EdicionService:
    @staticmethod
    def listar_por_usuario(usuario_id):
        """Devuelve las ediciones a las que pertenece el usuario."""
        with get_connection() as db:
            filas = db.execute(
                """SELECT e.*, ue.rol_en_edicion
                     FROM ediciones e
                     JOIN usuarios_ediciones ue ON ue.edicion_id = e.id
                    WHERE ue.usuario_sistema_id = ?
                      AND e.estado = 'ACTIVA'
                    ORDER BY e.nombre""",
                (usuario_id,),
            ).fetchall()
            return [dict(f) for f in filas]

    @staticmethod
    def obtener(id):
        with get_connection() as db:
            f = db.execute("SELECT * FROM ediciones WHERE id = ?", (id,)).fetchone()
            return dict(f) if f else None

    @staticmethod
    def obtener_por_slug(slug):
        with get_connection() as db:
            f = db.execute("SELECT * FROM ediciones WHERE slug = ?", (slug,)).fetchone()
            return dict(f) if f else None

    @staticmethod
    def crear(nombre, slug, descripcion, creado_por):
        with get_connection() as db:
            cur = db.execute(
                "INSERT INTO ediciones (nombre, slug, descripcion) VALUES (?, ?, ?)",
                (nombre, slug, descripcion),
            )
            edicion_id = cur.lastrowid
            db.execute(
                """INSERT INTO edicion_versiones
                    (edicion_id, numero_version, nombre_version, creado_por, snapshot_json)
                   VALUES (?, 1, 'Inicial', ?, '{}')""",
                (edicion_id, creado_por),
            )
            db.execute(
                "INSERT INTO usuarios_ediciones (usuario_sistema_id, edicion_id, rol_en_edicion) VALUES (?, ?, 'ADMINISTRADOR_EDICION')",
                (creado_por, edicion_id),
            )
            return edicion_id

    @staticmethod
    def listar_versiones(edicion_id):
        with get_connection() as db:
            filas = db.execute(
                """SELECT v.*, u.username AS creado_por_username
                     FROM edicion_versiones v
                     JOIN usuarios_sistema u ON u.id = v.creado_por
                    WHERE v.edicion_id = ?
                    ORDER BY v.numero_version DESC""",
                (edicion_id,),
            ).fetchall()
            return [dict(f) for f in filas]

    @staticmethod
    def _serializar_snapshot(db, edicion_id):
        """Extrae el estado completo de una edición como diccionario."""
        config = {
            row["clave"]: row["valor"]
            for row in db.execute(
                "SELECT clave, valor FROM edicion_configuracion WHERE edicion_id = ?",
                (edicion_id,),
            ).fetchall()
        }

        def fetch(tabla):
            cols = [c["name"] for c in db.execute(f"PRAGMA table_info({tabla})").fetchall()]
            rows = db.execute(
                f"SELECT {', '.join(cols)} FROM {tabla} WHERE edicion_id = ?",
                (edicion_id,),
            ).fetchall()
            return [dict(r) for r in rows]

        return {
            "configuracion": config,
            "laboratorios": fetch("laboratorios"),
            "prestatarios": fetch("prestatarios"),
            "secciones": fetch("secciones"),
            "materias": fetch("materias"),
            "equipos": fetch("equipos"),
            "reservas": fetch("reservas"),
            "prestamos_equipos": fetch("prestamos_equipos"),
        }

    @staticmethod
    def crear_version(edicion_id, nombre_version, notas_cambios, creado_por):
        with get_connection() as db:
            # Obtener el siguiente número de versión
            max_ver = db.execute(
                "SELECT MAX(numero_version) FROM edicion_versiones WHERE edicion_id = ?",
                (edicion_id,),
            ).fetchone()[0] or 0

            snapshot = EdicionService._serializar_snapshot(db, edicion_id)
            db.execute(
                """INSERT INTO edicion_versiones
                    (edicion_id, numero_version, nombre_version, creado_por,
                     notas_cambios, snapshot_json)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (edicion_id, max_ver + 1, nombre_version, creado_por,
                 notas_cambios, json.dumps(snapshot, ensure_ascii=False)),
            )
            return max_ver + 1

    @staticmethod
    def restaurar_version(version_id):
        """Restaura una edición al estado guardado en una versión anterior.

        Ejecuta dentro de una transacción:
        1. Elimina datos operativos actuales de la edición (hijos primero).
        2. Inserta los datos del snapshot preservando los id originales.
        3. Actualiza version_actual.
        """
        with get_connection() as db:
            version = db.execute(
                "SELECT * FROM edicion_versiones WHERE id = ?", (version_id,)
            ).fetchone()
            if not version:
                raise ValueError("Versión no encontrada.")

            edicion_id = version["edicion_id"]
            snapshot = json.loads(version["snapshot_json"])

            # 1. Eliminar en orden de dependencia (hijos antes que padres)
            db.execute("DELETE FROM prestamos_equipos WHERE edicion_id = ?", (edicion_id,))
            db.execute("DELETE FROM reservas WHERE edicion_id = ?", (edicion_id,))
            db.execute("DELETE FROM equipos WHERE edicion_id = ?", (edicion_id,))
            db.execute("DELETE FROM laboratorios WHERE edicion_id = ?", (edicion_id,))
            db.execute("DELETE FROM prestatarios WHERE edicion_id = ?", (edicion_id,))
            # secciones y materias se borran tras las reservas (que las referencian).
            db.execute("DELETE FROM secciones WHERE edicion_id = ?", (edicion_id,))
            db.execute("DELETE FROM materias WHERE edicion_id = ?", (edicion_id,))

            # 2. Insertar preservando id (SQLite permite si no hay autoincrement conflict)
            # Nota: para tablas con FOREIGN KEY, los ids deben coincidir. Las secciones
            # y materias se insertan ANTES de las reservas, que las referencian.
            for tabla in ("prestatarios", "laboratorios", "secciones", "materias",
                          "equipos", "reservas", "prestamos_equipos"):
                filas = snapshot.get(tabla, [])
                if not filas:
                    continue
                columnas = list(filas[0].keys())
                placeholders = ", ".join("?" for _ in columnas)
                col_names = ", ".join(columnas)
                for fila in filas:
                    valores = [fila.get(c) for c in columnas]
                    db.execute(
                        f"INSERT INTO {tabla} ({col_names}) VALUES ({placeholders})",
                        valores,
                    )

            # 3. Restaurar configuración
            db.execute("DELETE FROM edicion_configuracion WHERE edicion_id = ?", (edicion_id,))
            for clave, valor in snapshot.get("configuracion", {}).items():
                db.execute(
                    "INSERT INTO edicion_configuracion (edicion_id, clave, valor) VALUES (?, ?, ?)",
                    (edicion_id, clave, valor),
                )

            # 4. Actualizar versión activa
            db.execute(
                "UPDATE ediciones SET version_actual = ? WHERE id = ?",
                (version["numero_version"], edicion_id),
            )

    @staticmethod
    def cambiar_version_actual(edicion_id, numero_version):
        with get_connection() as db:
            db.execute(
                "UPDATE ediciones SET version_actual = ? WHERE id = ?",
                (numero_version, edicion_id),
            )

    @staticmethod
    def obtener_config(edicion_id):
        with get_connection() as db:
            filas = db.execute(
                "SELECT clave, valor FROM edicion_configuracion WHERE edicion_id = ?",
                (edicion_id,),
            ).fetchall()
            return {f["clave"]: f["valor"] for f in filas}

    @staticmethod
    def guardar_config(edicion_id, clave, valor):
        with get_connection() as db:
            db.execute(
                """INSERT INTO edicion_configuracion (edicion_id, clave, valor)
                    VALUES (?, ?, ?)
                    ON CONFLICT(edicion_id, clave) DO UPDATE SET valor = excluded.valor""",
                (edicion_id, clave, valor),
            )
