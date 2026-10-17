"""Servidor Flask de TechLoan.

Expone dos capas sobre el mismo núcleo de servicios:

1. **Interfaz web** (``web_bp``) — páginas HTML renderizadas con Jinja2. Es la
   entrega exigida por el PDF del profesor (``/``, ``/crear``, ``/editar/<id>``,
   ``/eliminar/<id>``, ...).
2. **API JSON** (``/api/...``) — endpoints reutilizados por el cliente Tkinter,
   por las pruebas y por las llamadas ``fetch()`` del navegador.

Ambas capas comparten exactamente los mismos servicios POO y, por tanto, las
mismas reglas de negocio y validaciones.
"""

from pathlib import Path

from flask import Flask, jsonify, render_template, request, session

from app.config import SECRET_KEY
from app.database import init_database
from app.routes.auth_routes import auth_bp
from app.routes.crud_routes import crud_bp
from app.routes.operations_routes import operations_bp
from app.routes.reservation_routes import reservation_bp

# Se importan para que registren sus rutas sobre ``web_bp``.
from app.routes import web_auth_routes  # noqa: F401
from app.routes import web_crud_routes  # noqa: F401
from app.routes import web_extra_routes  # noqa: F401
from app.routes import web_operations_routes  # noqa: F401
from app.routes import web_ediciones_routes  # noqa: F401
from app.routes import web_inspector_routes  # noqa: F401
from app.routes.web_common import csrf_token, web_bp

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


def _wants_json():
    """¿La petición espera una respuesta JSON en lugar de HTML?"""
    return request.path.startswith("/api/") or request.path.startswith("/health")


def _register_filters(app):
    """Filtros de plantilla disponibles en todo el proyecto."""
    from app.routes.web_common import fecha_corta

    app.jinja_env.filters["fecha_corta"] = fecha_corta
    app.jinja_env.filters["dia_corto"] = lambda valor: fecha_corta(valor, con_anio=False)


def _register_error_handlers(app):
    """Páginas de error amigables; nunca se muestra una traza al usuario."""

    def _render(codigo, titulo, detalle):
        if _wants_json():
            return jsonify({"ok": False, "error": titulo, "detalle": detalle}), codigo
        return (
            render_template(
                "errores/error.html", codigo=codigo, titulo=titulo, detalle=detalle
            ),
            codigo,
        )

    @app.errorhandler(400)
    def bad_request(error):
        return _render(
            400,
            "Solicitud inválida",
            getattr(error, "description", "") or "Los datos enviados no son válidos.",
        )

    @app.errorhandler(403)
    def forbidden(error):
        return _render(403, "Acceso denegado", "No tienes permisos para ver esta página.")

    @app.errorhandler(404)
    def not_found(error):
        return _render(404, "Página no encontrada", "La dirección solicitada no existe.")

    @app.errorhandler(500)
    def server_error(error):
        return _render(
            500,
            "Error interno del servidor",
            "Ocurrió un error inesperado. Vuelve a intentarlo desde el inicio.",
        )


def create_app():
    """Crea y configura la aplicación Flask."""
    app = Flask(
        __name__,
        template_folder=str(TEMPLATES_DIR),
        static_folder=str(STATIC_DIR),
    )
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # Garantiza que las tablas existan (CREATE TABLE IF NOT EXISTS).
    # Para reconstruir la base de datos con datos de prueba: ``python init_db.py``.
    init_database()

    # Capa 2: API JSON.
    app.register_blueprint(auth_bp)
    app.register_blueprint(reservation_bp)
    app.register_blueprint(crud_bp)
    app.register_blueprint(operations_bp)

    # Capa 1: interfaz web.
    app.register_blueprint(web_bp)

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "service": "TechLoan", "status": "running"})

    @app.context_processor
    def inject_globals():
        """Variables disponibles en todas las plantillas."""
        from datetime import datetime

        from app.routes.web_common import alertas_actuales, can, url_con
        from app.security.permissions import current_user
        from app.services.edicion_service import EdicionService

        user = current_user()
        ediciones = []
        edicion_actual = None
        if user:
            ediciones = EdicionService.listar_por_usuario(user["id"])
            edicion_id = session.get("edicion_id", 1)
            for e in ediciones:
                if e["id"] == edicion_id:
                    edicion_actual = e
                    break
            if not edicion_actual and ediciones:
                edicion_actual = ediciones[0]
                session["edicion_id"] = edicion_actual["id"]

        return {
            "csrf_token": csrf_token,
            "usuario_actual": user,
            "puede": can,
            "alertas": alertas_actuales(),
            "url_con": url_con,
            "anio": datetime.now().year,
            "edicion_actual": edicion_actual,
            "ediciones_disponibles": ediciones,
        }

    _register_error_handlers(app)
    _register_filters(app)
    return app


if __name__ == "__main__":
    from app.config import HOST, PORT

    create_app().run(host=HOST, port=PORT, debug=False)
