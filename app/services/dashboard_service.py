"""Servicio de indicadores para el panel de inicio (dashboard).

Concentra aquí las consultas de conteo y de series temporales para que las rutas
web no escriban SQL directamente y el panel siga respetando la arquitectura por
capas:

    Navegador -> Rutas web -> Servicios -> SQLite3
"""

from datetime import datetime, timedelta

from app.config import DIAS_PRESTAMO_LIMITE
from app.database import get_connection
from app.services.alertas_service import AlertasService
from app.services.auditoria_service import AuditoriaService


class DashboardService:
    """Indicadores, gráficos y actividad reciente para la página principal."""

    @staticmethod
    def _count(db, sql, params=()):
        return db.execute(sql, params).fetchone()[0]

    @staticmethod
    def stats():
        """Contadores principales del sistema."""
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
                "auditoria": AuditoriaService.total(),
            }

    @staticmethod
    def tendencias():
        """Variación porcentual de la actividad respecto a los 7 días anteriores.

        Da contexto a los indicadores: un número sin referencia no dice nada.
        """
        hoy = datetime.now().date()
        inicio_actual = (hoy - timedelta(days=6)).strftime("%Y-%m-%d")
        inicio_previo = (hoy - timedelta(days=13)).strftime("%Y-%m-%d")
        fin_previo = (hoy - timedelta(days=7)).strftime("%Y-%m-%d")
        clave_hoy = hoy.strftime("%Y-%m-%d")

        with get_connection() as db:
            reservas_actual = DashboardService._count(
                db,
                "SELECT COUNT(*) FROM reservas WHERE fecha BETWEEN ? AND ?",
                (inicio_actual, clave_hoy),
            )
            reservas_previo = DashboardService._count(
                db,
                "SELECT COUNT(*) FROM reservas WHERE fecha BETWEEN ? AND ?",
                (inicio_previo, fin_previo),
            )
            prestamos_actual = DashboardService._count(
                db,
                "SELECT COUNT(*) FROM prestamos_equipos WHERE substr(fecha_prestamo,1,10) BETWEEN ? AND ?",
                (inicio_actual, clave_hoy),
            )
            prestamos_previo = DashboardService._count(
                db,
                "SELECT COUNT(*) FROM prestamos_equipos WHERE substr(fecha_prestamo,1,10) BETWEEN ? AND ?",
                (inicio_previo, fin_previo),
            )

        def variacion(actual, previo):
            if previo == 0:
                return 100 if actual > 0 else 0
            return round((actual - previo) * 100 / previo)

        return {
            "reservas": variacion(reservas_actual, reservas_previo),
            "prestamos": variacion(prestamos_actual, prestamos_previo),
            "reservas_semana": reservas_actual,
            "prestamos_semana": prestamos_actual,
        }

    @staticmethod
    def reservas_proximas(limite=5):
        """Próximas reservas confirmadas a partir de hoy."""
        hoy = datetime.now().strftime("%Y-%m-%d")
        with get_connection() as db:
            return [
                dict(r)
                for r in db.execute(
                    """
                    SELECT r.id, r.fecha, r.hora_inicio, r.hora_fin, r.estado,
                           r.duracion_minutos,
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
        """Préstamos de equipos todavía no devueltos, los más antiguos primero."""
        with get_connection() as db:
            return [
                dict(r)
                for r in db.execute(
                    """
                    SELECT pe.id, pe.fecha_prestamo, pe.estado,
                           e.codigo AS equipo_codigo,
                           e.nombre AS equipo_nombre,
                           p.nombre || ' ' || p.apellido AS prestatario,
                           CAST(julianday('now','localtime') - julianday(pe.fecha_prestamo) AS INTEGER) AS dias
                    FROM prestamos_equipos pe
                    JOIN equipos e ON e.id = pe.equipo_id
                    JOIN prestatarios p ON p.id = pe.prestatario_id
                    WHERE pe.estado = 'ACTIVO'
                    ORDER BY dias DESC
                    LIMIT ?
                    """,
                    (limite,),
                ).fetchall()
            ]

    @staticmethod
    def prestamos_vencidos_detalle():
        """Préstamos que superan el límite de días sin devolverse."""
        return AlertasService.prestamos_vencidos_detalle()

    @staticmethod
    def actividad_reciente(limite=6):
        """Últimas acciones registradas en la auditoría."""
        return AuditoriaService.recientes(limite)

    @staticmethod
    def datos_graficos():
        """Series listas para dibujar en el panel.

        Se entregan ya con la forma que espera el dibujante de gráficos
        (``etiqueta`` / ``valor``), para que las plantillas no tengan que
        transformar nada.
        """
        etiquetas_estado = {
            "DISPONIBLE": "Disponible",
            "PRESTADO": "Prestado",
            "MANTENIMIENTO": "Mantenimiento",
            "DANADO": "Dañado",
            "INACTIVO": "Inactivo",
        }

        return {
            "serie_reservas": [
                {"etiqueta": punto["etiqueta"], "valor": punto["valor"], "es_hoy": punto["es_hoy"]}
                for punto in AlertasService.ocupacion_por_dia(11)
            ],
            "serie_equipos": [
                {
                    "etiqueta": etiquetas_estado.get(fila["estado"], fila["estado"].capitalize()),
                    "valor": fila["total"],
                }
                for fila in AlertasService.equipos_por_estado()
            ],
            "serie_laboratorios": [
                {
                    "etiqueta": fila["codigo"],
                    "detalle": fila["nombre"],
                    "valor": fila["total"],
                }
                for fila in AlertasService.ocupacion_por_laboratorio()
            ],
            "dias_limite": DIAS_PRESTAMO_LIMITE,
        }

    @staticmethod
    def estadisticas_publicas():
        """Cifras de titular para la portada pública.

        Se calculan sobre datos reales: si el sistema está vacío, la portada
        muestra sus valores por defecto y no cifras inventadas.
        """
        with get_connection() as db:
            return {
                "prestatarios": DashboardService._count(db, "SELECT COUNT(*) FROM prestatarios"),
                "laboratorios": DashboardService._count(db, "SELECT COUNT(*) FROM laboratorios"),
                "equipos": DashboardService._count(db, "SELECT COUNT(*) FROM equipos"),
                "reservas": DashboardService._count(db, "SELECT COUNT(*) FROM reservas"),
                "usuarios": DashboardService._count(db, "SELECT COUNT(*) FROM usuarios_sistema"),
                "tablas": DashboardService._count(
                    db, "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ),
            }
