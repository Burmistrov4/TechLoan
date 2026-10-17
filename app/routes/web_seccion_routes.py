"""Rutas web para las secciones académicas (multi-edición)."""

from flask import flash, redirect, render_template, request, url_for

from app.routes.web_common import (
    edicion_activa_id,
    form_fields,
    filtrar_por_edicion,
    permission_required,
    preparar_listado,
    registrar_accion,
    web_bp,
)
from app.services.seccion_service import SeccionService

ESTADOS = ("ACTIVA", "INACTIVA")
SEMESTRES = tuple(range(1, 11))

COLUMNAS_SECCION = (
    ("codigo_seccion", "Sección"),
    ("semestre", "Semestre"),
    ("periodo_academico", "Periodo"),
    ("carrera_o_escuela", "Carrera / Escuela"),
    ("cantidad_estimada", "Cant. estimada"),
    ("estado", "Estado"),
)


@web_bp.get("/secciones")
@permission_required("secciones.read")
def secciones():
    listado = preparar_listado(
        filtrar_por_edicion(SeccionService.list_all()),
        columnas_ordenables=tuple(clave for clave, _ in COLUMNAS_SECCION),
    )
    return render_template(
        "secciones/index.html", listado=listado, columnas=COLUMNAS_SECCION
    )


@web_bp.route("/secciones/crear", methods=["GET", "POST"])
@permission_required("secciones.write")
def seccion_crear():
    if request.method == "POST":
        data = form_fields(
            "codigo_seccion", "semestre", "periodo_academico",
            "carrera_o_escuela", "cantidad_estimada", "estado",
            empty_to_none=("cantidad_estimada",),
        )
        data["edicion_id"] = edicion_activa_id()
        try:
            nuevo_id = SeccionService.create(data)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "secciones/form.html", modo="crear", registro=data,
                estados=ESTADOS, semestres=SEMESTRES,
            ), 400
        registrar_accion("CREAR", "seccion", nuevo_id,
                         f"Alta de la sección {data['codigo_seccion']} "
                         f"({data['periodo_academico']})")
        flash("Sección registrada correctamente.", "success")
        return redirect(url_for("web.secciones"))

    return render_template(
        "secciones/form.html", modo="crear",
        registro={"estado": "ACTIVA", "semestre": ""},
        estados=ESTADOS, semestres=SEMESTRES,
    )


@web_bp.route("/secciones/<int:id_>/editar", methods=["GET", "POST"])
@permission_required("secciones.write")
def seccion_editar(id_):
    registro = SeccionService.get(id_)
    if not registro:
        flash("La sección indicada no existe.", "error")
        return redirect(url_for("web.secciones"))

    if request.method == "POST":
        data = form_fields(
            "codigo_seccion", "semestre", "periodo_academico",
            "carrera_o_escuela", "cantidad_estimada", "estado",
            empty_to_none=("cantidad_estimada",),
        )
        try:
            SeccionService.update(id_, data)
        except ValueError as exc:
            flash(str(exc), "error")
            data["id"] = id_
            return render_template(
                "secciones/form.html", modo="editar", registro=data,
                estados=ESTADOS, semestres=SEMESTRES,
            ), 400
        registrar_accion("ACTUALIZAR", "seccion", id_,
                         f"Modificación de la sección {data['codigo_seccion']}")
        flash("Sección actualizada correctamente.", "success")
        return redirect(url_for("web.secciones"))

    return render_template(
        "secciones/form.html", modo="editar", registro=registro,
        estados=ESTADOS, semestres=SEMESTRES,
    )


@web_bp.post("/secciones/<int:id_>/eliminar")
@permission_required("secciones.delete")
def seccion_eliminar(id_):
    registro = SeccionService.get(id_)
    try:
        SeccionService.delete(id_)
        if registro:
            registrar_accion("ELIMINAR", "seccion", id_,
                             f"Baja de la sección {registro['codigo_seccion']}")
        flash("Sección eliminada correctamente.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("web.secciones"))
