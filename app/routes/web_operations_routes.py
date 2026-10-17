"""Rutas web de las operaciones de negocio de TechLoan.

- Reservas de laboratorios (duración estándar de 70 min o personalizada, con
  rechazo de solapamientos y **sugerencia inteligente de horarios alternativos**).
- Comprobante imprimible de una reserva.
- Préstamos individuales de equipos (el equipo pasa a PRESTADO) y devoluciones
  (el equipo vuelve a DISPONIBLE), con detección de préstamos vencidos.
- Historial unificado con filtros y exportación.

Todas las reglas de negocio permanecen en los servicios; estas rutas solo
traducen formularios a llamadas de servicio y errores a mensajes amigables.
"""

from flask import flash, jsonify, redirect, render_template, request, url_for

from app.config import DIAS_PRESTAMO_LIMITE
from app.routes.web_common import (
    edicion_activa_id,
    exportar_csv,
    filtrar_por_edicion,
    form_fields,
    parse_int,
    permission_required,
    preparar_listado,
    registrar_accion,
    web_bp,
)
from app.security.permissions import current_user
from app.services.disponibilidad_service import DisponibilidadService
from app.services.equipo_service import EquipoService
from app.services.historial_service import HistorialService
from app.services.laboratorio_service import LaboratorioService
from app.services.prestamo_equipo_service import PrestamoEquipoService
from app.services.prestatario_service import PrestatarioService
from app.services.reservation_service import ReservaInvalida, ReservationService

ESTADOS_RESERVA = ("CONFIRMADA", "ACTIVA", "FINALIZADA", "CANCELADA")
TIPOS_HISTORIAL = ("TODOS", "RESERVA", "PRESTAMO", "DEVOLUCION")
ESTADOS_HISTORIAL = (
    "TODOS", "CONFIRMADA", "ACTIVA", "FINALIZADA",
    "CANCELADA", "DEVUELTO", "ACTIVO",
)

COLUMNAS_RESERVA = (
    ("fecha", "Fecha"),
    ("hora_inicio", "Hora de inicio"),
    ("hora_fin", "Hora de fin"),
    ("duracion_minutos", "Duración (min)"),
    ("laboratorio_codigo", "Laboratorio"),
    ("laboratorio_nombre", "Nombre del laboratorio"),
    ("cedula", "Cédula del prestatario"),
    ("prestatario_nombre", "Nombre del prestatario"),
    ("prestatario_apellido", "Apellido del prestatario"),
    ("estado", "Estado"),
    ("observaciones", "Observaciones"),
)

COLUMNAS_PRESTAMO = (
    ("id", "Nº de préstamo"),
    ("equipo_codigo", "Equipo"),
    ("prestatario_nombre", "Prestatario"),
    ("prestatario_apellido", "Apellido"),
    ("fecha_prestamo", "Fecha del préstamo"),
    ("fecha_devolucion", "Fecha de devolución"),
    ("dias_prestado", "Días prestado"),
    ("estado", "Estado"),
    ("observaciones", "Observaciones"),
)


# ===========================================================================
# RESERVAS
# ===========================================================================
@web_bp.get("/reservas")
@permission_required("reservas.read")
def reservas():
    listado = preparar_listado(
        filtrar_por_edicion(ReservationService.list_all()),
        columnas_ordenables=("fecha", "hora_inicio", "laboratorio_codigo",
                             "prestatario_apellido", "estado", "duracion_minutos"),
    )
    return render_template("reservas/index.html", listado=listado, columnas=COLUMNAS_RESERVA)


@web_bp.get("/reservas/exportar")
@permission_required("reservas.read")
def reservas_exportar():
    registrar_accion("EXPORTAR", "listado", None, "Exportación del listado de reservas")
    registros = filtrar_por_edicion(ReservationService.list_all())
    return exportar_csv(
        "techloan-reservas",
        [etiqueta for _, etiqueta in COLUMNAS_RESERVA],
        [tuple(registro.get(clave) for clave, _ in COLUMNAS_RESERVA) for registro in registros],
    )


