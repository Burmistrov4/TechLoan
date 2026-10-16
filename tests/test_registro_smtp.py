"""Prueba del ciclo de registro CON SMTP real (simula producción).

El test ``test_registro_phase7.py`` cubre el modo demostración, donde el enlace se
muestra en pantalla. Esta prueba monta un **servidor SMTP auténtico en un hilo**,
configura la aplicación como en producción (``TECHLOAN_SMTP_*`` +
``TECHLOAN_URL_BASE``) y verifica que:

1. el correo sale realmente por el socket SMTP,
2. el enlace del cuerpo del correo apunta al dominio correcto,
3. ese enlace, abierto en el navegador, confirma la cuenta,
4. el token del correo coincide con el de la base de datos.

Si algo de esto falla, es exactamente el error que ven los usuarios en producción:
*«les llega el correo pero el enlace no confirma la cuenta»*.

Uso::

    PYTHONPATH=. python tests/test_registro_smtp.py
"""

import os
import re
import socket
import sys
import tempfile
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# --- Configurar el entorno ANTES de importar la aplicación -------------------
# Igual que hace el archivo WSGI de PythonAnywhere: las variables se asignan
# antes del import porque app/config.py las lee al importarse.
_TMP = Path(tempfile.mkdtemp(prefix="techloan_smtp_test_"))
_DB = _TMP / "test_smtp.db"
os.environ["TECHLOAN_SECRET_KEY"] = "clave-de-prueba-smtp"
os.environ["TECHLOAN_URL_BASE"] = "https://tudominio.pythonanywhere.com"
os.environ["TECHLOAN_SMTP_HOST"] = "127.0.0.1"
os.environ["TECHLOAN_SMTP_PORT"] = "8025"
os.environ["TECHLOAN_SMTP_USER"] = "pruebas@tudominio.local"
os.environ["TECHLOAN_SMTP_PASSWORD"] = "secreta"
os.environ["TECHLOAN_SMTP_FROM"] = "pruebas@tudominio.local"
os.environ["TECHLOAN_SMTP_TLS"] = "0"          # sin STARTTLS: el servidor es local

import app.config as config          # noqa: E402
import app.database as database      # noqa: E402
config.DATABASE_PATH = _DB
database.DATABASE_PATH = _DB
config.BUZON_DIR = _TMP / "buzon"

from init_db import init_database as cargar_esquema  # noqa: E402
from app.server import create_app                    # noqa: E402
from app.services import correo_service              # noqa: E402


