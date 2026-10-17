"""Pruebas de la Fase 3: rejilla semanal y previsualización en vivo.

Cubre:
- ``RejillaService.construir``: matriz días(0..5) × bloques de la edición,
  laboratorios y ocupación (proyección de semestrales y puntuales).
- Endpoint ``GET /reservas/rejilla-semanal``: aislamiento por edición
  (edicion_id=1 vs 2) y eco de los 3 modos (laboratorio/seccion/profesor).
- ``ReservationService.estado_reserva`` (detección de estado en vivo, sin guardar):
  choque de laboratorio, choque de profesor (solo PROFESOR) y capacidad con
  laboratorios alternativos.

Corre contra una base temporal construida desde ``schema.sql``.

Uso::

    PYTHONPATH=. python tests/test_rejilla_semanal.py
"""

import re
import sys
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import _tempdb

_RUTA = _tempdb.preparar("test_rejilla.db")

from app.server import create_app  # noqa: E402
from app.services.laboratorio_service import LaboratorioService  # noqa: E402
from app.services.prestatario_service import PrestatarioService  # noqa: E402
from app.services.rejilla_service import RejillaService  # noqa: E402
from app.services.reservation_service import ReservationService  # noqa: E402
from app.services.seccion_service import SeccionService  # noqa: E402

app = create_app()
ED = 2
UID = 1


def afirmar(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)


def fecha_futura_en(weekday):
    d = date.today()
    while not (d.weekday() == weekday and d > date.today()):
        d += timedelta(days=1)
    return d.strftime("%Y-%m-%d")


# ===========================================================================
# 1. Servicio de rejilla: estructura y proyección de ocupación
# ===========================================================================
def test_rejilla_servicio():
    rejilla = RejillaService.construir(ED)
    afirmar(rejilla["edicion_id"] == ED, "La rejilla debe construirse para la edición dada")
    afirmar(rejilla["dias"] == [0, 1, 2, 3, 4, 5], "Debe cubrir Lunes a Sábado (0..5)")
    afirmar(len(rejilla["bloques"]) >= 10, "Debe haber bloques de 70 min entre 07:00 y 21:00")
    afirmar(all(b["fin"] - b["inicio"] == 70 for b in rejilla["bloques"]),
            "Los bloques por defecto son de 70 minutos")

    lab_ids = {l["id"] for l in rejilla["laboratorios"]}
    afirmar(len(lab_ids) == 3, "IUTEPI LABS tiene 3 laboratorios sembrados")

    oc = rejilla["ocupacion"]
    # Toda la ocupación pertenece a laboratorios de la edición (aislamiento).
    afirmar(all(c["laboratorio_id"] in lab_ids for c in oc),
            "La ocupación no debe filtrar laboratorios de otra edición")

    # La asignación SEMESTRAL de la semilla (LAB-01, lunes 07:00-09:10) se
    # proyecta en celdas del lunes (dia 0).
    lunes_lab01 = [c for c in oc if c["dia"] == 0 and c["laboratorio_codigo"] == "LAB-01"]
    afirmar(len(lunes_lab01) >= 2,
            "La clase semestral del lunes debe ocupar al menos 2 bloques")
    afirmar(any(c.get("profesor") for c in oc), "La ocupación debe incluir el profesor")

    # La rejilla de la edición 1 no debe contaminarse con la edición 2.
    r1 = RejillaService.construir(1)
    lab_ids_1 = {l["id"] for l in r1["laboratorios"]}
    afirmar(len(lab_ids_1) == 3, "La edición base tiene 3 laboratorios")
    afirmar(not (lab_ids & lab_ids_1), "Los ids de laboratorio deben ser distintos por edición")
    if r1["ocupacion"]:
        afirmar(all(c["laboratorio_id"] in lab_ids_1 for c in r1["ocupacion"]),
                "La ocupación de la edición 1 no debe incluir laboratorios de la edición 2")
    print("REJILLA_SERVICIO_OK")


# ===========================================================================
# 2. Endpoint: aislamiento por edición y eco de modos
# ===========================================================================
def _login(cliente, username="admin", password="Admin123!"):
    cliente.get("/login")
    tok = re.search(r'name="_csrf_token" value="([^"]+)"',
                    cliente.get("/login").get_data(as_text=True)).group(1)
    return cliente.post("/login", data={"_csrf_token": tok, "username": username, "password": password})


def _csrf(cliente, ruta):
    return re.search(r'name="_csrf_token" value="([^"]+)"',
                     cliente.get(ruta).get_data(as_text=True)).group(1)