def _contexto_reserva(registro=None):
    """Datos que necesita el formulario de reservas (listas de selección)."""
    from datetime import datetime

    from app.config import DIAS_SEMANA
    from app.services.materia_service import MateriaService
    from app.services.seccion_service import SeccionService

    laboratorios = [
        lab for lab in filtrar_por_edicion(LaboratorioService.list_all())
        if lab["estado"] == "DISPONIBLE"
    ]
    # Los desplegables muestran código y nombre para que no haya que memorizar
    # a qué laboratorio o persona corresponde cada identificador.
    for lab in laboratorios:
        lab["etiqueta"] = f"{lab['codigo']} — {lab['nombre']}"

    prestatarios = [
        p for p in filtrar_por_edicion(PrestatarioService.list_all())
        if p["estado"] == "ACTIVO"
    ]
    for prestatario in prestatarios:
        prestatario["etiqueta"] = (
            f"{prestatario['cedula']} — {prestatario['nombre']} {prestatario['apellido']}"
        )

    # Secciones y materias de la edición activa (para el horario semestral).
    secciones = [
        s for s in filtrar_por_edicion(SeccionService.list_all())
        if s["estado"] == "ACTIVA"
    ]
    for s in secciones:
        s["etiqueta"] = f"{s['codigo_seccion']} — {s['semestre']}º {s['carrera_o_escuela']}".strip()

    materias = [
        m for m in filtrar_por_edicion(MateriaService.list_all())
        if m["estado"] == "ACTIVA"
    ]
    for m in materias:
        m["etiqueta"] = f"{m['codigo']} — {m['nombre']}"

    dias = [{"valor": i, "etiqueta": DIAS_SEMANA[i]} for i in range(0, 6)]  # Lunes..Sábado

    return {
        "registro": registro or {},
        "laboratorios": laboratorios,
        "prestatarios": prestatarios,
        "secciones": secciones,
        "materias": materias,
        "dias": dias,
        # Mapa usado por JavaScript para autocompletar la duración estándar
        # del laboratorio seleccionado.
        "duraciones": {str(lab["id"]): lab["duracion_estandar_minutos"] for lab in laboratorios},
        # Fecha mínima admitida: no se permiten reservas en el pasado.
        "hoy": datetime.now().strftime("%Y-%m-%d"),
        "duracion_estandar": 70,
        "url_disponibilidad": url_for("web.disponibilidad_json"),
    }


