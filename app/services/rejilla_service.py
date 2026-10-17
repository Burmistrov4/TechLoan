"""Construcción de la rejilla (matriz) semanal por edición.

Centraliza los datos que alimentan:
- el endpoint JSON ``GET /reservas/rejilla-semanal`` (previsualización en vivo),
- y, más adelante (Fase 4), la exportación a PDF con ``fpdf2``.

La matriz es **días (0=Lunes..5=Sábado) × bloques horarios de la edición**
(``edicion_configuracion['bloques_horarios']`` o, en su defecto, bloques de 70
minutos entre ``HORA_APERTURA`` y ``HORA_CIERRE``).
"""

from datetime import datetime

from app.config import DIAS_SEMANA
from app.database import get_connection
from app.services.laboratorio_service import LaboratorioService
from app.services.seccion_service import SeccionService
from app.services.reservation_service import obtener_bloques_edicion, _a_minutos, _solapa


def _dias_de_reserva(tipo_reserva, dia_semana, fecha):
    """Días de la semana (0..5) que ocupa una reserva dentro de la semana tipo."""
    if tipo_reserva == "SEMESTRAL" and dia_semana is not None:
        return [int(dia_semana)]
    if tipo_reserva == "PUNTUAL" and fecha:
        try:
            weekday = datetime.strptime(fecha, "%Y-%m-%d").weekday()
        except (ValueError, TypeError):
            return []
        if 0 <= weekday <= 5:
            return [weekday]
    return []


class RejillaService:
    @staticmethod
    def construir(edicion_id):
        """Devuelve el diccionario con días, bloques, laboratorios y ocupación.

        ``ocupacion`` contiene una celda por cada (día, bloque) que una reserva
        activa ocupe en la semana tipo, con metadatos suficientes para pintar la
        rejilla y calcular conflictos en cliente (laboratorio, profesor,
        cantidad).
        """
        bloques_min = obtener_bloques_edicion(edicion_id)

        def _hhmm(minutos):
            return f"{minutos // 60:02d}:{minutos % 60:02d}"

        bloques = [
            {"inicio": ini, "fin": fin, "etiqueta": f"{_hhmm(ini)} – {_hhmm(fin)}"}
            for ini, fin in bloques_min
        ]

        laboratorios = [
            {"id": l["id"], "codigo": l["codigo"], "nombre": l["nombre"],
             "capacidad": l["capacidad"]}
            for l in LaboratorioService.list_all(edicion_id)
        ]

        secciones = []
        for s in SeccionService.list_all(edicion_id):
            etiqueta = f"{s['codigo_seccion']} — {s['semestre']}º {s['carrera_o_escuela']}".strip()
            secciones.append({"id": s["id"], "codigo_seccion": s["codigo_seccion"],
                              "semestre": s["semestre"], "etiqueta": etiqueta})

        with get_connection() as db:
            filas = db.execute(
                """SELECT r.id, r.laboratorio_id, r.prestatario_id, r.tipo_reserva,
                          r.fecha, r.dia_semana, r.hora_inicio, r.hora_fin,
                          r.cantidad_estudiantes,
                          l.codigo AS laboratorio_codigo,
                          m.codigo AS materia_codigo, m.nombre AS materia_nombre,
                          s.id AS seccion_id,
                          s.codigo_seccion AS seccion_codigo, s.semestre AS semestre,
                          p.nombre || ' ' || p.apellido AS profesor
                     FROM reservas r
                     LEFT JOIN laboratorios l ON l.id = r.laboratorio_id
                     LEFT JOIN materias m      ON m.id = r.materia_id
                     LEFT JOIN secciones s      ON s.id = r.seccion_id
                     LEFT JOIN prestatarios p   ON p.id = r.prestatario_id
                    WHERE r.edicion_id = ? AND r.estado IN ('CONFIRMADA','ACTIVA')""",
                (edicion_id,)
            ).fetchall()

        ocupacion = []
        for r in filas:
            ini_res = _a_minutos(r["hora_inicio"])
            fin_res = _a_minutos(r["hora_fin"])
            dias = _dias_de_reserva(r["tipo_reserva"], r["dia_semana"], r["fecha"])
            for dia in dias:
                for bloque in bloques:
                    if _solapa(ini_res, fin_res, bloque["inicio"], bloque["fin"]):
                        ocupacion.append({
                            "reserva_id": r["id"],
                            "dia": dia,
                            "inicio": bloque["inicio"],
                            "fin": bloque["fin"],
                            "laboratorio_id": r["laboratorio_id"],
                            "laboratorio_codigo": r["laboratorio_codigo"],
                            "prestatario_id": r["prestatario_id"],
                            "profesor": r["profesor"],
                            "materia_codigo": r["materia_codigo"],
                            "materia_nombre": r["materia_nombre"],
                            "seccion_id": r["seccion_id"],
                            "seccion_codigo": r["seccion_codigo"],
                            "semestre": r["semestre"],
                            "cantidad_estudiantes": r["cantidad_estudiantes"],
                            "tipo_reserva": r["tipo_reserva"],
                        })

        return {
            "edicion_id": edicion_id,
            "dias": list(range(0, 6)),
            "nombres_dias": {str(k): v for k, v in DIAS_SEMANA.items()},
            "bloques": bloques,
            "laboratorios": laboratorios,
            "secciones": secciones,
            "ocupacion": ocupacion,
        }
