"""Utilidades compartidas por las rutas web (HTML/Jinja2) de TechLoan.

Aquí vive el blueprint ``web_bp``, los decoradores de sesión/permisos y la
protección CSRF. Las rutas concretas se definen en:

- ``web_auth_routes.py``        → inicio de sesión, cierre de sesión, panel.
- ``web_crud_routes.py``        → CRUD de las entidades del dominio.
- ``web_operations_routes.py``  → reservas, préstamos, devoluciones e historial.

Todas las rutas web reutilizan los servicios POO existentes; ninguna escribe SQL
directamente.
"""

import secrets
from functools import wraps

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    request,
    session,
    url_for,
)

from app.security.permissions import current_user
from app.services.auth_service import AuthService

# Blueprint sin prefijo: el PDF pide rutas limpias en la raíz ("/", "/crear").
web_bp = Blueprint("web", __name__)


# ---------------------------------------------------------------------------
# Protección CSRF
# ---------------------------------------------------------------------------
def csrf_token():
    """Devuelve (creando si hace falta) el token CSRF de la sesión actual.

    Se expone a las plantillas mediante un context processor, de modo que todos
    los formularios puedan incluirlo como campo oculto.
    """
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


@web_bp.before_request
def _verify_csrf():
    """Rechaza cualquier POST web sin un token CSRF válido.

    La API JSON (``/api/...``) vive en otros blueprints y no se ve afectada.
    """
    if request.method != "POST":
        return None

    enviado = request.form.get("_csrf_token", "")
    esperado = session.get("_csrf_token", "")
    if not esperado or not enviado or not secrets.compare_digest(enviado, esperado):
        abort(400, description="Token de seguridad inválido o expirado. Recargue la página e inténtelo de nuevo.")
    return None


# ---------------------------------------------------------------------------
# Decoradores de sesión y permisos
# ---------------------------------------------------------------------------
def login_required(view):
    """Exige una sesión activa; si no la hay, redirige al formulario de acceso."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Debes iniciar sesión para acceder a esa página.", "error")
            return redirect(url_for("web.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def permission_required(permission, redirect_endpoint="web.dashboard"):
    """Exige que el usuario de la sesión tenga el permiso indicado.

    El rol se revalida contra la base de datos en cada petición (ver
    ``app.security.permissions.current_user``), por lo que un usuario degradado
    o desactivado pierde el acceso de inmediato.
    """

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                flash("Debes iniciar sesión para continuar.", "error")
                return redirect(url_for("web.login"))
            if not AuthService.can(user, permission):
                flash("Tu rol no tiene permisos para realizar esa acción.", "error")
                return redirect(url_for(redirect_endpoint))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def can(permission):
    """Atajo para las plantillas: ¿el usuario actual tiene este permiso?"""
    return AuthService.can(current_user(), permission)


# ---------------------------------------------------------------------------
# Lectura de formularios
# ---------------------------------------------------------------------------
def form_fields(*names, empty_to_none=()):
    """Extrae del formulario los campos indicados, ya recortados.

    Siempre devuelve cadenas (nunca ``None``) para que las validaciones de los
    servicios no fallen con ``AttributeError``. Los campos listados en
    ``empty_to_none`` se convierten a ``None`` cuando llegan vacíos, que es lo
    que esperan las columnas opcionales de la base de datos.
    """
    data = {name: (request.form.get(name) or "").strip() for name in names}
    for name in empty_to_none:
        if data.get(name) == "":
            data[name] = None
    return data


def parse_int(value, default=None):
    """Convierte a entero de forma segura; devuelve ``default`` si no es válido."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def safe_redirect_target(target):
    """Evita redirecciones abiertas: solo acepta rutas internas relativas."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return None
    return target
