"""Servicio de alertas: convierte los datos en avisos accionables.

Responde a la pregunta "¿qué requiere mi atención ahora mismo?" sin que el
usuario tenga que revisar cada módulo por su cuenta. Es la capa de inteligencia
operativa de TechLoan:

- **Préstamos vencidos**: equipos que llevan más días prestados de los
  permitidos. Se muestran en rojo y con los días transcurridos.
- **Reservas de hoy**: la agenda del día.
- **Laboratorios saturados**: los que superan el umbral de reservas en la
  próxima semana, señal de que conviene redistribuir la demanda.
"""

from datetime import datetime, timedelta

from app.config import DIAS_PRESTAMO_LIMITE, UMBRAL_SATURACION
from app.database import get_connection


class AlertasService:
    @staticmethod
    def resumen():
        """Resumen de avisos para la barra superior y el panel."""
        hoy = datetime.now().strftime("%Y-%m-%d")
        en_una_semana = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

        with get_connection() as db:
            prestamos_vencidos = db.execute(
                """SELECT COUNT(*) FROM prestamos_equipos
                   WHERE estado='ACTIVO'
                     AND CAST(julianday('now','localtime') - julianday(fecha_prestamo) AS INTEGER) > ?""",
                (DIAS_PRESTAMO_LIMITE,),
            ).fetchone()[0]

            reservas_hoy = db.execute(
                """SELECT COUNT(*) FROM reservas
                   WHERE fecha = ? AND estado IN ('CONFIRMADA','ACTIVA')""",
                (hoy,),
            ).fetchone()[0]

            labs_saturados = db.execute(
                """SELECT COUNT(*) FROM (
                       SELECT laboratorio_id
                       FROM reservas
                       WHERE fecha BETWEEN ? AND ?
                         AND estado IN ('CONFIRMADA','ACTIVA')
                       GROUP BY laboratorio_id
                       HAVING COUNT(*) >= ?
                   )""",
                (hoy, en_una_semana, UMBRAL_SATURACION),
            ).fetchone()[0]

        return {
            "prestamos_vencidos": prestamos_vencidos,
            "reservas_hoy": reservas_hoy,
            "labs_saturados": labs_saturados,
            "dias_limite": DIAS_PRESTAMO_LIMITE,
            "umbral_saturacion": UMBRAL_SATURACION,
            "total": prestamos_vencidos + reservas_hoy + labs_saturados,
        }

    @staticmethod
    def resumen_vacio():
        """Valor neutro para contextos sin sesión (acceso, portada)."""
        return {
            "prestamos_vencidos": 0,
            "reservas_hoy": 0,
            "labs_saturados": 0,
            "dias_limite": DIAS_PRESTAMO_LIMITE,
            "umbral_saturacion": UMBRAL_SATURACION,
            "total": 0,
        }

    @staticmethod
    def ocupacion_por_dia(dias=14):
        """Reservas confirmadas por día en la ventana indicada.

        Devuelve una serie lista para dibujar: etiqueta corta y valor.
        """
        hoy = datetime.now().date()
        desde = (hoy - timedelta(days=3)).strftime("%Y-%m-%d")
        hasta = (hoy + timedelta(days=dias)).strftime("%Y-%m-%d")

        with get_connection() as db:
            filas = db.execute(
                """SELECT fecha, COUNT(*) AS total
                   FROM reservas
                   WHERE fecha BETWEEN ? AND ? AND estado IN ('CONFIRMADA','ACTIVA')
                   GROUP BY fecha""",
                (desde, hasta),
            ).fetchall()

        conteo = {fila["fecha"]: fila["total"] for fila in filas}
        serie = []
        for desplazamiento in range(-3, dias):
            dia = hoy + timedelta(days=desplazamiento)
            clave = dia.strftime("%Y-%m-%d")
            serie.append(
                {
                    "fecha": clave,
                    "etiqueta": dia.strftime("%d/%m"),
                    "valor": conteo.get(clave, 0),
                    "es_hoy": desplazamiento == 0,
                }
            )
        return serie

    @staticmethod
    def equipos_por_estado():
        """Distribución del inventario por estado (para el gráfico de anillo)."""
        with get_connection() as db:
            return [
                dict(fila)
                for fila in db.execute(
                    """SELECT estado, COUNT(*) AS total
                       FROM equipos GROUP BY estado ORDER BY total DESC"""
                ).fetchall()
            ]

    @staticmethod
    def ocupacion_por_laboratorio(dias=7):
        """Reservas por laboratorio en los próximos días."""
        hoy = datetime.now().strftime("%Y-%m-%d")
        hasta = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")
        with get_connection() as db:
            return [
                dict(fila)
                for fila in db.execute(
                    """SELECT l.codigo, l.nombre, COUNT(r.id) AS total
                       FROM laboratorios l
                       LEFT JOIN reservas r
                         ON r.laboratorio_id = l.id
                        AND r.fecha BETWEEN ? AND ?
                        AND r.estado IN ('CONFIRMADA','ACTIVA')
                       GROUP BY l.id
                       ORDER BY total DESC, l.codigo""",
                    (hoy, hasta),
                ).fetchall()
            ]

    @staticmethod
    def prestamos_vencidos_detalle():
        """Lista de préstamos que superan el límite de días."""
        with get_connection() as db:
            return [
                dict(fila)
                for fila in db.execute(
                    """SELECT pe.id,
                              CAST(julianday('now','localtime') - julianday(pe.fecha_prestamo) AS INTEGER) AS dias,
                              pe.fecha_prestamo,
                              e.codigo AS equipo_codigo,
                              e.nombre AS equipo_nombre,
                              p.nombre || ' ' || p.apellido AS prestatario
                       FROM prestamos_equipos pe
                       JOIN equipos e ON e.id = pe.equipo_id
                       JOIN prestatarios p ON p.id = pe.prestatario_id
                       WHERE pe.estado = 'ACTIVO'
                         AND CAST(julianday('now','localtime') - julianday(pe.fecha_prestamo) AS INTEGER) > ?
                       ORDER BY dias DESC""",
                    (DIAS_PRESTAMO_LIMITE,),
                ).fetchall()
            ]
