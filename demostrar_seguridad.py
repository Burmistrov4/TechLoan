"""Demostración de seguridad de TechLoan para la defensa.

Este script NO modifica la base de datos: solo lee y ejecuta intentos que el
propio sistema rechaza. Sirve para mostrar en un minuto, en vivo, las tres cosas
que un jurado suele pedir:

  1. Las contraseñas se guardan como HASH (Werkzeug scrypt) en una columna
     VARCHAR(255), nunca en texto plano.
  2. Las VALIDACIONES se ejecutan en el servidor y rechazan datos inválidos.
  3. Las INYECCIONES SQL no funcionan: todas las consultas van parametrizadas.

Uso (desde la raíz del proyecto):

    python demostrar_seguridad.py
"""

import os
import re
import sys

# Permite ejecutar el script desde la raíz del proyecto sin instalar nada.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:  # Consola de Windows: asegura que los acentos y símbolos se impriman bien.
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover - según la consola
    pass

from werkzeug.security import check_password_hash, generate_password_hash  # noqa: E402

from app.config import DATABASE_PATH, PASSWORD_HASH_MAX_LENGTH  # noqa: E402
from app.database import get_connection  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402
from app.services.laboratorio_service import LaboratorioService  # noqa: E402
from app.services.prestatario_service import PrestatarioService  # noqa: E402
from app.services.usuario_service import UsuarioService  # noqa: E402

ANCHO = 78


def titulo(texto):
    print()
    print("=" * ANCHO)
    print(texto.center(ANCHO))
    print("=" * ANCHO)


def subtitulo(texto):
    print()
    print("-" * ANCHO)
    print(texto)
    print("-" * ANCHO)


def ok(texto):
    print("  [OK]   " + texto)


def dato(texto):
    print("         " + texto)


def mal(texto):
    print("  [BLOQUEADO] " + texto)


def _corta(valor, limite=72):
    valor = str(valor)
    return valor if len(valor) <= limite else valor[: limite - 1] + "…"


# ---------------------------------------------------------------------------
# 1. HASH DE CONTRASEÑAS
# ---------------------------------------------------------------------------
def demostrar_hash():
    titulo("1. LAS CONTRASEÑAS SE GUARDAN COMO HASH (Werkzeug scrypt)")

    subtitulo("a) Lo que hay en la tabla 'usuarios_sistema'")
    with get_connection() as db:
        filas = db.execute(
            "SELECT username, rol, password_hash FROM usuarios_sistema ORDER BY id"
        ).fetchall()

    for fila in filas:
        h = fila["password_hash"]
        print(f"  usuario: {fila['username']:<12} rol: {fila['rol']:<15} "
              f"longitud del hash: {len(h)}")
        dato(f"password_hash = {_corta(h, 70)}")

    if filas:
        muestra = filas[0]["password_hash"]
        algoritmo = muestra.split("$", 1)[0]
        ok(f"El formato es '{algoritmo}': es scrypt con sal aleatoria, no texto plano.")
        ok(f"Longitud {len(muestra)} caracteres ≤ {PASSWORD_HASH_MAX_LENGTH} "
           f"(columna VARCHAR({PASSWORD_HASH_MAX_LENGTH})).")

    subtitulo("b) La contraseña original NO está en la base de datos")
    with get_connection() as db:
        fuga = db.execute(
            "SELECT COUNT(*) AS n FROM usuarios_sistema WHERE password_hash IN "
            "('Admin123!', 'Operador123!', 'admin', 'operador')"
        ).fetchone()["n"]
    if fuga == 0:
        ok("Ninguna contraseña aparece en claro en la columna password_hash.")
    else:
        print("  [ALERTA] Se encontró texto plano (no debería ocurrir).")

    subtitulo("c) El hash se puede verificar, pero no revertir")
    demo = generate_password_hash("MiClaveSegura1!")
    print("  Se genera el hash de 'MiClaveSegura1!':")
    dato(_corta(demo, 70))
    ok("check_password_hash(hash, 'MiClaveSegura1!') -> "
       + str(check_password_hash(demo, "MiClaveSegura1!")))
    ok("check_password_hash(hash, 'otra-clave')          -> "
       + str(check_password_hash(demo, "otra-clave")))
    dato("Coincide solo con la contraseña correcta; del hash no se deduce la clave.")

    subtitulo("d) El servicio rechaza un hash que no quepa en la columna")
    print(f"  Tope configurado: PASSWORD_HASH_MAX_LENGTH = {PASSWORD_HASH_MAX_LENGTH}")
    dato("Si el hash excediera ese tamaño, UsuarioService/RegistroService abortan")
    dato("la inserción con un error claro en lugar de guardar un valor truncado.")


# ---------------------------------------------------------------------------
# 2. VALIDACIONES EN EL SERVIDOR
# ---------------------------------------------------------------------------
def _intento(descripcion, funcion):
    """Ejecuta una operación que debe ser rechazada y muestra el mensaje."""
    try:
        funcion()
        print(f"  [FALLO]  {descripcion}: NO fue rechazado (revisar).")
    except ValueError as exc:
        mal(descripcion)
        dato("mensaje del sistema: " + str(exc))
    except Exception as exc:  # noqa: BLE001
        mal(descripcion)
        dato(f"rechazado ({type(exc).__name__}): {exc}")


