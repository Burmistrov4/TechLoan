"""Pruebas del registro de usuarios con confirmación por correo.

Cubre el ciclo completo: alta, emisión del token, confirmación desde el enlace,
acceso con el correo y todos los caminos de error (contraseña débil, usuario o
correo repetido, token inválido, caducado y ya usado).

Se ejecuta contra una **base de datos temporal** y un buzón temporal, de modo que
nunca toca ``database/techloan.db`` ni deja mensajes en ``database/buzon/``.

Uso::

    PYTHONPATH=. python tests/test_registro_phase7.py
"""

import re
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import app.config as config  # noqa: E402
import app.database as database  # noqa: E402

# --- Entorno aislado --------------------------------------------------------
_TMP = Path(tempfile.mkdtemp(prefix="techloan_registro_test_"))
database.DATABASE_PATH = _TMP / "test_registro.db"
config.DATABASE_PATH = database.DATABASE_PATH
config.BUZON_DIR = _TMP / "buzon"

from init_db import init_database as cargar_esquema  # noqa: E402
from app.server import create_app  # noqa: E402
from app.services import correo_service, registro_service  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402

cargar_esquema(database.DATABASE_PATH)
app = create_app()


def afirmar(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)


def token_csrf(cliente, ruta):
    respuesta = cliente.get(ruta)
    coincidencia = re.search(
        r'name="_csrf_token" value="([^"]+)"', respuesta.get_data(as_text=True)
    )
    afirmar(coincidencia, f"No se encontró el token CSRF en {ruta}")
    return coincidencia.group(1)


def publicar(cliente, ruta, datos, ruta_token=None):
    cuerpo = dict(datos)
    cuerpo["_csrf_token"] = token_csrf(cliente, ruta_token or ruta)
    return cliente.post(ruta, data=cuerpo, follow_redirects=False)


def texto(respuesta):
    return respuesta.get_data(as_text=True)


# ===========================================================================
# 1. Alta y emisión del token
# ===========================================================================
def test_alta_y_token():
    cliente = app.test_client()

    respuesta = cliente.get("/registro")
    afirmar(respuesta.status_code == 200, "GET /registro debe responder 200")
    html = texto(respuesta)
    afirmar("Crear una cuenta" in html, "Debe mostrarse el formulario de alta")
    afirmar("Admin123" not in html, "El formulario no debe revelar credenciales")

    respuesta = publicar(cliente, "/registro", {
        "nombre": "Evelyn", "apellido": "Marcano",
        "username": "emarcano", "email": "evelyn.marcano@correo.com",
        "password": "ClaveSegura1!", "password_repetida": "ClaveSegura1!",
    })
    afirmar(respuesta.status_code == 200, f"El alta debe responder 200 (dio {respuesta.status_code})")
    html = texto(respuesta)
    afirmar("Revisa tu correo" in html, "Debe pedirse la confirmación por correo")
    afirmar("evelyn.marcano@correo.com" in html, "Debe mostrarse el correo destinatario")

    # El enlace de demostración aparece porque no hay SMTP configurado.
    afirmar(not correo_service.configurado(), "Sin SMTP, el servicio debe estar en modo demostración")
    coincidencia = re.search(r'href="([^"]*/confirmar/[^"]+)"', html)
    afirmar(coincidencia, "En modo demostración debe mostrarse el enlace de confirmación")
    enlace = coincidencia.group(1)

    # El mensaje quedó en el buzón local.
    archivos = list(config.BUZON_DIR.glob("*.txt"))
    afirmar(len(archivos) == 1, f"Debe guardarse un mensaje en el buzón (hay {len(archivos)})")
    contenido = archivos[0].read_text(encoding="utf-8")
    afirmar("Confirma tu correo" in contenido, "El mensaje debe pedir la confirmación")
    afirmar(enlace in contenido, "El mensaje debe incluir el enlace de confirmación")
    afirmar("MODO DEMOSTRACIÓN" in contenido,
            "El mensaje debe dejar claro que no salió por correo")

    # Estado en la base de datos: cuenta creada, sin confirmar, rol OPERADOR.
    with database.get_connection() as db:
        fila = db.execute(
            "SELECT id, rol, estado, email_confirmado FROM usuarios_sistema WHERE username = ?",
            ("emarcano",),
        ).fetchone()
        afirmar(fila is not None, "El usuario debe existir en la base de datos")
        afirmar(fila["email_confirmado"] == 0, "La cuenta debe nacer sin confirmar")
        afirmar(fila["rol"] == "OPERADOR", "El autoregistro solo puede crear operadores")
        afirmar(fila["estado"] == "ACTIVO", "La cuenta no confirmada no debe quedar inactiva")

        token = db.execute(
            "SELECT token, usado, fecha_expiracion FROM tokens_correo WHERE usuario_id = ?",
            (fila["id"],),
        ).fetchone()
        afirmar(token is not None, "Debe emitirse un token de confirmación")
        afirmar(token["usado"] == 0, "El token recién emitido no puede estar usado")
        afirmar(enlace.endswith(token["token"]), "El enlace debe llevar el token emitido")

    print("FASE7_ALTA_Y_TOKEN_OK")
    return enlace


