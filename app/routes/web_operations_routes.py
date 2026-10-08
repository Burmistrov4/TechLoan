"""Rutas web de las operaciones de negocio de TechLoan.

- Reservas de laboratorios (duración estándar de 70 min o personalizada,
  con rechazo de solapamientos).
- Préstamos individuales de equipos (el equipo pasa a PRESTADO).
- Devoluciones (el equipo vuelve a DISPONIBLE).
- Historial unificado con filtros.

Todas las reglas de negocio permanecen en los servicios; estas rutas solo
traducen formularios a llamadas de servicio y errores a mensajes amigables.
"""

from flask import flash, redirect, render_template, request, url_for

from app.routes.web_common import form_fields, parse_int, permission_required, web_bp
from app.services.disponibilidad_service import DisponibilidadService
from app.services.equipo_service import EquipoService
from app.services.historial_service import HistorialService
from app.services.laboratorio_service import LaboratorioService
from app.services.prestamo_equipo_service import PrestamoEquipoService
from app.services.prestatario_service import PrestatarioService
from app.services.reservation_service import ReservationService

ESTADOS_RESERVA = ("CONFIRMADA", "ACTIVA", "FINALIZADA", "CANCELADA")
TIPOS_HISTORIAL = ("TODOS", "RESERVA", "PRESTAMO", "DEVOLUCION")
ESTADOS_HISTORIAL = (
    "TODOS", "CONFIRMADA", "ACTIVA", "FINALIZADA",
    "CANCELADA", "DEVUELTO", "ACTIVO",
)


# ===========================================================================
# RESERVAS
# ===========================================================================
@web_bp.get("/reservas")
@permission_required("reservas.read")
def reservas():
    return render_template("reservas/index.html", reservas=ReservationService.list_all())


def _contexto_reserva(registro=None):
    """Datos que necesita el formulario de reservas (listas de selección)."""
    from datetime import datetime

    laboratorios = [
        lab for lab in LaboratorioService.list_all() if lab["estado"] == "DISPONIBLE"
    ]
    # Los desplegables muestran código y nombre para que no haya que memorizar
    # a qué laboratorio o persona corresponde cada identificador.
    for lab in laboratorios:
        lab["etiqueta"] = f"{lab['codigo']} — {lab['nombre']}"

    prestatarios = [
        p for p in PrestatarioService.list_all() if p["estado"] == "ACTIVO"
    ]
    for prestatario in prestatarios:
        prestatario["etiqueta"] = (
            f"{prestatario['cedula']} — {prestatario['nombre']} {prestatario['apellido']}"
        )

    return {
        "registro": registro or {},
        "laboratorios": laboratorios,
        "prestatarios": prestatarios,
        # Mapa usado por JavaScript para autocompletar la duración estándar
        # del laboratorio seleccionado.
        "duraciones": {str(lab["id"]): lab["duracion_estandar_minutos"] for lab in laboratorios},
        # Fecha mínima admitida: no se permiten reservas en el pasado.
        "hoy": datetime.now().strftime("%Y-%m-%d"),
        "duracion_estandar": 70,
    }


@web_bp.route("/reservas/crear", methods=["GET", "POST"])
@permission_required("reservas.write")
def reserva_crear():
    from app.security.permissions import current_user

    if request.method == "POST":
        data = form_fields(
            "laboratorio_id", "prestatario_id", "fecha", "hora_inicio",
            "duracion_minutos", "observaciones",
            empty_to_none=("observaciones",),
        )
        laboratorio_id = parse_int(data.get("laboratorio_id"))
        prestatario_id = parse_int(data.get("prestatario_id"))
        duracion = parse_int(data.get("duracion_minutos"))

        error = None
        if laboratorio_id is None:
            error = "Debes seleccionar un laboratorio."
        elif prestatario_id is None:
            error = "Debes seleccionar un prestatario."
        elif duracion is None:
            error = "La duración debe ser un número entero de minutos."

        if error is None:
            try:
                # El usuario que registra la reserva se toma SIEMPRE de la sesión,
                # nunca de un campo enviado por el navegador.
                ReservationService.create_reservation(
                    laboratorio_id,
                    prestatario_id,
                    current_user()["id"],
                    data["fecha"],
                    data["hora_inicio"],
                    duracion,
                    data.get("observaciones") or "",
                )
            except ValueError as exc:
                error = str(exc)

        if error:
            flash(error, "error")
            return render_template("reservas/form.html", **_contexto_reserva(data)), 400

        flash("Reserva registrada correctamente.", "success")
        return redirect(url_for("web.reservas"))

    return render_template("reservas/form.html", **_contexto_reserva())


