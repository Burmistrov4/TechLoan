from werkzeug.security import check_password_hash
from app.database import get_connection

class AuthService:
    @staticmethod
    def authenticate(username, password):
        if not username or not password:
            raise ValueError("Usuario y contraseña son obligatorios.")
        with get_connection() as db:
            row = db.execute("SELECT id,nombre,apellido,username,email,rol,estado,password_hash FROM usuarios_sistema WHERE username=?", (username.strip(),)).fetchone()
        if not row or row["estado"] != "ACTIVO" or not check_password_hash(row["password_hash"], password):
            raise ValueError("Credenciales inválidas.")
        user = dict(row)
        user.pop("password_hash", None)
        return user

    @staticmethod
    def can(user, permission):
        """Comprueba si el rol del usuario incluye el permiso indicado.

        El rol OPERADOR puede operar el día a día (prestatarios, reservas,
        préstamos y devoluciones) pero no administra el sistema: no gestiona
        usuarios, no elimina registros de catálogo y no consulta la auditoría.
        """
        permissions = {
            "ADMINISTRADOR": {
                "prestatarios.read", "prestatarios.write", "prestatarios.delete",
                "laboratorios.read", "laboratorios.write", "laboratorios.delete",
                "categorias.read", "categorias.write", "categorias.delete",
                "equipos.read", "equipos.write", "equipos.delete",
                "usuarios.read", "usuarios.write", "usuarios.delete",
                "reservas.read", "reservas.write",
                "prestamos.read", "prestamos.write", "prestamos.return",
                "historial.read", "auditoria.read",
            },
            "OPERADOR": {
                "prestatarios.read", "prestatarios.write",
                "laboratorios.read", "categorias.read", "equipos.read",
                "reservas.read", "reservas.write",
                "prestamos.read", "prestamos.write", "prestamos.return",
                "historial.read",
            },
        }
        return bool(user and permission in permissions.get(user.get("rol"), set()))
