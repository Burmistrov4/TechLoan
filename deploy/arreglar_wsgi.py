#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Corrige el archivo WSGI de PythonAnywhere para que tenga:
  - URL_BASE correcta (https://TU_USUARIO.pythonanywhere.com)
  - Variables SMTP configuradas (conservando la contraseña que ya esté)
  - SECRET_KEY preservada (para no cerrar sesiones activas)

Uso en la consola Bash de PythonAnywhere:
    python3 deploy/arreglar_wsgi.py
"""
import os
import re
import sys
from pathlib import Path

USER_PA = os.environ.get("USER", "")
if not USER_PA:
    print("ERROR: no detecto el usuario. Ejecuta esto en PythonAnywhere.", file=sys.stderr)
    sys.exit(1)

WSGI_PATH = Path(f"/var/www/{USER_PA}_pythonanywhere_com_wsgi.py")
if not WSGI_PATH.exists():
    print(f"ERROR: no existe {WSGI_PATH}", file=sys.stderr)
    print("Crea primero la aplicación web en la pestaña Web de PythonAnywhere.", file=sys.stderr)
    sys.exit(1)

contenido = WSGI_PATH.read_text(encoding="utf-8")
print(f"Leyendo {WSGI_PATH} ({len(contenido)} caracteres)...")

# Extraer valores que ya existen (para no perderlos)
def extraer(var, default=""):
    m = re.search(rf'os\.environ\["{re.escape(var)}"\]\s*=\s*"([^"]*)"', contenido)
    if m:
        return m.group(1)
    m = re.search(rf'os\.environ\.setdefault\("{re.escape(var)}",\s*"([^"]*)"\)', contenido)
    if m:
        return m.group(1)
    return default

clave     = extraer("TECHLOAN_SECRET_KEY")
url_base  = extraer("TECHLOAN_URL_BASE",  f"https://{USER_PA}.pythonanywhere.com")
smtp_host = extraer("TECHLOAN_SMTP_HOST",  "smtp.gmail.com")
smtp_port = extraer("TECHLOAN_SMTP_PORT",  "587")
smtp_user = extraer("TECHLOAN_SMTP_USER",  "lorenzoroca333@gmail.com")
smtp_pass = extraer("TECHLOAN_SMTP_PASSWORD")
smtp_from = extraer("TECHLOAN_SMTP_FROM",  smtp_user or "lorenzoroca333@gmail.com")

print(f"  SECRET_KEY  : {'*' * 8 if clave else 'NO HAY — se generará una nueva'}")
print(f"  URL_BASE    : {url_base}")
print(f"  SMTP_HOST   : {smtp_host}")
print(f"  SMTP_USER   : {smtp_user}")
print(f"  SMTP_PASS   : {'*' * 8 if smtp_pass else 'NO HAY — necesitas ponerla'}")

if not smtp_pass:
    print()
    print("=" * 60)
    print("ATENCIÓN: no encontré TECHLOAN_SMTP_PASSWORD en el WSGI.")
    print("Necesitas la contraseña de aplicación de Gmail (no tu clave normal).")
    print("Consíguela en: https://myaccount.google.com/apppasswords")
    print("=" * 60)
    print()
    nueva_pass = input("Pega la contraseña de aplicación (o Enter para dejarla vacía): ").strip()
    if nueva_pass:
        smtp_pass = nueva_pass

if not clave:
    import secrets
    clave = secrets.token_hex(32)
    print(f"SECRET_KEY generada: {clave[:8]}...{clave[-8:]}")

nuevo = f'''# -*- coding: utf-8 -*-
import os
import sys

RUTA = "/home/{USER_PA}/TechLoan"
if RUTA not in sys.path:
    sys.path.insert(0, RUTA)

# Variables de entorno ANTES del import (app/config.py las lee al importarse).
os.environ.setdefault("TECHLOAN_SECRET_KEY", "{clave}")
os.environ.setdefault("TECHLOAN_URL_BASE",  "{url_base}")

# --- Correo (SMTP) -----------------------------------------------------------
os.environ.setdefault("TECHLOAN_SMTP_HOST",     "{smtp_host}")
os.environ.setdefault("TECHLOAN_SMTP_PORT",     "{smtp_port}")
os.environ.setdefault("TECHLOAN_SMTP_USER",     "{smtp_user}")
os.environ.setdefault("TECHLOAN_SMTP_PASSWORD", "{smtp_pass}")
os.environ.setdefault("TECHLOAN_SMTP_FROM",     "{smtp_from}")

from app.server import create_app
application = create_app()
'''

# Backup
backup = WSGI_PATH.with_suffix(".py.bak")
backup.write_text(contenido, encoding="utf-8")
print(f"Respaldo guardado en: {backup}")

WSGI_PATH.write_text(nuevo, encoding="utf-8")
print(f"WSGI reescrito en:    {WSGI_PATH}")
print()
print("Paso final: ve a la pestaña Web de PythonAnywhere y pulsa el botón verde RELOAD.")
