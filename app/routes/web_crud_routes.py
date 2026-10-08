"""Rutas web del CRUD para las entidades del dominio TechLoan.

Cubre Prestatarios, Categorías, Laboratorios, Equipos y Usuarios del sistema.

Convenciones:
- ``GET  /<entidad>``                    → listado.
- ``GET  /<entidad>/crear``              → formulario de alta.
- ``POST /<entidad>/crear``              → guarda el registro.
- ``GET  /<entidad>/<id>/editar``        → formulario de edición precargado.
- ``POST /<entidad>/<id>/editar``        → guarda los cambios.
- ``POST /<entidad>/<id>/eliminar``      → elimina (nunca por GET).

Además, la entidad principal del caso de estudio (Prestatarios) expone también
las rutas limpias sugeridas por el PDF del profesor:

    /crear, /editar/<id>, /eliminar/<id>

Toda la lógica de negocio y la validación viven en los servicios; estas rutas
solo orquestan formularios, permisos y mensajes.
"""

from flask import flash, redirect, render_template, request, url_for

from app.routes.web_common import form_fields, permission_required, web_bp
from app.services.categoria_service import CategoriaService
from app.services.equipo_service import EquipoService
from app.services.laboratorio_service import LaboratorioService
from app.services.prestatario_service import PrestatarioService
from app.services.usuario_service import UsuarioService

# Valores admitidos por los CHECK de la base de datos. Se usan para poblar los
# <select> de los formularios y mantener la interfaz alineada con el esquema.
TIPOS_PRESTATARIO = ("ESTUDIANTE", "PROFESOR", "EMPLEADO", "OTRO")
ESTADOS_BASICOS = ("ACTIVO", "INACTIVO")
ESTADOS_LABORATORIO = ("DISPONIBLE", "MANTENIMIENTO", "INACTIVO")
ESTADOS_EQUIPO = ("DISPONIBLE", "PRESTADO", "MANTENIMIENTO", "DANADO", "INACTIVO")
ROLES = ("ADMINISTRADOR", "OPERADOR")


def _etiquetar_categorias():
    """Categorías con una clave ``etiqueta`` para los desplegables."""
    categorias = CategoriaService.list_all()
    for categoria in categorias:
        categoria["etiqueta"] = categoria["nombre"]
    return categorias


def _etiquetar_laboratorios():
    """Laboratorios con una clave ``etiqueta`` (código y nombre juntos)."""
    laboratorios = LaboratorioService.list_all()
    for laboratorio in laboratorios:
        laboratorio["etiqueta"] = f"{laboratorio['codigo']} — {laboratorio['nombre']}"
    return laboratorios


# ===========================================================================
# PRESTATARIOS — entidad principal del CRUD (rutas del PDF incluidas)
# ===========================================================================
@web_bp.get("/prestatarios")
@permission_required("prestatarios.read")
def prestatarios():
    return render_template("prestatarios/index.html", prestatarios=PrestatarioService.list_all())


@web_bp.route("/prestatarios/crear", methods=["GET", "POST"])
@web_bp.route("/crear", methods=["GET", "POST"])
@permission_required("prestatarios.write")
def prestatario_crear():
    if request.method == "POST":
        data = form_fields(
            "cedula", "nombre", "apellido", "tipo", "telefono", "email", "estado",
            empty_to_none=("telefono", "email"),
        )
        try:
            PrestatarioService.create(data)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "prestatarios/form.html", modo="crear", registro=data,
                tipos=TIPOS_PRESTATARIO, estados=ESTADOS_BASICOS,
            ), 400
        flash("Prestatario registrado correctamente.", "success")
        return redirect(url_for("web.prestatarios"))

    return render_template(
        "prestatarios/form.html", modo="crear",
        registro={"tipo": "ESTUDIANTE", "estado": "ACTIVO"},
        tipos=TIPOS_PRESTATARIO, estados=ESTADOS_BASICOS,
    )


@web_bp.route("/prestatarios/<int:id_>/editar", methods=["GET", "POST"])
@web_bp.route("/editar/<int:id_>", methods=["GET", "POST"])
@permission_required("prestatarios.write")
def prestatario_editar(id_):
    registro = PrestatarioService.get(id_)
    if not registro:
        flash("El prestatario indicado no existe.", "error")
        return redirect(url_for("web.prestatarios"))

    if request.method == "POST":
        data = form_fields(
            "cedula", "nombre", "apellido", "tipo", "telefono", "email", "estado",
            empty_to_none=("telefono", "email"),
        )
        try:
            PrestatarioService.update(id_, data)
        except ValueError as exc:
            flash(str(exc), "error")
            data["id"] = id_
            return render_template(
                "prestatarios/form.html", modo="editar", registro=data,
                tipos=TIPOS_PRESTATARIO, estados=ESTADOS_BASICOS,
            ), 400
        flash("Prestatario actualizado correctamente.", "success")
        return redirect(url_for("web.prestatarios"))

    return render_template(
        "prestatarios/form.html", modo="editar", registro=registro,
        tipos=TIPOS_PRESTATARIO, estados=ESTADOS_BASICOS,
    )