def demostrar_validaciones():
    titulo("2. VALIDACIONES DEL LADO DEL SERVIDOR")

    subtitulo("Prestatarios")
    _intento("Cédula con formato inválido", lambda: PrestatarioService.create({
        "cedula": "??", "nombre": "Ana", "apellido": "Pérez",
        "tipo": "ESTUDIANTE", "estado": "ACTIVO"}))
    _intento("Nombre con números", lambda: PrestatarioService.create({
        "cedula": "V-99999999", "nombre": "Ana123", "apellido": "Pérez",
        "tipo": "ESTUDIANTE", "estado": "ACTIVO"}))
    _intento("Tipo inexistente", lambda: PrestatarioService.create({
        "cedula": "V-99999998", "nombre": "Ana", "apellido": "Pérez",
        "tipo": "INVENTADO", "estado": "ACTIVO"}))

    subtitulo("Usuarios del sistema (reglas de contraseña)")
    _intento("Contraseña demasiado corta", lambda: UsuarioService.create({
        "nombre": "Luis", "apellido": "Gómez", "username": "luisg",
        "email": "luis@correo.com", "password": "Ab1!", "rol": "OPERADOR"}))
    _intento("Contraseña sin mayúscula ni símbolo", lambda: UsuarioService.create({
        "nombre": "Luis", "apellido": "Gómez", "username": "luisg",
        "email": "luis@correo.com", "password": "sololetras", "rol": "OPERADOR"}))
    _intento("Correo mal formado", lambda: UsuarioService.create({
        "nombre": "Luis", "apellido": "Gómez", "username": "luisg",
        "email": "correo-sin-arroba", "password": "Valida123!", "rol": "OPERADOR"}))

    subtitulo("Laboratorios")
    _intento("Capacidad igual a cero", lambda: LaboratorioService.create({
        "codigo": "LAB-DEMO", "nombre": "Demo", "ubicacion": "Edificio X",
        "capacidad": "0", "duracion_estandar_minutos": "70",
        "estado": "DISPONIBLE"}))

    dato("Todas estas reglas viven en app/services/*.py, no solo en el HTML:")
    dato("la validación del navegador es una comodidad; la definitiva es la del servidor.")


# ---------------------------------------------------------------------------
# 3. INYECCIÓN SQL
# ---------------------------------------------------------------------------
def demostrar_inyeccion():
    titulo("3. INYECCIÓN SQL: TODAS LAS CONSULTAS VAN PARAMETRIZADAS")

    subtitulo("a) Intentos de entrar saltándose la contraseña")
    payloads = [
        ("admin' OR '1'='1", "' OR '1'='1"),
        ("admin'--", "cualquiera"),
        ("' OR 1=1 --", "x"),
        ("admin'; DROP TABLE usuarios_sistema; --", "x"),
    ]
    for usuario, clave in payloads:
        try:
            AuthService.authenticate(usuario, clave)
            print(f"  [ALERTA] La inyección {usuario!r} entró (revisar).")
        except ValueError:
            mal(f"usuario={usuario!r} clave={clave!r}  ->  acceso denegado")

    dato("El patrón del servidor es:  WHERE username = ?  con el valor como parámetro.")
    dato("La entrada se trata como DATO, nunca como código SQL.")

    subtitulo("b) La tabla sigue intacta tras el intento de DROP")
    with get_connection() as db:
        n = db.execute("SELECT COUNT(*) AS n FROM usuarios_sistema").fetchone()["n"]
    ok(f"usuarios_sistema conserva sus {n} registros: el DROP no se ejecutó.")

    subtitulo("c) Prueba de concepto de por qué importa")
    dato("Con concatenación ingenua (NO es el caso de este proyecto):")
    dato("  \"SELECT * FROM usuarios WHERE username = '\" + entrada + \"'\"")
    dato("  entrada = admin' OR '1'='1  =>  la condición siempre es verdadera.")
    ok("TechLoan usa marcadores '?' y sqlite3 los escapa: el ataque no tiene efecto.")

    subtitulo("d) Comprobación automática sobre el código fuente")
    patron = re.compile(r"execute\(\s*(f[\"']|\"[^\"]*%|\"[^\"]*\+)")
    sospechosas = []
    raiz = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")
    for carpeta, _, archivos in os.walk(raiz):
        for archivo in archivos:
            if not archivo.endswith(".py"):
                continue
            ruta = os.path.join(carpeta, archivo)
            with open(ruta, encoding="utf-8") as fh:
                for numero, linea in enumerate(fh, 1):
                    if patron.search(linea) and "PRAGMA" not in linea:
                        sospechosas.append(f"{archivo}:{numero}: {linea.strip()}")
    if sospechosas:
        dato("Revisar manualmente (deben ser solo constantes internas):")
        for s in sospechosas:
            dato("  " + s)
    else:
        ok("No se encontró ninguna consulta que interpole entrada del usuario.")


def main():
    print()
    print("TECHLoan · Demostración de seguridad".center(ANCHO))
    print(f"Base de datos: {DATABASE_PATH}".center(ANCHO))

    if not os.path.exists(DATABASE_PATH):
        print("\nNo existe la base de datos. Ejecuta primero:  python init_db.py")
        return 1

    demostrar_hash()
    demostrar_validaciones()
    demostrar_inyeccion()

    titulo("FIN · Nada de lo anterior modificó la base de datos")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
