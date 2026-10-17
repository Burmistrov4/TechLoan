import re

from app.database import get_connection

ESTADOS = {"ACTIVA", "INACTIVA"}
# Admite «SA», «SB», «SA-A», «SAA» o códigos con número («3A-1»), pero no
# caracteres extraños ni minúsculas.
_REGLA_CODIGO = re.compile(r"[A-Z0-9]{1,4}(-[A-Z0-9]{1,3})?")


def _validate(data):
    errors = []
    codigo = (data.get("codigo_seccion") or "").strip().upper()
    if not _REGLA_CODIGO.fullmatch(codigo):
        errors.append("Código de sección inválido (usar 1–4 caracteres A-Z/0-9, "
                      "con un guion opcional y 1–3 caracteres más).")
    try:
        semestre = int(data["semestre"])
        if not 1 <= semestre <= 10:
            errors.append("El semestre debe estar entre 1 y 10.")
    except (KeyError, TypeError, ValueError):
        errors.append("Semestre inválido.")
    periodo = (data.get("periodo_academico") or "").strip()
    if not 2 <= len(periodo) <= 12:
        errors.append("Periodo académico inválido (ej.: 2026-2).")
    if len((data.get("carrera_o_escuela") or "").strip()) > 80:
        errors.append("La carrera o escuela es demasiado larga.")
    cant = data.get("cantidad_estimada")
    if cant not in (None, ""):
        try:
            if int(cant) < 0:
                errors.append("La cantidad estimada no puede ser negativa.")
        except (TypeError, ValueError):
            errors.append("Cantidad estimada inválida.")
    if data.get("estado", "ACTIVA") not in ESTADOS:
        errors.append("Estado inválido.")
    return errors


class SeccionService:
    @staticmethod
    def create(data):
        errors = _validate(data)
        if errors:
            raise ValueError(" ".join(errors))
        cant = data.get("cantidad_estimada")
        with get_connection() as db:
            try:
                cur = db.execute(
                    """INSERT INTO secciones
                    (edicion_id, codigo_seccion, semestre, periodo_academico,
                     carrera_o_escuela, cantidad_estimada, estado)
                    VALUES (?,?,?,?,?,?,?)""",
                    (int(data.get("edicion_id", 1)),
                     (data["codigo_seccion"]).strip().upper(),
                     int(data["semestre"]),
                     (data["periodo_academico"]).strip(),
                     (data.get("carrera_o_escuela") or "").strip(),
                     int(cant) if cant not in (None, "") else None,
                     data.get("estado", "ACTIVA"))
                )
                return cur.lastrowid
            except Exception as exc:
                if "UNIQUE constraint failed" in str(exc):
                    raise ValueError(
                        "Ya existe esa sección para el semestre y periodo indicados "
                        "en esta edición."
                    ) from exc
                raise

    @staticmethod
    def list_all(edicion_id=None):
        with get_connection() as db:
            if edicion_id is not None:
                filas = db.execute(
                    "SELECT * FROM secciones WHERE edicion_id = ? "
                    "ORDER BY codigo_seccion, semestre", (edicion_id,)
                ).fetchall()
            else:
                filas = db.execute(
                    "SELECT * FROM secciones ORDER BY codigo_seccion, semestre"
                ).fetchall()
            return [dict(f) for f in filas]

    @staticmethod
    def get(id_):
        with get_connection() as db:
            fila = db.execute("SELECT * FROM secciones WHERE id = ?", (id_,)).fetchone()
            return dict(fila) if fila else None

    @staticmethod
    def update(id_, data):
        errors = _validate(data)
        if errors:
            raise ValueError(" ".join(errors))
        cant = data.get("cantidad_estimada")
        with get_connection() as db:
            try:
                db.execute(
                    """UPDATE secciones SET codigo_seccion=?, semestre=?, periodo_academico=?,
                    carrera_o_escuela=?, cantidad_estimada=?, estado=? WHERE id=?""",
                    ((data["codigo_seccion"]).strip().upper(),
                     int(data["semestre"]),
                     (data["periodo_academico"]).strip(),
                     (data.get("carrera_o_escuela") or "").strip(),
                     int(cant) if cant not in (None, "") else None,
                     data.get("estado", "ACTIVA"), id_)
                )
            except Exception as exc:
                if "UNIQUE constraint failed" in str(exc):
                    raise ValueError(
                        "Ya existe esa sección para el semestre y periodo indicados "
                        "en esta edición."
                    ) from exc
                raise

    @staticmethod
    def delete(id_):
        with get_connection() as db:
            try:
                db.execute("DELETE FROM secciones WHERE id = ?", (id_,))
            except Exception as exc:
                if "FOREIGN KEY constraint failed" in str(exc):
                    raise ValueError(
                        "No se puede eliminar: la sección tiene reservas asociadas."
                    ) from exc
                raise