# ---------------------------------------------------------------------------
# Servidor SMTP mínimo: captura el mensaje y responde lo justo para que
# smtplib completa el envío. Sin dependencias externas.
# ---------------------------------------------------------------------------
class ServidorSMTPFalso:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("127.0.0.1", 0))
        self.puerto = self.socket.getsockname()[1]
        self.mensajes = []
        self.hilo = threading.Thread(target=self._servir, daemon=True)

    def iniciar(self):
        self.hilo.start()
        return self

    def _servir(self):
        self.socket.listen(5)
        while True:
            try:
                conexion, _ = self.socket.accept()
            except OSError:
                return
            with conexion:
                conexion.sendall(b"220 localhost SMTP de prueba\r\n")
                en_datos = False
                esperando_auth = None      # None | "usuario" | "password"
                buffer = b""
                while True:
                    try:
                        dato = conexion.recv(4096)
                    except OSError:
                        break
                    if not dato:
                        break
                    buffer += dato
                    while True:
                        if en_datos:
                            if buffer.endswith(b"\r\n.\r\n"):
                                self.mensajes.append(buffer[:-5].decode("utf-8", "replace"))
                                buffer = b""
                                en_datos = False
                                conexion.sendall(b"250 OK aceptado\r\n")
                                continue
                            if not buffer:
                                break
                            # El cuerpo puede no haber terminado: esperar más.
                            break
                        if b"\r\n" not in buffer:
                            break
                        linea, _, resto = buffer.partition(b"\r\n")
                        buffer = resto
                        comando = linea.decode("utf-8", "replace").strip()

                        if esperando_auth == "usuario":
                            esperando_auth = "password"
                            conexion.sendall(b"334 UGFzc3dvcmQ6\r\n")
                        elif esperando_auth == "password":
                            esperando_auth = None
                            conexion.sendall(b"235 2.7.0 Autenticacion correcta\r\n")
                        elif comando.upper().startswith("AUTH LOGIN"):
                            esperando_auth = "usuario"
                            conexion.sendall(b"334 VXNlcm5hbWU6\r\n")
                        elif comando.upper().startswith("AUTH PLAIN"):
                            conexion.sendall(b"235 2.7.0 Autenticacion correcta\r\n")
                        elif comando.upper().startswith(("EHLO", "HELO")):
                            # Se anuncia AUTH para que smtplib haga login().
                            conexion.sendall(b"250-localhost\r\n250-AUTH LOGIN PLAIN\r\n250 OK\r\n")
                        elif comando.upper().startswith("MAIL FROM"):
                            conexion.sendall(b"250 OK\r\n")
                        elif comando.upper().startswith("RCPT TO"):
                            conexion.sendall(b"250 OK\r\n")
                        elif comando.upper().startswith("DATA"):
                            conexion.sendall(b"354 Fin con <CR><LF>.<CR><LF>\r\n")
                            en_datos = True
                        elif comando.upper().startswith("RSET"):
                            conexion.sendall(b"250 OK\r\n")
                        elif comando.upper().startswith("NOOP"):
                            conexion.sendall(b"250 OK\r\n")
                        elif comando.upper().startswith("QUIT"):
                            conexion.sendall(b"221 Adios\r\n")
                            buffer = b""
                            break
                        else:
                            conexion.sendall(b"502 No implementado\r\n")

    def detener(self):
        try:
            self.socket.close()
        except OSError:
            pass


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


# ---------------------------------------------------------------------------
# Comienzo de la prueba
# ---------------------------------------------------------------------------
servidor = ServidorSMTPFalso().iniciar()
os.environ["TECHLOAN_SMTP_PORT"] = str(servidor.puerto)   # el puerto real asignado

cargar_esquema(_DB)

# Releer la configuración con el puerto verdadero (config ya se importó).
import importlib                        # noqa: E402
import app.services.correo_service as cs # noqa: E402
cs.SMTP_PORT = servidor.puerto
cs.SMTP_HOST = "127.0.0.1"

app = create_app()

afirmar(correo_service.configurado(),
        "Con TECHLOAN_SMTP_HOST definido, el servicio debe estar en modo SMTP")
print(f"[ok] modo de correo: {correo_service.modo()}")
print(f"[ok] URL_BASE: {config.URL_BASE}")

cliente = app.test_client()
csrf = token_csrf(cliente, "/registro")

respuesta = cliente.post("/registro", data={
    "_csrf_token": csrf,
    "nombre": "Compañero", "apellido": "De Prueba",
    "username": "companero", "email": "companero@correo.com",
    "password": "ClaveSegura1!", "password_repetida": "ClaveSegura1!",
}, follow_redirects=False)

afirmar(respuesta.status_code == 200,
        f"El registro debe responder 200 (dio {respuesta.status_code})")
html = respuesta.get_data(as_text=True)

# En modo SMTP la aplicación NO debe mostrar el enlace en pantalla.
if "/confirmar/" in html and "confirmar/" in html:
    enlaces_pantalla = re.findall(r'/confirmar/[A-Za-z0-9_\-]+', html)
    if enlaces_pantalla:
        print(f"[!] Se mostró un enlace en pantalla estando en modo SMTP: {enlaces_pantalla}")

