from app.database import get_connection


class HistorialService:
    @staticmethod
    def list_all(tipo="TODOS", prestatario_id=None, recurso="", estado="TODOS",
                 fecha_desde="", fecha_hasta=""):
        tipos_validos = {"TODOS", "RESERVA", "PRESTAMO", "DEVOLUCION"}
        estados_validos = {"TODOS", "CONFIRMADA", "ACTIVA", "FINALIZADA",
                           "CANCELADA", "DEVUELTO", "ACTIVO"}
        tipo = (tipo or "TODOS").upper()
        estado = (estado or "TODOS").upper()
        if tipo not in tipos_validos:
            raise ValueError("Tipo de operación inválido.")
        if estado not in estados_validos:
            raise ValueError("Estado inválido.")

        if fecha_desde:
            HistorialService._validate_date(fecha_desde)
        if fecha_hasta:
            HistorialService._validate_date(fecha_hasta)
        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            raise ValueError("La fecha desde no puede ser posterior a la fecha hasta.")

        recurso = (recurso or "").strip()

        sql = """
            SELECT * FROM (
                SELECT
                    'RESERVA' AS tipo,
                    r.id AS referencia_id,
                    r.fecha || ' ' || r.hora_inicio AS fecha_operacion,
                    r.fecha AS fecha_base,
                    r.hora_inicio AS hora_inicio,
                    r.hora_fin AS hora_fin,
                    r.estado AS estado,
                    p.id AS prestatario_id,
                    p.cedula AS prestatario_cedula,
                    p.nombre || ' ' || p.apellido AS prestatario,
                    'LABORATORIO' AS recurso_tipo,
                    l.codigo AS recurso_codigo,
                    l.nombre AS recurso_nombre,
                    u.username AS usuario,
                    r.observaciones AS observaciones
                FROM reservas r
                JOIN prestatarios p ON p.id = r.prestatario_id
                JOIN laboratorios l ON l.id = r.laboratorio_id
                JOIN usuarios_sistema u ON u.id = r.usuario_sistema_id

                UNION ALL

                SELECT
                    'PRESTAMO' AS tipo,
                    pe.id AS referencia_id,
                    pe.fecha_prestamo AS fecha_operacion,
                    substr(pe.fecha_prestamo, 1, 10) AS fecha_base,
                    substr(pe.fecha_prestamo, 12, 5) AS hora_inicio,
                    '' AS hora_fin,
                    CASE WHEN pe.estado = 'DEVUELTO' THEN 'DEVUELTO' ELSE pe.estado END AS estado,
                    p.id AS prestatario_id,
                    p.cedula AS prestatario_cedula,
                    p.nombre || ' ' || p.apellido AS prestatario,
                    'EQUIPO' AS recurso_tipo,
                    e.codigo AS recurso_codigo,
                    e.nombre AS recurso_nombre,
                    u.username AS usuario,
                    pe.observaciones AS observaciones
                FROM prestamos_equipos pe
                JOIN prestatarios p ON p.id = pe.prestatario_id
                JOIN equipos e ON e.id = pe.equipo_id
                JOIN usuarios_sistema u ON u.id = pe.usuario_sistema_id
                WHERE pe.estado IN ('ACTIVO', 'DEVUELTO', 'CANCELADO')

                UNION ALL

                SELECT
                    'DEVOLUCION' AS tipo,
                    pe.id AS referencia_id,
                    pe.fecha_devolucion AS fecha_operacion,
                    substr(pe.fecha_devolucion, 1, 10) AS fecha_base,
                    substr(pe.fecha_devolucion, 12, 5) AS hora_inicio,
                    '' AS hora_fin,
                    'DEVUELTO' AS estado,
                    p.id AS prestatario_id,
                    p.cedula AS prestatario_cedula,
                    p.nombre || ' ' || p.apellido AS prestatario,
                    'EQUIPO' AS recurso_tipo,
                    e.codigo AS recurso_codigo,
                    e.nombre AS recurso_nombre,
                    u.username AS usuario,
                    pe.observaciones AS observaciones
                FROM prestamos_equipos pe
                JOIN prestatarios p ON p.id = pe.prestatario_id
                JOIN equipos e ON e.id = pe.equipo_id
                JOIN usuarios_sistema u ON u.id = pe.usuario_sistema_id
                WHERE pe.fecha_devolucion IS NOT NULL
            ) h
            WHERE 1=1
        """
        params = []

        if tipo != "TODOS":
            sql += " AND h.tipo = ?"
            params.append(tipo)
        if prestatario_id is not None:
            sql += " AND h.prestatario_id = ?"
            params.append(prestatario_id)
        if recurso:
            sql += " AND (LOWER(h.recurso_codigo) LIKE LOWER(?) OR LOWER(h.recurso_nombre) LIKE LOWER(?))"
            like = f"%{recurso}%"
            params.extend([like, like])
        if estado != "TODOS":
            sql += " AND h.estado = ?"
            params.append(estado)
        if fecha_desde:
            sql += " AND h.fecha_base >= ?"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND h.fecha_base <= ?"
            params.append(fecha_hasta)

        sql += " ORDER BY h.fecha_operacion DESC, h.referencia_id DESC"

        with get_connection() as db:
            return [dict(row) for row in db.execute(sql, tuple(params)).fetchall()]

    @staticmethod
    def _validate_date(value):
        from datetime import datetime
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("Las fechas deben tener formato AAAA-MM-DD.") from exc
