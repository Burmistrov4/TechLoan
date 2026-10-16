"""Diagnóstico del ciclo de registro en el servidor (producción).

Responde, con datos reales de la base de datos y del entorno, a la pregunta
«¿por qué no confirma el enlace del correo?». Está pensado para ejecutarse en la
consola Bash de PythonAnywhere, donde el fallo solo se manifiesta en Producción.

Uso (en la consola Bash de PythonAnywhere, dentro del proyecto)::

    cd ~/TechLoan
    python3 deploy/diagnostico_registro.py

Qué comprueba, en orden:

1. La ruta de la base de datos que usa realmente la aplicación.
2. Si hay SMTP configurado y con qué valores (la contraseña se oculta).
3. La URL_BASE: si está mal, todos los enlaces apuntan a un dominio que no existe.
4. Las últimas 10 cuentas creadas, con su estado de confirmación.
5. Los últimos 10 tokens: usados, caducados, y a qué usuario pertenecen.
6. **La prueba que delata el fallo**: para cada cuenta sin confirmar, reconstruye
   el enlace que se habría enviado y comprueba si ese token existe y está usable.

No envía correos, no modifica nada y no muestra la contraseña.
"""

import os
import re
import sys
from datetime import datetime
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

# Mismo orden que el archivo WSGI: la ruta del proyecto antes de importar la app.
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import app.config as config          # noqa: E402
import app.database as database      # noqa: E402
from app.services import correo_service   # noqa: E402
from app.services.registro_service import RegistroService  # noqa: E402

SEP = "=" * 74


def titulo(texto):
    print()
    print(SEP)
    print(texto)
    print(SEP)


