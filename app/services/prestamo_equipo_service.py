from datetime import datetime
from app.database import get_connection

class PrestamoEquipoService:
    @staticmethod
    def create(equipo_id, prestatario_id, usuario_sistema_id, observaciones=""):
        with get_connection() as db:
            equipment = db.execute(
                "SELECT id, estado FROM equipos WHERE id=?", (equipo_id,)
            ).fetchone()
            if not equipment:
                raise ValueError("El equipo no existe.")
            if equipment["estado"] != "DISPONIBLE":
                raise ValueError("El equipo no está disponible para préstamo.")

            prestatario = db.execute(
                "SELECT estado FROM prestatarios WHERE id=?", (prestatario_id,)
            ).fetchone()
            if not prestatario:
                raise ValueError("El prestatario no existe.")
            if prestatario["estado"] != "ACTIVO":
                raise ValueError("El prestatario no está activo.")

            usuario = db.execute(
                "SELECT estado FROM usuarios_sistema WHERE id=?", (usuario_sistema_id,)
            ).fetchone()
            if not usuario:
                raise ValueError("El usuario del sistema no existe.")
            if usuario["estado"] != "ACTIVO":
                raise ValueError("El usuario del sistema no está activo.")

            active = db.execute(
                "SELECT id FROM prestamos_equipos WHERE equipo_id=? AND estado='ACTIVO' LIMIT 1",
                (equipo_id,)
            ).fetchone()
            if active:
                raise ValueError("El equipo ya tiene un préstamo activo.")

            cur = db.execute(
                """INSERT INTO prestamos_equipos
                (equipo_id,prestatario_id,usuario_sistema_id,fecha_prestamo,estado,observaciones)
                VALUES (?,?,?,?, 'ACTIVO', ?)""",
                (equipo_id, prestatario_id, usuario_sistema_id,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"), observaciones.strip())
            )
            db.execute("UPDATE equipos SET estado='PRESTADO' WHERE id=?", (equipo_id,))
            return cur.lastrowid

    @staticmethod
    def list_active():
        with get_connection() as db:
            return [dict(r) for r in db.execute(
                """SELECT p.*, e.codigo AS equipo_codigo, e.nombre AS equipo_nombre,
                   pr.cedula, pr.nombre AS prestatario_nombre, pr.apellido AS prestatario_apellido,
                   CAST(julianday('now','localtime') - julianday(p.fecha_prestamo) AS INTEGER) AS dias_prestado
                   FROM prestamos_equipos p
                   JOIN equipos e ON e.id=p.equipo_id
                   JOIN prestatarios pr ON pr.id=p.prestatario_id
                   WHERE p.estado='ACTIVO' ORDER BY dias_prestado DESC"""
            ).fetchall()]

    @staticmethod
    def list_all():
        with get_connection() as db:
            return [dict(r) for r in db.execute(
                """SELECT p.*, e.codigo AS equipo_codigo,
                   pr.nombre AS prestatario_nombre, pr.apellido AS prestatario_apellido,
                   CASE WHEN p.estado = 'ACTIVO'
                        THEN CAST(julianday('now','localtime') - julianday(p.fecha_prestamo) AS INTEGER)
                        ELSE NULL END AS dias_prestado
                   FROM prestamos_equipos p
                   JOIN equipos e ON e.id=p.equipo_id
                   JOIN prestatarios pr ON pr.id=p.prestatario_id
                   ORDER BY p.id DESC"""
            ).fetchall()]

    @staticmethod
    def get(prestamo_id):
        """Devuelve un préstamo con sus datos relacionados."""
        with get_connection() as db:
            fila = db.execute(
                """SELECT p.*, e.codigo AS equipo_codigo, e.nombre AS equipo_nombre,
                          pr.cedula, pr.nombre AS prestatario_nombre, pr.apellido AS prestatario_apellido,
                          u.username AS registrado_por
                   FROM prestamos_equipos p
                   JOIN equipos e ON e.id = p.equipo_id
                   JOIN prestatarios pr ON pr.id = p.prestatario_id
                   JOIN usuarios_sistema u ON u.id = p.usuario_sistema_id
                   WHERE p.id = ?""",
                (prestamo_id,),
            ).fetchone()
        return dict(fila) if fila else None

    @staticmethod
    def return_equipment(prestamo_id, observaciones=""):
        with get_connection() as db:
            loan = db.execute(
                "SELECT equipo_id, estado FROM prestamos_equipos WHERE id=?",
                (prestamo_id,)
            ).fetchone()
            if not loan:
                raise ValueError("El préstamo no existe.")
            if loan["estado"] != "ACTIVO":
                raise ValueError("El préstamo ya fue finalizado.")

            db.execute(
                """UPDATE prestamos_equipos
                   SET estado='DEVUELTO', fecha_devolucion=?, observaciones=?
                   WHERE id=?""",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), observaciones.strip(), prestamo_id)
            )
            db.execute(
                "UPDATE equipos SET estado='DISPONIBLE' WHERE id=?",
                (loan["equipo_id"],)
            )

    @staticmethod
    def equipment_available(equipo_id):
        with get_connection() as db:
            row = db.execute(
                """SELECT e.estado,
                   EXISTS(SELECT 1 FROM prestamos_equipos p
                          WHERE p.equipo_id=e.id AND p.estado='ACTIVO') AS tiene_prestamo
                   FROM equipos e WHERE e.id=?""",
                (equipo_id,)
            ).fetchone()
        return bool(row and row["estado"] == "DISPONIBLE" and not row["tiene_prestamo"])
