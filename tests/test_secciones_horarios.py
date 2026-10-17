"""Pruebas de la Fase 2: secciones, materias, horarios y choques.

Cubre el motor de validación de ``reservation_service`` y su integración web:
- UNIQUE compuesta de secciones (mismo código en distintos semestres) y materias.
- Choque de laboratorio (puntual/puntual y semestral/semestral) y adyacencia.
- Choque de PROFESOR entre dos laboratorios (los estudiantes no lo generan).
- Cruce puntual ↔ semestral (mismo día de semana y periodo).
- Validación de capacidad con laboratorios alternativos.
- Normalización de horas ('9:30' == '09:30') antes de comparar.
- Snapshot/restore de versiones incluyendo secciones y materias.
- Aislamiento por edición y bloques horarios configurables.
- Rutas web (listados, validación de sección y rechazo por capacidad).

Corre contra una base temporal construida desde ``schema.sql``.

Uso::

    PYTHONPATH=. python tests/test_secciones_horarios.py
"""

import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import _tempdb

_RUTA = _tempdb.preparar("test_secciones.db")

import app.database as database  # noqa: E402
from app.server import create_app  # noqa: E402
from app.services.edicion_service import EdicionService  # noqa: E402
from app.services.laboratorio_service import LaboratorioService  # noqa: E402
from app.services.materia_service import MateriaService  # noqa: E402
from app.services.prestatario_service import PrestatarioService  # noqa: E402
from app.services.reservation_service import (  # noqa: E402
    ReservaInvalida,
    ReservationService,
    obtener_bloques_edicion,
)
from app.services.seccion_service import SeccionService  # noqa: E402

app = create_app()
ED = 2  # edición «IUTEPI LABS» sembrada con datos de la Fase 2
UID = 1  # administrador sembrado


# ---------------------------------------------------------------------------
def afirmar(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)


def fecha_futura_en(weekday):
    """Primera fecha estrictamente futura cuyo weekday coincide (0=Lunes)."""
    d = date.today()
    while not (d.weekday() == weekday and d > date.today()):
        d += timedelta(days=1)
    return d.strftime("%Y-%m-%d")


def crear_profesor(cedula):
    return PrestatarioService.create({
        "cedula": cedula, "nombre": "Profe", "apellido": "Prueba",
        "tipo": "PROFESOR", "telefono": None, "email": None, "estado": "ACTIVO",
        "edicion_id": ED,
    })


def crear_estudiante(cedula):
    return PrestatarioService.create({
        "cedula": cedula, "nombre": "Estu", "apellido": "Prueba",
        "tipo": "ESTUDIANTE", "telefono": None, "email": None, "estado": "ACTIVO",
        "edicion_id": ED,
    })


def id_lab_ed2(codigo):
    lab = next(l for l in LaboratorioService.list_all(edicion_id=ED)
               if l["codigo"] == codigo)
    return lab["id"]


def crear_puntual(lab, prestatario, fecha, hora, dur, periodo=None, cantidad=None,
                  seccion=None, materia=None):
    return ReservationService.create_reservation(
        lab, prestatario, UID, fecha, hora, dur, "", edicion_id=ED,
        tipo_reserva="PUNTUAL", periodo_academico=periodo, cantidad_estudiantes=cantidad,
        seccion_id=seccion, materia_id=materia,
    )


def crear_semestral(lab, prestatario, dia, hora, dur, periodo="2026-2",
                    cantidad=None, seccion=None, materia=None):
    return ReservationService.create_reservation(
        lab, prestatario, UID, fecha_futura_en(dia), hora, dur, "", edicion_id=ED,
        tipo_reserva="SEMESTRAL", dia_semana=dia, periodo_academico=periodo,
        cantidad_estudiantes=cantidad, seccion_id=seccion, materia_id=materia,
    )


