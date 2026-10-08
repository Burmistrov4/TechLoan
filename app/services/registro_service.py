"""Registro de usuarios con confirmación por correo.

Flujo completo:

1. El visitante rellena el formulario de registro.
2. Se crea la cuenta con ``email_confirmado = 0`` y el rol **OPERADOR**: quien
   se da de alta por su cuenta no puede concederse privilegios.
3. Se emite un **token de un solo uso** con caducidad y se envía por correo.
4. Al abrir el enlace ``/confirmar/<token>`` la cuenta queda activada.

Decisiones de diseño:

- El token es aleatorio (``secrets``), de un solo uso y caduca. No da acceso por
  sí mismo: solo demuestra que quien abre el enlace controla ese correo.
- Si la cuenta ya estaba confirmada, el enlace avisa en lugar de fallar.
- El correo nunca puede tumbar el registro: si el envío falla, la cuenta se crea
  igual y el servicio informa del problema para que la interfaz lo muestre.
"""

import re
import secrets
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from app.config import HORAS_VALIDEZ_TOKEN, URL_BASE
from app.database import get_connection
from app.services import correo_service

# El autoregistro siempre crea operadores: el administrador es quien reparte
# privilegios desde el módulo de Usuarios.
ROL_AUTORREGISTRO = "OPERADOR"

_RE_NOMBRE = r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü ]{2,50}"
_RE_USERNAME = r"[A-Za-z0-9_]{4,20}"
_RE_EMAIL = r"[^\s@]+@[^\s@]+\.[^\s@]+"


