from datetime import datetime, timedelta
from app.config import HORA_APERTURA, HORA_CIERRE
from app.database import get_connection


def _a_minutos(hora):
    """Convierte 'HH:MM' en minutos desde medianoche."""
    horas, minutos = hora.split(":")
    return int(horas) * 60 + int(minutos)


def _a_hora(minutos):
    """Convierte minutos desde medianoche en 'HH:MM'."""
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


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
                           fecha, hora_inicio, duracion_minutos, observaciones="", edicion_id=1):
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
                (edicion_id, laboratorio_id,prestatario_id,usuario_sistema_id,fecha,hora_inicio,
                 hora_fin,duracion_minutos,observaciones)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (int(edicion_id), laboratorio_id, prestatario_id, usuario_sistema_id, fecha, hora_inicio,
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
    def get(reservation_id):
        """Devuelve una reserva con sus datos relacionados (para el comprobante)."""
        with get_connection() as db:
            fila = db.execute(
                """SELECT r.*,
                          l.codigo AS laboratorio_codigo,
                          l.nombre AS laboratorio_nombre,
                          l.ubicacion AS laboratorio_ubicacion,
                          p.cedula, p.nombre AS prestatario_nombre,
                          p.apellido AS prestatario_apellido,
                          p.email AS prestatario_email,
                          p.telefono AS prestatario_telefono,
                          u.username AS registrado_por,
                          u.nombre || ' ' || u.apellido AS registrado_por_nombre
                   FROM reservas r
                   JOIN laboratorios l ON l.id = r.laboratorio_id
                   JOIN prestatarios p ON p.id = r.prestatario_id
                   JOIN usuarios_sistema u ON u.id = r.usuario_sistema_id
                   WHERE r.id = ?""",
                (reservation_id,),
            ).fetchone()
        return dict(fila) if fila else None

    @staticmethod
    def ocupacion_del_dia(laboratorio_id, fecha):
        """Franjas ya ocupadas de un laboratorio en una fecha concreta.

        Se usa para dibujar la línea de tiempo del día en el formulario de
        reservas: el usuario ve de un vistazo qué queda libre.
        """
        with get_connection() as db:
            filas = db.execute(
                """SELECT hora_inicio, hora_fin, estado FROM reservas
                   WHERE laboratorio_id = ? AND fecha = ?
                     AND estado IN ('CONFIRMADA','ACTIVA')
                   ORDER BY hora_inicio""",
                (laboratorio_id, fecha),
            ).fetchall()
        return [dict(fila) for fila in filas]

    @staticmethod
    def sugerir_horarios(laboratorio_id, fecha, duracion_minutos, hora_deseada=None, limite=3):
        """Propone las franjas libres más cercanas a la hora solicitada.

        Es la parte "inteligente" del módulo de reservas: en lugar de limitarse a
        rechazar un solapamiento, calcula los huecos reales del día y ofrece
        alternativas ordenadas por cercanía a lo que el usuario pedía.
        """
        if not fecha or not duracion_minutos or duracion_minutos <= 0:
            return []

        apertura = _a_minutos(HORA_APERTURA)
        cierre = _a_minutos(HORA_CIERRE)

        ocupadas = sorted(
            (_a_minutos(r["hora_inicio"]), _a_minutos(r["hora_fin"]))
            for r in ReservationService.ocupacion_del_dia(laboratorio_id, fecha)
        )

        # Unir intervalos que se tocan o se superponen para obtener los bloques
        # realmente ocupados (las franjas adyacentes cuentan como un solo bloque).
        bloques = []
        for inicio, fin in ocupadas:
            if bloques and inicio <= bloques[-1][1]:
                bloques[-1] = (bloques[-1][0], max(bloques[-1][1], fin))
            else:
                bloques.append((inicio, fin))

        # Huecos libres dentro del horario de apertura.
        huecos = []
        cursor = apertura
        for inicio, fin in bloques:
            if inicio - cursor >= duracion_minutos:
                huecos.append((cursor, inicio))
            cursor = max(cursor, fin)
        if cierre - cursor >= duracion_minutos:
            huecos.append((cursor, cierre))

        deseada = _a_minutos(hora_deseada) if hora_deseada else None

        sugerencias = []
        for inicio, fin in huecos:
            propuesta = inicio
            if deseada is not None and inicio <= deseada and deseada + duracion_minutos <= fin:
                propuesta = deseada
            referencia = deseada if deseada is not None else apertura
            sugerencias.append(
                {
                    "hora_inicio": _a_hora(propuesta),
                    "hora_fin": _a_hora(propuesta + duracion_minutos),
                    # Hasta cuándo sigue libre el hueco: es más útil para el
                    # usuario que un número de minutos suelto.
                    "libre_hasta": _a_hora(fin),
                    "holgura_minutos": fin - inicio,
                    "_distancia": abs(propuesta - referencia),
                }
            )

        sugerencias.sort(key=lambda s: s["_distancia"])
        for sugerencia in sugerencias:
            sugerencia.pop("_distancia", None)
        return sugerencias[:limite]

    @staticmethod
    def proximas_reservas_por_laboratorio(dias=7):
        """Situación de cada laboratorio, indexada por id.

        Responde a lo que el listado de laboratorios no decía: si un laboratorio
        está libre ahora, ¿hasta cuándo? Y si está ocupado, ¿hasta qué hora?

        Devuelve, por laboratorio, la **próxima reserva** que empieza o está en
        curso (con ``es_hoy`` y ``en_curso`` ya calculados) y cuántas reservas
        tiene en los próximos ``dias``, que es la señal de saturación.
        """
        ahora = datetime.now()
        hoy = ahora.strftime("%Y-%m-%d")
        hora_actual = ahora.strftime("%H:%M")
        hasta = (ahora + timedelta(days=dias)).strftime("%Y-%m-%d")

        with get_connection() as db:
            proximas = db.execute(
                """SELECT r.laboratorio_id, r.fecha, r.hora_inicio, r.hora_fin,
                          p.nombre || ' ' || p.apellido AS prestatario
                     FROM reservas r
                     JOIN prestatarios p ON p.id = r.prestatario_id
                    WHERE r.estado IN ('CONFIRMADA', 'ACTIVA')
                      AND r.fecha >= ?
                      -- Las de hoy ya terminadas no cuentan como "próximas".
                      AND NOT (r.fecha = ? AND r.hora_fin <= ?)
                    ORDER BY r.fecha, r.hora_inicio""",
                (hoy, hoy, hora_actual),
            ).fetchall()

            demanda = db.execute(
                """SELECT laboratorio_id, COUNT(*) AS total
                     FROM reservas
                    WHERE estado IN ('CONFIRMADA', 'ACTIVA')
                      AND fecha BETWEEN ? AND ?
                    GROUP BY laboratorio_id""",
                (hoy, hasta),
            ).fetchall()

        resultado = {
            fila["laboratorio_id"]: {"total_semana": fila["total"]} for fila in demanda
        }

        for fila in proximas:
            laboratorio_id = fila["laboratorio_id"]
            dato = resultado.setdefault(laboratorio_id, {"total_semana": 0})
            if "fecha" in dato:
                continue  # ya se guardó la más próxima (vienen ordenadas)
            dato.update(
                {
                    "fecha": fila["fecha"],
                    "hora_inicio": fila["hora_inicio"],
                    "hora_fin": fila["hora_fin"],
                    "prestatario": fila["prestatario"],
                    "es_hoy": fila["fecha"] == hoy,
                    "en_curso": fila["fecha"] == hoy
                    and fila["hora_inicio"] <= hora_actual < fila["hora_fin"],
                }
            )

        return resultado

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
