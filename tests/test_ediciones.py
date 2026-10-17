"""Pruebas de la capa multi-edición de TechLoan (Fase 1).

Cubre:
- El context processor que expone ``edicion_actual`` y ``ediciones_disponibles``
  y dibuja el selector de edición en la barra (``/ediciones/cambiar``).
- El panel de ediciones (solo ADMINISTRADOR), la landing pública por slug y el
  panel de configuración (preferencias y versiones).
- El aislamiento de datos por ``edicion_id``: lo que se crea en una edición no
  aparece en la otra, en los listados, en la exportación ni al crear.
- La restricción UNIQUE compuesta ``(edicion_id, ...)``: el mismo código/cédula
  puede repetirse entre ediciones pero no dentro de la misma.
- El servicio de versiones: snapshot con los id preservados y restauración.

Las pruebas corren contra una base de datos temporal construida desde
``schema.sql``; nunca tocan ``database/techloan.db``.

Uso::

    PYTHONPATH=. python tests/test_ediciones.py
"""

import re
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import _tempdb

_RUTA = _tempdb.preparar("test_ediciones.db")

import app.database as database  # noqa: E402
from app.server import create_app  # noqa: E402
from app.services.edicion_service import EdicionService  # noqa: E402
from app.services.prestatario_service import PrestatarioService  # noqa: E402

app = create_app()


# ---------------------------------------------------------------------------
# Utilidades (mismo patrón que tests/test_web_phase6.py)
# ---------------------------------------------------------------------------
def token_csrf(cliente, ruta):
    respuesta = cliente.get(ruta)
    coincidencia = re.search(
        r'name="_csrf_token" value="([^"]+)"', respuesta.get_data(as_text=True)
    )
    assert coincidencia, f"No se encontró el token CSRF en {ruta}"
    return coincidencia.group(1)


def entrar(cliente, username="admin", password="Admin123!"):
    token = token_csrf(cliente, "/login")
    return cliente.post(
        "/login",
        data={"_csrf_token": token, "username": username, "password": password},
    )


def publicar(cliente, ruta, datos, ruta_token=None, seguir=True):
    datos = dict(datos)
    datos["_csrf_token"] = token_csrf(cliente, ruta_token or ruta)
    return cliente.post(ruta, data=datos, follow_redirects=seguir)


def cambiar_edicion(cliente, edicion_id, ruta_token="/panel"):
    return publicar(
        cliente, "/ediciones/cambiar",
        {"edicion_id": str(edicion_id)},
        ruta_token=ruta_token, seguir=True,
    )


def texto(respuesta):
    return respuesta.get_data(as_text=True)


def afirmar(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)


# ===========================================================================
# 1. Context processor y selector de edición
# ===========================================================================
def test_context_processor_y_selector():
    cliente = app.test_client()
    entrar(cliente, "admin", "Admin123!")

    html = texto(cliente.get("/panel"))
    # El administrador pertenece a dos ediciones ⇒ debe ver el selector.
    afirmar("selector-edicion" in html, "El administrador debe ver el selector de edición")
    afirmar("/ediciones/cambiar" in html, "El selector debe publicar en /ediciones/cambiar")
    afirmar("TechLoan Base" in html and "IUTEPI LABS" in html,
            "El selector debe ofrecer las dos ediciones sembradas")

    # La edición activa por defecto es la primera (base, id=1).
    with cliente.session_transaction() as sesion:
        afirmar(sesion.get("edicion_id", 1) == 1,
                "La edición por defecto debe ser la base (id 1)")

    print("EDICIONES_CONTEXT_OK")


# ===========================================================================
# 2. Cambiar de edición (POST) y aislamiento del listado de prestatarios
# ===========================================================================
def test_cambiar_edicion_y_aislamiento():
    cliente = app.test_client()
    entrar(cliente, "admin", "Admin123!")

    # En la edición base aparecen los prestatarios sembrados.
    base = texto(cliente.get("/prestatarios"))
    afirmar("V-12345678" in base, "La edición base debe mostrar sus prestatarios")

    # Cambiar a IUTEPI LABS (id 2): los datos de la base no deben filtrarse.
    cambiar_edicion(cliente, 2)
    iutepi = texto(cliente.get("/prestatarios"))
    afirmar("V-12345678" not in iutepi,
            "Los prestatarios de la edición base NO deben aparecer en IUTEPI LABS")

    # Crear un prestatario en IUTEPI LABS: debe quedar con edicion_id=2.
    datos = {
        "cedula": "V-20999999", "nombre": "Edicion", "apellido": "Dos",
        "tipo": "ESTUDIANTE", "telefono": "0414-2099999",
        "email": "edicion.dos@correo.com", "estado": "ACTIVO",
    }
    publicar(cliente, "/prestatarios/crear", datos, ruta_token="/prestatarios/crear")

    with database.get_connection() as db:
        fila = db.execute(
            "SELECT edicion_id FROM prestatarios WHERE cedula=?", ("V-20999999",)
        ).fetchone()
    afirmar(fila is not None, "El prestatario debe existir en la base de datos")
    afirmar(fila["edicion_id"] == 2,
            f"El prestatario creado debe pertenecer a la edición 2 (fue {fila['edicion_id']})")

    iutepi = texto(cliente.get("/prestatarios"))
    afirmar("V-20999999" in iutepi, "El nuevo prestatario debe aparecer en IUTEPI LABS")

    # Volver a la base: el prestatario de IUTEPI LABS ya no se ve.
    cambiar_edicion(cliente, 1)
    base = texto(cliente.get("/prestatarios"))
    afirmar("V-20999999" not in base,
            "El prestatario de IUTEPI LABS no debe aparecer en la edición base")
    afirmar("V-12345678" in base, "La base debe seguir mostrando sus propios datos")

    # Una edición a la que no se pertenece no se aplica (se ignora el cambio).
    cambiar_edicion(cliente, 999)
    with cliente.session_transaction() as sesion:
        afirmar(sesion.get("edicion_id") == 1,
                "Un id de edición inválido no debe cambiar la sesión")

    print("EDICIONES_CAMBIO_Y_AISLAMIENTO_OK")