def main():
    titulo("1. BASE DE DATOS")
    print(f"  DATABASE_PATH que usa la app : {database.DATABASE_PATH}")
    print(f"  ¿existe el archivo?          : {Path(database.DATABASE_PATH).exists()}")
    with database.get_connection() as db:
        for tabla in ("usuarios_sistema", "tokens_correo"):
            total = db.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0]
            print(f"  filas en {tabla:<18}: {total}")

    titulo("2. CORREO (SMTP)")
    if correo_service.configurado():
        print(f"  modo                        : {correo_service.modo()}")
        print(f"  TECHLOAN_SMTP_HOST          : {correo_service.SMTP_HOST}")
        print(f"  TECHLOAN_SMTP_PORT          : {correo_service.SMTP_PORT}")
        print(f"  TECHLOAN_SMTP_USER          : {correo_service.SMTP_USER}")
        print(f"  TECHLOAN_SMTP_TLS (STARTTLS): {correo_service.SMTP_TLS}")
        print(f"  contraseña definida         : {'sí' if correo_service.SMTP_PASSWORD else 'NO — ¡aquí está el fallo!'}")
        print(f"  longitud de la contraseña   : {len(correo_service.SMTP_PASSWORD)} carácter(es)")
        if correo_service.SMTP_PASSWORD and " " in correo_service.SMTP_PASSWORD:
            print("  ¡OJO! La contraseña tiene espacios.")
            print("  Google la muestra en grupos de 4 letras: quítale los espacios.")
    else:
        print("  modo: demostración (no hay TECHLOAN_SMTP_HOST).")
        print("  El correo se guarda en database/buzon/ y el enlace sale en pantalla.")

    titulo("3. URL DE LOS ENLACES")
    print(f"  TECHLOAN_URL_BASE           : {config.URL_BASE}")
    esperada = "https://" + os.environ.get("USER", "TU_USUARIO") + ".pythonanywhere.com"
    if config.URL_BASE.rstrip("/") != esperada.rstrip("/"):
        print()
        print(f"  ¡ATENCIÓN! Debería ser: {esperada}")
        print("  Si URL_BASE está mal, el enlace del correo apunta a un dominio")
        print("  que no existe y la cuenta nunca se confirma.")
    else:
        print("  (coincide con el dominio de esta cuenta)")

    titulo("4. ÚLTIMAS CUENTAS CREADAS")
    with database.get_connection() as db:
        filas = db.execute(
            """SELECT id, username, email, email_confirmado, fecha_registro
                 FROM usuarios_sistema ORDER BY id DESC LIMIT 10"""
        ).fetchall()
        if not filas:
            print("  (no hay cuentas)")
        for f in filas:
            marca = "CONFIRMADA " if f["email_confirmado"] else "SIN CONFIRMAR"
            print(f"  #{f['id']:<4} {f['username']:<22} {marca}  {f['email']}")

    titulo("5. ÚLTIMOS TOKENS")
    with database.get_connection() as db:
        tokens = db.execute(
            """SELECT t.id, t.usuario_id, t.token, t.usado, t.fecha_expiracion,
                      t.fecha_creacion, u.username, u.email_confirmado
                 FROM tokens_correo t
                 JOIN usuarios_sistema u ON u.id = t.usuario_id
                ORDER BY t.id DESC LIMIT 10"""
        ).fetchall()
        if not tokens:
            print("  (no se ha emitido ningún token)")
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for t in tokens:
            estado = []
            if t["usado"]:
                estado.append("USADO")
            if t["fecha_expiracion"] < ahora:
                estado.append("CADUCADO")
            if t["email_confirmado"]:
                estado.append("cuenta ya confirmada")
            if not estado:
                estado.append("VÁLIDO")
            print(f"  #{t['id']:<4} usuario {t['username']:<20} {'/'.join(estado):<34} "
                  f"expira {t['fecha_expiracion']}")

    titulo("6. PRUEBA DEFINITIVA: ¿confirmaría el enlace que se envió?")
    with database.get_connection() as db:
        pendientes = db.execute(
            """SELECT u.id, u.username, u.email, u.email_confirmado
                 FROM usuarios_sistema u
                WHERE u.email_confirmado = 0
                ORDER BY u.id DESC LIMIT 10"""
        ).fetchall()

        if not pendientes:
            print("  No hay cuentas pendientes de confirmar. Nada que reproducir.")
        for u in pendientes:
            # El último token emitido para esa cuenta es el que fue por correo.
            t = db.execute(
                """SELECT token, usado, fecha_expiracion FROM tokens_correo
                    WHERE usuario_id = ? ORDER BY id DESC LIMIT 1""",
                (u["id"],),
            ).fetchone()
            print()
            print(f"  Cuenta #{u['id']} «{u['username']}» ({u['email']})")
            if not t:
                print("    -> NO tiene ningún token: el correo nunca se generó.")
                print("       El registro falló ANTES de crear el token.")
                continue

            enlace = f"{config.URL_BASE}/confirmar/{t['token']}"
            print(f"    enlace que se habría enviado:")
            print(f"      {enlace}")
            print(f"    token usado      : {t['usado']}")
            print(f"    token caducado   : {t['fecha_expiracion'] < ahora} "
                  f"(expira {t['fecha_expiracion']})")

            # Se reproduce la comprobación que hace RegistroService.confirmar().
            if t["usado"] and not u["email_confirmado"]:
                print("    -> DIAGNÓSTICO: el token ya está usado y la cuenta sigue")
                print("       sin confirmar. Ese es el error que ve el usuario.")
                print("       CAUSA habitual: algo abrió el enlace antes que la persona")
                print("       (antivirus del correo, vista previa, doble clic).")
                print("       SOLUCIÓN: pedir un enlace nuevo en /reenviar.")
            elif t["fecha_expiracion"] < ahora:
                print("    -> DIAGNÓSTICO: el token caducó. Pide uno nuevo en /reenviar.")
            else:
                print("    -> El token está usable: al abrirlo debería confirmar.")

    titulo("7. ¿SE PUEDE CONECTAR AL SMTP?")
    if not correo_service.configurado():
        print("  No hay SMTP configurado, así que no hay nada que comprobar.")
    else:
        try:
            import smtplib
            with smtplib.SMTP(correo_service.SMTP_HOST, correo_service.SMTP_PORT,
                              timeout=10) as servidor:
                if correo_service.SMTP_TLS:
                    servidor.starttls()
                if correo_service.SMTP_USER:
                    servidor.login(correo_service.SMTP_USER, correo_service.SMTP_PASSWORD)
            print("  Conexión y autenticación SMTP: CORRECTAS.")
            print("  El problema no es el acceso al servidor de correo.")
        except Exception as exc:  # noqa: BLE001
            print(f"  Conexión/autenticación SMTP: FALLA -> {type(exc).__name__}: {exc}")
            print()
            print("  Posibles causas:")
            print("   - La contraseña de aplicación de Google no es válida o caducó.")
            print("   - La cuenta de Gmail no tiene la verificación en dos pasos activa.")
            print("   - PythonAnywhere está bloqueando la salida por el puerto SMTP.")
            print("   - Se agotó la cuota de envío de Gmail.")
            print()
            print("  Mientras tanto la app funciona en modo demostración: el enlace")
            print("  aparece en pantalla y la cuenta se confirma igual.")

    print()
    print("Fin del diagnóstico. Pega esta salida completa para interpretarla.")


if __name__ == "__main__":
    main()
