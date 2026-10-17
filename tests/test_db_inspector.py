"""Pruebas del Visor Técnico SQLite3 (Fase 1).

Cubre el servicio de solo lectura ``DBInspectorService`` (listado de tablas,
conteo, previsualización con filtro por edición, desglose de hash y enmascarado
de tokens) y sus rutas web (``/sistema/visor-sqlite``), incluyendo que el
OPERADOR no puede acceder.

Corren contra una base de datos temporal construida desde ``schema.sql``; nunca
tocan ``database/techloan.db``.

Uso::

    PYTHONPATH=. python tests/test_db_inspector.py
"""

import re
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import _tempdb

_RUTA = _tempdb.preparar("test_inspector.db")

import app.database as database  # noqa: E402
from app.server import create_app  # noqa: E402
from app.services.db_inspector_service import DBInspectorService  # noqa: E402

app = create_app()


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


def afirmar(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)


# ===========================================================================
# 1. Servicio: tablas y conteos
# ===========================================================================
def test_servicio_tablas_y_conteos():
    nombres = {t["name"] for t in DBInspectorService.listar_tablas()}
    for esperada in ("usuarios_sistema", "ediciones", "edicion_versiones",
                     "prestatarios", "laboratorios", "equipos"):
        afirmar(esperada in nombres, f"Debe listarse la tabla «{esperada}»")

    afirmar(DBInspectorService.contar_registros("ediciones") == 2,
            "Debe haber dos ediciones sembradas")
    # El conteo es global (todas las ediciones): el seed añadió prestatarios a
    # IUTEPI LABS. La cuenta de la edición base se verifica en la previsualización.
    afirmar(DBInspectorService.contar_registros("prestatarios") >= 4,
            "Debe haber al menos los 4 prestatarios de la edición base")

    try:
        DBInspectorService.contar_registros("tabla_inexistente")
        afirmar(False, "Contar una tabla inexistente debe fallar")
    except ValueError:
        pass

    print("INSPECTOR_TABLAS_OK")


# ===========================================================================
# 2. Servicio: previsualización con filtro por edición
# ===========================================================================
def test_servicio_previsualizar_por_edicion():
    # Edición base (1): 4 prestatarios sembrados.
    base = DBInspectorService.previsualizar("prestatarios", edicion_id=1)
    afirmar(len(base["filas"]) == 4, "La edición base tiene 4 prestatarios")
    afirmar("edicion_id" in base["columnas"], "Debe exponerse la columna edicion_id")

    # IUTEPI LABS (2): la semilla de Fase 2 añadió 2 profesores.
    iutepi = DBInspectorService.previsualizar("prestatarios", edicion_id=2)
    afirmar(len(iutepi["filas"]) == 2,
            f"IUTEPI LABS debe tener 2 prestatarios sembrados (tuvo {len(iutepi['filas'])})")

    # Tabla global (categorias): sin columna edicion_id ⇒ el filtro se ignora.
    cats = DBInspectorService.previsualizar("categorias", edicion_id=2)
    afirmar(len(cats["filas"]) == 3,
            "Las categorías son globales: el filtro de edición no debe aplicarse")
    afirmar("edicion_id" not in cats["columnas"],
            "categorias no debe exponer edicion_id")

    try:
        DBInspectorService.previsualizar("tabla_inexistente")
        afirmar(False, "Previsualizar una tabla inexistente debe fallar")
    except ValueError:
        pass

    print("INSPECTOR_PREVISUALIZAR_OK")