# ===========================================================================
# 2. No se puede entrar sin confirmar
# ===========================================================================
def test_sin_confirmar_no_entra():
    cliente = app.test_client()

    respuesta = publicar(cliente, "/login", {
        "username": "evelyn.marcano@correo.com", "password": "ClaveSegura1!",
    })
    afirmar(respuesta.status_code == 401, "Sin confirmar el correo, el acceso debe rechazarse")
    afirmar("no está confirmada" in texto(respuesta),
            "Debe explicarse que la cuenta no está confirmada")

    # Por nombre de usuario ocurre lo mismo.
    respuesta = publicar(cliente, "/login", {
        "username": "emarcano", "password": "ClaveSegura1!",
    })
    afirmar(respuesta.status_code == 401, "El rechazo no depende de cómo se identifique")

    # Una contraseña incorrecta sigue dando el mensaje genérico.
    respuesta = publicar(cliente, "/login", {
        "username": "emarcano", "password": "OtraClave1!",
    })
    afirmar("Credenciales inválidas" in texto(respuesta),
            "Con contraseña incorrecta el mensaje debe ser genérico")

    print("FASE7_SIN_CONFIRMAR_NO_ENTRA_OK")


# ===========================================================================
# 3. Confirmación desde el enlace y acceso con el correo
# ===========================================================================
def test_confirmar_y_entrar(enlace):
    cliente = app.test_client()
    token = enlace.rsplit("/", 1)[-1]

    respuesta = cliente.get(f"/confirmar/{token}")
    afirmar(respuesta.status_code == 200, "El enlace de confirmación debe responder 200")
    afirmar("Cuenta confirmada" in texto(respuesta), "Debe confirmarse la cuenta")

    with database.get_connection() as db:
        fila = db.execute(
            "SELECT email_confirmado FROM usuarios_sistema WHERE username = ?", ("emarcano",)
        ).fetchone()
        afirmar(fila["email_confirmado"] == 1, "La cuenta debe quedar confirmada")
        usado = db.execute(
            "SELECT usado FROM tokens_correo WHERE token = ?", (token,)
        ).fetchone()
        afirmar(usado["usado"] == 1, "El token debe quedar marcado como usado")

    # Ahora sí entra, y puede hacerlo con el correo.
    respuesta = publicar(cliente, "/login", {
        "username": "evelyn.marcano@correo.com", "password": "ClaveSegura1!",
    })
    afirmar(respuesta.status_code == 302, "Con el correo confirmado el acceso debe funcionar")

    # Reutilizar el enlace no rompe nada: avisa de que ya estaba confirmada.
    respuesta = cliente.get(f"/confirmar/{token}")
    afirmar(respuesta.status_code == 200, "Reusar el enlace debe responder 200")
    afirmar("ya estaba confirmada" in texto(respuesta), "Debe avisar de que ya estaba confirmada")

    print("FASE7_CONFIRMAR_Y_ENTRAR_OK")


