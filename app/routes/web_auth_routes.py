"""Rutas web de acceso, panel de inicio y búsqueda global.

- ``GET  /``              → portada pública (visitantes) o panel (sesión iniciada).
- ``GET  /panel``         → panel de inicio con indicadores y gráficos.
- ``GET  /login``         → formulario de acceso.
- ``POST /login``         → valida credenciales y abre la sesión Flask.
- ``POST /logout``        → cierra la sesión.
- ``GET  /buscar``        → búsqueda global en JSON (la usa la paleta de comandos).
- ``GET  /manifest.json`` → manifiesto de aplicación web instalable.

La portada se sirve en la raíz para que el sistema se presente ante un visitante
y, al mismo tiempo, ``/`` sigue siendo la vista principal cuando hay sesión
iniciada, tal como pide el enunciado del proyecto.
"""

from flask import (
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.config import DIAS_PRESTAMO_LIMITE, UMBRAL_SATURACION
from app.routes.web_common import (
    alertas_actuales,
    can,
    form_fields,
    login_required,
    registrar_accion,
    safe_redirect_target,
    web_bp,
)
from app.services import correo_service
from app.services.auth_service import AuthService
from app.services.dashboard_service import DashboardService
from app.services.equipo_service import EquipoService
from app.services.laboratorio_service import LaboratorioService
from app.services.prestatario_service import PrestatarioService
from app.services.registro_service import RegistroService
from app.services.reservation_service import ReservationService


# ---------------------------------------------------------------------------
# Portada pública y panel
# ---------------------------------------------------------------------------
def _contexto_panel():
    """Datos que alimentan el panel de inicio."""
    return {
        "stats": DashboardService.stats(),
        "tendencias": DashboardService.tendencias(),
        "reservas_proximas": DashboardService.reservas_proximas(),
        "prestamos_activos": DashboardService.prestamos_activos(),
        "actividad": DashboardService.actividad_reciente(),
        "vencidos": DashboardService.prestamos_vencidos_detalle(),
        "graficos": DashboardService.datos_graficos(),
        "alertas": alertas_actuales(),
    }


@web_bp.get("/")
def portada():
    """Portada pública; si ya hay sesión iniciada, muestra el panel."""
    from app.security.permissions import current_user

    if current_user():
        return render_template("index.html", **_contexto_panel())
    return render_template(
        "landing.html",
        dias_limite=DIAS_PRESTAMO_LIMITE,
        umbral_saturacion=UMBRAL_SATURACION,
        metricas=DashboardService.estadisticas_publicas(),
    )


@web_bp.get("/panel")
@login_required
def dashboard():
    """Panel principal con indicadores, gráficos y actividad reciente."""
    return render_template("index.html", **_contexto_panel())


# ---------------------------------------------------------------------------
# Acceso
# ---------------------------------------------------------------------------
@web_bp.get("/login")
def login():
    """Muestra el formulario de acceso."""
    if session.get("user"):
        return redirect(url_for("web.portada"))
    return render_template(
        "auth/login.html",
        siguiente=safe_redirect_target(request.args.get("next")) or "",
    )


@web_bp.post("/login")
def login_post():
    """Procesa el formulario de acceso."""
    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    destino = safe_redirect_target(request.form.get("next"))

    try:
        user = AuthService.authenticate(username, password)
    except ValueError as exc:
        # Mensaje genérico: no se revela si el usuario existe o no.
        registrar_accion("ACCEDER", "sesion", None, f"Intento de acceso fallido para «{username}»")
        flash(str(exc), "error")
        return (
            render_template(
                "auth/login.html", usuario_intentado=username, siguiente=destino or ""
            ),
            401,
        )

    session.clear()
    session["user"] = user
    registrar_accion("ACCEDER", "sesion", user.get("id"), f"Acceso correcto de «{user['username']}»")
    flash(f"Bienvenido, {user['nombre']}. Sesión iniciada correctamente.", "success")
    # Se vuelve a la raíz: con sesión iniciada, "/" es la vista principal del
    # sistema, tal como pide el enunciado del proyecto.
    return redirect(destino or url_for("web.portada"))


@web_bp.post("/logout")
def logout():
    """Cierra la sesión actual."""
    usuario = session.get("user") or {}
    registrar_accion(
        "SALIR", "sesion", usuario.get("id"), f"Cierre de sesión de «{usuario.get('username', '')}»"
    )
    session.clear()
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("web.login"))


# ---------------------------------------------------------------------------
# Registro de usuarios con confirmación por correo
# ---------------------------------------------------------------------------
@web_bp.get("/registro")
def registro():
    """Formulario de alta para quien todavía no tiene cuenta."""
    if session.get("user"):
        return redirect(url_for("web.portada"))
    return render_template(
        "auth/registro.html", datos={}, modo_correo=correo_service.modo()
    )