@web_bp.post("/reservas/<int:id_>/cancelar")
@permission_required("reservas.write")
def reserva_cancelar(id_):
    try:
        ReservationService.cancel(id_)
        flash("Reserva cancelada correctamente.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("web.reservas"))


@web_bp.get("/reservas/disponibilidad")
@permission_required("reservas.read")
def disponibilidad_json():
    """Endpoint JSON consumido con ``fetch()`` para avisar de solapamientos.

    Se apoya en el servicio de disponibilidad existente, de modo que la
    comprobación del navegador y la del servidor usan exactamente la misma
    regla de negocio.
    """
    from flask import jsonify

    laboratorio_id = parse_int(request.args.get("laboratorio_id"))
    fecha = (request.args.get("fecha") or "").strip()
    hora_inicio = (request.args.get("hora_inicio") or "").strip()
    hora_fin = (request.args.get("hora_fin") or "").strip()

    if laboratorio_id is None or not fecha or not hora_inicio or not hora_fin:
        return jsonify({"ok": False, "error": "Parámetros incompletos."}), 400

    disponible, mensaje = DisponibilidadService.laboratorio(
        laboratorio_id, fecha, hora_inicio, hora_fin
    )
    return jsonify({"ok": True, "disponible": disponible, "mensaje": mensaje})


# ===========================================================================
# PRÉSTAMOS Y DEVOLUCIONES
# ===========================================================================
@web_bp.get("/prestamos")
@permission_required("prestamos.read")
def prestamos():
    return render_template(
        "prestamos/index.html",
        prestamos=PrestamoEquipoService.list_all(),
        activos=PrestamoEquipoService.list_active(),
    )


def _contexto_prestamo(registro=None):
    equipos = [e for e in EquipoService.list_all() if e["estado"] == "DISPONIBLE"]
    for equipo in equipos:
        equipo["etiqueta"] = f"{equipo['codigo']} — {equipo['nombre']}"

    prestatarios = [p for p in PrestatarioService.list_all() if p["estado"] == "ACTIVO"]
    for prestatario in prestatarios:
        prestatario["etiqueta"] = (
            f"{prestatario['cedula']} — {prestatario['nombre']} {prestatario['apellido']}"
        )

    return {
        "registro": registro or {},
        "equipos": equipos,
        "prestatarios": prestatarios,
    }


@web_bp.route("/prestamos/crear", methods=["GET", "POST"])
@permission_required("prestamos.write")
def prestamo_crear():
    from app.security.permissions import current_user

    if request.method == "POST":
        data = form_fields(
            "equipo_id", "prestatario_id", "observaciones",
            empty_to_none=("observaciones",),
        )
        equipo_id = parse_int(data.get("equipo_id"))
        prestatario_id = parse_int(data.get("prestatario_id"))

        error = None
        if equipo_id is None:
            error = "Debes seleccionar un equipo."
        elif prestatario_id is None:
            error = "Debes seleccionar un prestatario."

        if error is None:
            try:
                PrestamoEquipoService.create(
                    equipo_id,
                    prestatario_id,
                    current_user()["id"],
                    data.get("observaciones") or "",
                )
            except ValueError as exc:
                error = str(exc)

        if error:
            flash(error, "error")
            return render_template("prestamos/form.html", **_contexto_prestamo(data)), 400

        flash("Préstamo registrado. El equipo figura ahora como PRESTADO.", "success")
        return redirect(url_for("web.prestamos"))

    return render_template("prestamos/form.html", **_contexto_prestamo())


@web_bp.post("/prestamos/<int:id_>/devolver")
@permission_required("prestamos.return")
def prestamo_devolver(id_):
    observaciones = (request.form.get("observaciones") or "").strip()
    try:
        PrestamoEquipoService.return_equipment(id_, observaciones)
        flash("Devolución registrada. El equipo vuelve a estar DISPONIBLE.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("web.prestamos"))


# ===========================================================================
# HISTORIAL
# ===========================================================================
@web_bp.get("/historial")
@permission_required("historial.read")
def historial():
    filtros = {
        "tipo": (request.args.get("tipo") or "TODOS").upper(),
        "estado": (request.args.get("estado") or "TODOS").upper(),
        "recurso": (request.args.get("recurso") or "").strip(),
        "prestatario_id": parse_int(request.args.get("prestatario_id")),
        "fecha_desde": (request.args.get("fecha_desde") or "").strip(),
        "fecha_hasta": (request.args.get("fecha_hasta") or "").strip(),
    }

    error = None
    registros = []
    try:
        registros = HistorialService.list_all(
            tipo=filtros["tipo"],
            prestatario_id=filtros["prestatario_id"],
            recurso=filtros["recurso"],
            estado=filtros["estado"],
            fecha_desde=filtros["fecha_desde"],
            fecha_hasta=filtros["fecha_hasta"],
        )
    except ValueError as exc:
        error = str(exc)
        flash(error, "error")

    prestatarios = PrestatarioService.list_all()
    for prestatario in prestatarios:
        prestatario["etiqueta"] = (
            f"{prestatario['cedula']} — {prestatario['nombre']} {prestatario['apellido']}"
        )

    return render_template(
        "historial/index.html",
        registros=registros,
        filtros=filtros,
        tipos=TIPOS_HISTORIAL,
        estados=ESTADOS_HISTORIAL,
        prestatarios=prestatarios,
        error=error,
    )
