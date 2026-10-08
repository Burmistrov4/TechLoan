from datetime import datetime, timedelta
from app.database import get_connection


class ReservationService:
    @staticmethod
    def calculate_end_time(hora_inicio, duracion_minutos):
        start = datetime.strptime(hora_inicio, "%H:%M")
        end = start + timedelta(minutes=duracion_minutos)
        if end.date() != start.date():
            raise ValueError("La reserva no puede superar las 23:59.")
        return end.strftime("%H:%M")

    @staticmethod
    def has_overlap(laboratorio_id, fecha, hora_inicio, hora_fin):
        with get_connection() as db:
            row = db.execute(
                """SELECT id FROM reservas
                   WHERE laboratorio_id=? AND fecha=?
                     AND estado IN ('CONFIRMADA','ACTIVA')
                     AND hora_inicio < ? AND hora_fin > ? LIMIT 1""",
                (laboratorio_id, fecha, hora_fin, hora_inicio)
            ).fetchone()
        return row is not None

    @staticmethod
    def create_reservation(laboratorio_id, prestatario_id, usuario_sistema_id,
                           fecha, hora_inicio, duracion_minutos, observaciones=""):
        if duracion_minutos <= 0 or duracion_minutos > 1440:
            raise ValueError("La duración debe estar entre 1 y 1440 minutos.")

        try:
            selected_date = datetime.strptime(fecha, "%Y-%m-%d").date()
            datetime.strptime(hora_inicio, "%H:%M")
        except ValueError as exc:
            raise ValueError("Fecha u hora inválida.") from exc

        if selected_date < datetime.now().date():
            raise ValueError("No se puede crear una reserva para una fecha pasada.")

        hora_fin = ReservationService.calculate_end_time(hora_inicio, duracion_minutos)

        with get_connection() as db:
            lab = db.execute(
                "SELECT estado, duracion_estandar_minutos FROM laboratorios WHERE id=?",
                (laboratorio_id,)
            ).fetchone()
            if not lab:
                raise ValueError("El laboratorio no existe.")
            if lab["estado"] != "DISPONIBLE":
                raise ValueError("El laboratorio no está disponible.")

            prestatario = db.execute(
                "SELECT estado FROM prestatarios WHERE id=?",
                (prestatario_id,)
            ).fetchone()
            if not prestatario:
                raise ValueError("El prestatario no existe.")
            if prestatario["estado"] != "ACTIVO":
                raise ValueError("El prestatario no está activo.")

            usuario = db.execute(
                "SELECT estado FROM usuarios_sistema WHERE id=?",
                (usuario_sistema_id,)
            ).fetchone()
            if not usuario:
                raise ValueError("El usuario del sistema no existe.")
            if usuario["estado"] != "ACTIVO":
                raise ValueError("El usuario del sistema no está activo.")

            overlap = db.execute(
                """SELECT id FROM reservas
                   WHERE laboratorio_id=? AND fecha=?
                     AND estado IN ('CONFIRMADA','ACTIVA')
                     AND hora_inicio < ? AND hora_fin > ? LIMIT 1""",
                (laboratorio_id, fecha, hora_fin, hora_inicio)
            ).fetchone()
            if overlap:
                raise ValueError(
                    "El laboratorio ya tiene una reserva que se superpone con ese horario."
                )

            cur = db.execute(
                """INSERT INTO reservas
                (laboratorio_id,prestatario_id,usuario_sistema_id,fecha,hora_inicio,
                 hora_fin,duracion_minutos,observaciones)
                VALUES (?,?,?,?,?,?,?,?)""",
                (laboratorio_id, prestatario_id, usuario_sistema_id, fecha, hora_inicio,
                 hora_fin, duracion_minutos, (observaciones or "").strip() or None)
            )
            return cur.lastrowid

    @staticmethod
    def cancel(reservation_id):
        """Marca una reserva como CANCELADA.

        Una reserva cancelada deja de bloquear la franja horaria: la regla de
        solapamiento solo considera los estados CONFIRMADA y ACTIVA.
        """
        with get_connection() as db:
            row = db.execute(
                "SELECT estado FROM reservas WHERE id=?", (reservation_id,)
            ).fetchone()
            if not row:
                raise ValueError("La reserva no existe.")
            if row["estado"] in ("CANCELADA", "FINALIZADA"):
                raise ValueError("La reserva ya no puede cancelarse.")
            db.execute(
                "UPDATE reservas SET estado='CANCELADA' WHERE id=?", (reservation_id,)
            )

    @staticmethod
    def list_all():
        with get_connection() as db:
            return [dict(r) for r in db.execute(
                """SELECT r.*, l.codigo AS laboratorio_codigo, l.nombre AS laboratorio_nombre,
                   p.cedula, p.nombre AS prestatario_nombre, p.apellido AS prestatario_apellido
                   FROM reservas r
                   JOIN laboratorios l ON l.id=r.laboratorio_id
                   JOIN prestatarios p ON p.id=r.prestatario_id
                   ORDER BY r.fecha DESC, r.hora_inicio DESC"""
            ).fetchall()]
