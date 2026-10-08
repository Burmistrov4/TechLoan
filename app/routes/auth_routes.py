from flask import Blueprint, jsonify, request, session
from app.services.auth_service import AuthService
from app.services.usuario_service import UsuarioService
from app.security.permissions import current_user, require_permission

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    try:
        user = AuthService.authenticate(data.get("username", ""), data.get("password", ""))
        session.clear()
        session["user"] = user
        return jsonify({"ok": True, "data": user})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 401

@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True, "message": "Sesión cerrada."})


@auth_bp.get("/me")
def me():
    user = current_user()
    if not user:
        return jsonify({"ok": False, "error": "Autenticación requerida."}), 401
    return jsonify({"ok": True, "data": user})


@auth_bp.post("/registro")
def registro():
    try:
        data = request.get_json(silent=True) or {}
        # El registro público nunca puede autoasignarse privilegios de administrador.
        data["rol"] = "OPERADOR"
        return jsonify({"ok": True, "data": {"id": UsuarioService.create(data)}}), 201
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