@web_bp.post("/registro")
def registro_post():
    """Crea la cuenta con el correo sin confirmar y manda el enlace."""
    datos = form_fields(
        "nombre", "apellido", "username", "email", "password", "password_repetida",
        # Las contraseñas no se recortan: un espacio podría ser parte de la clave.
        no_recortar=("password", "password_repetida"),
    )

    try:
        resultado = RegistroService.registrar(datos)
    except ValueError as exc:
        registrar_accion(
            "CREAR", "usuario", None,
            f"Registro rechazado para «{datos.get('username', '')}»",
        )
        flash(str(exc), "error")
        return (
            render_template(
                "auth/registro.html", datos=datos, modo_correo=correo_service.modo()
            ),
            400,
        )

    registrar_accion(
        "CREAR", "usuario", resultado["usuario_id"],
        f"Registro autoservicio de «{resultado['username']}» (pendiente de confirmar)",
    )
    return render_template("auth/revisar_correo.html", resultado=resultado)


@web_bp.get("/confirmar/<token>")
@web_bp.get("/c/<token>")
def confirmar(token):
    """Activa la cuenta a la que pertenece el enlace del correo.

    Hay dos rutas a propósito. La corta (``/c/<token>``) es la que se manda por
    correo: con ella el enlace mide 69 caracteres y cabe en una sola línea, así
    que la codificación quoted-printable del correo no lo parte. La larga
    (``/confirmar/<token>``) se conserva para que sigan funcionando los enlaces
    que se enviaron antes de existir la corta.
    """
    try:
        resultado = RegistroService.confirmar(token)
    except ValueError as exc:
        # Se deja rastro del intento fallido con el token recibido. Sin esto,
        # "no se pudo confirmar" no se puede depurar: no hay forma de saber si el
        # enlace llegó truncado, si el token caducó o si nunca existió.
        registrar_accion(
            "ACCEDER", "confirmacion", None,
            f"Confirmación rechazada para el enlace «{token[:12]}…»: {exc}",
        )
        return (
            render_template(
                "auth/confirmar.html",
                ok=False,
                mensaje=str(exc),
                token_recibido=token,
            ),
            400,
        )

    if not resultado["ya_confirmada"]:
        registrar_accion(
            "ACTUALIZAR", "usuario", None,
            f"Correo confirmado de «{resultado['username']}»",
        )

    return render_template(
        "auth/confirmar.html",
        ok=True,
        ya_confirmada=resultado["ya_confirmada"],
        username=resultado["username"],
    )


@web_bp.route("/reenviar", methods=["GET", "POST"])
def reenviar():
    """Pide un enlace de confirmación nuevo (el anterior caducó o se perdió)."""
    if request.method == "GET":
        return render_template("auth/reenviar.html", email="")

    email = (request.form.get("email") or "").strip()
    try:
        resultado = RegistroService.reenviar(email)
    except ValueError as exc:
        flash(str(exc), "error")
        return render_template("auth/reenviar.html", email=email), 400

    return render_template("auth/revisar_correo.html", resultado=resultado)


