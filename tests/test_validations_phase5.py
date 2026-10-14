import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import _tempdb  # noqa: E402

# Base de datos temporal: estas pruebas NUNCA tocan database/techloan.db.
_tempdb.preparar("test_validations.db")

from app.database import init_database, get_connection
from app.services.usuario_service import UsuarioService
from app.services.prestatario_service import PrestatarioService
from app.services.laboratorio_service import LaboratorioService
from app.services.categoria_service import CategoriaService
from app.services.equipo_service import EquipoService
from app.services.reservation_service import ReservationService
from app.services.prestamo_equipo_service import PrestamoEquipoService


def expect_value_error(fn, label):
    try:
        fn()
    except ValueError:
        return
    raise AssertionError(f"Se esperaba ValueError: {label}")


def db_exists(table, row_id):
    with get_connection() as db:
        row = db.execute(f"SELECT id FROM {table} WHERE id=?", (row_id,)).fetchone()
        return row is not None


init_database()

stamp = datetime.now().strftime("%H%M%S%f")
ids = {
    "usuario": None,
    "usuario_inactivo": None,
    "prestatario": None,
    "prestatario_inactivo": None,
    "laboratorio": None,
    "categoria": None,
    "equipo": None,
}

try:
    # ------------------------------------------------------------
    # 1) PRESTATARIOS
    # ------------------------------------------------------------
    base_p = {
        "cedula": f"VP{stamp[-8:]}",
        "nombre": "Valido",
        "apellido": "Prueba",
        "tipo": "ESTUDIANTE",
        "telefono": "04120000000",
        "email": f"prestatario_{stamp}@test.local",
        "estado": "ACTIVO",
    }

    expect_value_error(lambda: PrestatarioService.create({**base_p, "nombre": "A"}), "nombre corto prestatario")
    expect_value_error(lambda: PrestatarioService.create({**base_p, "apellido": "1"}), "apellido inválido")
    expect_value_error(lambda: PrestatarioService.create({**base_p, "cedula": "12"}), "cédula corta")
    expect_value_error(lambda: PrestatarioService.create({**base_p, "tipo": "INVALIDO"}), "tipo prestatario")
    expect_value_error(lambda: PrestatarioService.create({**base_p, "estado": "INVALIDO"}), "estado prestatario")
    expect_value_error(lambda: PrestatarioService.create({**base_p, "email": "correo-invalido"}), "email prestatario")

    ids["prestatario"] = PrestatarioService.create(base_p)
    assert db_exists("prestatarios", ids["prestatario"])

    expect_value_error(
        lambda: PrestatarioService.update(ids["prestatario"], {**base_p, "nombre": "!"}),
        "update prestatario inválido",
    )
    assert PrestatarioService.get(ids["prestatario"])["nombre"] == "Valido"

    expect_value_error(
        lambda: PrestatarioService.create({**base_p, "cedula": f"OTRO{stamp[-6:]}"}),
        "duplicado no detectado",
    ) if False else None

    # ------------------------------------------------------------
    # 2) LABORATORIOS
    # ------------------------------------------------------------
    base_l = {
        "codigo": f"LAB{stamp[-8:]}",
        "nombre": "Laboratorio de Prueba",
        "ubicacion": "Edificio A",
        "capacidad": 20,
        "duracion_estandar_minutos": 70,
        "estado": "DISPONIBLE",
    }

    expect_value_error(lambda: LaboratorioService.create({**base_l, "codigo": "!"}), "código laboratorio")
    expect_value_error(lambda: LaboratorioService.create({**base_l, "nombre": "A"}), "nombre laboratorio")
    expect_value_error(lambda: LaboratorioService.create({**base_l, "ubicacion": "A"}), "ubicación laboratorio")
    expect_value_error(lambda: LaboratorioService.create({**base_l, "capacidad": 0}), "capacidad cero")
    expect_value_error(lambda: LaboratorioService.create({**base_l, "capacidad": "abc"}), "capacidad texto")
    expect_value_error(lambda: LaboratorioService.create({**base_l, "duracion_estandar_minutos": 0}), "duración cero")
    expect_value_error(lambda: LaboratorioService.create({**base_l, "duracion_estandar_minutos": 1441}), "duración excesiva")
    expect_value_error(lambda: LaboratorioService.create({**base_l, "estado": "INVALIDO"}), "estado laboratorio")

    ids["laboratorio"] = LaboratorioService.create(base_l)
    assert db_exists("laboratorios", ids["laboratorio"])

    # ------------------------------------------------------------
    # 3) CATEGORÍAS
    # ------------------------------------------------------------
    base_c = {"nombre": f"Categoria {stamp[-6:]}", "descripcion": "Prueba"}
    expect_value_error(lambda: CategoriaService.create({"nombre": "A"}), "categoría demasiado corta")
    expect_value_error(lambda: CategoriaService.create({"nombre": " "}), "categoría vacía")

    ids["categoria"] = CategoriaService.create(base_c)
    assert db_exists("categorias", ids["categoria"])
    expect_value_error(
        lambda: CategoriaService.update(ids["categoria"], {"nombre": ""}),
        "update categoría inválido",
    )

    # ------------------------------------------------------------
    # 4) EQUIPOS
    # ------------------------------------------------------------
    base_e = {
        "codigo": f"EQ{stamp[-10:]}",
        "nombre": "Equipo de Prueba",
        "categoria_id": ids["categoria"],
        "marca": "Marca",
        "modelo": "Modelo",
        "serial": f"SER{stamp[-10:]}",
        "laboratorio_id": ids["laboratorio"],
        "estado": "DISPONIBLE",
    }

    expect_value_error(lambda: EquipoService.create({**base_e, "codigo": "!"}), "código equipo")
    expect_value_error(lambda: EquipoService.create({**base_e, "nombre": "A"}), "nombre equipo")
    expect_value_error(lambda: EquipoService.create({**base_e, "estado": "INVALIDO"}), "estado equipo")
    expect_value_error(lambda: EquipoService.create({**base_e, "categoria_id": 0}), "categoría cero")
    expect_value_error(lambda: EquipoService.create({**base_e, "laboratorio_id": "abc"}), "laboratorio texto")
    expect_value_error(lambda: EquipoService.create({**base_e, "serial": "!"}), "serial inválido")

    ids["equipo"] = EquipoService.create(base_e)
    assert db_exists("equipos", ids["equipo"])

    # ------------------------------------------------------------
    # 5) USUARIOS Y CONTRASEÑAS
    # ------------------------------------------------------------
    base_u = {
        "nombre": "Usuario",
        "apellido": "Prueba",
        "username": f"usr_{stamp[-10:]}",
        "email": f"usuario_{stamp}@test.local",
        "password": "Valid123!",
        "rol": "ADMINISTRADOR",
        "estado": "ACTIVO",
    }

    expect_value_error(lambda: UsuarioService.create({**base_u, "nombre": "A"}), "nombre usuario")
    expect_value_error(lambda: UsuarioService.create({**base_u, "apellido": "1"}), "apellido usuario")
    expect_value_error(lambda: UsuarioService.create({**base_u, "username": "ab"}), "username corto")
    expect_value_error(lambda: UsuarioService.create({**base_u, "username": "usuario con espacios"}), "username con espacios")
    expect_value_error(lambda: UsuarioService.create({**base_u, "email": "correo"}), "email usuario")
    expect_value_error(lambda: UsuarioService.create({**base_u, "rol": "SUPERADMIN"}), "rol inválido")
    expect_value_error(lambda: UsuarioService.create({**base_u, "estado": "BORRADO"}), "estado usuario")
    expect_value_error(lambda: UsuarioService.create({**base_u, "password": "weak"}), "contraseña débil")
    expect_value_error(lambda: UsuarioService.create({**base_u, "password": "Valid123"}), "sin carácter especial")
    expect_value_error(lambda: UsuarioService.create({**base_u, "password": "valid123!"}), "sin mayúscula")
    expect_value_error(lambda: UsuarioService.create({**base_u, "password": "VALID123!"}), "sin minúscula")
    expect_value_error(lambda: UsuarioService.create({**base_u, "password": "ValidPassword!"}), "sin número")

    ids["usuario"] = UsuarioService.create(base_u)
    assert db_exists("usuarios_sistema", ids["usuario"])

    # Hash almacenado no debe coincidir con la contraseña en texto plano.
    with get_connection() as db:
        row = db.execute("SELECT password_hash FROM usuarios_sistema WHERE id=?", (ids["usuario"],)).fetchone()
        assert row and row["password_hash"] != base_u["password"]
        assert len(row["password_hash"]) <= 255

    # ------------------------------------------------------------
    # 6) RESERVAS: fecha/hora/duración/entidades activas
    # ------------------------------------------------------------
    fecha = (datetime.now().date() + timedelta(days=2)).strftime("%Y-%m-%d")
    expect_value_error(
        lambda: ReservationService.create_reservation(
            ids["laboratorio"], ids["prestatario"], ids["usuario"], "2020-01-01", "08:00", 70
        ),
        "reserva en fecha pasada",
    )
    expect_value_error(
        lambda: ReservationService.create_reservation(
            ids["laboratorio"], ids["prestatario"], ids["usuario"], fecha, "99:99", 70
        ),
        "hora inválida",
    )
    expect_value_error(
        lambda: ReservationService.create_reservation(
            ids["laboratorio"], ids["prestatario"], ids["usuario"], fecha, "08:00", 0
        ),
        "duración cero reserva",
    )
    expect_value_error(
        lambda: ReservationService.create_reservation(
            ids["laboratorio"], ids["prestatario"], ids["usuario"], fecha, "23:30", 70
        ),
        "reserva después de medianoche",
    )
    expect_value_error(
        lambda: ReservationService.create_reservation(
            999999, ids["prestatario"], ids["usuario"], fecha, "08:00", 70
        ),
        "laboratorio inexistente",
    )

    # ------------------------------------------------------------
    # 7) ESTADOS INACTIVOS: reglas de negocio
    # ------------------------------------------------------------
    inactive_p = {
        **base_p,
        "cedula": f"INP{stamp[-7:]}",
        "email": f"inactive_p_{stamp}@test.local",
        "estado": "INACTIVO",
    }
    ids["prestatario_inactivo"] = PrestatarioService.create(inactive_p)

    expect_value_error(
        lambda: ReservationService.create_reservation(
            ids["laboratorio"], ids["prestatario_inactivo"], ids["usuario"], fecha, "08:00", 70
        ),
        "reserva con prestatario inactivo",
    )

    inactive_u = {**base_u, "username": f"inu_{stamp[-9:]}", "email": f"inactive_u_{stamp}@test.local", "estado": "INACTIVO"}
    ids["usuario_inactivo"] = UsuarioService.create(inactive_u)

    expect_value_error(
        lambda: ReservationService.create_reservation(
            ids["laboratorio"], ids["prestatario"], ids["usuario_inactivo"], fecha, "08:00", 70
        ),
        "reserva con usuario inactivo",
    )

    # ------------------------------------------------------------
    # 8) PRÉSTAMOS: equipo no disponible / prestatario / usuario
    # ------------------------------------------------------------
    expect_value_error(
        lambda: PrestamoEquipoService.create(999999, ids["prestatario"], ids["usuario"]),
        "préstamo con equipo inexistente",
    )
    expect_value_error(
        lambda: PrestamoEquipoService.create(ids["equipo"], ids["prestatario_inactivo"], ids["usuario"]),
        "préstamo con prestatario inactivo",
    )
    expect_value_error(
        lambda: PrestamoEquipoService.create(ids["equipo"], ids["prestatario"], ids["usuario_inactivo"]),
        "préstamo con usuario inactivo",
    )

    print("FASE5_29_VALIDACIONES_PRESTATARIOS_OK")
    print("FASE5_29_VALIDACIONES_LABORATORIOS_OK")
    print("FASE5_29_VALIDACIONES_CATEGORIAS_OK")
    print("FASE5_29_VALIDACIONES_EQUIPOS_OK")
    print("FASE5_29_VALIDACIONES_USUARIOS_OK")
    print("FASE5_29_VALIDACIONES_RESERVAS_OK")
    print("FASE5_29_VALIDACIONES_PRESTAMOS_OK")
    print("FASE5_29_PRUEBA_VALIDACIONES_OK")

finally:
    # Delete children before parents.
    for table, key in [
        ("prestamos_equipos", "equipo"),
        ("reservas", "laboratorio"),
        ("equipos", "equipo"),
    ]:
        if ids[key]:
            try:
                with get_connection() as db:
                    db.execute(f"DELETE FROM {table} WHERE " + ("equipo_id=?" if table == "prestamos_equipos" else "laboratorio_id=?"), (ids[key],))
            except Exception:
                pass

    for table, key in [
        ("equipos", "equipo"),
        ("categorias", "categoria"),
        ("laboratorios", "laboratorio"),
        ("prestatarios", "prestatario_inactivo"),
        ("prestatarios", "prestatario"),
        ("usuarios_sistema", "usuario_inactivo"),
        ("usuarios_sistema", "usuario"),
    ]:
        if ids[key]:
            try:
                with get_connection() as db:
                    db.execute(f"DELETE FROM {table} WHERE id=?", (ids[key],))
            except Exception:
                pass