# ===========================================================================
# 3. Servicio: enmascarado de tokens y desglose de hash
# ===========================================================================
def test_servicio_tokens_y_hash():
    # Insertar un token y comprobar que se enmascara en la previsualización.
    with database.get_connection() as db:
        db.execute(
            """INSERT INTO tokens_correo (usuario_id, token, tipo, fecha_expiracion)
               VALUES (1, 'abcdef1234567890SECRETO', 'CONFIRMACION', '2027-01-01')"""
        )
    prev = DBInspectorService.previsualizar("tokens_correo")
    afirmar(len(prev["filas"]) >= 1, "Debe previsualizarse el token insertado")
    token_visto = prev["filas"][0]["token"]
    afirmar(token_visto.startswith("abcdef12") and token_visto.endswith("..."),
            f"El token debe enmascararse (se vio «{token_visto}»)")
    afirmar("SECRETO" not in token_visto, "El token completo no debe exponerse")

    # Desglose del hash scrypt de admin.
    usuarios = DBInspectorService.obtener_usuarios_con_hash()
    admin = next(u for u in usuarios if u["rol"] == "ADMINISTRADOR")
    desglose = DBInspectorService.desglosar_hash(admin["password_hash"])
    afirmar(desglose["algoritmo"] == "scrypt",
            f"El algoritmo debe ser scrypt (fue {desglose['algoritmo']})")
    afirmar(desglose["parametros"] == "32768:8:1",
            f"Los parámetros deben parsearse (fueron {desglose['parametros']})")
    afirmar(desglose["salt"] and desglose["hash"], "Deben aislarse salt y hash")

    # Un hash con formato no reconocido devuelve error, no explosión.
    afirmar("error" in DBInspectorService.desglosar_hash("basura"),
            "Un hash inválido debe devolver error")

    # El hash generado es scrypt y el salt es aleatorio (dos llamadas distintas).
    h1 = DBInspectorService.generar_hash_demo("Clave123!")
    h2 = DBInspectorService.generar_hash_demo("Clave123!")
    afirmar(h1 != h2, "El salt aleatorio debe producir hashes distintos")
    afirmar(DBInspectorService.desglosar_hash(h1)["algoritmo"] == "scrypt",
            "El hash de demostración debe ser scrypt")

    print("INSPECTOR_TOKENS_HASH_OK")


# ===========================================================================
# 4. Rutas web: administrador
# ===========================================================================
def test_rutas_admin():
    cliente = app.test_client()
    entrar(cliente, "admin", "Admin123!")

    afirmar(cliente.get("/sistema/visor-sqlite").status_code == 200,
            "El administrador debe ver el visor")

    usuarios = cliente.get("/sistema/visor-sqlite/usuarios").get_json()
    afirmar("usuarios" in usuarios and len(usuarios["usuarios"]) >= 2,
            "El endpoint de usuarios debe devolver los usuarios")
    afirmar("desglose" in usuarios["usuarios"][0],
            "Cada usuario debe traer el desglose de su hash")

    tablas = cliente.get("/sistema/visor-sqlite/tablas").get_json()
    afirmar(any(t["name"] == "prestatarios" for t in tablas["tablas"]),
            "Debe listarse la tabla de prestatarios")
    prestatarios = next(t for t in tablas["tablas"] if t["name"] == "prestatarios")
    afirmar(prestatarios["registros"] >= 4,
            "El conteo de prestatarios debe ser al menos 4 (edición base)")

    preview = cliente.get("/sistema/visor-sqlite/tablas/prestatarios?edicion_id=1").get_json()
    afirmar(len(preview["filas"]) == 4, "La previsualización filtrada debe dar 4 filas")

    # Probar hash por POST.
    token = token_csrf(cliente, "/sistema/visor-sqlite")
    r = cliente.post(
        "/sistema/visor-sqlite/probar-hash",
        data={"_csrf_token": token, "password": "Prueba123!"},
    )
    datos = r.get_json()
    afirmar(r.status_code == 200 and datos["hash"].startswith("scrypt:"),
            "Probar hash debe devolver un hash scrypt")

    print("INSPECTOR_RUTAS_ADMIN_OK")


# ===========================================================================
# 5. Rutas web: tabla inexistente → 400 JSON, y operador bloqueado
# ===========================================================================
def test_rutas_errores_y_permisos():
    cliente = app.test_client()
    entrar(cliente, "admin", "Admin123!")

    r = cliente.get("/sistema/visor-sqlite/tablas/que_no_existe")
    afirmar(r.status_code == 400, "Una tabla inexistente debe devolver 400")
    afirmar("error" in r.get_json(), "El 400 debe explicarse en JSON")

    # Operador: sin permiso sistema.inspector ⇒ redirige, no ve el visor.
    op = app.test_client()
    entrar(op, "operador", "Operador123!")
    r = op.get("/sistema/visor-sqlite", follow_redirects=False)
    afirmar(r.status_code == 302, "El operador no debe acceder al visor")
    r = op.get("/sistema/visor-sqlite/usuarios", follow_redirects=False)
    afirmar(r.status_code == 302, "El operador tampoco debe consultar usuarios con hash")

    print("INSPECTOR_ERRORES_PERMISOS_OK")


# ===========================================================================
# Ejecución
# ===========================================================================
def main():
    print(f"Base de datos de prueba: {_RUTA}")
    test_servicio_tablas_y_conteos()
    test_servicio_previsualizar_por_edicion()
    test_servicio_tokens_y_hash()
    test_rutas_admin()
    test_rutas_errores_y_permisos()
    print("INSPECTOR_PRUEBA_COMPLETA_OK")


if __name__ == "__main__":
    main()
