from datetime import datetime

from app.config import DIAS_PRESTAMO_LIMITE
from app.database import get_connection

class PrestamoEquipoService:
    @staticmethod
    def create(equipo_id, prestatario_id, usuario_sistema_id, observaciones="", edicion_id=1):
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
                (edicion_id, equipo_id,prestatario_id,usuario_sistema_id,fecha_prestamo,estado,observaciones)
                VALUES (?,?,?,?,?, 'ACTIVO', ?)""",
                (int(edicion_id), equipo_id, prestatario_id, usuario_sistema_id,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"), observaciones.strip())
            )
            db.execute("UPDATE equipos SET estado='PRESTADO' WHERE id=?", (equipo_id,))
            return cur.lastrowid

    @staticmethod
    def prestamos_activos_por_equipo(dias_limite=None):
        """Préstamos en curso indexados por id de equipo.

        Responde a la pregunta que el listado de equipos no contestaba: si un
        equipo figura como PRESTADO, ¿a quién se le prestó, desde cuándo y para
        cuándo? La fecha límite se calcula sumando los días permitidos a la
        fecha del préstamo, y ``dias_restantes`` puede ser negativo cuando ya
        se pasó del plazo.
        """
        limite = DIAS_PRESTAMO_LIMITE if dias_limite is None else int(dias_limite)

        with get_connection() as db:
            filas = db.execute(
                """SELECT p.id AS prestamo_id, p.equipo_id, p.fecha_prestamo,
                          p.observaciones,
                          pr.nombre || ' ' || pr.apellido AS prestatario,
                          pr.cedula, pr.telefono,
                          CAST(julianday('now','localtime') - julianday(p.fecha_prestamo)
                               AS INTEGER) AS dias_prestado,
                          date(p.fecha_prestamo, '+' || ? || ' days') AS fecha_limite
                     FROM prestamos_equipos p
                     JOIN prestatarios pr ON pr.id = p.prestatario_id
                    WHERE p.estado = 'ACTIVO'""",
                (limite,),
            ).fetchall()

        hoy = datetime.now().date()
        resultado = {}
        for fila in filas:
            dato = dict(fila)
            try:
                vence = datetime.strptime(dato["fecha_limite"], "%Y-%m-%d").date()
                dato["dias_restantes"] = (vence - hoy).days
            except (TypeError, ValueError):
                dato["dias_restantes"] = None
            dato["vencido"] = (
                dato["dias_restantes"] is not None and dato["dias_restantes"] < 0
            )
            resultado[dato["equipo_id"]] = dato
        return resultado

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