@web_bp.post("/prestatarios/<int:id_>/eliminar")
@web_bp.post("/eliminar/<int:id_>")
@permission_required("prestatarios.delete")
def prestatario_eliminar(id_):
    try:
        PrestatarioService.delete(id_)
        flash("Prestatario eliminado correctamente.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("web.prestatarios"))


# ===========================================================================
# CATEGORÍAS
# ===========================================================================
@web_bp.get("/categorias")
@permission_required("categorias.read")
def categorias():
    return render_template("categorias/index.html", categorias=CategoriaService.list_all())


@web_bp.route("/categorias/crear", methods=["GET", "POST"])
@permission_required("categorias.write")
def categoria_crear():
    if request.method == "POST":
        data = form_fields("nombre", "descripcion", empty_to_none=("descripcion",))
        try:
            CategoriaService.create(data)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("categorias/form.html", modo="crear", registro=data), 400
        flash("Categoría registrada correctamente.", "success")
        return redirect(url_for("web.categorias"))

    return render_template("categorias/form.html", modo="crear", registro={})


@web_bp.route("/categorias/<int:id_>/editar", methods=["GET", "POST"])
@permission_required("categorias.write")
def categoria_editar(id_):
    registro = CategoriaService.get(id_)
    if not registro:
        flash("La categoría indicada no existe.", "error")
        return redirect(url_for("web.categorias"))

    if request.method == "POST":
        data = form_fields("nombre", "descripcion", empty_to_none=("descripcion",))
        try:
            CategoriaService.update(id_, data)
        except ValueError as exc:
            flash(str(exc), "error")
            data["id"] = id_
            return render_template("categorias/form.html", modo="editar", registro=data), 400
        flash("Categoría actualizada correctamente.", "success")
        return redirect(url_for("web.categorias"))

    return render_template("categorias/form.html", modo="editar", registro=registro)


@web_bp.post("/categorias/<int:id_>/eliminar")
@permission_required("categorias.delete")
def categoria_eliminar(id_):
    try:
        CategoriaService.delete(id_)
        flash("Categoría eliminada correctamente.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("web.categorias"))


# ===========================================================================
# LABORATORIOS
# ===========================================================================
@web_bp.get("/laboratorios")
@permission_required("laboratorios.read")
def laboratorios():
    return render_template("laboratorios/index.html", laboratorios=LaboratorioService.list_all())


@web_bp.route("/laboratorios/crear", methods=["GET", "POST"])
@permission_required("laboratorios.write")
def laboratorio_crear():
    if request.method == "POST":
        data = form_fields(
            "codigo", "nombre", "ubicacion", "capacidad",
            "duracion_estandar_minutos", "estado",
        )
        try:
            LaboratorioService.create(data)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "laboratorios/form.html", modo="crear", registro=data,
                estados=ESTADOS_LABORATORIO,
            ), 400
        flash("Laboratorio registrado correctamente.", "success")
        return redirect(url_for("web.laboratorios"))

    return render_template(
        "laboratorios/form.html", modo="crear",
        registro={"duracion_estandar_minutos": 70, "estado": "DISPONIBLE"},
        estados=ESTADOS_LABORATORIO,
    )


@web_bp.route("/laboratorios/<int:id_>/editar", methods=["GET", "POST"])
@permission_required("laboratorios.write")
def laboratorio_editar(id_):
    registro = LaboratorioService.get(id_)
    if not registro:
        flash("El laboratorio indicado no existe.", "error")
        return redirect(url_for("web.laboratorios"))

    if request.method == "POST":
        data = form_fields(
            "codigo", "nombre", "ubicacion", "capacidad",
            "duracion_estandar_minutos", "estado",
        )
        try:
            LaboratorioService.update(id_, data)
        except ValueError as exc:
            flash(str(exc), "error")
            data["id"] = id_
            return render_template(
                "laboratorios/form.html", modo="editar", registro=data,
                estados=ESTADOS_LABORATORIO,
            ), 400
        flash("Laboratorio actualizado correctamente.", "success")
        return redirect(url_for("web.laboratorios"))

    return render_template(
        "laboratorios/form.html", modo="editar", registro=registro,
        estados=ESTADOS_LABORATORIO,
    )


@web_bp.post("/laboratorios/<int:id_>/eliminar")
@permission_required("laboratorios.delete")
def laboratorio_eliminar(id_):
    try:
        LaboratorioService.delete(id_)
        flash("Laboratorio eliminado correctamente.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("web.laboratorios"))


# ===========================================================================
# EQUIPOS
# ===========================================================================
@web_bp.get("/equipos")
@permission_required("equipos.read")
def equipos():
    return render_template("equipos/index.html", equipos=EquipoService.list_all())


@web_bp.route("/equipos/crear", methods=["GET", "POST"])
@permission_required("equipos.write")
def equipo_crear():
    if request.method == "POST":
        data = form_fields(
            "codigo", "nombre", "categoria_id", "marca", "modelo", "serial",
            "laboratorio_id", "estado",
            empty_to_none=("categoria_id", "marca", "modelo", "serial", "laboratorio_id"),
        )
        try:
            EquipoService.create(data)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "equipos/form.html", modo="crear", registro=data,
                categorias=_etiquetar_categorias(),
                laboratorios=_etiquetar_laboratorios(),
                estados=ESTADOS_EQUIPO,
            ), 400
        flash("Equipo registrado correctamente.", "success")
        return redirect(url_for("web.equipos"))

    return render_template(
        "equipos/form.html", modo="crear", registro={"estado": "DISPONIBLE"},
        categorias=_etiquetar_categorias(),
        laboratorios=_etiquetar_laboratorios(),
        estados=ESTADOS_EQUIPO,
    )


@web_bp.route("/equipos/<int:id_>/editar", methods=["GET", "POST"])
@permission_required("equipos.write")
def equipo_editar(id_):
    registro = EquipoService.get(id_)
    if not registro:
        flash("El equipo indicado no existe.", "error")
        return redirect(url_for("web.equipos"))

    if request.method == "POST":
        data = form_fields(
            "codigo", "nombre", "categoria_id", "marca", "modelo", "serial",
            "laboratorio_id", "estado",
            empty_to_none=("categoria_id", "marca", "modelo", "serial", "laboratorio_id"),
        )
        try:
            EquipoService.update(id_, data)
        except ValueError as exc:
            flash(str(exc), "error")
            data["id"] = id_
            return render_template(
                "equipos/form.html", modo="editar", registro=data,
                categorias=_etiquetar_categorias(),
                laboratorios=_etiquetar_laboratorios(),
                estados=ESTADOS_EQUIPO,
            ), 400
        flash("Equipo actualizado correctamente.", "success")
        return redirect(url_for("web.equipos"))

    return render_template(
        "equipos/form.html", modo="editar", registro=registro,
        categorias=_etiquetar_categorias(),
        laboratorios=_etiquetar_laboratorios(),
        estados=ESTADOS_EQUIPO,
    )


@web_bp.post("/equipos/<int:id_>/eliminar")
@permission_required("equipos.delete")
def equipo_eliminar(id_):
    try:
        EquipoService.delete(id_)
        flash("Equipo eliminado correctamente.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("web.equipos"))


# ===========================================================================
# USUARIOS DEL SISTEMA (solo ADMINISTRADOR)
# ===========================================================================
@web_bp.get("/usuarios")
@permission_required("usuarios.read")
def usuarios():
    return render_template("usuarios/index.html", usuarios=UsuarioService.list_all())


@web_bp.route("/usuarios/crear", methods=["GET", "POST"])
@permission_required("usuarios.write")
def usuario_crear():
    if request.method == "POST":
        data = form_fields("nombre", "apellido", "username", "email", "password", "rol", "estado")
        try:
            UsuarioService.create(data)
        except ValueError as exc:
            flash(str(exc), "error")
            data.pop("password", None)  # nunca se reimprime la contraseña
            return render_template(
                "usuarios/form.html", modo="crear", registro=data,
                roles=ROLES, estados=ESTADOS_BASICOS,
            ), 400
        flash("Usuario del sistema registrado correctamente.", "success")
        return redirect(url_for("web.usuarios"))

    return render_template(
        "usuarios/form.html", modo="crear",
        registro={"rol": "OPERADOR", "estado": "ACTIVO"},
        roles=ROLES, estados=ESTADOS_BASICOS,
    )


@web_bp.route("/usuarios/<int:id_>/editar", methods=["GET", "POST"])
@permission_required("usuarios.write")
def usuario_editar(id_):
    registro = UsuarioService.get(id_)
    if not registro:
        flash("El usuario indicado no existe.", "error")
        return redirect(url_for("web.usuarios"))

    if request.method == "POST":
        data = form_fields("nombre", "apellido", "username", "email", "password", "rol", "estado")
        try:
            UsuarioService.update(id_, data)
        except ValueError as exc:
            flash(str(exc), "error")
            data.pop("password", None)
            data["id"] = id_
            return render_template(
                "usuarios/form.html", modo="editar", registro=data,
                roles=ROLES, estados=ESTADOS_BASICOS,
            ), 400
        flash("Usuario actualizado correctamente.", "success")
        return redirect(url_for("web.usuarios"))

    return render_template(
        "usuarios/form.html", modo="editar", registro=registro,
        roles=ROLES, estados=ESTADOS_BASICOS,
    )


@web_bp.post("/usuarios/<int:id_>/eliminar")
@permission_required("usuarios.delete")
def usuario_eliminar(id_):
    try:
        UsuarioService.delete(id_)
        flash("Usuario eliminado correctamente.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("web.usuarios"))