# ===========================================================================
# 4. Validaciones del formulario
# ===========================================================================
def test_validaciones():
    cliente = app.test_client()

    base = {
        "nombre": "Carlos", "apellido": "Pérez",
        "username": "cperez", "email": "carlos.perez@correo.com",
        "password": "ClaveSegura1!", "password_repetida": "ClaveSegura1!",
    }

    casos = [
        ("password", "corta1!", "entre 8 y 72 caracteres"),
        ("password", "clavesegura1!", "mayúscula"),
        ("password", "CLAVESEGURA1!", "minúscula"),
        ("password", "ClaveSegura!!", "número"),
        ("password", "ClaveSegura11", "carácter especial"),
        ("email", "correo-invalido", "correo"),
        ("username", "ab", "usuario"),
        ("nombre", "C4rlos", "nombre"),
    ]
    for campo, valor, esperado in casos:
        datos = dict(base)
        datos[campo] = valor
        if campo == "password":
            datos["password_repetida"] = valor
        respuesta = publicar(cliente, "/registro", datos)
        afirmar(respuesta.status_code == 400,
                f"Un {campo} inválido ({valor!r}) debe rechazarse con 400")
        afirmar(esperado.lower() in texto(respuesta).lower(),
                f"El error debe mencionar «{esperado}»")

    # Contraseñas que no coinciden.
    datos = dict(base, password_repetida="OtraClave1!")
    respuesta = publicar(cliente, "/registro", datos)
    afirmar(respuesta.status_code == 400, "Las contraseñas deben coincidir")
    afirmar("no coinciden" in texto(respuesta), "Debe avisarse de la discrepancia")

    # Alta correcta y duplicados.
    afirmar(publicar(cliente, "/registro", base).status_code == 200, "El alta debe funcionar")
    respuesta = publicar(cliente, "/registro", base)
    afirmar(respuesta.status_code == 400, "Repetir el usuario debe rechazarse")
    afirmar("ya está en uso" in texto(respuesta), "Debe indicarse que el usuario existe")

    respuesta = publicar(cliente, "/registro", dict(base, username="otro_usuario"))
    afirmar(respuesta.status_code == 400, "Repetir el correo debe rechazarse")
    afirmar("ya tiene una cuenta" in texto(respuesta), "Debe indicarse que el correo existe")

    print("FASE7_VALIDACIONES_OK")


