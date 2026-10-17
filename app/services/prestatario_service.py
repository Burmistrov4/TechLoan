import re
from app.database import get_connection

TIPOS = {"ESTUDIANTE", "PROFESOR", "EMPLEADO", "OTRO"}
ESTADOS = {"ACTIVO", "INACTIVO"}


def _validate(data):
    errors = []
    if not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü ]{2,50}", data.get("nombre", "").strip()):
        errors.append("Nombre inválido.")
    if not re.fullmatch(r"[A-Za-zÁÉÍÓÚáéíóúÑñÜü ]{2,50}", data.get("apellido", "").strip()):
        errors.append("Apellido inválido.")
    if not re.fullmatch(r"[A-Za-z0-9.-]{5,20}", data.get("cedula", "").strip()):
        errors.append("Cédula inválida.")
    if data.get("tipo") not in TIPOS:
        errors.append("Tipo de prestatario inválido.")
    if data.get("estado", "ACTIVO") not in ESTADOS:
        errors.append("Estado inválido.")
    email = (data.get("email") or "").strip()
    if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        errors.append("Correo inválido.")
    return errors


class PrestatarioService:
    @staticmethod
    def create(data):
        errors = _validate(data)
        if errors:
            raise ValueError(" ".join(errors))
        with get_connection() as db:
            try:
                cur = db.execute(
                    """INSERT INTO prestatarios
                    (edicion_id, cedula,nombre,apellido,tipo,telefono,email,estado)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (int(data.get("edicion_id", 1)), data["cedula"].strip(), data["nombre"].strip(), data["apellido"].strip(),
                     data["tipo"], data.get("telefono"), data.get("email"), data.get("estado","ACTIVO"))
                )
                return cur.lastrowid
            except Exception as exc:
                if "UNIQUE constraint failed" in str(exc) and "cedula" in str(exc):
                    raise ValueError("La cédula ya está registrada en esta edición.") from exc
                raise

    @staticmethod
    def list_all():
        with get_connection() as db:
            return [dict(r) for r in db.execute(
                "SELECT * FROM prestatarios ORDER BY apellido, nombre"
            ).fetchall()]

    @staticmethod
    def get(id_):
        with get_connection() as db:
            row = db.execute("SELECT * FROM prestatarios WHERE id = ?", (id_,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def update(id_, data):
        errors = _validate(data)
        if errors:
            raise ValueError(" ".join(errors))
        with get_connection() as db:
            try:
                db.execute(
                    """UPDATE prestatarios SET cedula=?,nombre=?,apellido=?,tipo=?,
                    telefono=?,email=?,estado=? WHERE id=?""",
                    (data["cedula"].strip(), data["nombre"].strip(), data["apellido"].strip(),
                     data["tipo"], data.get("telefono"), data.get("email"), data.get("estado","ACTIVO"), id_)
                )
            except Exception as exc:
                if "UNIQUE constraint failed" in str(exc) and "cedula" in str(exc):
                    raise ValueError("La cédula ya está registrada en esta edición.") from exc
                raise

    @staticmethod
    def delete(id_):
        with get_connection() as db:
            try:
                db.execute("DELETE FROM prestatarios WHERE id = ?", (id_,))
            except Exception as exc:
                if "FOREIGN KEY constraint failed" in str(exc):
                    raise ValueError("No se puede eliminar: el prestatario tiene registros asociados.") from exc
                raise
