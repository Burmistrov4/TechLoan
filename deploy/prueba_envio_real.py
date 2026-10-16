"""Prueba de envío REAL de correo (para ejecutarla en el servidor).

Este script NO se ejecuta en local: está pensado para la consola Bash de
PythonAnywhere, donde el correo falla de verdad. Envía un mensaje auténtico por
SMTP a las direcciones que le indiques y te dice, paso a paso, qué respondió el
servidor.

Sirve para distinguir los dos fallos que parecen el mismo:

  1. Gmail NO acepta el envío (contraseña inválida, cuenta sin verificar,
     cuota agotada, puerto bloqueado).
  2. Gmail SÍ lo acepta pero no llega a destino (filtro del destinatario,
     dirección inexistente, el proveedor descarta el mensaje).

Uso:

    cd ~/TechLoan
    python3 deploy/prueba_envio_real.py tu-correo@gmail.com
    python3 deploy/prueba_envio_real.py tu-correo@gmail.com otro@protonmail.com

No modifica nada. La contraseña de aplicación nunca se muestra.
"""

import os
import re
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from pathlib import Path


def _cargar_variables_wsgi():
    """En PythonAnywhere las variables de entorno van en el archivo WSGI,
    no en el entorno de la consola Bash. Este helper las extrae y las
    inyecta en os.environ para que app.config las vea."""
    user = os.environ.get("USER", "")
    if not user:
        return
    wsgi = Path(f"/var/www/{user}_pythonanywhere_com_wsgi.py")
    if not wsgi.exists():
        return
    texto = wsgi.read_text(encoding="utf-8")
    # os.environ["X"] = "Y"  o  os.environ.setdefault("X", "Y")
    for m in re.finditer(
        r'os\.environ\[["\']([^"\']+)["\']\]\s*=\s*["\']([^"\']*)["\']',
        texto,
    ):
        os.environ[m.group(1)] = m.group(2)
    for m in re.finditer(
        r'os\.environ\.setdefault\(["\']([^"\']+)["\']\s*,\s*["\']([^"\']*)["\']\)',
        texto,
    ):
        os.environ.setdefault(m.group(1), m.group(2))


_cargar_variables_wsgi()

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.services import correo_service  # noqa: E402
from app.config import SMTP_FROM, SMTP_HOST, SMTP_PORT, SMTP_TLS, SMTP_USER  # noqa: E402

SEP = "=" * 74


def titulo(texto):
    print()
    print(SEP)
    print(texto)
    print(SEP)


def construir(destinatario):
    """Mismo mensaje que manda la aplicación al registrar una cuenta."""
    mensaje = EmailMessage()
    mensaje["Subject"] = "TechLoan — prueba de envío"
    mensaje["From"] = f"TechLoan <{SMTP_FROM}>"
    mensaje["To"] = destinatario
    mensaje["Reply-To"] = SMTP_FROM
    mensaje["Date"] = format_datetime(datetime.now().astimezone())
    mensaje["Message-ID"] = make_msgid(domain=SMTP_FROM.split("@")[-1])
    mensaje["Auto-Submitted"] = "auto-generated"
    mensaje.set_content(
        "Esto es una prueba de envío automática de TechLoan.\n\n"
        f"Enviado a: {destinatario}\n"
        f"Fecha: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
        "Si estás leyendo este mensaje, el correo de confirmación también llega.\n"
    )
    return mensaje


def main():
    destinos = [a for a in sys.argv[1:] if "@" in a]
    if not destinos:
        print(__doc__)
        raise SystemExit(1)

    titulo("CONFIGURACIÓN DETECTADA")
    if not correo_service.configurado():
        print("  La aplicación está en MODO DEMOSTRACIÓN: no hay TECHLOAN_SMTP_HOST.")
        print("  Este script necesita SMTP configurado para poder enviar de verdad.")
        print("  Configúralo en el archivo WSGI y recarga la web.")
        raise SystemExit(1)
    print(f"  servidor : {SMTP_HOST}:{SMTP_PORT}")
    print(f"  usuario  : {SMTP_USER}")
    print(f"  STARTTLS : {SMTP_TLS}")
    print(f"  desde    : TechLoan <{SMTP_FROM}>")
    print(f"  contraseña: {'definida (' + str(len(correo_service.SMTP_PASSWORD)) + ' caracteres)' if correo_service.SMTP_PASSWORD else 'VACÍA'}")

    titulo("1. CONEXIÓN Y AUTENTICACIÓN")
    try:
        servidor = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
        print(f"  conectado a {SMTP_HOST}:{SMTP_PORT}")
        if SMTP_TLS:
            servidor.starttls()
            print("  STARTTLS: correcto")
        if SMTP_USER:
            servidor.login(SMTP_USER, correo_service.SMTP_PASSWORD)
            print("  login: correcto")
    except Exception as exc:  # noqa: BLE001
        print(f"  FALLO: {type(exc).__name__}: {exc}")
        print()
        print("  => Gmail no acepta la conexión. Revisa:")
        print("     · la contraseña de aplicación (16 letras, sin espacios)")
        print("     · que la cuenta tenga verificación en dos pasos")
        print("     · que el puerto 587 no esté bloqueado por la plataforma")
        raise SystemExit(2)
    print()
    print("  => Gmail acepta la conexión. Si el correo no llega, el problema")
    print("     está en la entrega, no en el acceso.")

    for destino in destinos:
        titulo(f"2. ENVÍO A {destino}")
        mensaje = construir(destino)
        try:
            rechazos = servidor.send_message(mensaje)
            if rechazos:
                print(f"  Gmail RECHAZó estos destinatarios: {rechazos}")
                print("  => La dirección existe pero el servidor la rechazó.")
            else:
                print("  Gmail ACEPTÓ el mensaje para entrega (código 250).")
                print(f"  Message-ID: {mensaje['Message-ID']}")
                print()
                print(f"  Revisa la bandeja de {destino} (¡y la carpeta de spam!).")
                print("  · Si llega aquí pero no al otro proveedor → el problema es")
                print("    del destinatario o del filtro, no de TechLoan.")
                print("  · Si no llega a ninguno → puede tardar unos minutos, o Gmail")
                print("    está reteniéndolo. Comprueba también la carpeta «Enviado»")
                print("    de lorenzoroca333@gmail.com: si el mensaje está ahí, salió.")
        except Exception as exc:  # noqa: BLE001
            print(f"  FALLO al enviar: {type(exc).__name__}: {exc}")

    try:
        servidor.quit()
    except Exception:  # noqa: BLE001
        pass

    titulo("RESUMEN")
    print("  Pega esta salida completa: dice sin ambigüedad si Gmail acepta el")
    print("  envío y a qué direcciones lo entrega.")


if __name__ == "__main__":
    main()
