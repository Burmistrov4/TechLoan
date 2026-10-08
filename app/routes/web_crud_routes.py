"""Rutas web del CRUD para las entidades del dominio TechLoan.

Cubre Prestatarios, Categorías, Laboratorios, Equipos y Usuarios del sistema.

Convenciones:
- ``GET  /<entidad>``                    → listado con búsqueda, orden y paginación.
- ``GET  /<entidad>/exportar``           → descarga del listado en CSV.
- ``GET  /<entidad>/crear``              → formulario de alta.
- ``POST /<entidad>/crear``              → guarda el registro.
- ``GET  /<entidad>/<id>/editar``        → formulario de edición precargado.
- ``POST /<entidad>/<id>/editar``        → guarda los cambios.
- ``POST /<entidad>/<id>/eliminar``      → elimina (nunca por GET).

Además, la entidad principal del caso de estudio (Prestatarios) expone también
las rutas limpias sugeridas por el PDF del profesor:

    /crear, /editar/<id>, /eliminar/<id>

Toda la lógica de negocio y la validación viven en los servicios; estas rutas
solo orquestan formularios, permisos, mensajes y el registro de auditoría.
"""

from flask import flash, redirect, render_template, request, url_for

from app.routes.web_common import (
    exportar_csv,
    filtrar_texto,
    form_fields,
    permission_required,
    preparar_listado,
    registrar_accion,
    web_bp,
)
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

# Definición de columnas de cada listado: (clave, etiqueta).
# La misma definición alimenta la cabecera ordenable de la tabla y la
# exportación a CSV, de modo que ambas no pueden desincronizarse.
COLUMNAS_PRESTATARIO = (
    ("cedula", "Cédula"),
    ("nombre", "Nombre"),
    ("apellido", "Apellido"),
    ("tipo", "Tipo"),
    ("telefono", "Teléfono"),
    ("email", "Correo"),
    ("estado", "Estado"),
)
COLUMNAS_CATEGORIA = (
    ("nombre", "Nombre"),
    ("descripcion", "Descripción"),
)
COLUMNAS_LABORATORIO = (
    ("codigo", "Código"),
    ("nombre", "Nombre"),
    ("ubicacion", "Ubicación"),
    ("capacidad", "Capacidad"),
    ("duracion_estandar_minutos", "Duración estándar (min)"),
    ("estado", "Estado"),
)
COLUMNAS_EQUIPO = (
    ("codigo", "Código"),
    ("nombre", "Nombre"),
    ("categoria_nombre", "Categoría"),
    ("laboratorio_nombre", "Laboratorio"),
    ("marca", "Marca"),
    ("modelo", "Modelo"),
    ("serial", "Serial"),
    ("estado", "Estado"),
)
COLUMNAS_USUARIO = (
    ("nombre", "Nombre"),
    ("apellido", "Apellido"),
    ("username", "Usuario"),
    ("email", "Correo"),
    ("rol", "Rol"),
    ("estado", "Estado"),
)


def _exportar(nombre_archivo, columnas, registros, descripcion):
    """Genera la descarga CSV (respetando la búsqueda activa) y la audita."""
    consulta = (request.args.get("q") or "").strip()
    registros = filtrar_texto(registros, consulta)
    registrar_accion(
        "EXPORTAR", "listado", None,
        descripcion + (f' (filtro: «{consulta}»)' if consulta else ""),
    )
    return exportar_csv(
        nombre_archivo,
        [etiqueta for _, etiqueta in columnas],
        [tuple(registro.get(clave) for clave, _ in columnas) for registro in registros],
    )


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
    listado = preparar_listado(
        PrestatarioService.list_all(),
        columnas_ordenables=tuple(clave for clave, _ in COLUMNAS_PRESTATARIO),
    )
    return render_template(
        "prestatarios/index.html", listado=listado, columnas=COLUMNAS_PRESTATARIO
    )


