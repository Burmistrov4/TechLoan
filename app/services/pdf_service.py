"""Generación de PDF con fpdf2 (Fase 4).

Documentos:
- ``horario_maestro_pdf(edicion_id, laboratorio_id)``: rejilla semanal del laboratorio.
- ``comprobante_seccion_pdf(edicion_id, seccion_id)``: clases semanales de una sección.
- ``comprobante_reserva_pdf(reserva_id, edicion_id)``: comprobante de una reserva.

Portabilidad: se usan las fuentes **core** de fpdf2 (Helvetica) y todo el texto se
normaliza a Latin-1 (se cambian guiones largos, comillas tipográficas, etc.). Así
el PDF funciona igual en Windows y en PythonAnywhere sin subir archivos TTF.
"""

from datetime import datetime

from fpdf import FPDF

from app.config import DIAS_SEMANA
from app.database import get_connection
from app.services.edicion_service import EdicionService
from app.services.rejilla_service import RejillaService
from app.services.reservation_service import ReservationService
from app.services.seccion_service import SeccionService

# Caracteres Unicode que no existen en Latin-1 y que aparecen en textos del proyecto.
_REEMPLAZOS = {
    "\u2013": "-",   # en dash
    "\u2014": "-",   # em dash
    "\u201c": '"', "\u201d": '"',
    "\u2018": "'", "\u2019": "'",
    "\u2026": "...",  # ellipsis
    "\u2022": "-",   # bullet
    "\u2192": "->",
    "\u00b7": "-",   # middle dot
}


def _lat1(valor):
    """Normaliza un texto a Latin-1 (lo que admiten las fuentes core de fpdf2)."""
    texto = "" if valor is None else str(valor)
    for origen, destino in _REEMPLAZOS.items():
        texto = texto.replace(origen, destino)
    return texto.encode("latin-1", "replace").decode("latin-1")


def _recortar(valor, maximo):
    texto = _lat1(valor)
    if len(texto) <= maximo:
        return texto
    return texto[: max(0, maximo - 3)] + "..."


def _nombre_edicion(edicion_id):
    edicion = EdicionService.obtener(edicion_id)
    return edicion["nombre"] if edicion else f"Edicion {edicion_id}"


def _periodo(edicion_id):
    """Periodo académico: de la configuración de la edición; si no, el más usado
    en las reservas de esa edición."""
    config = EdicionService.obtener_config(edicion_id) or {}
    periodo = config.get("periodo_academico")
    if periodo:
        return periodo
    with get_connection() as db:
        fila = db.execute(
            """SELECT periodo_academico FROM reservas
               WHERE edicion_id=? AND periodo_academico IS NOT NULL AND periodo_academico <> ''
               GROUP BY periodo_academico ORDER BY COUNT(*) DESC LIMIT 1""",
            (edicion_id,)
        ).fetchone()
    return fila["periodo_academico"] if fila else "-"


def _pie(pdf):
    pdf.set_y(-14)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(120, 120, 120)
    ancho = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.cell(ancho / 2, 6, _lat1("TechLoan - generado el " + datetime.now().strftime("%d/%m/%Y %H:%M")), align="L")
    pdf.cell(ancho / 2, 6, _lat1("Página " + str(pdf.page_no())), align="R")
    pdf.set_text_color(0, 0, 0)


def _encabezado(pdf, titulo, lineas):
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 9, _lat1(titulo))
    pdf.ln(9)
    pdf.set_font("Helvetica", "", 9)
    for linea in lineas:
        pdf.multi_cell(0, 5, _lat1(linea))
        pdf.set_x(pdf.l_margin)
    pdf.ln(2)


def horario_maestro_pdf(edicion_id, laboratorio_id):
    """Rejilla semanal (bloques x días) de un laboratorio. Devuelve bytes."""
    datos = RejillaService.construir(edicion_id)
    lab = next((l for l in datos["laboratorios"] if l["id"] == laboratorio_id), None)
    if not lab:
        raise ValueError("El laboratorio no pertenece a la edición activa.")

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=16)
    pdf.add_page()
    _encabezado(pdf, "Horario semanal de laboratorio", [
        f"Edición: {_nombre_edicion(edicion_id)}",
        f"Período académico: {_periodo(edicion_id)}",
        f"Laboratorio: {lab['codigo']} - {lab['nombre']} (capacidad {lab['capacidad']})",
    ])

    dias = datos["dias"]
    nombres = datos["nombres_dias"]
    # Ocupación indexada por (dia, inicio de bloque) para este laboratorio.
    ocupadas = {}
    for celda in datos["ocupacion"]:
        if celda["laboratorio_id"] != laboratorio_id:
            continue
        ocupadas.setdefault((celda["dia"], celda["inicio"]), []).append(celda)

    ancho_util = 277  # A4 horizontal (297) menos margenes
    ancho_bloque = 26
    ancho_dia = (ancho_util - ancho_bloque) / len(dias)
    alto = 9

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(230, 234, 246)
    pdf.cell(ancho_bloque, alto, _lat1("Bloque"), border=1, fill=True, align="C")
    for dia in dias:
        pdf.cell(ancho_dia, alto, _lat1(nombres.get(str(dia), nombres.get(dia, dia))),
                 border=1, fill=True, align="C")
    pdf.ln(alto)

    pdf.set_font("Helvetica", "", 7)
    for bloque in datos["bloques"]:
        pdf.set_fill_color(245, 246, 250)
        pdf.cell(ancho_bloque, alto, _lat1(bloque["etiqueta"]), border=1, fill=True, align="C")
        for dia in dias:
            items = ocupadas.get((dia, bloque["inicio"]), [])
            if items:
                partes = []
                for it in items:
                    parte = ""
                    if it.get("materia_codigo"):
                        parte += it["materia_codigo"]
                    if it.get("seccion_codigo"):
                        parte += " " + it["seccion_codigo"]
                        if it.get("semestre") is not None:
                            parte += "-" + str(it["semestre"])
                    if it.get("profesor"):
                        parte += " " + it["profesor"]
                    partes.append(parte.strip() or "-")
                texto = _recortar(" / ".join(partes), 30)
                pdf.set_fill_color(232, 236, 255)
                pdf.cell(ancho_dia, alto, texto, border=1, fill=True, align="L")
            else:
                pdf.cell(ancho_dia, alto, "", border=1)
        pdf.ln(alto)

    _pie(pdf)
    return bytes(pdf.output())