def test_endpoint_aislamiento_y_modos():
    cliente = app.test_client()
    _login(cliente)

    # Edición activa por defecto (1).
    r = cliente.get("/reservas/rejilla-semanal")
    afirmar(r.status_code == 200, "El endpoint debe responder 200")
    datos = r.get_json()
    afirmar(datos["ok"] and datos["edicion_id"] == 1, "Sin cambiar, la edición activa es 1")
    lab_ids = {l["id"] for l in datos["laboratorios"]}
    if datos["ocupacion"]:
        afirmar(all(c["laboratorio_id"] in lab_ids for c in datos["ocupacion"]),
                "La edición 1 no debe exponer laboratorios de la edición 2")

    # Cambia a IUTEPI LABS (edición 2): la rejilla es la de esa edición.
    cliente.post("/ediciones/cambiar",
                 data={"_csrf_token": _csrf(cliente, "/panel"), "edicion_id": str(ED)},
                 follow_redirects=True)
    r2 = cliente.get("/reservas/rejilla-semanal")
    datos2 = r2.get_json()
    afirmar(datos2["edicion_id"] == ED, "Tras cambiar, la edición activa es 2")
    lab_ids2 = {l["id"] for l in datos2["laboratorios"]}
    afirmar(not (lab_ids & lab_ids2), "Las ediciones no comparten laboratorios")

    # Eco de los 3 modos (el filtrado fino es del cliente; el servidor devuelve
    # la ocupación completa de la edición y hace eco del modo/objetivo).
    seccion_sa1 = next(s["id"] for s in SeccionService.list_all(ED)
                       if s["codigo_seccion"] == "SA" and s["semestre"] == 1)
    for modo in ("laboratorio", "seccion", "profesor"):
        rx = cliente.get(f"/reservas/rejilla-semanal?modo={modo}&id=1")
        d = rx.get_json()
        afirmar(rx.status_code == 200 and d["ok"], f"modo {modo} debe responder ok")
        afirmar(d["modo"] == modo, f"Debe hacer eco del modo {modo}")
        afirmar("bloques" in d and "ocupacion" in d and "laboratorios" in d,
                "La respuesta debe incluir bloques, ocupación y laboratorios")

    # El formulario de reserva expone el contenedor y la URL de la rejilla.
    form = cliente.get("/reservas/crear").get_data(as_text=True)
    afirmar("rejilla-semanal" in form, "El formulario debe tener el contenedor de la rejilla")
    afirmar("/reservas/rejilla-semanal" in form, "Debe apuntar al endpoint de la rejilla")
    afirmar("selector-bloque" in form, "Debe existir el selector asistido de bloques")
    afirmar('name="rejilla-modo"' in form, "Debe existir el selector de modo")
    print("ENDPOINT_AISLAMIENTO_MODOS_OK")


# ===========================================================================
# 3. estado_reserva: detección de estado en vivo (sin guardar)
# ===========================================================================
def test_estado_en_vivo():
    lab_a = LaboratorioService.create({  # capacidad 30
        "codigo": "LAB-F3A", "nombre": "Lab A F3", "ubicacion": "Aula A",
        "capacidad": 30, "duracion_estandar_minutos": 70, "estado": "DISPONIBLE", "edicion_id": ED})
    lab_b = LaboratorioService.create({  # capacidad 20
        "codigo": "LAB-F3B", "nombre": "Lab B F3", "ubicacion": "Aula B",
        "capacidad": 20, "duracion_estandar_minutos": 70, "estado": "DISPONIBLE", "edicion_id": ED})
    profe = PrestatarioService.create({
        "cedula": "V-F3-PROFE", "nombre": "Profe", "apellido": "Tres", "tipo": "PROFESOR",
        "estado": "ACTIVO", "edicion_id": ED})
    estudiante = PrestatarioService.create({
        "cedula": "V-F3-ESTU", "nombre": "Estu", "apellido": "Tres", "tipo": "ESTUDIANTE",
        "estado": "ACTIVO", "edicion_id": ED})

    martes = fecha_futura_en(1)
    # Base: clase semestral del profesor en LAB-A, martes 08:00-09:10.
    ReservationService.create_reservation(
        lab_a, profe, UID, martes, "08:00", 70, "", edicion_id=ED,
        tipo_reserva="SEMESTRAL", dia_semana=1, periodo_academico="2026-2")

    # a) Choque de laboratorio: misma fecha/martes, mismo lab, solapado.
    est = ReservationService.estado_reserva(
        ED, lab_a, estudiante, "PUNTUAL", martes, 1, "2026-2", "08:30", "09:00")
    afirmar(est["choque_laboratorio"] and not est["disponible"],
            "Debe detectar choque de laboratorio en la vista previa")

    # b) Choque de profesor: otro laboratorio, mismo profesor, mismo día/hora.
    est = ReservationService.estado_reserva(
        ED, lab_b, profe, "PUNTUAL", martes, 1, "2026-2", "08:30", "09:00")
    afirmar(est["choque_profesor"] and not est["disponible"],
            "Debe detectar choque de profesor en la vista previa")

    # c) Válido: otro laboratorio, un estudiante, misma franja → libre.
    est = ReservationService.estado_reserva(
        ED, lab_b, estudiante, "PUNTUAL", martes, 1, "2026-2", "08:30", "09:00")
    afirmar(est["disponible"], f"Debería estar libre (motivo: {est['motivo']})")

    # d) Capacidad excedida → sugerencias de laboratorios con cupo.
    est = ReservationService.estado_reserva(
        ED, lab_b, profe, "PUNTUAL", fecha_futura_en(3), None, "2026-2", "10:00", "11:10",
        cantidad_estudiantes=25)
    afirmar(not est["capacidad_ok"] and not est["disponible"],
            "La cantidad por encima de la capacidad debe marcar conflicto")
    codigos = {s["codigo"] for s in est["sugerencias"]}
    afirmar("LAB-F3A" in codigos and "LAB-F3B" not in codigos,
            f"Debe sugerir el lab con cupo y no el saturado (sugirió {codigos})")

    print("ESTADO_EN_VIVO_OK")


# ===========================================================================
def main():
    print(f"Base de datos de prueba: {_RUTA}")
    test_rejilla_servicio()
    test_endpoint_aislamiento_y_modos()
    test_estado_en_vivo()
    print("FASE3_REJILLA_SEMANAL_OK")


if __name__ == "__main__":
    main()
