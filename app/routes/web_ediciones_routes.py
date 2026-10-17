"""Rutas web para la gestión de ediciones."""

from flask import flash, redirect, render_template, request, session, url_for

from app.routes.web_common import login_required, permission_required, web_bp
from app.services.edicion_service import EdicionService


@web_bp.get("/ediciones")
@login_required
@permission_required("ediciones.read")
def ediciones_index():
    """Panel de ediciones (solo ADMINISTRADOR global)."""
    from app.services.auth_service import AuthService
    from app.security.permissions import current_user

    user = current_user()
    if not user or user.get("rol") != "ADMINISTRADOR":
        flash("Solo el administrador global puede gestionar ediciones.", "error")
        return redirect(url_for("web.dashboard"))

    ediciones = EdicionService.listar_por_usuario(user["id"])
    return render_template("ediciones/index.html", ediciones=ediciones)


@web_bp.get("/ediciones/<slug>")
@login_required
def edicion_landing(slug):
    """Landing pública de una edición."""
    edicion = EdicionService.obtener_por_slug(slug)
    if not edicion:
        flash("Edición no encontrada.", "error")
        return redirect(url_for("web.dashboard"))
    return render_template("ediciones/landing.html", edicion=edicion)


@web_bp.route("/ediciones/<slug>/configuracion", methods=["GET", "POST"])
@login_required
@permission_required("configuracion.read")
def edicion_configuracion(slug):
    """Panel de configuración de una edición (preferencias y versiones)."""
    from app.services.auth_service import AuthService
    from app.security.permissions import current_user

    edicion = EdicionService.obtener_por_slug(slug)
    if not edicion:
        flash("Edición no encontrada.", "error")
        return redirect(url_for("web.dashboard"))

    user = current_user()

    if request.method == "POST":
        accion = request.form.get("accion", "guardar")
        if accion == "guardar_config":
            if not AuthService.can(user, "configuracion.write"):
                flash("Tu rol no puede modificar la configuración.", "error")
                return redirect(url_for("web.edicion_configuracion", slug=slug))
            for clave in ("periodo_academico", "bloques_horarios"):
                valor = (request.form.get(clave) or "").strip()
                if valor:
                    EdicionService.guardar_config(edicion["id"], clave, valor)
            flash("Configuración guardada correctamente.", "success")
        elif accion == "crear_version":
            if not AuthService.can(user, "configuracion.write"):
                flash("Tu rol no puede crear versiones.", "error")
                return redirect(url_for("web.edicion_configuracion", slug=slug))
            notas = (request.form.get("notas_cambios") or "").strip()
            version = EdicionService.crear_version(
                edicion["id"], "Manual", notas, user["id"]
            )
            EdicionService.cambiar_version_actual(edicion["id"], version)
            flash(f"Versión v{version} creada correctamente.", "success")
        elif accion == "restaurar_version":
            if not AuthService.can(user, "configuracion.write"):
                flash("Tu rol no puede restaurar versiones.", "error")
                return redirect(url_for("web.edicion_configuracion", slug=slug))
            version_id = request.form.get("version_id")
            try:
                EdicionService.restaurar_version(int(version_id))
                flash("Edición restaurada a la versión seleccionada.", "success")
            except (ValueError, TypeError):
                flash("No se pudo restaurar la versión indicada.", "error")
        return redirect(url_for("web.edicion_configuracion", slug=slug))

    config = EdicionService.obtener_config(edicion["id"])
    versiones = EdicionService.listar_versiones(edicion["id"])
    return render_template(
        "ediciones/configuracion.html",
        edicion=edicion,
        config=config,
        versiones=versiones,
        puede_editar=AuthService.can(user, "configuracion.write"),
    )


@web_bp.post("/ediciones/cambiar")
@login_required
def edicion_cambiar():
    """Cambia la edición activa en la sesión del usuario."""
    nueva_edicion = request.form.get("edicion_id", "1")
    try:
        nueva_edicion = int(nueva_edicion)
    except ValueError:
        nueva_edicion = 1

    from app.security.permissions import current_user
    user = current_user()
    if user:
        # Validar que el usuario pertenezca a esa edición
        ediciones = EdicionService.listar_por_usuario(user["id"])
        ids_permitidos = {e["id"] for e in ediciones}
        if nueva_edicion in ids_permitidos:
            session["edicion_id"] = nueva_edicion
            flash("Edición cambiada correctamente.", "success")
        else:
            flash("No tienes acceso a esa edición.", "error")

    referrer = request.referrer
    if referrer and referrer.startswith(request.host_url):
        return redirect(referrer)
    return redirect(url_for("web.dashboard"))
