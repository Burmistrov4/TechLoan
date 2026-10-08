from flask import Blueprint, jsonify, request

from app.services.prestatario_service import PrestatarioService
from app.services.laboratorio_service import LaboratorioService
from app.services.categoria_service import CategoriaService
from app.services.equipo_service import EquipoService
from app.services.usuario_service import UsuarioService
from app.security.permissions import require_crud_permissions

crud_bp = Blueprint("crud", __name__, url_prefix="/api")


def _response(action):
    try:
        result = action()
        return jsonify({"ok": True, "data": result}), 200
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


# Prestatarios
@crud_bp.route("/prestatarios", methods=["GET", "POST"])
@require_crud_permissions("prestatarios.read", "prestatarios.write", "prestatarios.delete")
def prestatarios():
    if request.method == "GET":
        return jsonify({"ok": True, "data": PrestatarioService.list_all()})
    return _response(lambda: PrestatarioService.create(request.get_json(silent=True) or {}))


@crud_bp.route("/prestatarios/<int:id_>", methods=["GET", "PUT", "DELETE"])
@require_crud_permissions("prestatarios.read", "prestatarios.write", "prestatarios.delete")
def prestatario(id_):
    if request.method == "GET":
        item = PrestatarioService.get(id_)
        return (jsonify({"ok": True, "data": item}), 200) if item else (jsonify({"ok": False, "error": "No encontrado."}), 404)
    if request.method == "PUT":
        return _response(lambda: PrestatarioService.update(id_, request.get_json(silent=True) or {}))
    return _response(lambda: PrestatarioService.delete(id_))


# Laboratorios
@crud_bp.route("/laboratorios", methods=["GET", "POST"])
@require_crud_permissions("laboratorios.read", "laboratorios.write", "laboratorios.delete")
def laboratorios():
    if request.method == "GET":
        return jsonify({"ok": True, "data": LaboratorioService.list_all()})
    return _response(lambda: LaboratorioService.create(request.get_json(silent=True) or {}))


@crud_bp.route("/laboratorios/<int:id_>", methods=["GET", "PUT", "DELETE"])
@require_crud_permissions("laboratorios.read", "laboratorios.write", "laboratorios.delete")
def laboratorio(id_):
    if request.method == "GET":
        item = LaboratorioService.get(id_)
        return (jsonify({"ok": True, "data": item}), 200) if item else (jsonify({"ok": False, "error": "No encontrado."}), 404)
    if request.method == "PUT":
        return _response(lambda: LaboratorioService.update(id_, request.get_json(silent=True) or {}))
    return _response(lambda: LaboratorioService.delete(id_))


# Categorías
@crud_bp.route("/categorias", methods=["GET", "POST"])
@require_crud_permissions("categorias.read", "categorias.write", "categorias.delete")
def categorias():
    if request.method == "GET":
        return jsonify({"ok": True, "data": CategoriaService.list_all()})
    return _response(lambda: CategoriaService.create(request.get_json(silent=True) or {}))


@crud_bp.route("/categorias/<int:id_>", methods=["GET", "PUT", "DELETE"])
@require_crud_permissions("categorias.read", "categorias.write", "categorias.delete")
def categoria(id_):
    if request.method == "GET":
        item = CategoriaService.get(id_)
        return (jsonify({"ok": True, "data": item}), 200) if item else (jsonify({"ok": False, "error": "No encontrado."}), 404)
    if request.method == "PUT":
        return _response(lambda: CategoriaService.update(id_, request.get_json(silent=True) or {}))
    return _response(lambda: CategoriaService.delete(id_))


# Equipos
@crud_bp.route("/equipos", methods=["GET", "POST"])
@require_crud_permissions("equipos.read", "equipos.write", "equipos.delete")
def equipos():
    if request.method == "GET":
        return jsonify({"ok": True, "data": EquipoService.list_all()})
    return _response(lambda: EquipoService.create(request.get_json(silent=True) or {}))


@crud_bp.route("/equipos/<int:id_>", methods=["GET", "PUT", "DELETE"])
@require_crud_permissions("equipos.read", "equipos.write", "equipos.delete")
def equipo(id_):
    if request.method == "GET":
        item = EquipoService.get(id_)
        return (jsonify({"ok": True, "data": item}), 200) if item else (jsonify({"ok": False, "error": "No encontrado."}), 404)
    if request.method == "PUT":
        return _response(lambda: EquipoService.update(id_, request.get_json(silent=True) or {}))
    return _response(lambda: EquipoService.delete(id_))


# Usuarios del sistema
@crud_bp.route("/usuarios", methods=["GET", "POST"])
@require_crud_permissions("usuarios.read", "usuarios.write", "usuarios.delete")
def usuarios():
    if request.method == "GET":
        return jsonify({"ok": True, "data": UsuarioService.list_all()})
    return _response(lambda: UsuarioService.create(request.get_json(silent=True) or {}))


@crud_bp.route("/usuarios/<int:id_>", methods=["GET", "PUT", "DELETE"])
@require_crud_permissions("usuarios.read", "usuarios.write", "usuarios.delete")
def usuario(id_):
    if request.method == "GET":
        item = UsuarioService.get(id_)
        return (jsonify({"ok": True, "data": item}), 200) if item else (jsonify({"ok": False, "error": "No encontrado."}), 404)
    if request.method == "PUT":
        return _response(lambda: UsuarioService.update(id_, request.get_json(silent=True) or {}))
    return _response(lambda: UsuarioService.delete(id_))