# ===========================================================================
# 3. Exportación CSV también respeta la edición activa
# ===========================================================================
def test_exportacion_por_edicion():
    cliente = app.test_client()
    entrar(cliente, "admin", "Admin123!")

    cambiar_edicion(cliente, 2)
    csv = cliente.get("/prestatarios/exportar")
    cuerpo = csv.get_data(as_text=True)
    afirmar(csv.status_code == 200, "La exportación debe responder 200")
    afirmar("V-20999999" in cuerpo, "La exportación debe incluir el dato de la edición 2")
    afirmar("V-12345678" not in cuerpo,
            "La exportación no debe filtrar datos de otra edición")

    print("EDICIONES_EXPORTACION_OK")


# ===========================================================================
# 4. UNIQUE compuesta por edición (servicio)
# ===========================================================================
def test_unique_compuesta():
    # Mismo «cedula» en ediciones distintas: permitido.
    comun = {"nombre": "Misma", "apellido": "Persona", "tipo": "PROFESOR",
             "telefono": None, "email": None, "estado": "ACTIVO"}
    id_ed1 = PrestatarioService.create(dict(comun, cedula="V-ED-UNICA", edicion_id=1))
    id_ed2 = PrestatarioService.create(dict(comun, cedula="V-ED-UNICA", edicion_id=2))
    afirmar(id_ed1 != id_ed2, "La misma cédula debe poder existir en dos ediciones")

    # Repetir dentro de la MISMA edición: rechazado con mensaje amable.
    try:
        PrestatarioService.create(dict(comun, cedula="V-ED-UNICA", edicion_id=1))
        afirmar(False, "Duplicar la cédula en la misma edición debe fallar")
    except ValueError as exc:
        afirmar("ya está registrada" in str(exc),
                f"El mensaje debe explicar el duplicado por edición: {exc}")

    print("EDICIONES_UNIQUE_COMPUESTA_OK")


# ===========================================================================
# 5. Panel de ediciones: permisos
# ===========================================================================
def test_panel_permisos():
    # Administrador: 200 y con las dos ediciones.
    cliente = app.test_client()
    entrar(cliente, "admin", "Admin123!")
    r = cliente.get("/ediciones")
    afirmar(r.status_code == 200, "El administrador debe ver el panel de ediciones")
    html = texto(r)
    afirmar("TechLoan Base" in html and "IUTEPI LABS" in html, "Deben listarse las ediciones")
    afirmar("iutepi-labs" in html, "Debe mostrarse el slug de la edición")

    # Operador: el módulo de ediciones es de administración ⇒ redirige (302).
    op = app.test_client()
    entrar(op, "operador", "Operador123!")
    r = op.get("/ediciones", follow_redirects=False)
    afirmar(r.status_code == 302, "El operador no debe gestionar ediciones")

    print("EDICIONES_PERMISOS_OK")


# ===========================================================================
# 6. Landing pública por slug
# ===========================================================================
def test_landing():
    cliente = app.test_client()
    entrar(cliente, "admin", "Admin123!")

    r = cliente.get("/ediciones/iutepi-labs")
    afirmar(r.status_code == 200, "La landing de una edición debe responder 200")
    afirmar("IUTEPI LABS" in texto(r), "La landing debe mostrar el nombre de la edición")

    r = cliente.get("/ediciones/slug-que-no-existe", follow_redirects=False)
    afirmar(r.status_code == 302, "Un slug inexistente debe redirigir")

    print("EDICIONES_LANDING_OK")


