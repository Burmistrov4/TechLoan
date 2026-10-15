"""Diagnóstico de correo saliente para TechLoan.

Responde a UNA pregunta: ¿esta máquina puede conectarse a un servidor SMTP?

Se usa en PythonAnywhere (u otro servidor) para saber, en segundos, si el modo
demostración es una elección o una obligación. **No envía ningún correo y no
necesita credenciales**: solo comprueba que el puerto responde.

Uso:

    cd ~/TechLoan
    python3 deploy/diagnostico_correo.py

    # Para probar otro servidor:
    python3 deploy/diagnostico_correo.py smtp.gmail.com 587
"""

import smtplib
import socket
import sys

HOST = sys.argv[1] if len(sys.argv) > 1 else "smtp.gmail.com"
PUERTO = int(sys.argv[2]) if len(sys.argv) > 2 else 587

print(f"Comprobando {HOST}:{PUERTO} ...")
print()

# 1. ¿Se resuelve el nombre?
try:
    ip = socket.gethostbyname(HOST)
    print(f"  [OK]   DNS: {HOST} se resuelve como {ip}")
except OSError as exc:
    print(f"  [FALLA] DNS: no se pudo resolver {HOST} ({exc})")
    print()
    print("=> Sin resolución de nombres no hay correo posible.")
    raise SystemExit(1)

# 2. ¿Responde el puerto?
try:
    with socket.create_connection((HOST, PUERTO), timeout=10) as conexion:
        conexion.settimeout(5)
        saludo = conexion.recv(200).decode("utf-8", "replace").strip()
    print(f"  [OK]   TCP: el puerto {PUERTO} responde")
    print(f"         saludo del servidor: {saludo[:120]}")
except OSError as exc:
    print(f"  [FALLA] TCP: no se pudo abrir {HOST}:{PUERTO} ({exc})")
    print()
    print("=> El correo saliente está BLOQUEADO en este servidor.")
    print("   En el plan gratuito de PythonAnywhere esto es lo esperado:")
    print("   la aplicación se queda en MODO DEMOSTRACIÓN y muestra el enlace")
    print("   de confirmación en pantalla. Para la defensa es suficiente.")
    raise SystemExit(2)

# 3. ¿Acepta STARTTLS?
try:
    with smtplib.SMTP(HOST, PUERTO, timeout=10) as servidor:
        servidor.ehlo()
        servidor.starttls()
        servidor.ehlo()
    print("  [OK]   STARTTLS: el servidor acepta cifrado")
except Exception as exc:  # noqa: BLE001
    print(f"  [AVISO] STARTTLS: no se pudo negociar ({exc})")
    print("          Puede que el servidor pida otro puerto o cifrado implícito.")

print()
print("RESULTADO: este servidor SÍ puede hablar con", HOST)
print("Para activarlo, descomenta las líneas TECHLOAN_SMTP_* del archivo WSGI")
print("y rellena el usuario y la contraseña de aplicación.")
