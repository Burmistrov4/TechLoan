"""Rutas web complementarias: perfil, guía de uso y auditoría.

- ``/perfil``    → datos de la propia cuenta y cambio de contraseña.
- ``/ayuda``     → guía de uso dentro de la aplicación.
- ``/auditoria`` → registro de actividad (solo ADMINISTRADOR).
"""

from flask import flash, redirect, render_template, request, url_for

from app.routes.web_common import (
    exportar_csv,
    form_fields,
    login_required,
    permission_required,
    preparar_listado,
    registrar_accion,
    web_bp,
)
from app.security.permissions import current_user
from app.services.auditoria_service import (
    ACCIONES,
    ETIQUETAS_ACCION,
    ETIQUETAS_ENTIDAD,
    AuditoriaService,
)
from app.services.usuario_service import UsuarioService


# ===========================================================================
# Perfil de la propia cuenta
# ===========================================================================
@web_bp.route("/perfil", methods=["GET", "POST"])
def perfil():
    """Muestra los datos de la cuenta y permite cambiar la contraseña."""
    usuario = current_user()
    if not usuario:
        flash("Debes iniciar sesión para ver tu perfil.", "error")
        return redirect(url_for("web.login"))

    if request.method == "POST":
        datos = form_fields("password_actual", "password_nueva", "password_repetida")
        try:
            UsuarioService.cambiar_password(
                usuario["id"],
                datos["password_actual"],
                datos["password_nueva"],
                datos["password_repetida"],
            )
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("perfil.html", usuario=usuario), 400

        registrar_accion("ACTUALIZAR", "usuario", usuario["id"],
                         f"Cambio de contraseña de «{usuario['username']}»")
        flash("Contraseña actualizada correctamente.", "success")
        return redirect(url_for("web.perfil"))

    return render_template("perfil.html", usuario=usuario)


# ===========================================================================
# Guía de uso dentro de la aplicación
# ===========================================================================
@web_bp.get("/ayuda")
@login_required
def ayuda():
    """Manual de uso resumido, accesible desde cualquier punto de la app.

    Vive dentro del shell autenticado (``base_app.html``), que necesita los datos
    del usuario en sesión para pintar la cabecera y el avatar. Sin sesión, la
    página no puede renderizarse: se redirige al acceso en lugar de fallar.
    """
    return render_template("ayuda.html", usuario=current_user())


# ===========================================================================
# Auditoría
# ===========================================================================
@web_bp.get("/auditoria")
@permission_required("auditoria.read")
def auditoria():
    """Registro de actividad del sistema con filtros."""
    filtros = {
        "accion": (request.args.get("accion") or "").upper(),
        "entidad": (request.args.get("entidad") or "").lower(),
        "usuario": (request.args.get("usuario") or "").strip(),
        "fecha_desde": (request.args.get("fecha_desde") or "").strip(),
        "fecha_hasta": (request.args.get("fecha_hasta") or "").strip(),
    }

    registros = AuditoriaService.listar(**filtros, limite=500)
    listado = preparar_listado(registros, columnas_ordenables=("fecha", "accion", "entidad", "usuario_username"))

    return render_template(
        "auditoria/index.html",
        listado=listado,
        filtros=filtros,
        acciones=ACCIONES,
        entidades=sorted(ETIQUETAS_ENTIDAD),
        etiquetas_accion=ETIQUETAS_ACCION,
        etiquetas_entidad=ETIQUETAS_ENTIDAD,
    )


@web_bp.get("/auditoria/exportar")
@permission_required("auditoria.read")
def auditoria_exportar():
    """Exporta el registro de actividad a CSV."""
    registros = AuditoriaService.listar(
        accion=(request.args.get("accion") or "").upper(),
        entidad=(request.args.get("entidad") or "").lower(),
        usuario=(request.args.get("usuario") or "").strip(),
        fecha_desde=(request.args.get("fecha_desde") or "").strip(),
        fecha_hasta=(request.args.get("fecha_hasta") or "").strip(),
        limite=5000,
    )
    registrar_accion("EXPORTAR", "listado", None, "Exportación del registro de auditoría")
    return exportar_csv(
        "techloan-auditoria",
        ["Fecha", "Usuario", "Acción", "Entidad", "ID", "Descripción", "IP"],
        [
            (r["fecha"], r["usuario_username"], ETIQUETAS_ACCION.get(r["accion"], r["accion"]),
             ETIQUETAS_ENTIDAD.get(r["entidad"], r["entidad"]), r["entidad_id"],
             r["descripcion"], r["direccion_ip"])
            for r in registros
        ],
    )
