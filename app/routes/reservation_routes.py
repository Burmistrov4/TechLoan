from flask import Blueprint, jsonify, request

from app.services.reservation_service import ReservationService
from app.security.permissions import current_user, require_permission

reservation_bp = Blueprint("reservations", __name__, url_prefix="/api/reservas")


@reservation_bp.post("")
@require_permission("reservas.write")
def create_reservation():
    data = request.get_json(silent=True) or {}
    required = [
        "laboratorio_id",
        "prestatario_id",
        "fecha",
        "hora_inicio",
        "duracion_minutos",
    ]
    missing = [field for field in required if data.get(field) is None]
    if missing:
        return jsonify({"ok": False, "error": f"Faltan campos: {', '.join(missing)}"}), 400

    try:
        ReservationService.create_reservation(
            int(data["laboratorio_id"]),
            int(data["prestatario_id"]),
            current_user()["id"],
            data["fecha"],
            data["hora_inicio"],
            int(data["duracion_minutos"]),
            data.get("observaciones", ""),
        )
        return jsonify({"ok": True, "message": "Reserva creada correctamente."}), 201
    except (ValueError, TypeError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