# ===========================================================================
# 7. Configuración: lectura, guardado y control de versiones
# ===========================================================================
def test_configuracion_y_versiones():
    cliente = app.test_client()
    entrar(cliente, "admin", "Admin123!")

    # GET del panel de configuración de la edición base.
    r = cliente.get("/ediciones/base/configuracion")
    afirmar(r.status_code == 200, "El panel de configuración debe responder 200")
    html = texto(r)
    afirmar("Guardar configuración" in html, "El administrador debe poder guardar")
    afirmar("periodo_academico" in html, "Debe ofrecerse el campo de periodo académico")

    # Guardar preferencias (POST).
    publicar(
        cliente, "/ediciones/base/configuracion",
        {"accion": "guardar_config", "periodo_academico": "2026-2",
         "bloques_horarios": '["07:00-08:10"]'},
        ruta_token="/ediciones/base/configuracion",
    )
    config = EdicionService.obtener_config(1)
    afirmar(config.get("periodo_academico") == "2026-2",
            "La configuración debe quedar guardada")
    afirmar(config.get("bloques_horarios") == '["07:00-08:10"]',
            "Los bloques horarios deben quedar guardados")

    # Crear una versión a partir del estado actual.
    publicar(
        cliente, "/ediciones/base/configuracion",
        {"accion": "crear_version", "notas_cambios": "Tras guardar configuración"},
        ruta_token="/ediciones/base/configuracion",
    )
    versiones = EdicionService.listar_versiones(1)
    afirmar(any(v["numero_version"] == 2 for v in versiones),
            "Debe existir una versión 2 creada desde la interfaz")
    v2 = next(v for v in versiones if v["numero_version"] == 2)
    # El snapshot debe conservar la configuración guardada.
    import json
    snap = json.loads(v2["snapshot_json"])
    afirmar(snap.get("configuracion", {}).get("periodo_academico") == "2026-2",
            "El snapshot debe incluir la configuración vigente")

    print("EDICIONES_CONFIG_OK")


# ===========================================================================
# 8. Operador puede LEER la configuración pero NO modificarla
# ===========================================================================
def test_config_operador_solo_lectura():
    cliente = app.test_client()
    entrar(cliente, "operador", "Operador123!")

    r = cliente.get("/ediciones/base/configuracion")
    afirmar(r.status_code == 200, "El operador puede ver la configuración")
    html = texto(r)
    afirmar("Guardar configuración" not in html,
            "El operador no debe ver el botón de guardar")

    # Aunque fuerce el POST, la escritura debe impedirse.
    publicar(
        cliente, "/ediciones/base/configuracion",
        {"accion": "guardar_config", "periodo_academico": "HACKEADO"},
        ruta_token="/ediciones/base/configuracion",
    )
    config = EdicionService.obtener_config(1)
    afirmar(config.get("periodo_academico") != "HACKEADO",
            "El operador no debe poder modificar la configuración")

    print("EDICIONES_CONFIG_OPERADOR_OK")


# ===========================================================================
# 9. Servicio de versiones: snapshot con id preservado y restauración
# ===========================================================================
def test_restaurar_version_preserva_ids():
    # Crear un prestatario en la edición base y tomar una versión.
    pid = PrestatarioService.create(
        {"cedula": "V-SNAP-0001", "nombre": "Snapshot", "apellido": "Prueba",
         "tipo": "ESTUDIANTE", "estado": "ACTIVO", "edicion_id": 1}
    )
    EdicionService.guardar_config(1, "marca", "valor-original")
    numero = EdicionService.crear_version(1, "ConSnapshot", "Estado a conservar", 1)

    version_id = next(
        v["id"] for v in EdicionService.listar_versiones(1)
        if v["numero_version"] == numero
    )

    # Mutar el estado: borrar el prestatario y cambiar la configuración.
    PrestatarioService.delete(pid)
    EdicionService.guardar_config(1, "marca", "valor-modificado")

    # Restaurar la versión: el prestatario debe reaparecer con EL MISMO id.
    EdicionService.restaurar_version(version_id)

    with database.get_connection() as db:
        fila = db.execute(
            "SELECT id FROM prestatarios WHERE cedula=?", ("V-SNAP-0001",)
        ).fetchone()
        version_actual = db.execute(
            "SELECT version_actual FROM ediciones WHERE id=1"
        ).fetchone()["version_actual"]

    afirmar(fila is not None, "La restauración debe devolver el prestatario borrado")
    afirmar(fila["id"] == pid,
            f"El id debe preservarse tras restaurar (esperado {pid}, fue {fila['id']})")
    afirmar(version_actual == numero,
            "Al restaurar debe actualizarse la versión activa de la edición")
    afirmar(EdicionService.obtener_config(1).get("marca") == "valor-original",
            "La configuración debe volver al estado de la versión restaurada")

    print("EDICIONES_RESTAURAR_OK")


# ===========================================================================
# Ejecución
# ===========================================================================
def main():
    print(f"Base de datos de prueba: {_RUTA}")
    test_context_processor_y_selector()
    test_cambiar_edicion_y_aislamiento()
    test_exportacion_por_edicion()
    test_unique_compuesta()
    test_panel_permisos()
    test_landing()
    test_configuracion_y_versiones()
    test_config_operador_solo_lectura()
    test_restaurar_version_preserva_ids()
    print("EDICIONES_PRUEBA_COMPLETA_OK")


if __name__ == "__main__":
    main()
