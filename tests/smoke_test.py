"""Prueba smoke moderna de TechLoan.

Verificación rápida de extremo a extremo: esquema, claves foráneas, hash de
contraseñas, reglas de negocio y arranque de la aplicación web.

Sustituye a la prueba smoke antigua, que era incompatible con la arquitectura
actual (llamaba a ``AuthService.register``, método que ya no existe, y esperaba
que el usuario autenticado incluyera ``password_hash``, algo que el servicio
elimina deliberadamente por seguridad).

Uso::

    PYTHONPATH=. python tests/smoke_test.py
"""

import sys
from datetime import date, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from werkzeug.security import check_password_hash  # noqa: E402

from app.database import get_connection, init_database  # noqa: E402
from app.server import create_app  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402
from app.services.reservation_service import ReservationService  # noqa: E402

MARCA = "SMOKE-TEST"

TABLAS_ESPERADAS = {
    "usuarios_sistema",
    "prestatarios",
    "laboratorios",
    "categorias",
    "equipos",
    "reservas",
    "prestamos_equipos",
}


def limpiar():
    """Elimina los registros creados por esta prueba (idempotente)."""
    with get_connection() as db:
        db.execute("DELETE FROM reservas WHERE observaciones = ?", (MARCA,))
        db.execute("DELETE FROM prestatarios WHERE cedula = ?", (MARCA,))
        db.execute("DELETE FROM laboratorios WHERE codigo = ?", (MARCA,))


def test_esquema():
    init_database()
    with get_connection() as db:
        tablas = {
            fila["name"]
            for fila in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        claves_foraneas = db.execute("PRAGMA foreign_keys").fetchone()[0]
        indices = {
            fila["name"]
            for fila in db.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            ).fetchall()
        }

    faltantes = TABLAS_ESPERADAS - tablas
    assert not faltantes, f"Faltan tablas: {faltantes}"
    assert claves_foraneas == 1, "Las claves foráneas deben estar activas"
    assert indices, "Deben existir los índices declarados en schema.sql"

    print("SMOKE_ESQUEMA_OK")


def test_seguridad_password():
    with get_connection() as db:
        fila = db.execute(
            "SELECT username, password_hash FROM usuarios_sistema ORDER BY id LIMIT 1"
        ).fetchone()
    assert fila is not None, "Debe existir al menos un usuario del sistema"

    # La contraseña se almacena como hash, nunca en texto plano.
    assert fila["password_hash"] != "Admin123!", "La contraseña no debe guardarse en claro"
    assert fila["password_hash"].startswith("scrypt:"), "El hash debe generarlo Werkzeug"
    assert len(fila["password_hash"]) <= 255, "El hash debe caber en VARCHAR(255)"

    # El usuario autenticado NUNCA debe exponer el hash.
    usuario = AuthService.authenticate("admin", "Admin123!")
    assert usuario is not None, "El usuario admin debe autenticarse"
    assert usuario["rol"] == "ADMINISTRADOR", "El rol debe ser ADMINISTRADOR"
    assert "password_hash" not in usuario, "El hash no debe exponerse en la sesión"

    # La contraseña almacenada corresponde a la contraseña conocida.
    assert check_password_hash(fila["password_hash"], "Admin123!"), "El hash debe validar"

    print("SMOKE_PASSWORD_HASH_OK")


def test_regla_solapamiento():
    limpiar()
    fecha = (date.today() + timedelta(days=90)).strftime("%Y-%m-%d")

    with get_connection() as db:
        db.execute(
            "INSERT INTO prestatarios (cedula, nombre, apellido, tipo) VALUES (?,?,?,?)",
            (MARCA, "Prueba", "Smoke", "ESTUDIANTE"),
        )
        db.execute(
            "INSERT INTO laboratorios (codigo, nombre, ubicacion, capacidad) VALUES (?,?,?,?)",
            (MARCA, "Laboratorio Smoke", "Aula Smoke", 20),
        )
        prestatario_id = db.execute(
            "SELECT id FROM prestatarios WHERE cedula=?", (MARCA,)
        ).fetchone()["id"]
        laboratorio_id = db.execute(
            "SELECT id FROM laboratorios WHERE codigo=?", (MARCA,)
        ).fetchone()["id"]
        usuario_id = db.execute(
            "SELECT id FROM usuarios_sistema ORDER BY id LIMIT 1"
        ).fetchone()["id"]

    # Primera reserva: 08:00 + 70 min → 09:10
    ReservationService.create_reservation(
        laboratorio_id, prestatario_id, usuario_id, fecha, "08:00", 70, MARCA
    )

    # Reserva adyacente (09:10–10:20): debe permitirse.
    ReservationService.create_reservation(
        laboratorio_id, prestatario_id, usuario_id, fecha, "09:10", 70, MARCA
    )

    # Reserva solapada (09:30–10:40): debe rechazarse.
    try:
        ReservationService.create_reservation(
            laboratorio_id, prestatario_id, usuario_id, fecha, "09:30", 70, MARCA
        )
    except ValueError as exc:
        assert "superpone" in str(exc), f"Mensaje inesperado: {exc}"
    else:
        raise AssertionError("Se permitió una reserva solapada")

    limpiar()
    print("SMOKE_SOLAPAMIENTO_OK")


def test_arranque_web():
    app = create_app()
    cliente = app.test_client()

    respuesta = cliente.get("/health")
    assert respuesta.status_code == 200, "/health debe responder 200"
    assert respuesta.get_json()["ok"] is True, "/health debe devolver ok"

    respuesta = cliente.get("/")
    assert respuesta.status_code == 302, "Sin sesión, / debe redirigir al login"

    respuesta = cliente.get("/login")
    assert respuesta.status_code == 200, "El formulario de acceso debe responder 200"
    html = respuesta.get_data(as_text=True)
    assert "<!DOCTYPE html>" in html, "La página debe ser HTML5"
    assert 'name="viewport"' in html, "La página debe ser responsive"

    print("SMOKE_ARRANQUE_WEB_OK")


def main():
    test_esquema()
    test_seguridad_password()
    test_regla_solapamiento()
    test_arranque_web()
    print("SMOKE_TEST_OK")


if __name__ == "__main__":
    main()
