"""Servicio de auditoría: registra quién hizo qué y cuándo.

La auditoría es deliberadamente **tolerante a fallos**: si el registro de una
acción falla, la operación de negocio que la originó no debe romperse. Un
problema al escribir el historial nunca debe impedir que el usuario guarde su
trabajo.

Nota de diseño: ``usuario_id`` no tiene clave foránea a ``usuarios_sistema``.
Un registro de auditoría debe sobrevivir a la eliminación del usuario y
conservar su nombre como evidencia histórica.
"""

import sys
from datetime import datetime

from app.database import get_connection

ACCIONES = ("CREAR", "ACTUALIZAR", "ELIMINAR", "DEVOLVER", "CANCELAR",
            "ACCEDER", "SALIR", "EXPORTAR")

# Etiquetas legibles para la interfaz.
ETIQUETAS_ACCION = {
    "CREAR": "Creación",
    "ACTUALIZAR": "Modificación",
    "ELIMINAR": "Eliminación",
    "DEVOLVER": "Devolución",
    "CANCELAR": "Cancelación",
    "ACCEDER": "Inicio de sesión",
    "SALIR": "Cierre de sesión",
    "EXPORTAR": "Exportación",
}

ETIQUETAS_ENTIDAD = {
    "prestatario": "Prestatario",
    "categoria": "Categoría",
    "laboratorio": "Laboratorio",
    "equipo": "Equipo",
    "usuario": "Usuario del sistema",
    "reserva": "Reserva",
    "prestamo": "Préstamo",
    "sesion": "Sesión",
    "listado": "Listado",
}


class AuditoriaService:
    @staticmethod
    def registrar(usuario, accion, entidad, entidad_id=None, descripcion="", direccion_ip=None):
        """Anota una acción en el registro de actividad.

        Nunca lanza excepción: si la escritura falla, se informa por la salida
        de errores y el flujo principal continúa.
        """
        if accion not in ACCIONES:
            return
        try:
            with get_connection() as db:
                db.execute(
                    """INSERT INTO auditoria
                       (usuario_id, usuario_username, accion, entidad, entidad_id,
                        descripcion, direccion_ip, fecha)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        (usuario or {}).get("id"),
                        (usuario or {}).get("username", "anónimo"),
                        accion,
                        entidad,
                        entidad_id,
                        descripcion or "",
                        direccion_ip,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
        except Exception as exc:  # pragma: no cover - la auditoría no debe romper el flujo
            print(f"[auditoria] No se pudo registrar la acción: {exc}", file=sys.stderr)

    @staticmethod
    def listar(accion="", entidad="", usuario="", fecha_desde="", fecha_hasta="", limite=200):
        """Devuelve el registro de actividad con filtros opcionales."""
        sql = "SELECT * FROM auditoria WHERE 1=1"
        params = []

        if accion:
            sql += " AND accion = ?"
            params.append(accion.upper())
        if entidad:
            sql += " AND entidad = ?"
            params.append(entidad.lower())
        if usuario:
            sql += " AND LOWER(usuario_username) LIKE LOWER(?)"
            params.append(f"%{usuario}%")
        if fecha_desde:
            sql += " AND substr(fecha, 1, 10) >= ?"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND substr(fecha, 1, 10) <= ?"
            params.append(fecha_hasta)

        sql += " ORDER BY fecha DESC, id DESC LIMIT ?"
        params.append(int(limite))

        with get_connection() as db:
            return [dict(fila) for fila in db.execute(sql, tuple(params)).fetchall()]

    @staticmethod
    def recientes(limite=6):
        """Últimas acciones registradas, para el panel de inicio."""
        with get_connection() as db:
            return [
                dict(fila)
                for fila in db.execute(
                    "SELECT * FROM auditoria ORDER BY fecha DESC, id DESC LIMIT ?",
                    (int(limite),),
                ).fetchall()
            ]

    @staticmethod
    def total():
        with get_connection() as db:
            return db.execute("SELECT COUNT(*) FROM auditoria").fetchone()[0]