# ---------------------------------------------------------------------------
# Búsqueda global (paleta de comandos)
# ---------------------------------------------------------------------------
@web_bp.get("/buscar")
@login_required
def buscar():
    """Búsqueda global en JSON: secciones, acciones y registros del dominio.

    Alimenta la paleta de comandos (Ctrl+K). Respeta los permisos del rol: solo
    devuelve registros de los módulos a los que el usuario puede acceder.
    """
    consulta = (request.args.get("q") or "").strip()
    aguja = consulta.lower()

    def coincide(*valores):
        if not aguja:
            return False
        return any(aguja in str(valor or "").lower() for valor in valores)

    grupos = []

    # --- Secciones y acciones ---
    secciones = [
        ("Inicio", "Panel con indicadores y actividad", url_for("web.dashboard"), "inicio", "dashboard"),
        ("Reservas", "Agenda de laboratorios", url_for("web.reservas"), "reservas", "reservas.read"),
        ("Nueva reserva", "Registrar una reserva de laboratorio", url_for("web.reserva_crear"), "mas", "reservas.write"),
        ("Préstamos", "Equipos prestados y devoluciones", url_for("web.prestamos"), "prestamos", "prestamos.read"),
        ("Nuevo préstamo", "Registrar la salida de un equipo", url_for("web.prestamo_crear"), "mas", "prestamos.write"),
        ("Historial", "Reservas, préstamos y devoluciones", url_for("web.historial"), "historial", "historial.read"),
        ("Prestatarios", "Personas que reciben recursos", url_for("web.prestatarios"), "prestatarios", "prestatarios.read"),
        ("Nuevo prestatario", "Dar de alta a un prestatario", url_for("web.prestatario_crear"), "mas", "prestatarios.write"),
        ("Equipos", "Inventario de recursos prestables", url_for("web.equipos"), "equipos", "equipos.read"),
        ("Laboratorios", "Espacios reservables", url_for("web.laboratorios"), "laboratorios", "laboratorios.read"),
        ("Categorías", "Clasificación de equipos", url_for("web.categorias"), "categorias", "categorias.read"),
        ("Usuarios", "Cuentas con acceso al sistema", url_for("web.usuarios"), "usuarios", "usuarios.read"),
        ("Auditoría", "Registro de actividad del sistema", url_for("web.auditoria"), "auditoria", "auditoria.read"),
        ("Guía de uso", "Cómo usar TechLoan paso a paso", url_for("web.ayuda"), "libro", None),
        ("Mi perfil", "Datos de tu cuenta y contraseña", url_for("web.perfil"), "perfil", None),
        ("Cambiar tema", "Alternar entre claro y oscuro", "#tema", "luna", None),
    ]
    encontrados = [
        {"titulo": titulo, "subtitulo": subtitulo, "url": url, "icono": icono}
        for titulo, subtitulo, url, icono, permiso in secciones
        if (permiso is None or can(permiso)) and (not aguja or coincide(titulo, subtitulo))
    ]
    if encontrados:
        grupos.append({"titulo": "Secciones y acciones", "items": encontrados[:6]})

    # --- Registros del dominio ---
    if aguja:
        if can("prestatarios.read"):
            items = [
                {
                    "titulo": f"{p['nombre']} {p['apellido']}",
                    "subtitulo": f"{p['cedula']} · {p['tipo'].capitalize()}",
                    "url": url_for("web.prestatario_editar", id_=p["id"]),
                    "icono": "prestatarios",
                }
                for p in PrestatarioService.list_all()
                if coincide(p["nombre"], p["apellido"], p["cedula"], p.get("email"))
            ][:5]
            if items:
                grupos.append({"titulo": "Prestatarios", "items": items})

        if can("equipos.read"):
            items = [
                {
                    "titulo": f"{e['codigo']} · {e['nombre']}",
                    "subtitulo": e["estado"].capitalize()
                    + (f" · {e['categoria_nombre']}" if e.get("categoria_nombre") else ""),
                    "url": url_for("web.equipo_editar", id_=e["id"]),
                    "icono": "equipos",
                }
                for e in EquipoService.list_all()
                if coincide(e["codigo"], e["nombre"], e.get("serial"), e.get("marca"))
            ][:5]
            if items:
                grupos.append({"titulo": "Equipos", "items": items})

        if can("laboratorios.read"):
            items = [
                {
                    "titulo": f"{lab['codigo']} · {lab['nombre']}",
                    "subtitulo": f"{lab['ubicacion']} · {lab['capacidad']} personas",
                    "url": url_for("web.laboratorio_editar", id_=lab["id"]),
                    "icono": "laboratorios",
                }
                for lab in LaboratorioService.list_all()
                if coincide(lab["codigo"], lab["nombre"], lab["ubicacion"])
            ][:5]
            if items:
                grupos.append({"titulo": "Laboratorios", "items": items})

        if can("reservas.read"):
            items = [
                {
                    "titulo": f"{r['laboratorio_codigo']} · {r['fecha']} {r['hora_inicio']}",
                    "subtitulo": f"{r['prestatario_nombre']} {r['prestatario_apellido']} · "
                                 f"{r['estado'].capitalize()}",
                    "url": url_for("web.reserva_comprobante", id_=r["id"]),
                    "icono": "reservas",
                }
                for r in ReservationService.list_all()
                if coincide(r["fecha"], r["hora_inicio"], r["laboratorio_codigo"],
                            r["prestatario_nombre"], r["prestatario_apellido"], r["observaciones"])
            ][:5]
            if items:
                grupos.append({"titulo": "Reservas", "items": items})

    return jsonify({"ok": True, "grupos": grupos, "consulta": consulta})


# ---------------------------------------------------------------------------
# Manifiesto de aplicación web
# ---------------------------------------------------------------------------
@web_bp.get("/manifest.json")
def manifest():
    """Manifiesto que permite instalar TechLoan como aplicación de escritorio."""
    datos = {
        "name": "TechLoan — Gestión de recursos tecnológicos",
        "short_name": "TechLoan",
        "description": "Reservas de laboratorios y préstamos de equipos con control de "
                       "disponibilidad, roles y auditoría.",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#060a13",
        "theme_color": "#0b1120",
        "lang": "es",
        "icons": [
            {"src": url_for("static", filename="img/icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": url_for("static", filename="img/icon-512.png"), "sizes": "512x512", "type": "image/png"},
            {"src": url_for("static", filename="img/icon-512.png"), "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ],
    }
    respuesta = make_response(jsonify(datos))
    respuesta.headers["Content-Type"] = "application/manifest+json"
    return respuesta