@web_bp.get("/prestatarios/exportar")
@permission_required("prestatarios.read")
def prestatarios_exportar():
    return _exportar(
        "techloan-prestatarios", COLUMNAS_PRESTATARIO,
        PrestatarioService.list_all(), "Exportación del listado de prestatarios",
    )


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
            nuevo_id = PrestatarioService.create(data)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "prestatarios/form.html", modo="crear", registro=data,
                tipos=TIPOS_PRESTATARIO, estados=ESTADOS_BASICOS,
            ), 400
        registrar_accion("CREAR", "prestatario", nuevo_id,
                         f"Alta del prestatario {data['cedula']} ({data['nombre']} {data['apellido']})")
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
        registrar_accion("ACTUALIZAR", "prestatario", id_,
                         f"Modificación del prestatario {data['cedula']} ({data['nombre']} {data['apellido']})")
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
    registro = PrestatarioService.get(id_)
    try:
        PrestatarioService.delete(id_)
        if registro:
            registrar_accion("ELIMINAR", "prestatario", id_,
                             f"Baja del prestatario {registro['cedula']} "
                             f"({registro['nombre']} {registro['apellido']})")
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
    listado = preparar_listado(
        CategoriaService.list_all(),
        columnas_ordenables=tuple(clave for clave, _ in COLUMNAS_CATEGORIA),
    )
    return render_template(
        "categorias/index.html", listado=listado, columnas=COLUMNAS_CATEGORIA
    )


@web_bp.get("/categorias/exportar")
@permission_required("categorias.read")
def categorias_exportar():
    return _exportar(
        "techloan-categorias", COLUMNAS_CATEGORIA,
        CategoriaService.list_all(), "Exportación del listado de categorías",
    )


@web_bp.route("/categorias/crear", methods=["GET", "POST"])
@permission_required("categorias.write")
def categoria_crear():
    if request.method == "POST":
        data = form_fields("nombre", "descripcion", empty_to_none=("descripcion",))
        try:
            nuevo_id = CategoriaService.create(data)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("categorias/form.html", modo="crear", registro=data), 400
        registrar_accion("CREAR", "categoria", nuevo_id, f"Alta de la categoría «{data['nombre']}»")
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
        registrar_accion("ACTUALIZAR", "categoria", id_, f"Modificación de la categoría «{data['nombre']}»")
        flash("Categoría actualizada correctamente.", "success")
        return redirect(url_for("web.categorias"))

    return render_template("categorias/form.html", modo="editar", registro=registro)


@web_bp.post("/categorias/<int:id_>/eliminar")
@permission_required("categorias.delete")
def categoria_eliminar(id_):
    registro = CategoriaService.get(id_)
    try:
        CategoriaService.delete(id_)
        if registro:
            registrar_accion("ELIMINAR", "categoria", id_, f"Baja de la categoría «{registro['nombre']}»")
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
    listado = preparar_listado(
        LaboratorioService.list_all(),
        columnas_ordenables=tuple(clave for clave, _ in COLUMNAS_LABORATORIO),
    )
    return render_template(
        "laboratorios/index.html", listado=listado, columnas=COLUMNAS_LABORATORIO
    )


@web_bp.get("/laboratorios/exportar")
@permission_required("laboratorios.read")
def laboratorios_exportar():
    return _exportar(
        "techloan-laboratorios", COLUMNAS_LABORATORIO,
        LaboratorioService.list_all(), "Exportación del listado de laboratorios",
    )


@web_bp.route("/laboratorios/crear", methods=["GET", "POST"])
@permission_required("laboratorios.write")
def laboratorio_crear():
    if request.method == "POST":
        data = form_fields(
            "codigo", "nombre", "ubicacion", "capacidad",
            "duracion_estandar_minutos", "estado",
        )
        try:
            nuevo_id = LaboratorioService.create(data)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "laboratorios/form.html", modo="crear", registro=data,
                estados=ESTADOS_LABORATORIO,
            ), 400
        registrar_accion("CREAR", "laboratorio", nuevo_id,
                         f"Alta del laboratorio {data['codigo']} ({data['nombre']})")
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
        registrar_accion("ACTUALIZAR", "laboratorio", id_,
                         f"Modificación del laboratorio {data['codigo']} ({data['nombre']})")
        flash("Laboratorio actualizado correctamente.", "success")
        return redirect(url_for("web.laboratorios"))

    return render_template(
        "laboratorios/form.html", modo="editar", registro=registro,
        estados=ESTADOS_LABORATORIO,
    )


