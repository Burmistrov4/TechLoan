from app.database import get_connection

class DisponibilidadService:
    @staticmethod
    def laboratorio(laboratorio_id, fecha, hora_inicio, hora_fin):
        with get_connection() as db:
            lab = db.execute(
                "SELECT id, estado FROM laboratorios WHERE id=?", (laboratorio_id,)
            ).fetchone()
            if not lab:
                return False, "El laboratorio no existe."
            if lab["estado"] != "DISPONIBLE":
                return False, "El laboratorio no está disponible."

            overlap = db.execute(
                """SELECT id FROM reservas
                   WHERE laboratorio_id=? AND fecha=?
                     AND estado IN ('CONFIRMADA','ACTIVA')
                     AND hora_inicio < ? AND hora_fin > ?
                   LIMIT 1""",
                (laboratorio_id, fecha, hora_fin, hora_inicio)
            ).fetchone()
            if overlap:
                return False, "El laboratorio tiene una reserva que se superpone."
        return True, "Laboratorio disponible."

    @staticmethod
    def estado(edicion_id, laboratorio_id, prestatario_id, tipo_reserva, fecha, dia_semana,
               periodo_academico, hora_inicio, hora_fin, cantidad_estudiantes=None):
        """Evaluación completa de disponibilidad de una celda/reserva candidata.

        A diferencia de :meth:`laboratorio` (que solo mira solapamiento puntual),
        contempla reservas SEMESTRALES (por ``dia_semana`` + ``periodo_academico``)
        y PUNTUALES (por ``fecha``), la disponibilidad del profesor (solo si es
        PROFESOR) y la capacidad del laboratorio. Comparte la semántica de choques
        con ``ReservationService``.
        """
        from app.services.reservation_service import ReservationService

        return ReservationService.estado_reserva(
            edicion_id, laboratorio_id, prestatario_id, tipo_reserva, fecha, dia_semana,
            periodo_academico, hora_inicio, hora_fin, cantidad_estudiantes,
        )

    @staticmethod
    def equipo(equipo_id):
        with get_connection() as db:
            row = db.execute(
                """SELECT e.estado,
                   EXISTS(SELECT 1 FROM prestamos_equipos p
                          WHERE p.equipo_id=e.id AND p.estado='ACTIVO') AS prestado
                   FROM equipos e WHERE e.id=?""",
                (equipo_id,)
            ).fetchone()
        if not row:
            return False, "El equipo no existe."
        if row["estado"] != "DISPONIBLE":
            return False, f"El equipo está en estado {row['estado']}."
        if row["prestado"]:
            return False, "El equipo tiene un préstamo activo."
        return True, "Equipo disponible."