# ===========================================================================
# 1. Secciones: UNIQUE compuesta + validación de código
# ===========================================================================
def test_secciones_unique_y_validacion():
    seed = SeccionService.list_all(edicion_id=ED)
    codes = {(s["codigo_seccion"], s["semestre"]) for s in seed}
    afirmar(("SA", 1) in codes and ("SA", 2) in codes and ("SA-A", 1) in codes,
                   "La semilla debe traer SA 1, SA 2 y SA-A")

    # Crear SA en 3.er semestre: permitido.
    SeccionService.create({"codigo_seccion": "SA", "semestre": 3, "periodo_academico": "2026-2",
                           "carrera_o_escuela": "Escuela de Sistemas", "estado": "ACTIVA",
                           "edicion_id": ED})
    # Repetir SA 1 mismo periodo/escuela (ya existe en la semilla): rechazado.
    try:
        SeccionService.create({"codigo_seccion": "sa", "semestre": 1, "periodo_academico": "2026-2",
                               "carrera_o_escuela": "Escuela de Sistemas", "estado": "ACTIVA",
                               "edicion_id": ED})
        afirmar(False, "Repetir SA 1 mismo periodo/escuela debe fallar")
    except ValueError as exc:
        afirmar("Ya existe esa sección" in str(exc), f"Mensaje inesperado: {exc}")

    # Código inválido rechazado; 'sa' se normaliza a 'SA'.
    try:
        SeccionService.create({"codigo_seccion": "SA#", "semestre": 4,
                               "periodo_academico": "2026-2", "estado": "ACTIVA", "edicion_id": ED})
        afirmar(False, "Un código de sección inválido debe fallar")
    except ValueError:
        pass

    # Mismo código en otra edición: permitido (UNIQUE por edición).
    SeccionService.create({"codigo_seccion": "SA", "semestre": 1,
                           "periodo_academico": "2026-2", "carrera_o_escuela": "",
                           "estado": "ACTIVA", "edicion_id": 1})

    print("SECCIONES_UNIQUE_VALIDACION_OK")


# ===========================================================================
# 2. Materias: UNIQUE por edición
# ===========================================================================
def test_materias_unique():
    afirmar(len(MateriaService.list_all(edicion_id=ED)) == 3, "Debe haber 3 materias sembradas")
    MateriaService.create({"codigo": "GEN-120", "nombre": "Física", "escuela": "Escuelas Generales",
                           "semestre": 2, "estado": "ACTIVA", "edicion_id": ED})
    try:
        MateriaService.create({"codigo": "SIS-101", "nombre": "Otra", "edicion_id": ED})
        afirmar(False, "Repetir el código de materia en la edición debe fallar")
    except ValueError as exc:
        afirmar("ya existe en esta edición" in str(exc), f"Mensaje inesperado: {exc}")
    # Mismo código en otra edición permitido.
    MateriaService.create({"codigo": "SIS-101", "nombre": "Programación I (base)", "edicion_id": 1})
    print("MATERIAS_UNIQUE_OK")


# ===========================================================================
# 3. Choque de laboratorio (puntual) y adyacencia
# ===========================================================================
def test_choque_laboratorio_puntual():
    lab = id_lab_ed2("LAB-02")   # capacidad 30
    profe = crear_estudiante("V-P31-PROFE")   # estudiante: aísla el choque de LABORATORIO
    f = fecha_futura_en(2)       # un miércoles futuro
    crear_puntual(lab, profe, f, "08:00", 70, periodo="2026-2")  # 08:00-09:10

    try:
        crear_puntual(lab, profe, f, "09:09", 70, periodo="2026-2")
        afirmar(False, "Un minuto de solapamiento debe rechazarse")
    except ReservaInvalida as exc:
        afirmar("superpone" in str(exc).lower(), f"Mensaje inesperado: {exc}")

    # Adyacente exacto: 09:10 → permitido.
    crear_puntual(lab, profe, f, "09:10", 70, periodo="2026-2")

    # Otro laboratorio, misma hora → permitido (no es choque de laboratorio).
    lab2 = id_lab_ed2("LAB-03")
    crear_puntual(lab2, profe, f, "08:00", 70, periodo="2026-2")
    print("CHOQUE_LABORATORIO_PUNTUAL_OK")


# ===========================================================================
# 4. Choque de profesor (solo PROFESOR) entre dos laboratorios
# ===========================================================================
def test_choque_profesor():
    lab_a = id_lab_ed2("LAB-02")
    lab_b = id_lab_ed2("LAB-03")
    profe = crear_profesor("V-PROFE-A")
    estudiante = crear_estudiante("V-ESTU-A")
    f = fecha_futura_en(3)  # jueves futuro

    # Base en LAB-02.
    crear_puntual(lab_a, profe, f, "10:00", 70, periodo="2026-2")
    # Mismo PROFESOR en otro laboratorio y misma franja → choque de profesor.
    try:
        crear_puntual(lab_b, profe, f, "10:30", 35, periodo="2026-2")
        afirmar(False, "Un profesor en dos laboratorios a la misma hora debe ser rechazado")
    except ReservaInvalida as exc:
        afirmar("profesor" in str(exc).lower(), f"Mensaje inesperado: {exc}")

    # Un ESTUDIANTE en dos laboratorios a la misma hora: permitido.
    crear_puntual(lab_a, estudiante, f, "12:00", 70, periodo="2026-2")
    crear_puntual(lab_b, estudiante, f, "12:00", 70, periodo="2026-2")
    print("CHOQUE_PROFESOR_OK")


