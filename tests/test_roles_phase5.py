from app.server import create_app
from app.database import init_database, get_connection
from app.services.usuario_service import UsuarioService
from app.services.auth_service import AuthService
from app.gui.session import Session

PASSWORD = "RolesTest123!"


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def ensure_user(username, email, role):
    with get_connection() as db:
        row = db.execute("SELECT id FROM usuarios_sistema WHERE username=?", (username,)).fetchone()
        if row:
            db.execute("DELETE FROM usuarios_sistema WHERE id=?", (row["id"],))
    return UsuarioService.create({
        "nombre": "Prueba",
        "apellido": "Roles",
        "username": username,
        "email": email,
        "password": PASSWORD,
        "rol": role,
        "estado": "ACTIVO",
    })


def main():
    init_database()
    app = create_app()
    app.config["TESTING"] = True

    admin_id = ensure_user("admin_p32", "admin_p32@techloan.local", "ADMINISTRADOR")
    operator_id = ensure_user("op_p32", "op_p32@techloan.local", "OPERADOR")
    created_borrowers = []

    try:
        # 1. Matriz completa del motor de permisos.
        crud = {
            "prestatarios": ("prestatarios.read", "prestatarios.write", "prestatarios.delete"),
            "laboratorios": ("laboratorios.read", "laboratorios.write", "laboratorios.delete"),
            "categorias": ("categorias.read", "categorias.write", "categorias.delete"),
            "equipos": ("equipos.read", "equipos.write", "equipos.delete"),
            "usuarios": ("usuarios.read", "usuarios.write", "usuarios.delete"),
        }
        operator_write = {"prestatarios.write"}
        operator_read = {"prestatarios.read", "laboratorios.read", "categorias.read", "equipos.read"}
        for module, (read, write, delete) in crud.items():
            assert_true(AuthService.can({"rol": "ADMINISTRADOR"}, read), f"ADMIN sin {read}")
            assert_true(AuthService.can({"rol": "ADMINISTRADOR"}, write), f"ADMIN sin {write}")
            assert_true(AuthService.can({"rol": "ADMINISTRADOR"}, delete), f"ADMIN sin {delete}")
            assert_true(AuthService.can({"rol": "OPERADOR"}, read) == (read in operator_read),
                        f"OPERADOR matriz lectura incorrecta: {read}")
            assert_true(AuthService.can({"rol": "OPERADOR"}, write) == (write in operator_write),
                        f"OPERADOR matriz escritura incorrecta: {write}")
            assert_true(not AuthService.can({"rol": "OPERADOR"}, delete),
                        f"OPERADOR tiene eliminación: {delete}")

        operational = [
            "reservas.read", "reservas.write",
            "prestamos.read", "prestamos.write", "prestamos.return",
            "historial.read",
        ]
        for permission in operational:
            assert_true(AuthService.can({"rol": "ADMINISTRADOR"}, permission), f"ADMIN sin {permission}")
            assert_true(AuthService.can({"rol": "OPERADOR"}, permission), f"OPERADOR sin {permission}")

        # 2. GUI: Session.can usa exactamente la misma matriz.
        Session.start({"id": admin_id, "rol": "ADMINISTRADOR"})
        for permission in [
            "usuarios.read", "usuarios.write", "usuarios.delete",
            "equipos.write", "equipos.delete", "prestatarios.delete",
            "reservas.write", "prestamos.return", "historial.read"
        ]:
            assert_true(Session.can(permission), f"GUI ADMIN sin {permission}")

        Session.start({"id": operator_id, "rol": "OPERADOR"})
        for permission in [
            "prestatarios.read", "prestatarios.write",
            "laboratorios.read", "categorias.read", "equipos.read",
            "reservas.write", "prestamos.write", "prestamos.return", "historial.read"
        ]:
            assert_true(Session.can(permission), f"GUI OPERADOR sin {permission}")
        for permission in [
            "usuarios.read", "usuarios.write", "usuarios.delete",
            "prestatarios.delete", "laboratorios.write", "laboratorios.delete",
            "categorias.write", "categorias.delete", "equipos.write", "equipos.delete"
        ]:
            assert_true(not Session.can(permission), f"GUI OPERADOR habilita {permission}")
        Session.end()

        # 3. API: primero OPERADOR, después ADMINISTRADOR.
        with app.test_client() as client:
            login = client.post("/api/auth/login", json={"username": "op_p32", "password": PASSWORD})
            assert_true(login.status_code == 200, "Login API OPERADOR falló")

            for endpoint in [
                "/api/prestatarios", "/api/laboratorios", "/api/categorias",
                "/api/equipos", "/api/reservas", "/api/prestamos"
            ]:
                assert_true(client.get(endpoint).status_code == 200,
                            f"OPERADOR no puede leer {endpoint}")
            assert_true(client.get("/api/usuarios").status_code == 403,
                        "OPERADOR puede leer usuarios")

            borrower_payload = {
                "cedula": "P32-OP",
                "nombre": "Temporal",
                "apellido": "Roles",
                "tipo": "ESTUDIANTE",
                "telefono": "0414000032",
                "email": "tmp_p32_op@techloan.local",
                "estado": "ACTIVO",
            }
            create_borrower = client.post("/api/prestatarios", json=borrower_payload)
            assert_true(create_borrower.status_code == 200,
                        "OPERADOR debe poder crear prestatarios")
            borrower_id = create_borrower.get_json()["data"]
            created_borrowers.append(borrower_id)

            update_borrower = client.put(
                f"/api/prestatarios/{borrower_id}",
                json={**borrower_payload, "apellido": "Actualizado"},
            )
            assert_true(update_borrower.status_code == 200,
                        "OPERADOR debe poder actualizar prestatarios")
            assert_true(client.delete(f"/api/prestatarios/{borrower_id}").status_code == 403,
                        "OPERADOR puede eliminar prestatarios")

            equipment_payload = {
                "codigo": "EQ-P32-OP",
                "nombre": "Equipo Roles",
                "categoria_id": None,
                "marca": "Test",
                "modelo": "P32",
                "serial": "SER-P32-OP",
                "laboratorio_id": None,
                "estado": "DISPONIBLE",
            }
            assert_true(client.post("/api/equipos", json=equipment_payload).status_code == 403,
                        "OPERADOR puede crear equipos")
            assert_true(client.post("/api/usuarios", json={
                "nombre": "Temporal", "apellido": "P32",
                "username": "tmp_p32_op", "email": "tmp_p32_op_user@techloan.local",
                "password": "TmpRoles123!", "rol": "OPERADOR", "estado": "ACTIVO"
            }).status_code == 403, "OPERADOR puede crear usuarios")

            client.post("/api/auth/logout")

            login = client.post("/api/auth/login", json={"username": "admin_p32", "password": PASSWORD})
            assert_true(login.status_code == 200, "Login API ADMINISTRADOR falló")
            assert_true(client.get("/api/usuarios").status_code == 200,
                        "ADMINISTRADOR no puede leer usuarios")

            # ADMIN puede eliminar el prestatario creado por OPERADOR.
            assert_true(client.delete(f"/api/prestatarios/{borrower_id}").status_code == 200,
                        "ADMINISTRADOR no puede eliminar prestatario")

            # ADMIN puede crear equipo; después se elimina para limpiar.
            equipment_payload["codigo"] = "EQ-P32-AD"
            equipment_payload["serial"] = "SER-P32-AD"
            create_equipment = client.post("/api/equipos", json=equipment_payload)
            assert_true(create_equipment.status_code == 200,
                        "ADMINISTRADOR no puede crear equipos")
            equipment_id = create_equipment.get_json()["data"]
            assert_true(client.delete(f"/api/equipos/{equipment_id}").status_code == 200,
                        "ADMINISTRADOR no puede eliminar equipos")

            # ADMIN puede modificar y eliminar usuarios.
            update_operator = client.put(
                f"/api/usuarios/{operator_id}",
                json={
                    "nombre": "Prueba", "apellido": "RolesActualizado",
                    "username": "op_p32", "email": "op_p32@techloan.local",
                    "password": "", "rol": "OPERADOR", "estado": "ACTIVO"
                },
            )
            assert_true(update_operator.status_code == 200,
                        "ADMINISTRADOR no puede actualizar usuarios")
            assert_true(client.delete(f"/api/usuarios/{operator_id}").status_code == 200,
                        "ADMINISTRADOR no puede eliminar usuarios")
            operator_id = None

            client.post("/api/auth/logout")

        print("FASE5_32_MATRIZ_AUTH_PERMISSIONS_OK")
        print("FASE5_32_MATRIZ_GUI_SESSION_OK")
        print("FASE5_32_MATRIZ_API_ROLES_OK")
        print("FASE5_32_ADMINISTRADOR_VS_OPERADOR_OK")
        print("FASE5_32_PRESTATARIOS_OPERADOR_ESCRITURA_OK")
        print("FASE5_32_PRUEBA_ROLES_OK")

    finally:
        Session.end()
        with get_connection() as db:
            if operator_id:
                db.execute("DELETE FROM usuarios_sistema WHERE id=?", (operator_id,))
            if admin_id:
                db.execute("DELETE FROM usuarios_sistema WHERE id=?", (admin_id,))
            for borrower_id in created_borrowers:
                db.execute("DELETE FROM prestatarios WHERE id=?", (borrower_id,))


if __name__ == "__main__":
    main()
