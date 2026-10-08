import re
from app.database import get_connection

ESTADOS = {"DISPONIBLE", "PRESTADO", "MANTENIMIENTO", "DANADO", "INACTIVO"}


def _validate(data):
    errors = []
    if not re.fullmatch(r"[A-Za-z0-9._-]{2,30}", data.get("codigo", "").strip()):
        errors.append("Código de equipo inválido.")
    if not 2 <= len(data.get("nombre", "").strip()) <= 100:
        errors.append("Nombre de equipo inválido.")
    if data.get("estado", "DISPONIBLE") not in ESTADOS:
        errors.append("Estado de equipo inválido.")
    for field in ("categoria_id", "laboratorio_id"):
        if data.get(field) not in (None, ""):
            try:
                if int(data[field]) <= 0:
                    errors.append(f"{field} inválido.")
            except (TypeError, ValueError):
                errors.append(f"{field} inválido.")
    serial = data.get("serial")
    if serial and not re.fullmatch(r"[A-Za-z0-9._-]{3,50}", serial.strip()):
        errors.append("Serial inválido.")
    return errors


class EquipoService:
    @staticmethod
    def create(data):
        errors = _validate(data)
        if errors:
            raise ValueError(" ".join(errors))
        with get_connection() as db:
            try:
                cur = db.execute(
                    """INSERT INTO equipos
                    (codigo,nombre,categoria_id,marca,modelo,serial,laboratorio_id,estado)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (data["codigo"].strip(),data["nombre"].strip(),
                     int(data["categoria_id"]) if data.get("categoria_id") else None,
                     (data.get("marca") or "").strip() or None,
                     (data.get("modelo") or "").strip() or None,
                     (data.get("serial") or "").strip() or None,
                     int(data["laboratorio_id"]) if data.get("laboratorio_id") else None,
                     data.get("estado","DISPONIBLE"))
                )
                return cur.lastrowid
            except Exception as exc:
                if "UNIQUE constraint failed: equipos.codigo" in str(exc):
                    raise ValueError("El código de equipo ya existe.") from exc
                if "UNIQUE constraint failed: equipos.serial" in str(exc):
                    raise ValueError("El serial ya existe.") from exc
                raise

    @staticmethod
    def list_all():
        with get_connection() as db:
            return [dict(r) for r in db.execute(
                """SELECT e.*, c.nombre AS categoria_nombre, l.nombre AS laboratorio_nombre
                   FROM equipos e
                   LEFT JOIN categorias c ON c.id=e.categoria_id
                   LEFT JOIN laboratorios l ON l.id=e.laboratorio_id
                   ORDER BY e.codigo"""
            ).fetchall()]

    @staticmethod
    def get(id_):
        with get_connection() as db:
            row = db.execute("SELECT * FROM equipos WHERE id = ?", (id_,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def update(id_, data):
        errors = _validate(data)
        if errors:
            raise ValueError(" ".join(errors))
        with get_connection() as db:
            try:
                db.execute(
                    """UPDATE equipos SET codigo=?,nombre=?,categoria_id=?,marca=?,modelo=?,
                    serial=?,laboratorio_id=?,estado=? WHERE id=?""",
                    (data["codigo"].strip(),data["nombre"].strip(),
                     int(data["categoria_id"]) if data.get("categoria_id") else None,
                     (data.get("marca") or "").strip() or None,
                     (data.get("modelo") or "").strip() or None,
                     (data.get("serial") or "").strip() or None,
                     int(data["laboratorio_id"]) if data.get("laboratorio_id") else None,
                     data.get("estado","DISPONIBLE"),id_)
                )
            except Exception as exc:
                if "UNIQUE constraint failed: equipos.codigo" in str(exc):
                    raise ValueError("El código de equipo ya existe.") from exc
                if "UNIQUE constraint failed: equipos.serial" in str(exc):
                    raise ValueError("El serial ya existe.") from exc
                raise

    @staticmethod
    def delete(id_):
        with get_connection() as db:
            try:
                db.execute("DELETE FROM equipos WHERE id = ?", (id_,))
            except Exception as exc:
                if "FOREIGN KEY constraint failed" in str(exc):
                    raise ValueError("No se puede eliminar: el equipo tiene registros asociados.") from exc
                raise
