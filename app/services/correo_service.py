"""Envío de correo saliente, con modo demostración.

El registro de usuarios necesita mandar un enlace de confirmación. En un
servidor real eso se resuelve por SMTP; en una demostración local no hay
servidor de correo, así que este servicio tiene dos modos:

- **SMTP configurado** (variables ``TECHLOAN_SMTP_*``): envía el mensaje de
  verdad, con STARTTLS si el puerto lo requiere.
- **Sin SMTP** (modo demostración): escribe el mensaje en ``database/buzon/`` y
  devuelve la ruta, para que la interfaz pueda mostrar el enlace en pantalla.
  Así el flujo completo —registro, correo y confirmación— se puede enseñar en
  la defensa sin depender de internet ni de una cuenta de correo.

El servicio **nunca lanza la excepción hacia arriba**: un fallo de correo no
debe tumbar el registro de un usuario. Siempre devuelve un diccionario con el
resultado, y quien llama decide qué mensaje mostrar.
"""

import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid

from app.config import (
    BUZON_DIR,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_TLS,
    SMTP_USER,
)


def configurado():
    """¿Hay un servidor SMTP configurado?"""
    return bool(SMTP_HOST)


def modo():
    """Identificador del modo activo, para mostrarlo en la interfaz."""
    return "smtp" if configurado() else "demostracion"


def _guardar_en_buzon(destinatario, asunto, texto, html):
    """Deja el mensaje en disco y devuelve la ruta del archivo."""
    BUZON_DIR.mkdir(parents=True, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d-%H%M%S")
    seguro = "".join(c if c.isalnum() or c in ".-_@" else "_" for c in destinatario)
    ruta = BUZON_DIR / f"{marca}-{seguro}.txt"

    ruta.write_text(
        "\n".join(
            [
                "=" * 72,
                " MENSAJE GENERADO POR TECHLOAN (MODO DEMOSTRACIÓN)",
                "=" * 72,
                f"Para:    {destinatario}",
                f"De:      {SMTP_FROM}",
                f"Asunto:  {asunto}",
                f"Fecha:   {datetime.now():%Y-%m-%d %H:%M:%S}",
                "",
                "-" * 72,
                texto,
                "-" * 72,
                "",
                "Nota: no hay servidor SMTP configurado, así que el mensaje no se",
                "envió por correo. Se guardó aquí y la aplicación muestra el enlace",
                "de confirmación directamente en pantalla.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return ruta


def enviar(destinatario, asunto, texto, html=None):
    """Envía (o guarda) un mensaje.

    Devuelve un diccionario con ``enviado``, ``modo`` y, en modo demostración,
    la ruta del archivo. Si algo falla, ``error`` lleva la explicación.
    """
    destinatario = (destinatario or "").strip()
    if not destinatario:
        return {"enviado": False, "modo": modo(), "error": "Falta el destinatario."}

    if not configurado():
        try:
            ruta = _guardar_en_buzon(destinatario, asunto, texto, html)
        except OSError as exc:
            print(f"[correo] No se pudo escribir en el buzón: {exc}", file=sys.stderr)
            return {"enviado": False, "modo": "demostracion", "error": str(exc)}
        return {"enviado": False, "modo": "demostracion", "archivo": str(ruta)}

    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    # Remitente con nombre legible: "TechLoan" <correo>. Los filtros de spam
    # puntúan mejor un From con nombre que un From que es solo una dirección.
    mensaje["From"] = f"TechLoan <{SMTP_FROM}>"
    mensaje["To"] = destinatario
    mensaje["Reply-To"] = SMTP_FROM
    # Cabeceras que el RFC 5322 exige y que este servicio no estaba poniendo.
    # Gmail las añade por su cuenta, pero receptores estrictos (Proton Mail,
    # Outlook, muchos filtros corporativos) descartan o archivan como spam un
    # mensaje sin Date o sin Message-ID propio. Es la diferencia entre "el
    # correo llega a Gmail pero no a Proton".
    mensaje["Date"] = format_datetime(datetime.now().astimezone())
    mensaje["Message-ID"] = make_msgid(domain=SMTP_FROM.split("@")[-1])
    # Declara que es un mensaje automático transaccional: mejora la
    # entregabilidad frente a los filtros que penalizan el envío masivo.
    mensaje["Auto-Submitted"] = "auto-generated"
    mensaje.set_content(texto)
    if html:
        mensaje.add_alternative(html, subtype="html")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as servidor:
            if SMTP_TLS:
                servidor.starttls()
            if SMTP_USER:
                servidor.login(SMTP_USER, SMTP_PASSWORD)
            servidor.send_message(mensaje)
    except Exception as exc:  # noqa: BLE001 - el registro no debe romperse por el correo
        print(f"[correo] Falló el envío a {destinatario}: {exc}", file=sys.stderr)
        # Se deja copia local para no perder el enlace.
        try:
            ruta = _guardar_en_buzon(destinatario, asunto, texto, html)
            return {"enviado": False, "modo": "smtp", "error": str(exc), "archivo": str(ruta)}
        except OSError:
            return {"enviado": False, "modo": "smtp", "error": str(exc)}

    return {"enviado": True, "modo": "smtp"}
