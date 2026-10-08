"""Rutas web de autenticación y panel de inicio.

- ``GET  /login``   → formulario de acceso.
- ``POST /login``   → valida credenciales y abre la sesión Flask.
- ``POST /logout``  → cierra la sesión.
- ``GET  /``        → panel principal (dashboard) con indicadores.

La autenticación reutiliza ``AuthService``, que compara el hash de la contraseña
con ``werkzeug.security``. La contraseña nunca se guarda ni se compara en claro.
"""

from flask import flash, redirect, render_template, request, session, url_for

from app.routes.web_common import login_required, safe_redirect_target, web_bp
from app.services.auth_service import AuthService
from app.services.dashboard_service import DashboardService


@web_bp.get("/login")
def login():
    """Muestra el formulario de acceso."""
    if session.get("user"):
        return redirect(url_for("web.dashboard"))
    return render_template(
        "auth/login.html",
        siguiente=safe_redirect_target(request.args.get("next")) or "",
    )


@web_bp.post("/login")
def login_post():
    """Procesa el formulario de acceso."""
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    destino = safe_redirect_target(request.form.get("next"))

    try:
        user = AuthService.authenticate(username, password)
    except ValueError as exc:
        # Mensaje genérico: no se revela si el usuario existe o no.
        flash(str(exc), "error")
        return render_template("auth/login.html", usuario_intentado=username, siguiente=destino or ""), 401

    session.clear()
    session["user"] = user
    flash(f"Bienvenido, {user['nombre']}. Sesión iniciada correctamente.", "success")
    return redirect(destino or url_for("web.dashboard"))


@web_bp.post("/logout")
def logout():
    """Cierra la sesión actual."""
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("web.login"))


@web_bp.get("/")
@login_required
def dashboard():
    """Panel principal con indicadores y actividad reciente."""
    return render_template(
        "index.html",
        stats=DashboardService.stats(),
        reservas_proximas=DashboardService.reservas_proximas(),
        prestamos_activos=DashboardService.prestamos_activos(),
    )
