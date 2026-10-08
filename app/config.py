import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "database" / "techloan.db"

HOST = "127.0.0.1"
PORT = 5000
SECRET_KEY = os.environ.get("TECHLOAN_SECRET_KEY", "CAMBIAR_EN_PRODUCCION")

DEFAULT_RESERVATION_MINUTES = 70
PASSWORD_HASH_MAX_LENGTH = 255

# --- Parámetros de negocio configurables ------------------------------------
# Días que puede estar un equipo prestado antes de considerarse vencido.
DIAS_PRESTAMO_LIMITE = 7
# Número de reservas en los próximos 7 días a partir del cual un laboratorio
# se considera saturado.
UMBRAL_SATURACION = 5
# Franja de apertura de los laboratorios, usada para sugerir horarios libres.
HORA_APERTURA = "07:00"
HORA_CIERRE = "21:00"
# Resultados por página en los listados.
FILAS_POR_PAGINA = 10

# --- Registro de usuarios y correo de confirmación ---------------------------
# El registro por correo es el único módulo que necesita hablar con el exterior.
# Si no se configura un servidor SMTP, la aplicación entra en MODO DEMOSTRACIÓN:
# en lugar de enviar el mensaje, lo deja en `database/buzon/` y muestra el enlace
# de confirmación en pantalla. Así el flujo completo se puede enseñar en la
# defensa sin depender de una cuenta de correo ni de internet.
SMTP_HOST = os.environ.get("TECHLOAN_SMTP_HOST", "").strip()
SMTP_PORT = int(os.environ.get("TECHLOAN_SMTP_PORT", "587") or 587)
SMTP_USER = os.environ.get("TECHLOAN_SMTP_USER", "").strip()
SMTP_PASSWORD = os.environ.get("TECHLOAN_SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("TECHLOAN_SMTP_FROM", "").strip() or SMTP_USER or "no-reply@techloan.local"
SMTP_TLS = os.environ.get("TECHLOAN_SMTP_TLS", "1").strip().lower() not in ("0", "false", "no")

# Dirección pública con la que se construyen los enlaces de confirmación.
URL_BASE = os.environ.get("TECHLOAN_URL_BASE", f"http://{HOST}:{PORT}").rstrip("/")

# Horas que vale un enlace de confirmación antes de caducar.
HORAS_VALIDEZ_TOKEN = int(os.environ.get("TECHLOAN_HORAS_TOKEN", "24") or 24)

# Carpeta donde se dejan los correos cuando no hay SMTP configurado.
BUZON_DIR = BASE_DIR / "database" / "buzon"
