"""Rutas web para las materias (multi-edición)."""

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
from app.services.materia_service import MateriaService

ESTADOS = ("ACTIVA", "INACTIVA")
SEMESTRES = ("",) + tuple(range(1, 11))  # el vacío = sin semestre

COLUMNAS_MATERIA = (
    ("codigo", "Código"),
    ("nombre", "Nombre"),
    ("escuela", "Escuela"),
    ("semestre", "Semestre"),
    ("estado", "Estado"),
)


@web_bp.get("/materias")
@permission_required("materias.read")
def materias():
    listado = preparar_listado(
        filtrar_por_edicion(MateriaService.list_all()),
        columnas_ordenables=tuple(clave for clave, _ in COLUMNAS_MATERIA),
    )
    return render_template(
        "materias/index.html", listado=listado, columnas=COLUMNAS_MATERIA
    )


@web_bp.route("/materias/crear", methods=["GET", "POST"])
@permission_required("materias.write")
def materia_crear():
    if request.method == "POST":
        data = form_fields(
            "codigo", "nombre", "escuela", "semestre", "estado",
            empty_to_none=("semestre",),
        )
        data["edicion_id"] = edicion_activa_id()
        try:
            nuevo_id = MateriaService.create(data)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "materias/form.html", modo="crear", registro=data,
                estados=ESTADOS, semestres=SEMESTRES,
            ), 400
        registrar_accion("CREAR", "materia", nuevo_id,
                         f"Alta de la materia {data['codigo']} ({data['nombre']})")
        flash("Materia registrada correctamente.", "success")
        return redirect(url_for("web.materias"))

    return render_template(
        "materias/form.html", modo="crear",
        registro={"estado": "ACTIVA", "semestre": ""},
        estados=ESTADOS, semestres=SEMESTRES,
    )


@web_bp.route("/materias/<int:id_>/editar", methods=["GET", "POST"])
@permission_required("materias.write")
def materia_editar(id_):
    registro = MateriaService.get(id_)
    if not registro:
        flash("La materia indicada no existe.", "error")
        return redirect(url_for("web.materias"))

    if request.method == "POST":
        data = form_fields(
            "codigo", "nombre", "escuela", "semestre", "estado",
            empty_to_none=("semestre",),
        )
        try:
            MateriaService.update(id_, data)
        except ValueError as exc:
            flash(str(exc), "error")
            data["id"] = id_
            return render_template(
                "materias/form.html", modo="editar", registro=data,
                estados=ESTADOS, semestres=SEMESTRES,
            ), 400
        registrar_accion("ACTUALIZAR", "materia", id_,
                         f"Modificación de la materia {data['codigo']}")
        flash("Materia actualizada correctamente.", "success")
        return redirect(url_for("web.materias"))

    return render_template(
        "materias/form.html", modo="editar", registro=registro,
        estados=ESTADOS, semestres=SEMESTRES,
    )


@web_bp.post("/materias/<int:id_>/eliminar")
@permission_required("materias.delete")
def materia_eliminar(id_):
    registro = MateriaService.get(id_)
    try:
        MateriaService.delete(id_)
        if registro:
            registrar_accion("ELIMINAR", "materia", id_,
                             f"Baja de la materia {registro['codigo']}")
        flash("Materia eliminada correctamente.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("web.materias"))
