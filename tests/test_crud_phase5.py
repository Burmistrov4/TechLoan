from datetime import date, timedelta

from app.database import init_database, get_connection
from app.services.prestatario_service import PrestatarioService
from app.services.laboratorio_service import LaboratorioService
from app.services.categoria_service import CategoriaService
from app.services.equipo_service import EquipoService
from app.services.usuario_service import UsuarioService
from app.services.auth_service import AuthService
from app.services.reservation_service import ReservationService
from app.services.prestamo_equipo_service import PrestamoEquipoService
from app.services.disponibilidad_service import DisponibilidadService
from app.services.historial_service import HistorialService


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    init_database()

    with get_connection() as db:
        active_admin = db.execute(
            "SELECT id FROM usuarios_sistema WHERE rol='ADMINISTRADOR' AND estado='ACTIVO' ORDER BY id LIMIT 1"
        ).fetchone()
    assert_true(active_admin is not None, "Se requiere un administrador activo para la prueba.")
    admin_id = active_admin["id"]

    suffix = "P28"
    ids = {"usuario": None, "prestatario": None, "lab": None, "categoria": None,
           "equipo": None, "reserva": None, "prestamo": None}

    try:
        # 1) USUARIO: CREATE -> READ -> UPDATE -> AUTH -> DELETE
        ids["usuario"] = UsuarioService.create({
            "nombre": "Operador",
            "apellido": "CRUD",
            "username": "op_" + suffix.lower(),
            "email": "op_" + suffix.lower() + "@techloan.local",
            "password": "CrudTest123!",
            "rol": "OPERADOR",
            "estado": "ACTIVO",
        })
        user = UsuarioService.get(ids["usuario"])
        assert_true(user and user["rol"] == "OPERADOR", "Usuario CREATE/READ falló.")
        UsuarioService.update(ids["usuario"], {
            "nombre": "Operador",
            "apellido": "Actualizado",
            "username": "op_" + suffix.lower(),
            "email": "op_" + suffix.lower() + "@techloan.local",
            "password": "",
            "rol": "OPERADOR",
            "estado": "ACTIVO",
        })
        assert_true(UsuarioService.get(ids["usuario"])["apellido"] == "Actualizado",
                    "Usuario UPDATE falló.")
        authenticated = AuthService.authenticate("op_" + suffix.lower(), "CrudTest123!")
        assert_true(authenticated["id"] == ids["usuario"], "Autenticación del usuario CRUD falló.")

        # 2) PRESTATARIO
        ids["prestatario"] = PrestatarioService.create({
            "cedula": "P28-0001",
            "nombre": "Prestatario",
            "apellido": "CRUD",
            "tipo": "ESTUDIANTE",
            "telefono": "0414000000",
            "email": "prestatario.p28@techloan.local",
            "estado": "ACTIVO",
        })
        assert_true(PrestatarioService.get(ids["prestatario"]) is not None,
                    "Prestatario CREATE/READ falló.")
        PrestatarioService.update(ids["prestatario"], {
            "cedula": "P28-0001",
            "nombre": "Prestatario",
            "apellido": "Actualizado",
            "tipo": "PROFESOR",
            "telefono": "0414111111",
            "email": "prestatario.p28@techloan.local",
            "estado": "ACTIVO",
        })
        assert_true(PrestatarioService.get(ids["prestatario"])["tipo"] == "PROFESOR",
                    "Prestatario UPDATE falló.")

        # 3) LABORATORIO
        ids["lab"] = LaboratorioService.create({
            "codigo": "LAB-P28",
            "nombre": "Laboratorio CRUD",
            "ubicacion": "Aula P28",
            "capacidad": 20,
            "duracion_estandar_minutos": 70,
            "estado": "DISPONIBLE",
        })
        assert_true(LaboratorioService.get(ids["lab"])["duracion_estandar_minutos"] == 70,
                    "Laboratorio CREATE/READ falló.")
        LaboratorioService.update(ids["lab"], {
            "codigo": "LAB-P28",
            "nombre": "Laboratorio Actualizado",
            "ubicacion": "Aula P29",
            "capacidad": 25,
            "duracion_estandar_minutos": 80,
            "estado": "DISPONIBLE",
        })
        lab = LaboratorioService.get(ids["lab"])
        assert_true(lab["capacidad"] == 25 and lab["duracion_estandar_minutos"] == 80,
                    "Laboratorio UPDATE falló.")

        # 4) CATEGORIA
        ids["categoria"] = CategoriaService.create({
            "nombre": "Categoria P28",
            "descripcion": "Prueba CRUD Fase 5",
        })
        assert_true(CategoriaService.get(ids["categoria"]) is not None,
                    "Categoría CREATE/READ falló.")
        CategoriaService.update(ids["categoria"], {
            "nombre": "Categoria P28 Actualizada",
            "descripcion": "Descripción actualizada",
        })
        assert_true(CategoriaService.get(ids["categoria"])["nombre"] == "Categoria P28 Actualizada",
                    "Categoría UPDATE falló.")

        # 5) EQUIPO + relaciones
        ids["equipo"] = EquipoService.create({
            "codigo": "EQ-P28",
            "nombre": "Equipo CRUD",
            "categoria_id": ids["categoria"],
            "marca": "MarcaTest",
            "modelo": "M-P28",
            "serial": "SER-P28",
            "laboratorio_id": ids["lab"],
            "estado": "DISPONIBLE",
        })
        equipo = EquipoService.get(ids["equipo"])
        assert_true(equipo and equipo["categoria_id"] == ids["categoria"]
                    and equipo["laboratorio_id"] == ids["lab"],
                    "Equipo CREATE/READ o relaciones fallaron.")
        EquipoService.update(ids["equipo"], {
            "codigo": "EQ-P28",
            "nombre": "Equipo Actualizado",
            "categoria_id": ids["categoria"],
            "marca": "MarcaTest",
            "modelo": "M-P28-2",
            "serial": "SER-P28",
            "laboratorio_id": ids["lab"],
            "estado": "DISPONIBLE",
        })
        assert_true(EquipoService.get(ids["equipo"])["modelo"] == "M-P28-2",
                    "Equipo UPDATE falló.")

        # 6) RESERVA + disponibilidad
        fecha = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d")
        ids["reserva"] = ReservationService.create_reservation(
            ids["lab"], ids["prestatario"], admin_id, fecha, "10:00", 70, "CRUD Fase 5"
        )
        lab_available, _ = DisponibilidadService.laboratorio(
            ids["lab"], fecha, "10:00", "11:10"
        )
        assert_true(not lab_available, "Disponibilidad de laboratorio no detectó reserva.")
        reservation = next(
            (r for r in ReservationService.list_all() if r["id"] == ids["reserva"]), None
        )
        assert_true(reservation is not None, "Reserva CREATE/READ falló.")

        # 7) PRESTAMO + DEVOLUCIÓN
        ids["prestamo"] = PrestamoEquipoService.create(
            ids["equipo"], ids["prestatario"], admin_id, "Préstamo CRUD Fase 5"
        )
        assert_true(EquipoService.get(ids["equipo"])["estado"] == "PRESTADO",
                    "Préstamo no cambió estado del equipo.")
        equipment_available, _ = DisponibilidadService.equipo(ids["equipo"])
        assert_true(not equipment_available, "Disponibilidad de equipo no detectó préstamo activo.")
        PrestamoEquipoService.return_equipment(ids["prestamo"])
        assert_true(EquipoService.get(ids["equipo"])["estado"] == "DISPONIBLE",
                    "Devolución no restituyó DISPONIBLE.")

        # 8) HISTORIAL: debe conservar préstamo y devolución mientras existan registros
        history = HistorialService.list_all(prestatario_id=ids["prestatario"])
        assert_true(any(r["tipo"] == "RESERVA" and r["referencia_id"] == ids["reserva"] for r in history),
                    "Historial no contiene la reserva.")
        assert_true(any(r["tipo"] == "PRESTAMO" and r["referencia_id"] == ids["prestamo"] for r in history),
                    "Historial no contiene el préstamo.")
        assert_true(any(r["tipo"] == "DEVOLUCION" and r["referencia_id"] == ids["prestamo"] for r in history),
                    "Historial no contiene la devolución.")

        print("FASE5_28_CRUD_CREATE_READ_UPDATE_OK")
        print("FASE5_28_RELACIONES_RESERVA_PRESTAMO_OK")
        print("FASE5_28_HISTORIAL_OK")
        print("FASE5_28_PRUEBA_INTEGRAL_OK")

    finally:
        # Eliminar dependencias en orden inverso.
        with get_connection() as db:
            if ids["prestamo"]:
                db.execute("DELETE FROM prestamos_equipos WHERE id=?", (ids["prestamo"],))
            if ids["reserva"]:
                db.execute("DELETE FROM reservas WHERE id=?", (ids["reserva"],))
        if ids["equipo"]:
            EquipoService.delete(ids["equipo"])
        if ids["categoria"]:
            CategoriaService.delete(ids["categoria"])
        if ids["lab"]:
            LaboratorioService.delete(ids["lab"])
        if ids["prestatario"]:
            PrestatarioService.delete(ids["prestatario"])
        if ids["usuario"]:
            UsuarioService.delete(ids["usuario"])


if __name__ == "__main__":
    main()
