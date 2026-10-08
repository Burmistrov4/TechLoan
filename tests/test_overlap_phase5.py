from datetime import date, timedelta

from app.database import init_database, get_connection
from app.services.prestatario_service import PrestatarioService
from app.services.laboratorio_service import LaboratorioService
from app.services.reservation_service import ReservationService
from app.services.usuario_service import UsuarioService


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def expect_rejected(lab_id, borrower_id, user_id, fecha, hora, duracion, label):
    try:
        ReservationService.create_reservation(
            lab_id, borrower_id, user_id, fecha, hora, duracion, label
        )
    except ValueError as exc:
        assert_true("superpone" in str(exc).lower(), f"{label}: rechazo inesperado: {exc}")
        return
    raise AssertionError(f"{label}: la reserva debía ser rechazada por solapamiento.")


def expect_allowed(lab_id, borrower_id, user_id, fecha, hora, duracion, label):
    return ReservationService.create_reservation(
        lab_id, borrower_id, user_id, fecha, hora, duracion, label
    )


def main():
    init_database()

    with get_connection() as db:
        admin = db.execute(
            "SELECT id FROM usuarios_sistema WHERE rol='ADMINISTRADOR' AND estado='ACTIVO' ORDER BY id LIMIT 1"
        ).fetchone()
    assert_true(admin is not None, "Se requiere un administrador activo.")
    user_id = admin["id"]

    suffix = "P31"
    ids = {"borrower": None, "lab1": None, "lab2": None}
    reservation_ids = []

    try:
        ids["borrower"] = PrestatarioService.create({
            "cedula": "P31-0001",
            "nombre": "Prestatario",
            "apellido": "Solapamiento",
            "tipo": "ESTUDIANTE",
            "telefono": "0414000031",
            "email": "p31@techloan.local",
            "estado": "ACTIVO",
        })
        ids["lab1"] = _create_lab("LAB-P31-A", "Laboratorio Solapamiento A")
        ids["lab2"] = _create_lab("LAB-P31-B", "Laboratorio Solapamiento B")

        fecha = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")

        # Base: 08:00–09:10.
        base = expect_allowed(ids["lab1"], ids["borrower"], user_id, fecha, "08:00", 70, "base")
        reservation_ids.append(base)

        # Límite exacto: 09:10 es el final de la anterior -> permitido.
        adjacent = expect_allowed(
            ids["lab1"], ids["borrower"], user_id, fecha, "09:10", 70, "límite exacto"
        )
        reservation_ids.append(adjacent)

        # Un minuto de solapamiento: 09:09–10:19 -> rechazado.
        expect_rejected(
            ids["lab1"], ids["borrower"], user_id, fecha, "09:09", 70,
            "solapamiento de un minuto"
        )

        # Misma hora de inicio -> rechazado.
        expect_rejected(
            ids["lab1"], ids["borrower"], user_id, fecha, "08:00", 30,
            "misma hora de inicio"
        )

        # Reserva contenida dentro de la base: 08:20–08:50 -> rechazado.
        expect_rejected(
            ids["lab1"], ids["borrower"], user_id, fecha, "08:20", 30,
            "reserva contenida"
        )

        # Reserva que contiene completamente la base: 07:30–09:30 -> rechazado.
        expect_rejected(
            ids["lab1"], ids["borrower"], user_id, fecha, "07:30", 120,
            "reserva contenedora"
        )

        # Diferente laboratorio: mismo horario, debe permitirse.
        different_lab = expect_allowed(
            ids["lab2"], ids["borrower"], user_id, fecha, "08:00", 70,
            "laboratorio diferente"
        )
        reservation_ids.append(different_lab)

        # CANCELADA no debe bloquear.
        cancelled = expect_allowed(
            ids["lab1"], ids["borrower"], user_id, fecha, "11:00", 70,
            "reserva cancelable"
        )
        reservation_ids.append(cancelled)
        with get_connection() as db:
            db.execute("UPDATE reservas SET estado='CANCELADA' WHERE id=?", (cancelled,))
        allowed_after_cancel = expect_allowed(
            ids["lab1"], ids["borrower"], user_id, fecha, "11:00", 70,
            "horario liberado tras CANCELADA"
        )
        reservation_ids.append(allowed_after_cancel)

        # Finalizada/completada tampoco debe bloquear.
        completed = expect_allowed(
            ids["lab1"], ids["borrower"], user_id, fecha, "13:00", 70,
            "reserva finalizada"
        )
        reservation_ids.append(completed)
        with get_connection() as db:
            db.execute("UPDATE reservas SET estado='FINALIZADA' WHERE id=?", (completed,))
        allowed_after_completed = expect_allowed(
            ids["lab1"], ids["borrower"], user_id, fecha, "13:00", 70,
            "horario liberado tras FINALIZADA"
        )
        reservation_ids.append(allowed_after_completed)

        # La misma regla debe rechazar otra reserva de cualquier prestatario:
        # el recurso (laboratorio) es lo que determina el conflicto.
        other_borrower = PrestatarioService.create({
            "cedula": "P31-0002",
            "nombre": "Otro",
            "apellido": "Prestatario",
            "tipo": "PROFESOR",
            "telefono": "0414000032",
            "email": "p31b@techloan.local",
            "estado": "ACTIVO",
        })
        ids["other_borrower"] = other_borrower
        expect_rejected(
            ids["lab1"], other_borrower, user_id, fecha, "08:30", 20,
            "conflicto entre prestatarios"
        )

        print("FASE5_31_LIMITE_EXACTO_ADYACENTE_OK")
        print("FASE5_31_SOLAPAMIENTO_UN_MINUTO_OK")
        print("FASE5_31_MISMA_HORA_CONTENIDA_CONTENEDORA_OK")
        print("FASE5_31_LABORATORIO_DIFERENTE_OK")
        print("FASE5_31_ESTADOS_CANCELADA_FINALIZADA_NO_BLOQUEAN_OK")
        print("FASE5_31_RECURSO_COMPARTIDO_ENTRE_PRESTATARIOS_OK")
        print("FASE5_31_PRUEBA_SOLAPAMIENTOS_OK")

    finally:
        with get_connection() as db:
            if reservation_ids:
                placeholders = ",".join("?" for _ in reservation_ids)
                db.execute(
                    f"DELETE FROM reservas WHERE id IN ({placeholders})",
                    tuple(reservation_ids),
                )
        if ids.get("other_borrower"):
            PrestatarioService.delete(ids["other_borrower"])
        if ids["lab2"]:
            _delete_lab(ids["lab2"])
        if ids["lab1"]:
            _delete_lab(ids["lab1"])
        if ids["borrower"]:
            PrestatarioService.delete(ids["borrower"])


def _create_lab(code, name):
    return __import__("app.services.laboratorio_service", fromlist=["LaboratorioService"]).LaboratorioService.create({
        "codigo": code,
        "nombre": name,
        "ubicacion": "Aula P31",
        "capacidad": 20,
        "duracion_estandar_minutos": 70,
        "estado": "DISPONIBLE",
    })


def _delete_lab(lab_id):
    __import__("app.services.laboratorio_service", fromlist=["LaboratorioService"]).LaboratorioService.delete(lab_id)


if __name__ == "__main__":
    main()
