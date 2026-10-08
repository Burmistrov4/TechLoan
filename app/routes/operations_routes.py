from flask import Blueprint, jsonify, request
from app.services.prestamo_equipo_service import PrestamoEquipoService
from app.services.disponibilidad_service import DisponibilidadService
from app.services.reservation_service import ReservationService
from app.security.permissions import current_user, require_permission

operations_bp = Blueprint("operations", __name__, url_prefix="/api")


@operations_bp.post("/prestamos")
@require_permission("prestamos.write")
def create_loan():
    data = request.get_json(silent=True) or {}
    required = ("equipo_id", "prestatario_id")
    if any(data.get(x) is None for x in required):
        return jsonify({"ok": False, "error": "Faltan datos obligatorios."}), 400
    try:
        loan_id = PrestamoEquipoService.create(
            int(data["equipo_id"]), int(data["prestatario_id"]),
            current_user()["id"], data.get("observaciones", "")
        )
        return jsonify({"ok": True, "data": {"id": loan_id}}), 201
    except (ValueError, TypeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@operations_bp.get("/prestamos")
@require_permission("prestamos.read")
def list_loans():
    return jsonify({"ok": True, "data": PrestamoEquipoService.list_all()})


@operations_bp.post("/prestamos/<int:loan_id>/devolver")
@require_permission("prestamos.return")
def return_loan(loan_id):
    try:
        PrestamoEquipoService.return_equipment(loan_id, (request.get_json(silent=True) or {}).get("observaciones", ""))
        return jsonify({"ok": True, "message": "Equipo devuelto correctamente."})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@operations_bp.get("/disponibilidad/equipos/<int:equipment_id>")
@require_permission("equipos.read")
def equipment_availability(equipment_id):
    ok, message = DisponibilidadService.equipo(equipment_id)
    return jsonify({"ok": ok, "available": ok, "message": message})


@operations_bp.get("/disponibilidad/laboratorios")
@require_permission("laboratorios.read")
def laboratory_availability():
    required = ("laboratorio_id", "fecha", "hora_inicio", "hora_fin")
    if any(request.args.get(x) is None for x in required):
        return jsonify({"ok": False, "error": "Faltan parámetros de disponibilidad."}), 400
    ok, message = DisponibilidadService.laboratorio(
        int(request.args["laboratorio_id"]), request.args["fecha"],
        request.args["hora_inicio"], request.args["hora_fin"]
    )
    return jsonify({"ok": ok, "available": ok, "message": message})


@operations_bp.get("/reservas")
@require_permission("reservas.read")
def list_reservations():
    return jsonify({"ok": True, "data": ReservationService.list_all()})
