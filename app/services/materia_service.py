import re

from app.database import get_connection

ESTADOS = {"ACTIVA", "INACTIVA"}


def _validate(data):
    errors = []
    if not re.fullmatch(r"[A-Za-z0-9._-]{2,20}", (data.get("codigo") or "").strip()):
        errors.append("Código de materia inválido (2–20 caracteres alfanuméricos).")
    if not 2 <= len((data.get("nombre") or "").strip()) <= 100:
        errors.append("Nombre de materia inválido.")
    if len((data.get("escuela") or "").strip()) > 80:
        errors.append("La escuela es demasiado larga.")
    sem = data.get("semestre")
    if sem not in (None, ""):
        try:
            if not 1 <= int(sem) <= 10:
                errors.append("El semestre debe estar entre 1 y 10.")
        except (TypeError, ValueError):
            errors.append("Semestre inválido.")
    if data.get("estado", "ACTIVA") not in ESTADOS:
        errors.append("Estado inválido.")
    return errors


class MateriaService:
    @staticmethod
    def create(data):
        errors = _validate(data)
        if errors:
            raise ValueError(" ".join(errors))
        sem = data.get("semestre")
        with get_connection() as db:
            try:
                cur = db.execute(
                    """INSERT INTO materias
                    (edicion_id, codigo, nombre, escuela, semestre, estado)
                    VALUES (?,?,?,?,?,?)""",
                    (int(data.get("edicion_id", 1)),
                     (data["codigo"]).strip(), (data["nombre"]).strip(),
                     (data.get("escuela") or "").strip(),
                     int(sem) if sem not in (None, "") else None,
                     data.get("estado", "ACTIVA"))
                )
                return cur.lastrowid
            except Exception as exc:
                if "UNIQUE constraint failed" in str(exc):
                    raise ValueError("El código de materia ya existe en esta edición.") from exc
                raise

    @staticmethod
    def list_all(edicion_id=None):
        with get_connection() as db:
            if edicion_id is not None:
                filas = db.execute(
                    "SELECT * FROM materias WHERE edicion_id = ? ORDER BY codigo",
                    (edicion_id,)
                ).fetchall()
            else:
                filas = db.execute("SELECT * FROM materias ORDER BY codigo").fetchall()
            return [dict(f) for f in filas]

    @staticmethod
    def get(id_):
        with get_connection() as db:
            fila = db.execute("SELECT * FROM materias WHERE id = ?", (id_,)).fetchone()
            return dict(fila) if fila else None

    @staticmethod
    def update(id_, data):
        errors = _validate(data)
        if errors:
            raise ValueError(" ".join(errors))
        sem = data.get("semestre")
        with get_connection() as db:
            try:
                db.execute(
                    """UPDATE materias SET codigo=?, nombre=?, escuela=?, semestre=?, estado=?
                    WHERE id=?""",
                    ((data["codigo"]).strip(), (data["nombre"]).strip(),
                     (data.get("escuela") or "").strip(),
                     int(sem) if sem not in (None, "") else None,
                     data.get("estado", "ACTIVA"), id_)
                )
            except Exception as exc:
                if "UNIQUE constraint failed" in str(exc):
                    raise ValueError("El código de materia ya existe en esta edición.") from exc
                raise

    @staticmethod
    def delete(id_):
        with get_connection() as db:
            try:
                db.execute("DELETE FROM materias WHERE id = ?", (id_,))
            except Exception as exc:
                if "FOREIGN KEY constraint failed" in str(exc):
                    raise ValueError(
                        "No se puede eliminar: la materia tiene reservas asociadas."
                    ) from exc
                raise
