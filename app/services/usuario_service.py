import re
from werkzeug.security import check_password_hash, generate_password_hash
from app.database import get_connection

ROLES = {"ADMINISTRADOR", "OPERADOR"}
ESTADOS = {"ACTIVO", "INACTIVO"}

class UsuarioService:
    @staticmethod
    def _validate(data, password_required=True):
        errors = []
        if not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü ]{2,50}", data.get("nombre", "").strip()):
            errors.append("Nombre inválido.")
        if not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü ]{2,50}", data.get("apellido", "").strip()):
            errors.append("Apellido inválido.")
        if not re.fullmatch(r"[A-Za-z0-9_]{4,20}", data.get("username", "").strip()):
            errors.append("El usuario debe tener 4-20 caracteres alfanuméricos o _.")
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", data.get("email", "").strip()):
            errors.append("Correo inválido.")
        if data.get("rol") not in ROLES:
            errors.append("Rol inválido.")
        if data.get("estado", "ACTIVO") not in ESTADOS:
            errors.append("Estado inválido.")
        password = data.get("password", "")
        if password_required or password:
            if len(password) < 8 or len(password) > 72:
                errors.append("La contraseña debe tener entre 8 y 72 caracteres.")
            if not re.search(r"[A-Z]", password):
                errors.append("La contraseña debe incluir una mayúscula.")
            if not re.search(r"[a-z]", password):
                errors.append("La contraseña debe incluir una minúscula.")
            if not re.search(r"\d", password):
                errors.append("La contraseña debe incluir un número.")
            if not re.search(r"[^A-Za-z0-9]", password):
                errors.append("La contraseña debe incluir un carácter especial.")
        return errors

    @staticmethod
    def create(data):
        errors = UsuarioService._validate(data, True)
        if errors:
            raise ValueError(" ".join(errors))
        password_hash = generate_password_hash(data["password"])
        if len(password_hash) > 255:
            raise ValueError("El hash generado excede VARCHAR(255).")
        with get_connection() as db:
            try:
                cur = db.execute(
                    "INSERT INTO usuarios_sistema (nombre,apellido,username,email,password_hash,rol,estado) VALUES (?,?,?,?,?,?,?)",
                    (data["nombre"].strip(), data["apellido"].strip(), data["username"].strip(),
                     data["email"].strip().lower(), password_hash, data["rol"], data.get("estado","ACTIVO"))
                )
                return cur.lastrowid
            except Exception as exc:
                if "usuarios_sistema.username" in str(exc):
                    raise ValueError("El nombre de usuario ya existe.") from exc
                if "usuarios_sistema.email" in str(exc):
                    raise ValueError("El correo ya está registrado.") from exc
                raise

    @staticmethod
    def list_all():
        with get_connection() as db:
            return [dict(r) for r in db.execute(
                "SELECT id,nombre,apellido,username,email,rol,estado,fecha_registro FROM usuarios_sistema ORDER BY apellido,nombre"
            ).fetchall()]

    @staticmethod
    def get(id_):
        with get_connection() as db:
            row = db.execute(
                "SELECT id,nombre,apellido,username,email,rol,estado,fecha_registro FROM usuarios_sistema WHERE id=?",
                (id_,)
            ).fetchone()
            return dict(row) if row else None

    @staticmethod
    def update(id_, data):
        errors = UsuarioService._validate(data, bool(data.get("password")))
        if errors:
            raise ValueError(" ".join(errors))
        with get_connection() as db:
            try:
                if data.get("password"):
                    password_hash = generate_password_hash(data["password"])
                    db.execute(
                        "UPDATE usuarios_sistema SET nombre=?,apellido=?,username=?,email=?,password_hash=?,rol=?,estado=? WHERE id=?",
                        (data["nombre"].strip(),data["apellido"].strip(),data["username"].strip(),
                         data["email"].strip().lower(),password_hash,data["rol"],data.get("estado","ACTIVO"),id_)
                    )
                else:
                    db.execute(
                        "UPDATE usuarios_sistema SET nombre=?,apellido=?,username=?,email=?,rol=?,estado=? WHERE id=?",
                        (data["nombre"].strip(),data["apellido"].strip(),data["username"].strip(),
                         data["email"].strip().lower(),data["rol"],data.get("estado","ACTIVO"),id_)
                    )
            except Exception as exc:
                if "usuarios_sistema.username" in str(exc):
                    raise ValueError("El nombre de usuario ya existe.") from exc
                if "usuarios_sistema.email" in str(exc):
                    raise ValueError("El correo ya está registrado.") from exc
                raise

    @staticmethod
    def cambiar_password(usuario_id, password_actual, password_nueva, password_repetida):
        """Cambia la contraseña del propio usuario.

        Exige la contraseña actual como comprobación de identidad: tener la
        sesión abierta no basta para cambiarla. La nueva contraseña se valida
        con las mismas reglas que las demás y se guarda siempre como hash.
        """
        if password_nueva != password_repetida:
            raise ValueError("La nueva contraseña y su confirmación no coinciden.")

        with get_connection() as db:
            fila = db.execute(
                "SELECT password_hash FROM usuarios_sistema WHERE id=?", (usuario_id,)
            ).fetchone()
            if not fila:
                raise ValueError("El usuario no existe.")
            if not check_password_hash(fila["password_hash"], password_actual or ""):
                raise ValueError("La contraseña actual no es correcta.")

            errores = []
            if len(password_nueva) < 8 or len(password_nueva) > 72:
                errores.append("La contraseña debe tener entre 8 y 72 caracteres.")
            if not re.search(r"[A-Z]", password_nueva):
                errores.append("La contraseña debe incluir una mayúscula.")
            if not re.search(r"[a-z]", password_nueva):
                errores.append("La contraseña debe incluir una minúscula.")
            if not re.search(r"\d", password_nueva):
                errores.append("La contraseña debe incluir un número.")
            if not re.search(r"[^A-Za-z0-9]", password_nueva):
                errores.append("La contraseña debe incluir un carácter especial.")
            if errores:
                raise ValueError(" ".join(errores))

            if check_password_hash(fila["password_hash"], password_nueva):
                raise ValueError("La nueva contraseña debe ser distinta de la actual.")

            nuevo_hash = generate_password_hash(password_nueva)
            if len(nuevo_hash) > 255:
                raise ValueError("El hash generado excede VARCHAR(255).")

            db.execute(
                "UPDATE usuarios_sistema SET password_hash=? WHERE id=?",
                (nuevo_hash, usuario_id),
            )

    @staticmethod
    def delete(id_):
        with get_connection() as db:
            row = db.execute("SELECT rol FROM usuarios_sistema WHERE id=?", (id_,)).fetchone()
            if not row:
                return
            if row["rol"] == "ADMINISTRADOR":
                total = db.execute("SELECT COUNT(*) AS total FROM usuarios_sistema WHERE rol='ADMINISTRADOR' AND estado='ACTIVO'").fetchone()["total"]
                if total <= 1:
                    raise ValueError("No se puede eliminar al último administrador activo.")
            db.execute("DELETE FROM usuarios_sistema WHERE id=?", (id_,))
