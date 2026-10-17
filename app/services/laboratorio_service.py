import re
from app.database import get_connection

ESTADOS = {"DISPONIBLE", "MANTENIMIENTO", "INACTIVO"}


def _validate(data):
    errors = []
    if not re.fullmatch(r"[A-Za-z0-9._-]{2,20}", data.get("codigo", "").strip()):
        errors.append("Código de laboratorio inválido.")
    if not 2 <= len(data.get("nombre", "").strip()) <= 80:
        errors.append("Nombre de laboratorio inválido.")
    if not 2 <= len(data.get("ubicacion", "").strip()) <= 100:
        errors.append("Ubicación inválida.")
    try:
        capacidad = int(data["capacidad"])
        if capacidad <= 0 or capacidad > 1000:
            errors.append("La capacidad debe estar entre 1 y 1000.")
    except (KeyError, TypeError, ValueError):
        errors.append("Capacidad inválida.")
    try:
        duracion = int(data.get("duracion_estandar_minutos", 70))
        if duracion <= 0 or duracion > 1440:
            errors.append("La duración estándar debe estar entre 1 y 1440 minutos.")
    except (TypeError, ValueError):
        errors.append("Duración estándar inválida.")
    if data.get("estado", "DISPONIBLE") not in ESTADOS:
        errors.append("Estado inválido.")
    return errors


class LaboratorioService:
    @staticmethod
    def create(data):
        errors = _validate(data)
        if errors:
            raise ValueError(" ".join(errors))
        with get_connection() as db:
            try:
                cur = db.execute(
                    """INSERT INTO laboratorios
                    (edicion_id, codigo,nombre,ubicacion,capacidad,duracion_estandar_minutos,estado)
                    VALUES (?,?,?,?,?,?,?)""",
                    (int(data.get("edicion_id", 1)), data["codigo"].strip(),data["nombre"].strip(),data["ubicacion"].strip(),
                     int(data["capacidad"]),int(data.get("duracion_estandar_minutos",70)),
                     data.get("estado","DISPONIBLE"))
                )
                return cur.lastrowid
            except Exception as exc:
                if "UNIQUE constraint failed" in str(exc) and "codigo" in str(exc):
                    raise ValueError("El código de laboratorio ya existe en esta edición.") from exc
                raise

    @staticmethod
    def list_all(edicion_id=None):
        with get_connection() as db:
            if edicion_id is not None:
                return [dict(r) for r in db.execute(
                    "SELECT * FROM laboratorios WHERE edicion_id = ? ORDER BY codigo", (edicion_id,)
                ).fetchall()]
            return [dict(r) for r in db.execute("SELECT * FROM laboratorios ORDER BY codigo").fetchall()]

    @staticmethod
    def get(id_):
        with get_connection() as db:
            row = db.execute("SELECT * FROM laboratorios WHERE id = ?", (id_,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def update(id_, data):
        errors = _validate(data)
        if errors:
            raise ValueError(" ".join(errors))
        with get_connection() as db:
            try:
                db.execute(
                    """UPDATE laboratorios SET codigo=?,nombre=?,ubicacion=?,capacidad=?,
                    duracion_estandar_minutos=?,estado=? WHERE id=?""",
                    (data["codigo"].strip(),data["nombre"].strip(),data["ubicacion"].strip(),
                     int(data["capacidad"]),int(data.get("duracion_estandar_minutos",70)),
                     data.get("estado","DISPONIBLE"),id_)
                )
            except Exception as exc:
                if "UNIQUE constraint failed" in str(exc) and "codigo" in str(exc):
                    raise ValueError("El código de laboratorio ya existe en esta edición.") from exc
                raise

    @staticmethod
    def delete(id_):
        with get_connection() as db:
            try:
                db.execute("DELETE FROM laboratorios WHERE id = ?", (id_,))
            except Exception as exc:
                if "FOREIGN KEY constraint failed" in str(exc):
                    raise ValueError("No se puede eliminar: el laboratorio tiene equipos o reservas asociadas.") from exc
                raise