# ===========================================================================
# 5. Cruce puntual ↔ semestral y semestral ↔ semestral
# ===========================================================================
def test_cruce_semestral():
    lab = id_lab_ed2("LAB-03")   # capacidad 40, sin choques con la semilla
    profe_s = crear_profesor("V-PROFE-S")     # responsable de la semestral
    estudiante = crear_estudiante("V-ESTU-S")

    # Asignación semestral: lunes (0), 10:00-11:10.
    crear_semestral(lab, profe_s, 0, "10:00", 70, periodo="2026-2")

    # Otra semestral mismo día+periodo+lab, solapada → choque.
    try:
        crear_semestral(lab, crear_profesor("V-PROFE-S2"), 0, "10:30", 70, periodo="2026-2")
        afirmar(False, "Semestral vs semestral (mismo día) debe chocar")
    except ReservaInvalida:
        pass
    # Mismo día pero otro día de la semana (martes) → permitido.
    crear_semestral(lab, crear_profesor("V-PROFE-S3"), 1, "10:00", 70, periodo="2026-2")

    # Puntual un lunes (weekday 0), mismo periodo, solapada → choque con la semestral.
    lunes = fecha_futura_en(0)
    try:
        crear_puntual(lab, estudiante, lunes, "10:30", 70, periodo="2026-2")
        afirmar(False, "Una puntual en el día de la semestral debe chocar")
    except ReservaInvalida as exc:
        afirmar("superpone" in str(exc).lower(), f"Mensaje inesperado: {exc}")

    # Misma puntual pero EN OTRO PERIODO → permitido (el periodo no coincide).
    crear_puntual(lab, estudiante, lunes, "10:30", 70, periodo="2027-1")

    # Misma hora pero OTRO día de la semana (martes), en franja libre → permitido.
    martes = fecha_futura_en(1)
    crear_puntual(lab, estudiante, martes, "15:00", 70, periodo="2026-2")
    print("CRUCE_SEMESTRAL_OK")


# ===========================================================================
# 6. Validación de capacidad con laboratorios alternativos
# ===========================================================================
def test_capacidad_y_sugerencias():
    lab20 = id_lab_ed2("LAB-01")   # capacidad 20
    profe = crear_profesor("V-CAP-PROFE")
    f = fecha_futura_en(4)         # viernes futuro

    # 25 estudiantes exceden la capacidad 20 → rechazo con alternativas.
    capturado = None
    try:
        crear_puntual(lab20, profe, f, "07:00", 70, periodo="2026-2", cantidad=25)
    except ReservaInvalida as exc:
        capturado = exc
    afirmar(capturado is not None, "Debe rechazarse por capacidad")
    afirmar("supera la capacidad" in str(capturado).lower(),
            f"Mensaje inesperado: {capturado}")
    codigos_alt = {a["codigo"] for a in capturado.sugerencias}
    afirmar("LAB-01" not in codigos_alt, "El laboratorio sin cupo no debe sugerirse a sí mismo")
    afirmar(codigos_alt >= {"LAB-02", "LAB-03"},
            f"Debe sugerir laboratorios con cupo (sugirió {codigos_alt})")

    # La cantidad puede tomarse de la sección (cantidad_estimada).
    seccion_id = SeccionService.create(
        {"codigo_seccion": "SB", "semestre": 1, "periodo_academico": "2026-2",
         "carrera_o_escuela": "Escuela de Sistemas", "cantidad_estimada": 35,
         "estado": "ACTIVA", "edicion_id": ED})
    try:
        crear_puntual(lab20, profe, f, "08:00", 70, periodo="2026-2", seccion=seccion_id)
        afirmar(False, "La cantidad estimada de la sección debe validarse contra la capacidad")
    except ReservaInvalida as exc:
        afirmar("35" in str(exc), f"Debe mencionar la cantidad (35): {exc}")

    # Cantidad que sí cabe → permitida.
    crear_puntual(lab20, profe, f, "16:00", 70, periodo="2026-2", cantidad=20)
    print("CAPACIDAD_Y_SUGERENCIAS_OK")


