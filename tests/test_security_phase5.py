from datetime import datetime, timedelta

from app.database import init_database, get_connection
from app.server import create_app
from app.services.usuario_service import UsuarioService
from app.services.prestatario_service import PrestatarioService
from app.services.laboratorio_service import LaboratorioService
from app.services.categoria_service import CategoriaService
from app.services.equipo_service import EquipoService


init_database()
app = create_app()
app.config["TESTING"] = True

stamp = datetime.now().strftime("%H%M%S%f")
ids = {}

def login(client, username, password):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response

try:
    admin_data = {
        "nombre": "Admin", "apellido": "Security",
        "username": f"adm_{stamp[-10:]}",
        "email": f"adm_{stamp}@test.local",
        "password": "Admin123!", "rol": "ADMINISTRADOR", "estado": "ACTIVO"
    }
    operator_data = {
        "nombre": "Operador", "apellido": "Security",
        "username": f"op_{stamp[-10:]}",
        "email": f"op_{stamp}@test.local",
        "password": "Operator123!", "rol": "OPERADOR", "estado": "ACTIVO"
    }
    ids["admin"] = UsuarioService.create(admin_data)
    ids["operator"] = UsuarioService.create(operator_data)

    # SQL injection and authentication.
    unauth = app.test_client()
    assert unauth.get("/api/equipos").status_code == 401
    bad = unauth.post("/api/auth/login", json={"username": "' OR 1=1 --", "password": "' OR 1=1 --"})
    assert bad.status_code == 401

    # Public registration cannot escalate to administrator.
    public_reg = unauth.post("/api/auth/registro", json={
        "nombre": "Registro", "apellido": "Publico",
        "username": f"pub_{stamp[-8:]}",
        "email": f"pub_{stamp}@test.local",
        "password": "Public123!",
        "rol": "ADMINISTRADOR"
    })
    assert public_reg.status_code == 201
    ids["public"] = public_reg.get_json()["data"]["id"]
    assert UsuarioService.get(ids["public"])["rol"] == "OPERADOR"

    # Password hash is not exposed and is not plaintext.
    auth = login(unauth, admin_data["username"], admin_data["password"])
    payload = auth.get_json()["data"]
    assert "password_hash" not in payload
    with get_connection() as db:
        row = db.execute("SELECT password_hash FROM usuarios_sistema WHERE id=?", (ids["admin"],)).fetchone()
        assert row["password_hash"] != admin_data["password"]
        assert len(row["password_hash"]) <= 255

    # Operator: read allowed, write/admin actions denied.
    operator_client = app.test_client()
    login(operator_client, operator_data["username"], operator_data["password"])
    assert operator_client.get("/api/equipos").status_code == 200
    assert operator_client.get("/api/usuarios").status_code == 403
    denied_equipment = operator_client.post("/api/equipos", json={
        "codigo": f"SEC{stamp[-8:]}",
        "nombre": "No autorizado",
        "estado": "DISPONIBLE"
    })
    assert denied_equipment.status_code == 403

    # Admin can perform protected CRUD.
    admin_client = app.test_client()
    login(admin_client, admin_data["username"], admin_data["password"])
    created = admin_client.post("/api/categorias", json={"nombre": f"SecCat {stamp[-6:]}"})
    assert created.status_code == 200
    ids["category"] = created.get_json()["data"]

    # Logout invalidates the session.
    assert admin_client.post("/api/auth/logout").status_code == 200
    assert admin_client.get("/api/equipos").status_code == 401

    # Build operation data for parameter-tampering test.
    ids["borrower"] = PrestatarioService.create({
        "cedula": f"SEC{stamp[-8:]}",
        "nombre": "Borrower", "apellido": "Security",
        "tipo": "ESTUDIANTE", "estado": "ACTIVO"
    })
    ids["lab"] = LaboratorioService.create({
        "codigo": f"SL{stamp[-8:]}",
        "nombre": "Security Lab", "ubicacion": "A1",
        "capacidad": 20, "duracion_estandar_minutos": 70, "estado": "DISPONIBLE"
    })
    ids["equipment"] = EquipoService.create({
        "codigo": f"SE{stamp[-8:]}",
        "nombre": "Security Equipment",
        "categoria_id": ids["category"],
        "laboratorio_id": ids["lab"],
        "estado": "DISPONIBLE"
    })

    # Login as operator and attempt to impersonate admin through usuario_sistema_id.
    login(operator_client, operator_data["username"], operator_data["password"])
    loan = operator_client.post("/api/prestamos", json={
        "equipo_id": ids["equipment"],
        "prestatario_id": ids["borrower"],
        "usuario_sistema_id": ids["admin"]
    })
    assert loan.status_code == 201
    loan_id = loan.get_json()["data"]["id"]
    with get_connection() as db:
        row = db.execute("SELECT usuario_sistema_id FROM prestamos_equipos WHERE id=?", (loan_id,)).fetchone()
        assert row["usuario_sistema_id"] == ids["operator"]

    print("FASE5_30_SQL_INJECTION_AUTH_OK")
    print("FASE5_30_PASSWORD_HASH_OK")
    print("FASE5_30_ROLES_PERMISSIONS_OK")
    print("FASE5_30_SESSION_LOGOUT_OK")
    print("FASE5_30_PARAMETER_TAMPERING_OK")
    print("FASE5_30_PUBLIC_REGISTRATION_ESCALATION_OK")
    print("FASE5_30_PRUEBA_SEGURIDAD_OK")

finally:
    try:
        with get_connection() as db:
            if ids.get("loan_id"):
                db.execute("DELETE FROM prestamos_equipos WHERE id=?", (ids["loan_id"],))
            if ids.get("equipment"):
                db.execute("DELETE FROM prestamos_equipos WHERE equipo_id=?", (ids["equipment"],))
                db.execute("DELETE FROM equipos WHERE id=?", (ids["equipment"],))
            if ids.get("borrower"):
                db.execute("DELETE FROM prestatarios WHERE id=?", (ids["borrower"],))
            if ids.get("lab"):
                db.execute("DELETE FROM reservas WHERE laboratorio_id=?", (ids["lab"],))
                db.execute("DELETE FROM laboratorios WHERE id=?", (ids["lab"],))
            if ids.get("category"):
                db.execute("DELETE FROM categorias WHERE id=?", (ids["category"],))
            for key in ("public", "operator", "admin"):
                if ids.get(key):
                    db.execute("DELETE FROM usuarios_sistema WHERE id=?", (ids[key],))
    except Exception:
        pass
