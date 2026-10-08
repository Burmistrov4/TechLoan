from datetime import date, timedelta
from app.database import get_connection
from app.services.historial_service import HistorialService
from app.services.prestatario_service import PrestatarioService
from app.services.laboratorio_service import LaboratorioService
from app.services.categoria_service import CategoriaService
from app.services.equipo_service import EquipoService
from app.services.reservation_service import ReservationService
from app.services.prestamo_equipo_service import PrestamoEquipoService
from app.services.usuario_service import UsuarioService

def main():
    with get_connection() as db:
        user = db.execute("SELECT id FROM usuarios_sistema WHERE estado='ACTIVO' ORDER BY id LIMIT 1").fetchone()
    if not user:
        raise RuntimeError("No existe usuario de sistema activo para la prueba.")
    uid = user["id"]

    suffix = "HIST" + str(uid)
    borrower = PrestatarioService.create({
        "cedula": "9999" + suffix,
        "nombre": "Prueba",
        "apellido": "Historial",
        "tipo": "ESTUDIANTE",
        "telefono": "",
        "email": "",
        "estado": "ACTIVO",
    })
    lab = LaboratorioService.create({
        "codigo": "LAB-" + suffix,
        "nombre": "Lab Historial",
        "ubicacion": "Prueba",
        "capacidad": 20,
        "duracion_estandar_minutos": 70,
        "estado": "DISPONIBLE",
    })
    cat = CategoriaService.create({"nombre": "CAT " + suffix, "descripcion": "Prueba"})
    eq = EquipoService.create({
        "codigo": "EQ-" + suffix,
        "nombre": "Equipo Historial",
        "categoria_id": cat,
        "marca": "Test",
        "modelo": "T1",
        "serial": "SER-" + suffix,
        "laboratorio_id": lab,
        "estado": "DISPONIBLE",
    })

    future = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    rid = ReservationService.create_reservation(lab, borrower, uid, future, "09:00", 70, "Reserva de prueba")
    lid = PrestamoEquipoService.create(eq, borrower, uid, "Préstamo de prueba")
    PrestamoEquipoService.return_equipment(lid)

    all_rows = HistorialService.list_all()
    res_rows = HistorialService.list_all(tipo="RESERVA", prestatario_id=borrower)
    ret_rows = HistorialService.list_all(tipo="DEVOLUCION", prestatario_id=borrower)
    date_rows = HistorialService.list_all(fecha_desde=future, fecha_hasta=future)
    assert any(r["referencia_id"] == rid and r["tipo"] == "RESERVA" for r in res_rows)
    assert any(r["referencia_id"] == lid and r["tipo"] == "DEVOLUCION" for r in ret_rows)
    assert len(date_rows) >= 1
    assert HistorialService.list_all(recurso="EQ-" + suffix)
    assert HistorialService.list_all(estado="DEVUELTO")

    with get_connection() as db:
        db.execute("DELETE FROM prestamos_equipos WHERE id=?", (lid,))
        db.execute("DELETE FROM reservas WHERE id=?", (rid,))
        db.execute("DELETE FROM equipos WHERE id=?", (eq,))
        db.execute("DELETE FROM categorias WHERE id=?", (cat,))
        db.execute("DELETE FROM laboratorios WHERE id=?", (lab,))
        db.execute("DELETE FROM prestatarios WHERE id=?", (borrower,))
    print("PHASE4_HISTORIAL_FILTERS_OK")
    print("RESERVA_ID=" + str(rid) + "; PRESTAMO_ID=" + str(lid) + "; DEVOLUCION_DETECTADA=SI")

if __name__ == "__main__":
    main()