# ===========================================================================
# 7. Normalización de horas ('9:30' == '09:30')
# ===========================================================================
def test_normalizacion_horas():
    # Laboratorio propio para no interferir con las reservas de otros tests.
    lab = LaboratorioService.create({
        "codigo": "LAB-NORM", "nombre": "Lab normalización", "ubicacion": "Aula Norm",
        "capacidad": 30, "duracion_estandar_minutos": 70, "estado": "DISPONIBLE",
        "edicion_id": ED,
    })
    estudiante = crear_estudiante("V-NORM-ESTU")
    f = fecha_futura_en(2)  # miércoles
    crear_puntual(lab, estudiante, f, "09:00", 70, periodo="2026-2")  # 09:00-10:20

    # '9:30' sin cero a la izquierda debe interpretarse como 09:30 y chocar con 09:00-10:20.
    # (La comparación textual antigua NO detectaba este solapamiento.)
    try:
        crear_puntual(lab, estudiante, f, "9:30", 30, periodo="2026-2")
        afirmar(False, "'9:30' debe normalizarse a 09:30 y detectar el solapamiento")
    except ReservaInvalida:
        pass
    print("NORMALIZACION_HORAS_OK")


# ===========================================================================
# 8. Snapshot / restore de versiones con secciones y materias
# ===========================================================================
def test_snapshot_restore():
    seccion_id = SeccionService.create(
        {"codigo_seccion": "SC", "semestre": 5, "periodo_academico": "2026-2",
         "carrera_o_escuela": "Escuela de Sistemas", "estado": "ACTIVA", "edicion_id": ED})
    materia_id = MateriaService.create(
        {"codigo": "SC-500", "nombre": "Materia snapshot", "edicion_id": ED, "estado": "ACTIVA"})

    version = EdicionService.crear_version(ED, "ConSecciones", "Snapshot con secciones/materias", UID)
    version_id = next(v["id"] for v in EdicionService.listar_versiones(ED)
                      if v["numero_version"] == version)

    # El snapshot debe incluir las secciones y materias.
    with database.get_connection() as db:
        raw = db.execute("SELECT snapshot_json FROM edicion_versiones WHERE id=?",
                         (version_id,)).fetchone()["snapshot_json"]
    snap = json.loads(raw)
    afirmar("secciones" in snap and "materias" in snap, "El snapshot debe incluir secciones y materias")

    # Mutar: eliminar seccion y materia.
    SeccionService.delete(seccion_id)
    MateriaService.delete(materia_id)
    afirmar(SeccionService.get(seccion_id) is None, "La sección debe estar borrada antes de restaurar")

    # Restaurar: reaparecen con el MISMO id.
    EdicionService.restaurar_version(version_id)
    afirmar(SeccionService.get(seccion_id) is not None, "La sección debe restaurarse")
    afirmar(SeccionService.get(seccion_id)["id"] == seccion_id, "El id de la sección debe preservarse")
    afirmar(MateriaService.get(materia_id) is not None, "La materia debe restaurarse")

    with database.get_connection() as db:
        vactual = db.execute("SELECT version_actual FROM ediciones WHERE id=?",
                             (ED,)).fetchone()["version_actual"]
    afirmar(vactual == version, "Restaurar debe actualizar la versión activa")
    print("SNAPSHOT_RESTORE_OK")


# ===========================================================================
# 9. Aislamiento por edición y bloques horarios configurables
# ===========================================================================
def test_aislamiento_y_bloques():
    # Reservas en distintas ediciones no chocan aunque compartan fecha/hora.
    with database.get_connection() as db:
        lab1 = db.execute("SELECT id FROM laboratorios WHERE edicion_id=1 ORDER BY id LIMIT 1").fetchone()["id"]
        prest1 = db.execute("SELECT id FROM prestatarios WHERE edicion_id=1 ORDER BY id LIMIT 1").fetchone()["id"]
    f = fecha_futura_en(2)
    ReservationService.create_reservation(lab1, prest1, UID, f, "07:00", 70, "",
                                          edicion_id=1, tipo_reserva="PUNTUAL")
    # Laboratorio propio de la edición 2, MISMA fecha/hora que la de la edición 1:
    # al ser otra edición, no debe chocar.
    lab2propio = LaboratorioService.create({
        "codigo": "LAB-ISO", "nombre": "Lab aislamiento", "ubicacion": "Aula Iso",
        "capacidad": 30, "duracion_estandar_minutos": 70, "estado": "DISPONIBLE",
        "edicion_id": ED,
    })
    ReservationService.create_reservation(lab2propio, crear_estudiante("V-ISO-ESTU"),
                                          UID, f, "07:00", 70, "",
                                          edicion_id=ED, tipo_reserva="PUNTUAL")

    # Bloques por defecto (no hay configuración todavía): 70 min desde 07:00.
    bloques = obtener_bloques_edicion(ED)
    afirmar(bloques and bloques[0][0] == 7 * 60, "El primer bloque por defecto empieza a las 07:00")
    afirmar(all(fin - ini == 70 for ini, fin in bloques), "Los bloques por defecto son de 70 min")

    # Configurar bloques y comprobar que se leen desde edicion_configuracion.
    EdicionService.guardar_config(ED, "bloques_horarios", json.dumps(["07:00-08:40", "08:40-10:20"]))
    bloques_cfg = obtener_bloques_edicion(ED)
    afirmar(bloques_cfg == [(7 * 60, 8 * 60 + 40), (8 * 60 + 40, 10 * 60 + 20)],
            f"Bloques configurados incorrectos: {bloques_cfg}")
    print("AISLAMIENTO_Y_BLOQUES_OK")


