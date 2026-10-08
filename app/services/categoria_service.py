from app.database import get_connection


class CategoriaService:
    @staticmethod
    def _validate(data):
        nombre = data.get("nombre", "").strip()
        if not 2 <= len(nombre) <= 60:
            raise ValueError("El nombre de categoría debe tener entre 2 y 60 caracteres.")
        return nombre

    @staticmethod
    def create(data):
        nombre = CategoriaService._validate(data)
        with get_connection() as db:
            try:
                cur = db.execute(
                    "INSERT INTO categorias (nombre,descripcion) VALUES (?,?)",
                    (nombre, (data.get("descripcion") or "").strip() or None)
                )
                return cur.lastrowid
            except Exception as exc:
                if "UNIQUE constraint failed: categorias.nombre" in str(exc):
                    raise ValueError("La categoría ya existe.") from exc
                raise

    @staticmethod
    def list_all():
        with get_connection() as db:
            return [dict(r) for r in db.execute("SELECT * FROM categorias ORDER BY nombre").fetchall()]

    @staticmethod
    def get(id_):
        with get_connection() as db:
            row = db.execute("SELECT * FROM categorias WHERE id = ?", (id_,)).fetchone()
            return dict(row) if row else None

    @staticmethod
    def update(id_, data):
        nombre = CategoriaService._validate(data)
        with get_connection() as db:
            try:
                db.execute(
                    "UPDATE categorias SET nombre=?,descripcion=? WHERE id=?",
                    (nombre, (data.get("descripcion") or "").strip() or None, id_)
                )
            except Exception as exc:
                if "UNIQUE constraint failed: categorias.nombre" in str(exc):
                    raise ValueError("La categoría ya existe.") from exc
                raise

    @staticmethod
    def delete(id_):
        with get_connection() as db:
            try:
                db.execute("DELETE FROM categorias WHERE id = ?", (id_,))
            except Exception as exc:
                if "FOREIGN KEY constraint failed" in str(exc):
                    raise ValueError("No se puede eliminar: la categoría está asociada a equipos.") from exc
                raise
