"""Servicio de indicadores para el panel de inicio (dashboard).

Concentra aquí las consultas de conteo para que las rutas web no escriban SQL
directamente y el panel siga respetando la arquitectura por capas:

    Navegador -> Rutas web -> Servicios -> SQLite3
"""

from datetime import datetime

from app.database import get_connection


class DashboardService:
    """Indicadores y actividad reciente para la página principal."""

    @staticmethod
    def _count(db, sql, params=()):
        return db.execute(sql, params).fetchone()[0]

    @staticmethod
    def stats():
        """Devuelve un diccionario con los contadores del sistema."""
        with get_connection() as db:
            hoy = datetime.now().strftime("%Y-%m-%d")
            return {
                "prestatarios": DashboardService._count(db, "SELECT COUNT(*) FROM prestatarios"),
                "prestatarios_activos": DashboardService._count(
                    db, "SELECT COUNT(*) FROM prestatarios WHERE estado='ACTIVO'"
                ),
                "laboratorios": DashboardService._count(db, "SELECT COUNT(*) FROM laboratorios"),
                "laboratorios_disponibles": DashboardService._count(
                    db, "SELECT COUNT(*) FROM laboratorios WHERE estado='DISPONIBLE'"
                ),
                "categorias": DashboardService._count(db, "SELECT COUNT(*) FROM categorias"),
                "equipos": DashboardService._count(db, "SELECT COUNT(*) FROM equipos"),
                "equipos_disponibles": DashboardService._count(
                    db, "SELECT COUNT(*) FROM equipos WHERE estado='DISPONIBLE'"
                ),
                "equipos_prestados": DashboardService._count(
                    db, "SELECT COUNT(*) FROM equipos WHERE estado='PRESTADO'"
                ),
                "usuarios": DashboardService._count(db, "SELECT COUNT(*) FROM usuarios_sistema"),
                "reservas": DashboardService._count(db, "SELECT COUNT(*) FROM reservas"),
                "reservas_confirmadas": DashboardService._count(
                    db,
                    "SELECT COUNT(*) FROM reservas "
                    "WHERE estado IN ('CONFIRMADA','ACTIVA') AND fecha >= ?",
                    (hoy,),
                ),
                "prestamos_activos": DashboardService._count(
                    db, "SELECT COUNT(*) FROM prestamos_equipos WHERE estado='ACTIVO'"
                ),
            }

    @staticmethod
    def reservas_proximas(limite=5):
        """Últimas reservas confirmadas a partir de hoy."""
        hoy = datetime.now().strftime("%Y-%m-%d")
        with get_connection() as db:
            return [
                dict(r)
                for r in db.execute(
                    """
                    SELECT r.id, r.fecha, r.hora_inicio, r.hora_fin, r.estado,
                           l.codigo AS laboratorio_codigo,
                           l.nombre AS laboratorio_nombre,
                           p.nombre || ' ' || p.apellido AS prestatario
                    FROM reservas r
                    JOIN laboratorios l ON l.id = r.laboratorio_id
                    JOIN prestatarios p ON p.id = r.prestatario_id
                    WHERE r.fecha >= ? AND r.estado IN ('CONFIRMADA','ACTIVA')
                    ORDER BY r.fecha ASC, r.hora_inicio ASC
                    LIMIT ?
                    """,
                    (hoy, limite),
                ).fetchall()
            ]

    @staticmethod
    def prestamos_activos(limite=5):
        """Préstamos de equipos todavía no devueltos."""
        with get_connection() as db:
            return [
                dict(r)
                for r in db.execute(
                    """
                    SELECT pe.id, pe.fecha_prestamo, pe.estado,
                           e.codigo AS equipo_codigo,
                           e.nombre AS equipo_nombre,
                           p.nombre || ' ' || p.apellido AS prestatario
                    FROM prestamos_equipos pe
                    JOIN equipos e ON e.id = pe.equipo_id
                    JOIN prestatarios p ON p.id = pe.prestatario_id
                    WHERE pe.estado = 'ACTIVO'
                    ORDER BY pe.fecha_prestamo DESC
                    LIMIT ?
                    """,
                    (limite,),
                ).fetchall()
            ]
