"""Arranca TechLoan accesible desde la red local (laptop + teléfono).

Un solo comando levanta el servidor en ``0.0.0.0`` para que cualquier
dispositivo de la misma red (teléfono, tablet, otra laptop) pueda abrir la app
con la IP de esta computadora.

Uso::

    .venv/Scripts/python.exe iniciar_servidor.py

- Muestra la URL local (127.0.0.1) y la URL de red (http://IP:puerto).
- Abre el navegador en la URL local automáticamente.
- El puerto se puede cambiar con ``TECHLOAN_PORT`` (o ``PORT``).

Nota (Windows): la primera vez, el Firewall puede pedir permiso para Python.
Hay que permitirlo (redes privadas) para que el teléfono pueda conectarse.
Si no aparece el aviso, ejecutar como administrador una vez:

    netsh advfirewall firewall add rule name="TechLoan" dir=in action=allow protocol=TCP localport=5000
"""

import os
import socket
import sys
import threading
import time
import webbrowser

# Permite ejecutar el script desde cualquier carpeta.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


def ip_local():
    """Devuelve la IP de esta máquina en la red local (sin enviar tráfico)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No envía paquetes: solo resuelve qué interfaz usaría para salir.
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "127.0.0.1"
    finally:
        sock.close()


def main():
    from app.config import PORT
    from app.server import create_app

    puerto = int(os.environ.get("TECHLOAN_PORT") or os.environ.get("PORT") or PORT or 5000)
    ip = ip_local()

    app = create_app()

    print("\n" + "=" * 64)
    print("  TechLoan — servidor en marcha")
    print("=" * 64)
    print(f"  En esta laptop:   http://127.0.0.1:{puerto}")
    print(f"  Desde el teléfono: http://{ip}:{puerto}")
    print("  (mismo Wi-Fi / red local; el firewall debe permitir Python)")
    print("=" * 64 + "\n")

    # Abre el navegador localmente, sin bloquear el arranque del servidor.
    def abrir_navegador():
        time.sleep(1.5)
        try:
            webbrowser.open(f"http://127.0.0.1:{puerto}")
        except Exception:
            pass

    threading.Thread(target=abrir_navegador, daemon=True).start()

    # 0.0.0.0 = escucha en todas las interfaces (LAN). threaded=True atiende
    # varios dispositivos a la vez.
    app.run(host="0.0.0.0", port=puerto, debug=False, threaded=True)


if __name__ == "__main__":
    main()
