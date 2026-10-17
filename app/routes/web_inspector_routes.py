"""Rutas web para el Visor Técnico SQLite3 (solo ADMINISTRADOR)."""

from flask import abort, jsonify, render_template, request

from app.routes.web_common import login_required, permission_required, web_bp
from app.services.db_inspector_service import DBInspectorService


@web_bp.get("/sistema/visor-sqlite")
@login_required
@permission_required("sistema.inspector")
def visor_sqlite():
    """Renderiza la plantilla con las dos pestañas."""
    return render_template("sistema/visor_sqlite.html")


@web_bp.get("/sistema/visor-sqlite/usuarios")
@login_required
@permission_required("sistema.inspector")
def visor_usuarios():
    usuarios = DBInspectorService.obtener_usuarios_con_hash()
    for u in usuarios:
        u["desglose"] = DBInspectorService.desglosar_hash(u.get("password_hash", ""))
    return jsonify({"usuarios": usuarios})


@web_bp.post("/sistema/visor-sqlite/probar-hash")
@login_required
@permission_required("sistema.inspector")
def visor_probar_hash():
    password = request.form.get("password", "")
    if not password:
        return jsonify({"error": "Escribe una contraseña."}), 400
    hash_generado = DBInspectorService.generar_hash_demo(password)
    return jsonify({
        "password": password,
        "hash": hash_generado,
        "desglose": DBInspectorService.desglosar_hash(hash_generado),
    })


@web_bp.get("/sistema/visor-sqlite/tablas")
@login_required
@permission_required("sistema.inspector")
def visor_tablas():
    tablas = DBInspectorService.listar_tablas()
    # Añadir conteo a cada tabla
    for t in tablas:
        try:
            t["registros"] = DBInspectorService.contar_registros(t["name"])
        except Exception:
            t["registros"] = 0
    return jsonify({"tablas": tablas})


@web_bp.get("/sistema/visor-sqlite/tablas/<nombre>")
@login_required
@permission_required("sistema.inspector")
def visor_tabla_preview(nombre):
    edicion_id = request.args.get("edicion_id", type=int)
    try:
        preview = DBInspectorService.previsualizar(nombre, limite=50, edicion_id=edicion_id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(preview)
