from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "database" / "techloan.db"

HOST = "127.0.0.1"
PORT = 5000
SECRET_KEY = "CAMBIAR_EN_PRODUCCION"

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