def comprobante_seccion_pdf(edicion_id, seccion_id):
    """Clases semanales de una sección (día, bloque, materia, laboratorio, profesor)."""
    seccion = SeccionService.get(seccion_id)
    if not seccion or seccion.get("edicion_id") != edicion_id:
        raise ValueError("La sección no pertenece a la edición activa.")

    datos = RejillaService.construir(edicion_id)
    clases = [c for c in datos["ocupacion"] if c.get("seccion_id") == seccion_id]
    clases.sort(key=lambda c: (c["dia"], c["inicio"]))

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=16)
    pdf.add_page()
    _encabezado(pdf, "Horario semanal de sección", [
        f"Edición: {_nombre_edicion(edicion_id)}",
        f"Período académico: {_periodo(edicion_id)}",
        f"Sección: {seccion['codigo_seccion']} - {seccion['semestre']}º semestre "
        f"({seccion.get('carrera_o_escuela') or 'sin escuela'})",
    ])

    if not clases:
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 7, _lat1("La sección no tiene clases asignadas en esta edición."))
        _pie(pdf)
        return bytes(pdf.output())

    columnas = [("Día", 26), ("Bloque", 28), ("Materia", 52), ("Laboratorio", 30),
                ("Profesor", 34), ("Cant.", 12)]
    alto = 8
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(230, 234, 246)
    for titulo, ancho in columnas:
        pdf.cell(ancho, alto, _lat1(titulo), border=1, fill=True, align="C")
    pdf.ln(alto)

    pdf.set_font("Helvetica", "", 8)
    for c in clases:
        bloque = next((b for b in datos["bloques"] if b["inicio"] == c["inicio"]), None)
        etiqueta = bloque["etiqueta"] if bloque else ""
        valores = [
            (DIAS_SEMANA.get(c["dia"], "-"), 26),
            (etiqueta, 28),
            ((c.get("materia_codigo") or "-") + (" " + c["materia_nombre"] if c.get("materia_nombre") else ""), 52),
            (c.get("laboratorio_codigo") or "-", 30),
            (c.get("profesor") or "-", 34),
            (str(c.get("cantidad_estudiantes") or "-"), 12),
        ]
        for valor, ancho in valores:
            pdf.cell(ancho, alto, _recortar(valor, int(ancho / 1.7)), border=1)
        pdf.ln(alto)

    _pie(pdf)
    return bytes(pdf.output())


def comprobante_reserva_pdf(reserva_id, edicion_id=None):
    """Comprobante de una reserva concreta (una página)."""
    r = ReservationService.get(reserva_id)
    if not r:
        raise ValueError("La reserva no existe.")
    if edicion_id is not None and r.get("edicion_id") != edicion_id:
        raise ValueError("La reserva no pertenece a la edición activa.")

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(True, margin=16)
    pdf.add_page()
    _encabezado(pdf, "Comprobante de reserva", [
        f"Folio: {int(r['id']):05d}",
        f"Edición: {_nombre_edicion(r.get('edicion_id', edicion_id or 1))}",
    ])

    tipo = (r.get("tipo_reserva") or "PUNTUAL")
    filas = [
        ("Estado", r.get("estado")),
        ("Tipo", tipo),
        ("Laboratorio", f"{r.get('laboratorio_codigo')} - {r.get('laboratorio_nombre')}"),
        ("Ubicación", r.get("laboratorio_ubicacion")),
        ("Período académico", r.get("periodo_academico") or _periodo(r.get("edicion_id", 1))),
        ("Fecha", r.get("fecha")),
        ("Hora", f"{r.get('hora_inicio')} - {r.get('hora_fin')} ({r.get('duracion_minutos')} min)"),
        ("Prestatario", f"{r.get('prestatario_nombre')} {r.get('prestatario_apellido')} ({r.get('cedula')})"),
        ("Registrado por", r.get("registrado_por_nombre") or r.get("registrado_por")),
    ]
    if tipo == "SEMESTRAL":
        dia = r.get("dia_semana")
        filas.insert(5, ("Día de la semana", DIAS_SEMANA.get(dia, "-") if dia is not None else "-"))
    if r.get("cantidad_estudiantes") is not None:
        filas.append(("Cantidad de estudiantes", r.get("cantidad_estudiantes")))
    if r.get("observaciones"):
        filas.append(("Observaciones", r.get("observaciones")))

    pdf.set_font("Helvetica", "", 10)
    for etiqueta, valor in filas:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(50, 7, _lat1(etiqueta + ":"))
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 7, _lat1(valor if valor is not None else "-"))
        pdf.set_x(pdf.l_margin)

    _pie(pdf)
    return bytes(pdf.output())
