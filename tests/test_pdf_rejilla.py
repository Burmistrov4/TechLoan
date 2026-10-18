"""Pruebas de la Fase 4: exportación a PDF con fpdf2.

Cubre:
- Generación de los tres documentos: horario maestro por laboratorio,
  comprobante por sección y comprobante de reserva (todos empiezan por ``%PDF``).
- Sanitización Latin-1 (los bloques usan «–», que no existe en Latin-1 y no debe
  romper la generación).
- Aislamiento por edición, tanto en el servicio (ValueError) como en las rutas.
- Rutas de descarga (200 + ``application/pdf``) y protección sin sesión.

Corre contra una base temporal construida desde ``schema.sql``.

Uso::

    PYTHONPATH=. python tests/test_pdf_rejilla.py
"""

import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import _tempdb

_RUTA = _tempdb.preparar("test_pdf.db")

import app.database as database  # noqa: E402
from app.server import create_app  # noqa: E402
from app.services.pdf_service import (  # noqa: E402
    comprobante_reserva_pdf,
    comprobante_seccion_pdf,
    horario_maestro_pdf,
)

app = create_app()


def afirmar(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)


def _ids():
    with database.get_connection() as db:
        lab1 = db.execute("SELECT id FROM laboratorios WHERE edicion_id=1 ORDER BY id LIMIT 1").fetchone()["id"]
        lab2 = db.execute("SELECT id FROM laboratorios WHERE edicion_id=2 ORDER BY id LIMIT 1").fetchone()["id"]
        res1 = db.execute("SELECT id FROM reservas WHERE edicion_id=1 ORDER BY id LIMIT 1").fetchone()["id"]
        res2 = db.execute("SELECT id FROM reservas WHERE edicion_id=2 ORDER BY id LIMIT 1").fetchone()["id"]
        sec2 = db.execute(
            "SELECT id FROM secciones WHERE edicion_id=2 AND codigo_seccion='SA' AND semestre=1"
        ).fetchone()["id"]
    return lab1, lab2, res1, res2, sec2


def _es_pdf(datos):
    return isinstance(datos, (bytes, bytearray)) and bytes(datos[:4]) == b"%PDF" and len(datos) > 800


# ===========================================================================
# 1. Generación de los tres PDF (servicio)
# ===========================================================================
def test_generacion_pdf():
    lab1, lab2, res1, res2, sec2 = _ids()

    pdf_lab = horario_maestro_pdf(2, lab2)          # incluye bloques con «–»
    afirmar(_es_pdf(pdf_lab), "El horario del laboratorio debe ser un PDF válido")

    pdf_sec = comprobante_seccion_pdf(2, sec2)
    afirmar(_es_pdf(pdf_sec), "El comprobante de sección debe ser un PDF válido")

    pdf_res = comprobante_reserva_pdf(res2, 2)
    afirmar(_es_pdf(pdf_res), "El comprobante de reserva debe ser un PDF válido")

    # Los tres empiezan por %PDF y tienen tamaño razonable.
    afirmar(min(len(pdf_lab), len(pdf_sec), len(pdf_res)) > 800, "PDFs demasiado pequeños")
    print("PDF_GENERACION_OK")


# ===========================================================================
# 2. Aislamiento por edición (servicio)
# ===========================================================================
def test_aislamiento_servicio():
    lab1, lab2, res1, res2, sec2 = _ids()

    # Un laboratorio de la edición 2 no existe para la edición 1.
    try:
        horario_maestro_pdf(1, lab2)
        afirmar(False, "El laboratorio de otra edición debe rechazarse")
    except ValueError:
        pass
    # Una sección de la edición 2 no existe para la edición 1.
    try:
        comprobante_seccion_pdf(1, sec2)
        afirmar(False, "La sección de otra edición debe rechazarse")
    except ValueError:
        pass
    # Una reserva de la edición 2 no se exporta desde la edición 1.
    try:
        comprobante_reserva_pdf(res2, 1)
        afirmar(False, "La reserva de otra edición debe rechazarse")
    except ValueError:
        pass
    print("PDF_AISLAMIENTO_SERVICIO_OK")


# ===========================================================================
# 3. Rutas web de descarga
# ===========================================================================
def _login(cliente, username="admin", password="Admin123!"):
    cliente.get("/login")
    tok = re.search(r'name="_csrf_token" value="([^"]+)"',
                    cliente.get("/login").get_data(as_text=True)).group(1)
    return cliente.post("/login", data={"_csrf_token": tok, "username": username, "password": password})


def test_rutas_pdf():
    lab1, lab2, res1, res2, sec2 = _ids()
    cliente = app.test_client()
    _login(cliente)

    # Horario del laboratorio (edición 1).
    r = cliente.get(f"/reservas/horario-pdf?modo=laboratorio&id={lab1}")
    afirmar(r.status_code == 200, f"El horario debe responder 200 (fue {r.status_code})")
    afirmar("application/pdf" in r.headers.get("Content-Type", ""), "Content-Type debe ser PDF")
    afirmar(r.data[:4] == b"%PDF", "El cuerpo debe empezar por %PDF")

    # Comprobante de reserva (edición 1).
    r = cliente.get(f"/reservas/{res1}/pdf")
    afirmar(r.status_code == 200 and r.data[:4] == b"%PDF", "El comprobante de reserva debe ser PDF")

    # Aislamiento en la ruta: un laboratorio de la edición 2 estando en la 1 → redirige.
    r = cliente.get(f"/reservas/horario-pdf?modo=laboratorio&id={lab2}", follow_redirects=False)
    afirmar(r.status_code == 302, "Un recurso de otra edición debe redirigir (no servir PDF)")

    # Una reserva de la edición 2 estando en la 1 → redirige.
    r = cliente.get(f"/reservas/{res2}/pdf", follow_redirects=False)
    afirmar(r.status_code == 302, "Una reserva de otra edición debe redirigir")

    # Sin id → redirige con aviso.
    r = cliente.get("/reservas/horario-pdf", follow_redirects=False)
    afirmar(r.status_code == 302, "Sin id debe redirigir")

    # El formulario ofrece el botón de PDF y su URL.
    form = cliente.get("/reservas/crear").get_data(as_text=True)
    afirmar("rejilla-pdf" in form, "El formulario debe tener el botón Descargar PDF")
    afirmar("/reservas/horario-pdf" in form, "El formulario debe apuntar a la ruta del PDF")

    # Sin sesión → redirige a login (302), no sirve el PDF.
    anon = app.test_client()
    r = anon.get(f"/reservas/horario-pdf?modo=laboratorio&id={lab1}", follow_redirects=False)
    afirmar(r.status_code == 302, "Sin sesión no debe descargarse el PDF")

    print("PDF_RUTAS_OK")


# ===========================================================================
def main():
    print(f"Base de datos de prueba: {_RUTA}")
    test_generacion_pdf()
    test_aislamiento_servicio()
    test_rutas_pdf()
    print("FASE4_PDF_OK")


if __name__ == "__main__":
    main()
