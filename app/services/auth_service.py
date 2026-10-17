from werkzeug.security import check_password_hash
from app.database import get_connection

class AuthService:
    _CAMPOS = (
        "id,nombre,apellido,username,email,rol,estado,email_confirmado,password_hash"
    )

    @staticmethod
    def authenticate(identificador, password):
        """Valida las credenciales por nombre de usuario **o** por correo.

        El mensaje de error distingue tres situaciones, pero solo revela
        información a quien ya demuestra conocer la contraseña:

        - credenciales incorrectas → mensaje genérico (no se sabe si el usuario
          existe, que es lo correcto);
        - contraseña correcta pero correo sin confirmar → se explica qué hacer,
          porque si no el usuario quedaría atrapado sin saber por qué;
        - cuenta desactivada → se avisa de que debe contactar con administración.
        """
        if not identificador or not password:
            raise ValueError("Usuario y contraseña son obligatorios.")

        identificador = identificador.strip()

        with get_connection() as db:
            row = db.execute(
                f"SELECT {AuthService._CAMPOS} FROM usuarios_sistema WHERE username = ?",
                (identificador,),
            ).fetchone()
            if not row:
                # Se admite también el correo, que es como se registra la gente.
                row = db.execute(
                    f"SELECT {AuthService._CAMPOS} FROM usuarios_sistema WHERE email = ?",
                    (identificador.lower(),),
                ).fetchone()

        if not row or not check_password_hash(row["password_hash"], password):
            raise ValueError("Credenciales inválidas.")

        if not row["email_confirmado"]:
            raise ValueError(
                "Tu cuenta todavía no está confirmada. Abre el enlace que te enviamos "
                "por correo; si caducó, pide uno nuevo desde la pantalla de acceso."
            )

        if row["estado"] != "ACTIVO":
            raise ValueError("Tu cuenta está desactivada. Contacta con la administración.")

        user = dict(row)
        # Datos internos que no deben viajar en la sesión.
        user.pop("password_hash", None)
        user.pop("email_confirmado", None)
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
                "ediciones.read", "ediciones.write", "ediciones.delete",
                "configuracion.read", "configuracion.write",
                "secciones.read", "secciones.write", "secciones.delete",
                "materias.read", "materias.write", "materias.delete",
                "sistema.inspector",
            },
            "OPERADOR": {
                "prestatarios.read", "prestatarios.write",
                "laboratorios.read", "categorias.read", "equipos.read",
                "reservas.read", "reservas.write",
                "prestamos.read", "prestamos.write", "prestamos.return",
                "historial.read",
                "ediciones.read", "configuracion.read",
                "secciones.read", "secciones.write",
                "materias.read", "materias.write",
            },
        }
        return bool(user and permission in permissions.get(user.get("rol"), set()))
