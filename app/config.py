from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "database" / "techloan.db"

HOST = "127.0.0.1"
PORT = 5000
SECRET_KEY = "CAMBIAR_EN_PRODUCCION"

DEFAULT_RESERVATION_MINUTES = 70
PASSWORD_HASH_MAX_LENGTH = 255
