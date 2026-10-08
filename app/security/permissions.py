from functools import wraps

from flask import g, has_request_context, jsonify, session

from app.services.auth_service import AuthService

# Centinela que distingue "todavía no calculado" de "calculado y sin usuario".
_SIN_CALCULAR = object()


def current_user():
    """Devuelve el usuario de la sesión revalidado contra la base de datos.

    El resultado se memoriza en ``flask.g`` para no repetir la consulta varias
    veces dentro de la misma petición (el menú de navegación, por ejemplo,
    comprueba permisos en cada enlace).
    """
    if has_request_context():
        memorizado = getattr(g, "_techloan_usuario", _SIN_CALCULAR)
        if memorizado is not _SIN_CALCULAR:
            return memorizado

    resultado = _load_current_user()

    if has_request_context():
        g._techloan_usuario = resultado
    return resultado


def _load_current_user():
    user = session.get("user")
    if not user:
        return None

    # Revalidar el estado/rol desde la base de datos en cada petición protegida.
    from app.database import get_connection

    with get_connection() as db:
        row = db.execute(
            "SELECT id,nombre,apellido,username,email,rol,estado "
            "FROM usuarios_sistema WHERE id=?",
            (user.get("id"),),
        ).fetchone()

    if not row or row["estado"] != "ACTIVO":
        session.clear()
        return None

    return dict(row)


def _check(permission):
    user = current_user()
    if not user:
        return None, (jsonify({"ok": False, "error": "Autenticación requerida."}), 401)
    if not AuthService.can(user, permission):
        return None, (jsonify({"ok": False, "error": "Permiso insuficiente."}), 403)
    return user, None


def require_permission(permission):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                return jsonify({"ok": False, "error": "Autenticación requerida."}), 401
            if not AuthService.can(user, permission):
                return jsonify({"ok": False, "error": "Permiso insuficiente."}), 403
            return view(*args, **kwargs)

        return wrapped

    return decorator


def require_crud_permissions(read_permission, write_permission, delete_permission):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            from flask import request
            permission = read_permission
            if request.method in ("POST", "PUT"):
                permission = write_permission
            elif request.method == "DELETE":
                permission = delete_permission
            _, error = _check(permission)
            if error:
                return error
            return view(*args, **kwargs)
        return wrapped
    return decorator