@web_bp.route("/reservas/crear", methods=["GET", "POST"])
@permission_required("reservas.write")
def reserva_crear():
    if request.method == "POST":
        data = form_fields(
            "laboratorio_id", "prestatario_id", "fecha", "hora_inicio",
            "duracion_minutos", "observaciones",
            "tipo_reserva", "dia_semana", "periodo_academico",
            "seccion_id", "materia_id", "cantidad_estudiantes",
            empty_to_none=("observaciones", "dia_semana", "seccion_id",
                           "materia_id", "cantidad_estudiantes"),
        )
        laboratorio_id = parse_int(data.get("laboratorio_id"))
        prestatario_id = parse_int(data.get("prestatario_id"))
        duracion = parse_int(data.get("duracion_minutos"))
        tipo_reserva = (data.get("tipo_reserva") or "PUNTUAL").upper()
        dia_semana = parse_int(data.get("dia_semana"))
        seccion_id = parse_int(data.get("seccion_id"))
        materia_id = parse_int(data.get("materia_id"))
        cantidad = parse_int(data.get("cantidad_estudiantes"))

        error = None
        sugerencias = []       # franjas horarias libres
        alternativas = []      # laboratorios con cupo suficiente
        if laboratorio_id is None:
            error = "Debes seleccionar un laboratorio."
        elif prestatario_id is None:
            error = "Debes seleccionar un prestatario."
        elif duracion is None:
            error = "La duración debe ser un número entero de minutos."
        elif tipo_reserva == "SEMESTRAL" and dia_semana is None:
            error = "Para una asignación semestral debes indicar el día de la semana."

        if error is None:
            try:
                # El usuario que registra la reserva se toma SIEMPRE de la sesión,
                # nunca de un campo enviado por el navegador.
                nuevo_id = ReservationService.create_reservation(
                    laboratorio_id,
                    prestatario_id,
                    current_user()["id"],
                    data["fecha"],
                    data["hora_inicio"],
                    duracion,
                    data.get("observaciones") or "",
                    edicion_id=edicion_activa_id(),
                    tipo_reserva=tipo_reserva,
                    dia_semana=dia_semana,
                    periodo_academico=(data.get("periodo_academico") or "").strip() or None,
                    seccion_id=seccion_id,
                    materia_id=materia_id,
                    cantidad_estudiantes=cantidad,
                )
            except ReservaInvalida as exc:
                error = str(exc)
                alternativas = getattr(exc, "sugerencias", [])
                # Si el problema es un choque de horario, se calculan alternativas
                # reales en lugar de dejar al usuario sin salida.
                if "superpone" in error.lower():
                    sugerencias = ReservationService.sugerir_horarios(
                        laboratorio_id, data["fecha"], duracion, data["hora_inicio"]
                    )
            except ValueError as exc:
                error = str(exc)
                if "superpone" in error.lower():
                    sugerencias = ReservationService.sugerir_horarios(
                        laboratorio_id, data["fecha"], duracion, data["hora_inicio"]
                    )
            else:
                registrar_accion(
                    "CREAR", "reserva", nuevo_id,
                    f"Reserva {tipo_reserva} de {data['fecha']} {data['hora_inicio']} "
                    f"({duracion} min) en el laboratorio #{laboratorio_id}",
                )
                flash("Reserva registrada correctamente.", "success")
                return redirect(url_for("web.reservas"))

        flash(error, "error")
        return (
            render_template(
                "reservas/form.html",
                sugerencias=sugerencias,
                alternativas=alternativas,
                **_contexto_reserva(data),
            ),
            400,
        )

    return render_template(
        "reservas/form.html", sugerencias=[], alternativas=[], **_contexto_reserva()
    )


@web_bp.get("/reservas/rejilla-semanal")
@permission_required("reservas.read")
def reservas_rejilla():
    """Matriz semanal de la edición activa (días 0..5 × bloques).

    Devuelve la ocupación completa de la edición; el cliente filtra/resalta según
    el modo elegido (laboratorio, sección o profesor) y añade la previsualización
    en vivo. Reutilizable en la Fase 4 para el PDF.
    """
    edicion = edicion_activa_id()
    modo = (request.args.get("modo") or "laboratorio").lower()
    if modo not in ("laboratorio", "seccion", "profesor"):
        modo = "laboratorio"
    objetivo = request.args.get("id", type=int)

    from app.services.rejilla_service import RejillaService
    datos = RejillaService.construir(edicion)
    datos["modo"] = modo
    datos["objetivo_id"] = objetivo
    return jsonify({"ok": True, **datos})


@web_bp.get("/reservas/<int:id_>/comprobante")
@permission_required("reservas.read")
def reserva_comprobante(id_):
    """Comprobante imprimible de una reserva."""
    reserva = ReservationService.get(id_)
    if not reserva:
        flash("La reserva indicada no existe.", "error")
        return redirect(url_for("web.reservas"))
    return render_template("reservas/comprobante.html", reserva=reserva)