def _ahora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _crear_token(db, usuario_id, tipo="CONFIRMACION"):
    """Emite un token nuevo, invalida los anteriores del mismo tipo y lo guarda."""
    token = secrets.token_urlsafe(32)
    expiracion = (datetime.now() + timedelta(hours=HORAS_VALIDEZ_TOKEN)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # Un usuario solo debe tener un enlace vivo por tipo.
    db.execute(
        "UPDATE tokens_correo SET usado = 1 WHERE usuario_id = ? AND tipo = ? AND usado = 0",
        (usuario_id, tipo),
    )
    db.execute(
        "INSERT INTO tokens_correo (usuario_id, token, tipo, fecha_expiracion) VALUES (?,?,?,?)",
        (usuario_id, token, tipo, expiracion),
    )
    return token


def _cuerpo_correo(nombre, username, enlace):
    texto = (
        f"Hola {nombre}:\n\n"
        "Tu cuenta en TechLoan está casi lista. Confirma tu correo abriendo este enlace:\n\n"
        f"{enlace}\n\n"
        f"Tu nombre de usuario es: {username}\n\n"
        f"El enlace caduca en {HORAS_VALIDEZ_TOKEN} horas y solo puede usarse una vez.\n"
        "Si no creaste esta cuenta, puedes ignorar este mensaje.\n\n"
        "— TechLoan\n"
    )
    html = f"""\
<div style="font-family:Segoe UI,Arial,sans-serif;font-size:15px;color:#0a1224;line-height:1.6">
  <h2 style="margin:0 0 12px">Confirma tu cuenta de TechLoan</h2>
  <p>Hola {nombre}:</p>
  <p>Tu cuenta está casi lista. Haz clic en el botón para confirmar tu correo:</p>
  <p style="margin:24px 0">
    <a href="{enlace}"
       style="display:inline-block;padding:12px 22px;border-radius:10px;
              background:#2563eb;color:#fff;text-decoration:none;font-weight:600">
      Confirmar mi cuenta
    </a>
  </p>
  <p style="color:#55637c;font-size:13px">
    Si el botón no funciona, copia esta dirección en el navegador:<br>
    <span style="word-break:break-all">{enlace}</span>
  </p>
  <p style="color:#55637c;font-size:13px">
    Tu nombre de usuario es <strong>{username}</strong>. El enlace caduca en
    {HORAS_VALIDEZ_TOKEN} horas y solo puede usarse una vez.
  </p>
</div>
"""
    return texto, html


class RegistroService:
    @staticmethod
    def validar(datos):
        """Devuelve la lista de problemas del formulario (vacía si todo está bien)."""
        errores = []

        if not re.fullmatch(_RE_NOMBRE, (datos.get("nombre") or "").strip()):
            errores.append("El nombre solo admite letras y espacios (2 a 50 caracteres).")
        if not re.fullmatch(_RE_NOMBRE, (datos.get("apellido") or "").strip()):
            errores.append("El apellido solo admite letras y espacios (2 a 50 caracteres).")
        if not re.fullmatch(_RE_USERNAME, (datos.get("username") or "").strip()):
            errores.append(
                "El usuario debe tener entre 4 y 20 caracteres alfanuméricos o guion bajo."
            )
        if not re.fullmatch(_RE_EMAIL, (datos.get("email") or "").strip()):
            errores.append("El correo no tiene un formato válido.")

        password = datos.get("password") or ""
        if len(password) < 8 or len(password) > 72:
            errores.append("La contraseña debe tener entre 8 y 72 caracteres.")
        else:
            if not re.search(r"[A-Z]", password):
                errores.append("La contraseña debe incluir al menos una mayúscula.")
            if not re.search(r"[a-z]", password):
                errores.append("La contraseña debe incluir al menos una minúscula.")
            if not re.search(r"\d", password):
                errores.append("La contraseña debe incluir al menos un número.")
            if not re.search(r"[^A-Za-z0-9]", password):
                errores.append("La contraseña debe incluir al menos un carácter especial.")

        if password != (datos.get("password_repetida") or ""):
            errores.append("Las dos contraseñas no coinciden.")

        return errores

    @staticmethod
    def enlace_confirmacion(token):
        return f"{URL_BASE}/confirmar/{token}"

    @staticmethod
    def registrar(datos):
        """Da de alta la cuenta y manda el enlace de confirmación.

        Devuelve ``{"usuario_id", "nombre", "username", "email", "enlace", "correo"}``.
        Lanza ``ValueError`` con un mensaje claro si los datos no sirven.
        """
        errores = RegistroService.validar(datos)
        if errores:
            raise ValueError(" ".join(errores))

        nombre = datos["nombre"].strip()
        apellido = datos["apellido"].strip()
        username = datos["username"].strip()
        email = datos["email"].strip().lower()

        password_hash = generate_password_hash(datos["password"])
        if len(password_hash) > 255:
            raise ValueError("El hash generado excede VARCHAR(255).")

        with get_connection() as db:
            existente = db.execute(
                "SELECT username, email FROM usuarios_sistema WHERE username = ? OR email = ?",
                (username, email),
            ).fetchone()
            if existente:
                if existente["username"] == username:
                    raise ValueError("Ese nombre de usuario ya está en uso.")
                raise ValueError("Ese correo ya tiene una cuenta registrada.")

            try:
                cur = db.execute(
                    """INSERT INTO usuarios_sistema
                       (nombre, apellido, username, email, password_hash, rol, estado,
                        email_confirmado)
                       VALUES (?,?,?,?,?,?,'ACTIVO',0)""",
                    (nombre, apellido, username, email, password_hash, ROL_AUTORREGISTRO),
                )
            except Exception as exc:  # noqa: BLE001 - se traduce a un mensaje de usuario
                if "usuarios_sistema.username" in str(exc):
                    raise ValueError("Ese nombre de usuario ya está en uso.") from exc
                if "usuarios_sistema.email" in str(exc):
                    raise ValueError("Ese correo ya tiene una cuenta registrada.") from exc
                raise

            usuario_id = cur.lastrowid
            token = _crear_token(db, usuario_id, "CONFIRMACION")

        enlace = RegistroService.enlace_confirmacion(token)
        texto, html = _cuerpo_correo(nombre, username, enlace)
        resultado_correo = correo_service.enviar(
            email, "Confirma tu cuenta de TechLoan", texto, html
        )

        return {
            "usuario_id": usuario_id,
            "nombre": nombre,
            "username": username,
            "email": email,
            "enlace": enlace,
            "correo": resultado_correo,
        }

    @staticmethod
    def confirmar(token):
        """Activa la cuenta asociada al token.

        Devuelve ``{"username", "ya_confirmada"}``. Lanza ``ValueError`` si el
        token no existe, ya se usó o caducó.
        """
        token = (token or "").strip()
        if not token:
            raise ValueError("El enlace no incluye ningún código.")

        with get_connection() as db:
            fila = db.execute(
                """SELECT t.id, t.usuario_id, t.usado, t.fecha_expiracion, t.tipo,
                          u.username, u.email, u.email_confirmado
                     FROM tokens_correo t
                     JOIN usuarios_sistema u ON u.id = t.usuario_id
                    WHERE t.token = ?""",
                (token,),
            ).fetchone()

            if not fila:
                raise ValueError("Este enlace no es válido. Solicita uno nuevo.")

            if fila["tipo"] != "CONFIRMACION":
                raise ValueError("Este enlace no sirve para confirmar una cuenta.")

            if fila["usado"]:
                if fila["email_confirmado"]:
                    return {"username": fila["username"], "ya_confirmada": True}
                raise ValueError("Este enlace ya se usó. Solicita uno nuevo.")

            if fila["fecha_expiracion"] < _ahora():
                raise ValueError("El enlace caducó. Solicita uno nuevo.")

            if fila["email_confirmado"]:
                db.execute("UPDATE tokens_correo SET usado = 1 WHERE id = ?", (fila["id"],))
                return {"username": fila["username"], "ya_confirmada": True}

            db.execute(
                "UPDATE usuarios_sistema SET email_confirmado = 1 WHERE id = ?",
                (fila["usuario_id"],),
            )
            db.execute("UPDATE tokens_correo SET usado = 1 WHERE id = ?", (fila["id"],))
            return {"username": fila["username"], "ya_confirmada": False}

    @staticmethod
    def reenviar(email):
        """Emite un enlace nuevo para una cuenta que aún no está confirmada."""
        email = (email or "").strip().lower()
        if not re.fullmatch(_RE_EMAIL, email):
            raise ValueError("El correo no tiene un formato válido.")

        with get_connection() as db:
            fila = db.execute(
                "SELECT id, nombre, username, email_confirmado "
                "FROM usuarios_sistema WHERE email = ?",
                (email,),
            ).fetchone()

            if not fila:
                raise ValueError("No hay ninguna cuenta con ese correo.")
            if fila["email_confirmado"]:
                raise ValueError("Esa cuenta ya está confirmada. Puedes iniciar sesión.")

            token = _crear_token(db, fila["id"], "CONFIRMACION")
            nombre = fila["nombre"]
            username = fila["username"]

        enlace = RegistroService.enlace_confirmacion(token)
        texto, html = _cuerpo_correo(nombre, username, enlace)
        resultado_correo = correo_service.enviar(
            email, "Confirma tu cuenta de TechLoan", texto, html
        )

        return {
            "enlace": enlace,
            "correo": resultado_correo,
            "username": username,
            "email": email,
        }

    @staticmethod
    def limpiar_caducados():
        """Marca como usados los tokens caducados. Mantenimiento opcional."""
        with get_connection() as db:
            cur = db.execute(
                "UPDATE tokens_correo SET usado = 1 WHERE usado = 0 AND fecha_expiracion < ?",
                (_ahora(),),
            )
            return cur.rowcount