afirmar(servidor.mensajes, "El correo debió salir por el socket SMTP")
mensaje = servidor.mensajes[0]
print("[ok] el correo salió por SMTP")
print("---- cabeceras del correo capturado ----")
for linea in mensaje.splitlines()[:12]:
    print("   ", linea)
print("----------------------------------------")

# Extraer el enlace decodificando el correo como haría un cliente de verdad.
# Es imprescindible: el cuerpo va en quoted-printable y parte la URL larga con
# un salto de línea blando (=CRLF). Buscar con expresiones regulares sobre el
# mensaje crudo devuelve un token truncado y un falso negativo.
import email                                        # noqa: E402
from email import policy                            # noqa: E402

# Con policy.default, get_content() decodifica el quoted-printable y deshace los
# saltos de línea blandos, así que la URL queda entera.
buzon = email.message_from_string(mensaje, policy=policy.default)
cuerpo_texto = buzon.get_body(preferencelist=("plain",)).get_content()
encontrados = re.findall(r'https?://\S+/(?:confirmar|c)/\S+', cuerpo_texto)
afirmar(encontrados, "El cuerpo del correo debe contener el enlace de confirmación")
enlace = encontrados[0]
print(f"[ok] enlace del correo: {enlace}")

# Comprobación de que la decodificación fue completa: si el token del correo
# tuviera un '=' final, seguiría partido por el quoted-printable.
token = enlace.rsplit("/", 1)[-1]
afirmar(not token.endswith("="),
        "El token no debe acabar en '=' (la URL quedó partida por quoted-printable)")

# 1. El enlace debe apuntar al dominio configurado.
afirmar(enlace.startswith("https://tudominio.pythonanywhere.com/c/"),
        f"El enlace debe empezar por la URL_BASE configurada: {enlace}")

# Y debe caber en una sola línea: a partir de 76 caracteres el cuerpo del correo
# se codifica en quoted-printable y la URL se parte en dos.
afirmar(len(enlace) <= 76,
        f"El enlace mide {len(enlace)} caracteres: se partiría en el correo")

# 2. El token del enlace debe existir en la base de datos y sin usar.
token = enlace.rsplit("/", 1)[-1]
print(f"[ok] token del correo: {token}")
with database.get_connection() as db:
    fila = db.execute(
        "SELECT t.usado, t.fecha_expiracion, u.email_confirmado, u.username "
        "FROM tokens_correo t JOIN usuarios_sistema u ON u.id = t.usuario_id "
        "WHERE t.token = ?", (token,)).fetchone()
afirmar(fila is not None, "El token del correo debe existir en la base de datos")
print(f"[ok] token en BD: usado={fila['usado']} expira={fila['fecha_expiracion']} "
      f"confirmado={fila['email_confirmado']}")
afirmar(fila["usado"] == 0, "El token recién emitido no puede estar usado")

# 3. Abrir el enlace en el navegador debe confirmar la cuenta.
respuesta = cliente.get(f"/confirmar/{token}")
afirmar(respuesta.status_code == 200,
        f"GET /confirmar/<token> debe responder 200 (dio {respuesta.status_code})")
cuerpo = respuesta.get_data(as_text=True)
afirmar("Cuenta confirmada" in cuerpo,
        "La página debe confirmar la cuenta (¿sale 'No se pudo confirmar'?)")
print("[ok] el enlace del correo confirma la cuenta")

# 4. Ya no se puede entrar sin confirmar... bueno, sí: ya está confirmada.
respuesta = cliente.post("/login", data={
    "_csrf_token": token_csrf(cliente, "/login"),
    "username": "companero@correo.com", "password": "ClaveSegura1!",
}, follow_redirects=False)
afirmar(respuesta.status_code == 302,
        f"Tras confirmar, el acceso debe funcionar (dio {respuesta.status_code})")
print("[ok] acceso con el correo tras confirmar")

servidor.detener()
print("SMTP_PRUEBA_REGISTRO_OK")