# ===========================================================================
# 10. Integración web: listados, alta de sección y rechazo por capacidad
# ===========================================================================
def _login(cliente, username="admin", password="Admin123!"):
    cliente.get("/login")
    tok = re.search(r'name="_csrf_token" value="([^"]+)"',
                    cliente.get("/login").get_data(as_text=True)).group(1)
    return cliente.post("/login", data={"_csrf_token": tok, "username": username, "password": password})


def _csrf(cliente, ruta):
    return re.search(r'name="_csrf_token" value="([^"]+)"',
                     cliente.get(ruta).get_data(as_text=True)).group(1)


def test_rutas_web():
    cliente = app.test_client()
    _login(cliente)
    # Cambiar a la edición IUTEPI LABS (id 2).
    cliente.post("/ediciones/cambiar",
                 data={"_csrf_token": _csrf(cliente, "/panel"), "edicion_id": str(ED)},
                 follow_redirects=True)

    afirmar(cliente.get("/secciones").status_code == 200, "GET /secciones debe responder 200")
    afirmar("SA-A" in cliente.get("/secciones").get_data(as_text=True),
            "El listado de secciones debe mostrar la subsección SA-A")
    afirmar(cliente.get("/materias").status_code == 200, "GET /materias debe responder 200")
    afirmar("SIS-101" in cliente.get("/materias").get_data(as_text=True),
            "El listado de materias debe mostrar SIS-101")

    # El formulario de reserva ofrece el conmutador y los desplegables filtrados.
    form = cliente.get("/reservas/crear").get_data(as_text=True)
    afirmar("tipo_reserva" in form and "dia_semana" in form, "El formulario debe tener tipo y día de semana")
    afirmar('name="seccion_id"' in form and 'name="materia_id"' in form,
            "El formulario debe ofrecer sección y materia")
    afirmar("grupo-semestral" in form, "Debe existir el grupo condicional semestral")

    # Alta de sección por la web.
    r = cliente.post("/secciones/crear",
                     data={"_csrf_token": _csrf(cliente, "/secciones/crear"),
                           "codigo_seccion": "SD", "semestre": "6", "periodo_academico": "2026-2",
                           "carrera_o_escuela": "Escuela de Sistemas", "estado": "ACTIVA"},
                     follow_redirects=True)
    afirmar("SD" in r.get_data(as_text=True), "La sección creada debe aparecer en el listado")

    # Rechazo por capacidad vía web, mostrando laboratorios alternativos.
    lab20 = id_lab_ed2("LAB-01")
    profe = crear_profesor("V-WEB-PROFE")
    r = cliente.post("/reservas/crear",
                     data={"_csrf_token": _csrf(cliente, "/reservas/crear"),
                           "laboratorio_id": str(lab20), "prestatario_id": str(profe),
                           "fecha": fecha_futura_en(2), "hora_inicio": "18:00",
                           "duracion_minutos": "70", "tipo_reserva": "PUNTUAL",
                           "periodo_academico": "2026-2", "cantidad_estudiantes": "45"},
                     follow_redirects=False)
    cuerpo = r.get_data(as_text=True)
    afirmar(r.status_code == 400, f"El rechazo por capacidad debe devolver 400 (fue {r.status_code})")
    afirmar("capacidad" in cuerpo.lower(), "Debe explicarse el rechazo por capacidad")
    afirmar("LAB-03" in cuerpo, "Deben listarse laboratorios alternativos con cupo")
    print("RUTAS_WEB_OK")


# ===========================================================================
def main():
    print(f"Base de datos de prueba: {_RUTA}")
    test_secciones_unique_y_validacion()
    test_materias_unique()
    test_choque_laboratorio_puntual()
    test_choque_profesor()
    test_cruce_semestral()
    test_capacidad_y_sugerencias()
    test_normalizacion_horas()
    test_snapshot_restore()
    test_aislamiento_y_bloques()
    test_rutas_web()
    print("FASE2_SECCIONES_HORARIOS_OK")


if __name__ == "__main__":
    main()