@web_bp.post("/reservas/<int:id_>/cancelar")
@permission_required("reservas.write")
def reserva_cancelar(id_):
    reserva = ReservationService.get(id_)
    try:
        ReservationService.cancel(id_)
        if reserva:
            registrar_accion(
                "CANCELAR", "reserva", id_,
                f"Cancelación de la reserva del {reserva['fecha']} "
                f"{reserva['hora_inicio']} en {reserva['laboratorio_codigo']}",
            )
        flash("Reserva cancelada correctamente.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("web.reservas"))


@web_bp.get("/reservas/disponibilidad")
@permission_required("reservas.read")
def disponibilidad_json():
    """Disponibilidad del día en JSON: la consume el formulario con ``fetch()``.

    Devuelve la ocupación completa de la jornada (para dibujar la línea de
    tiempo), si la franja consultada está libre y, cuando no lo está, las
    alternativas más cercanas. Se apoya en los mismos servicios que la
    validación del servidor, de modo que navegador y servidor nunca discrepan.
    """
    laboratorio_id = parse_int(request.args.get("laboratorio_id"))
    fecha = (request.args.get("fecha") or "").strip()
    hora_inicio = (request.args.get("hora_inicio") or "").strip()
    hora_fin = (request.args.get("hora_fin") or "").strip()
    duracion = parse_int(request.args.get("duracion"))

    if laboratorio_id is None or not fecha:
        return jsonify({"ok": False, "error": "Parámetros incompletos."}), 400

    datos = {
        "ok": True,
        "ocupacion": ReservationService.ocupacion_del_dia(laboratorio_id, fecha),
    }

    if hora_inicio and hora_fin:
        disponible, mensaje = DisponibilidadService.laboratorio(
            laboratorio_id, fecha, hora_inicio, hora_fin
        )
        datos["disponible"] = disponible
        datos["mensaje"] = mensaje
        if not disponible and duracion:
            datos["sugerencias"] = ReservationService.sugerir_horarios(
                laboratorio_id, fecha, duracion, hora_inicio
            )
    elif duracion:
        datos["sugerencias"] = ReservationService.sugerir_horarios(
            laboratorio_id, fecha, duracion, hora_inicio or None
        )

    return jsonify(datos)


# ===========================================================================
# PRÉSTAMOS Y DEVOLUCIONES
# ===========================================================================
@web_bp.get("/prestamos")
@permission_required("prestamos.read")
def prestamos():
    activos = filtrar_por_edicion(PrestamoEquipoService.list_active())
    for prestamo in activos:
        prestamo["vencido"] = (prestamo.get("dias_prestado") or 0) > DIAS_PRESTAMO_LIMITE

    todos = filtrar_por_edicion(PrestamoEquipoService.list_all())
    for prestamo in todos:
        prestamo["vencido"] = (
            prestamo["estado"] == "ACTIVO"
            and (prestamo.get("dias_prestado") or 0) > DIAS_PRESTAMO_LIMITE
        )

    solo_vencidos = (request.args.get("filtro") or "") == "vencidos"
    if solo_vencidos:
        activos = [p for p in activos if p["vencido"]]

    listado = preparar_listado(
        todos,
        columnas_ordenables=("id", "equipo_codigo", "prestatario_apellido",
                             "fecha_prestamo", "estado", "dias_prestado"),
    )

    return render_template(
        "prestamos/index.html",
        activos=activos,
        listado=listado,
        columnas=COLUMNAS_PRESTAMO,
        dias_limite=DIAS_PRESTAMO_LIMITE,
        solo_vencidos=solo_vencidos,
    )


@web_bp.get("/prestamos/exportar")
@permission_required("prestamos.read")
def prestamos_exportar():
    registrar_accion("EXPORTAR", "listado", None, "Exportación del listado de préstamos")
    registros = filtrar_por_edicion(PrestamoEquipoService.list_all())
    return exportar_csv(
        "techloan-prestamos",
        [etiqueta for _, etiqueta in COLUMNAS_PRESTAMO],
        [tuple(registro.get(clave) for clave, _ in COLUMNAS_PRESTAMO) for registro in registros],
    )


def _contexto_prestamo(registro=None):
    equipos = [
        e for e in filtrar_por_edicion(EquipoService.list_all())
        if e["estado"] == "DISPONIBLE"
    ]
    for equipo in equipos:
        equipo["etiqueta"] = f"{equipo['codigo']} — {equipo['nombre']}"

    prestatarios = [
        p for p in filtrar_por_edicion(PrestatarioService.list_all())
        if p["estado"] == "ACTIVO"
    ]
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
                nuevo_id = PrestamoEquipoService.create(
                    equipo_id,
                    prestatario_id,
                    current_user()["id"],
                    data.get("observaciones") or "",
                    edicion_id=edicion_activa_id(),
                )
            except ValueError as exc:
                error = str(exc)
            else:
                equipo = EquipoService.get(equipo_id) or {}
                registrar_accion(
                    "CREAR", "prestamo", nuevo_id,
                    f"Préstamo del equipo {equipo.get('codigo', equipo_id)} "
                    f"({equipo.get('nombre', '')})",
                )
                flash("Préstamo registrado. El equipo figura ahora como PRESTADO.", "success")
                return redirect(url_for("web.prestamos"))

        flash(error, "error")
        return render_template("prestamos/form.html", **_contexto_prestamo(data)), 400

    return render_template("prestamos/form.html", **_contexto_prestamo())


@web_bp.post("/prestamos/<int:id_>/devolver")
@permission_required("prestamos.return")
def prestamo_devolver(id_):
    observaciones = (request.form.get("observaciones") or "").strip()
    prestamo = PrestamoEquipoService.get(id_)
    try:
        PrestamoEquipoService.return_equipment(id_, observaciones)
        if prestamo:
            registrar_accion(
                "DEVOLVER", "prestamo", id_,
                f"Devolución del equipo {prestamo['equipo_codigo']} "
                f"({prestamo['equipo_nombre']})",
            )
        flash("Devolución registrada. El equipo vuelve a estar DISPONIBLE.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("web.prestamos"))


# ===========================================================================
# HISTORIAL
# ===========================================================================
def _filtros_historial():
    return {
        "tipo": (request.args.get("tipo") or "TODOS").upper(),
        "estado": (request.args.get("estado") or "TODOS").upper(),
        "recurso": (request.args.get("recurso") or "").strip(),
        "prestatario_id": parse_int(request.args.get("prestatario_id")),
        "fecha_desde": (request.args.get("fecha_desde") or "").strip(),
        "fecha_hasta": (request.args.get("fecha_hasta") or "").strip(),
    }


@web_bp.get("/historial")
@permission_required("historial.read")
def historial():
    filtros = _filtros_historial()

    registros = []
    try:
        registros = filtrar_por_edicion(HistorialService.list_all(**filtros))
    except ValueError as exc:
        flash(str(exc), "error")

    listado = preparar_listado(
        registros,
        columnas_ordenables=("fecha_operacion", "tipo", "estado", "prestatario", "recurso_codigo"),
        por_pagina_por_defecto=15,
    )

    prestatarios = filtrar_por_edicion(PrestatarioService.list_all())
    for prestatario in prestatarios:
        prestatario["etiqueta"] = (
            f"{prestatario['cedula']} — {prestatario['nombre']} {prestatario['apellido']}"
        )

    return render_template(
        "historial/index.html",
        listado=listado,
        filtros=filtros,
        tipos=TIPOS_HISTORIAL,
        estados=ESTADOS_HISTORIAL,
        prestatarios=prestatarios,
    )


@web_bp.get("/historial/exportar")
@permission_required("historial.read")
def historial_exportar():
    try:
        registros = filtrar_por_edicion(HistorialService.list_all(**_filtros_historial()))
    except ValueError:
        registros = []
    registrar_accion("EXPORTAR", "listado", None, "Exportación del historial de operaciones")
    return exportar_csv(
        "techloan-historial",
        ["Tipo", "Fecha y hora", "Prestatario", "Cédula", "Recurso", "Nombre del recurso",
         "Estado", "Registrado por", "Observaciones"],
        [
            (r["tipo"], r["fecha_operacion"], r["prestatario"], r["prestatario_cedula"],
             r["recurso_codigo"], r["recurso_nombre"], r["estado"], r["usuario"], r["observaciones"])
            for r in registros
        ],
    )