@web_bp.post("/laboratorios/<int:id_>/eliminar")
@permission_required("laboratorios.delete")
def laboratorio_eliminar(id_):
    registro = LaboratorioService.get(id_)
    try:
        LaboratorioService.delete(id_)
        if registro:
            registrar_accion("ELIMINAR", "laboratorio", id_,
                             f"Baja del laboratorio {registro['codigo']} ({registro['nombre']})")
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
    listado = preparar_listado(
        EquipoService.list_all(),
        columnas_ordenables=tuple(clave for clave, _ in COLUMNAS_EQUIPO),
    )
    return render_template("equipos/index.html", listado=listado, columnas=COLUMNAS_EQUIPO)


@web_bp.get("/equipos/exportar")
@permission_required("equipos.read")
def equipos_exportar():
    return _exportar(
        "techloan-equipos", COLUMNAS_EQUIPO,
        EquipoService.list_all(), "Exportación del listado de equipos",
    )


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
            nuevo_id = EquipoService.create(data)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template(
                "equipos/form.html", modo="crear", registro=data,
                categorias=_etiquetar_categorias(),
                laboratorios=_etiquetar_laboratorios(),
                estados=ESTADOS_EQUIPO,
            ), 400
        registrar_accion("CREAR", "equipo", nuevo_id,
                         f"Alta del equipo {data['codigo']} ({data['nombre']})")
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
        registrar_accion("ACTUALIZAR", "equipo", id_,
                         f"Modificación del equipo {data['codigo']} ({data['nombre']})")
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
    registro = EquipoService.get(id_)
    try:
        EquipoService.delete(id_)
        if registro:
            registrar_accion("ELIMINAR", "equipo", id_,
                             f"Baja del equipo {registro['codigo']} ({registro['nombre']})")
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
    listado = preparar_listado(
        UsuarioService.list_all(),
        columnas_ordenables=tuple(clave for clave, _ in COLUMNAS_USUARIO),
    )
    return render_template("usuarios/index.html", listado=listado, columnas=COLUMNAS_USUARIO)


@web_bp.get("/usuarios/exportar")
@permission_required("usuarios.read")
def usuarios_exportar():
    return _exportar(
        "techloan-usuarios", COLUMNAS_USUARIO,
        UsuarioService.list_all(), "Exportación del listado de usuarios del sistema",
    )


@web_bp.route("/usuarios/crear", methods=["GET", "POST"])
@permission_required("usuarios.write")
def usuario_crear():
    if request.method == "POST":
        data = form_fields("nombre", "apellido", "username", "email", "password", "rol", "estado")
        try:
            nuevo_id = UsuarioService.create(data)
        except ValueError as exc:
            flash(str(exc), "error")
            data.pop("password", None)  # nunca se reimprime la contraseña
            return render_template(
                "usuarios/form.html", modo="crear", registro=data,
                roles=ROLES, estados=ESTADOS_BASICOS,
            ), 400
        registrar_accion("CREAR", "usuario", nuevo_id,
                         f"Alta del usuario «{data['username']}» con rol {data['rol']}")
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
        detalle = f"Modificación del usuario «{data['username']}» (rol {data['rol']})"
        if data.get("password"):
            detalle += " y cambio de contraseña"
        registrar_accion("ACTUALIZAR", "usuario", id_, detalle)
        flash("Usuario actualizado correctamente.", "success")
        return redirect(url_for("web.usuarios"))

    return render_template(
        "usuarios/form.html", modo="editar", registro=registro,
        roles=ROLES, estados=ESTADOS_BASICOS,
    )


@web_bp.post("/usuarios/<int:id_>/eliminar")
@permission_required("usuarios.delete")
def usuario_eliminar(id_):
    registro = UsuarioService.get(id_)
    try:
        UsuarioService.delete(id_)
        if registro:
            registrar_accion("ELIMINAR", "usuario", id_,
                             f"Baja del usuario «{registro['username']}» (rol {registro['rol']})")
        flash("Usuario eliminado correctamente.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("web.usuarios"))