# ===========================================================================
# 5. Tokens inválidos, caducados y reenvío
# ===========================================================================
def test_tokens_y_reenvio():
    cliente = app.test_client()

    respuesta = cliente.get("/confirmar/no-existe-este-token")
    afirmar(respuesta.status_code == 400, "Un token inexistente debe dar 400")
    afirmar("no es válido" in texto(respuesta), "Debe explicarse que el enlace no sirve")

    # Token caducado a mano.
    with database.get_connection() as db:
        usuario_id = db.execute(
            "SELECT id FROM usuarios_sistema WHERE username = ?", ("cperez",)
        ).fetchone()["id"]
        ayer = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        db.execute(
            "UPDATE tokens_correo SET fecha_expiracion = ? WHERE usuario_id = ? AND usado = 0",
            (ayer, usuario_id),
        )
        token_caducado = db.execute(
            "SELECT token FROM tokens_correo WHERE usuario_id = ? AND usado = 0", (usuario_id,)
        ).fetchone()["token"]

    respuesta = cliente.get(f"/confirmar/{token_caducado}")
    afirmar(respuesta.status_code == 400, "Un token caducado debe dar 400")
    afirmar("caducó" in texto(respuesta), "Debe avisarse de la caducidad")

    # Reenvío: emite un token nuevo y deja inservible el anterior.
    respuesta = cliente.get("/reenviar")
    afirmar(respuesta.status_code == 200, "GET /reenviar debe responder 200")

    respuesta = publicar(cliente, "/reenviar", {"email": "carlos.perez@correo.com"})
    afirmar(respuesta.status_code == 200, "El reenvío debe responder 200")
    coincidencia = re.search(r'href="([^"]*/confirmar/[^"]+)"', texto(respuesta))
    afirmar(coincidencia, "El reenvío debe mostrar un enlace nuevo")
    enlace_nuevo = coincidencia.group(1)
    afirmar(enlace_nuevo.rsplit("/", 1)[-1] != token_caducado, "El enlace debe ser distinto")

    respuesta = cliente.get(enlace_nuevo)
    afirmar(respuesta.status_code == 200 and "Cuenta confirmada" in texto(respuesta),
            "El enlace reenviado debe confirmar la cuenta")

    # Reenviar a una cuenta ya confirmada avisa en lugar de fallar.
    respuesta = publicar(cliente, "/reenviar", {"email": "carlos.perez@correo.com"})
    afirmar(respuesta.status_code == 400, "Reenviar a una cuenta confirmada debe dar 400")
    afirmar("ya está confirmada" in texto(respuesta), "Debe indicarse que ya está confirmada")

    # Correo sin cuenta.
    respuesta = publicar(cliente, "/reenviar", {"email": "nadie@correo.com"})
    afirmar(respuesta.status_code == 400, "Un correo desconocido debe dar 400")

    print("FASE7_TOKENS_Y_REENVIO_OK")


# ===========================================================================
# 6. Compatibilidad: los usuarios de siempre siguen entrando
# ===========================================================================
def test_usuarios_existentes():
    afirmar(AuthService.authenticate("admin", "Admin123!")["rol"] == "ADMINISTRADOR",
            "El administrador de siempre debe poder entrar")
    afirmar(AuthService.authenticate("admin@techloan.local", "Admin123!")["rol"] == "ADMINISTRADOR",
            "El administrador también debe poder entrar con su correo")

    with database.get_connection() as db:
        # Los usuarios sembrados por schema.sql nacen confirmados: existían antes
        # de que hubiera registro por correo, así que no deben quedar bloqueados.
        sembrados = db.execute(
            "SELECT username, email_confirmado FROM usuarios_sistema "
            "WHERE username IN ('admin', 'operador')"
        ).fetchall()
        afirmar(len(sembrados) == 2, "Los dos usuarios de demostración deben existir")
        afirmar(all(f["email_confirmado"] == 1 for f in sembrados),
                "Los usuarios sembrados deben estar confirmados de origen")

        # Al terminar el recorrido, todas las cuentas registradas quedaron confirmadas.
        pendientes = db.execute(
            "SELECT COUNT(*) FROM usuarios_sistema WHERE email_confirmado = 0"
        ).fetchone()[0]
        afirmar(pendientes == 0, f"No debe quedar ninguna cuenta sin confirmar ({pendientes})")

        total = db.execute("SELECT COUNT(*) FROM usuarios_sistema").fetchone()[0]
        afirmar(total == 4, f"Deben existir 2 sembrados + 2 registrados ({total})")

    print("FASE7_USUARIOS_EXISTENTES_OK")


def main():
    print(f"Base de datos de prueba: {database.DATABASE_PATH}")
    print(f"Buzón de prueba: {config.BUZON_DIR}")
    enlace = test_alta_y_token()
    test_sin_confirmar_no_entra()
    test_confirmar_y_entrar(enlace)
    test_validaciones()
    test_tokens_y_reenvio()
    test_usuarios_existentes()
    print("FASE7_PRUEBA_REGISTRO_OK")


if __name__ == "__main__":
    main()
