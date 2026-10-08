"""Utilidades compartidas por las rutas web (HTML/Jinja2) de TechLoan.

Aquí vive el blueprint ``web_bp``, los decoradores de sesión/permisos y la
protección CSRF. Las rutas concretas se definen en:

- ``web_auth_routes.py``        → inicio de sesión, cierre de sesión, panel.
- ``web_crud_routes.py``        → CRUD de las entidades del dominio.
- ``web_operations_routes.py``  → reservas, préstamos, devoluciones e historial.

Todas las rutas web reutilizan los servicios POO existentes; ninguna escribe SQL
directamente.
"""

import csv
import io
import math
import secrets
from functools import wraps

from flask import (
    Blueprint,
    Response,
    abort,
    flash,
    g,
    redirect,
    request,
    session,
    url_for,
)

from app.config import FILAS_POR_PAGINA
from app.security.permissions import current_user
from app.services.auth_service import AuthService
from app.services.auditoria_service import AuditoriaService

# Blueprint sin prefijo: el PDF pide rutas limpias en la raíz ("/", "/crear").
web_bp = Blueprint("web", __name__)


# ---------------------------------------------------------------------------
# Protección CSRF
# ---------------------------------------------------------------------------
def csrf_token():
    """Devuelve (creando si hace falta) el token CSRF de la sesión actual.

    Se expone a las plantillas mediante un context processor, de modo que todos
    los formularios puedan incluirlo como campo oculto.
    """
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


@web_bp.before_request
def _verify_csrf():
    """Rechaza cualquier POST web sin un token CSRF válido.

    La API JSON (``/api/...``) vive en otros blueprints y no se ve afectada.
    """
    if request.method != "POST":
        return None

    enviado = request.form.get("_csrf_token", "")
    esperado = session.get("_csrf_token", "")
    if not esperado or not enviado or not secrets.compare_digest(enviado, esperado):
        abort(400, description="Token de seguridad inválido o expirado. Recargue la página e inténtelo de nuevo.")
    return None


# ---------------------------------------------------------------------------
# Decoradores de sesión y permisos
# ---------------------------------------------------------------------------
def login_required(view):
    """Exige una sesión activa; si no la hay, redirige al formulario de acceso."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Debes iniciar sesión para acceder a esa página.", "error")
            return redirect(url_for("web.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def permission_required(permission, redirect_endpoint="web.dashboard"):
    """Exige que el usuario de la sesión tenga el permiso indicado.

    El rol se revalida contra la base de datos en cada petición (ver
    ``app.security.permissions.current_user``), por lo que un usuario degradado
    o desactivado pierde el acceso de inmediato.
    """

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                flash("Debes iniciar sesión para continuar.", "error")
                return redirect(url_for("web.login"))
            if not AuthService.can(user, permission):
                flash("Tu rol no tiene permisos para realizar esa acción.", "error")
                return redirect(url_for(redirect_endpoint))
            return view(*args, **kwargs)

        return wrapped

    return decorator


def can(permission):
    """Atajo para las plantillas: ¿el usuario actual tiene este permiso?"""
    return AuthService.can(current_user(), permission)


# ---------------------------------------------------------------------------
# Lectura de formularios
# ---------------------------------------------------------------------------
def form_fields(*names, empty_to_none=()):
    """Extrae del formulario los campos indicados, ya recortados.

    Siempre devuelve cadenas (nunca ``None``) para que las validaciones de los
    servicios no fallen con ``AttributeError``. Los campos listados en
    ``empty_to_none`` se convierten a ``None`` cuando llegan vacíos, que es lo
    que esperan las columnas opcionales de la base de datos.
    """
    data = {name: (request.form.get(name) or "").strip() for name in names}
    for name in empty_to_none:
        if data.get(name) == "":
            data[name] = None
    return data


def parse_int(value, default=None):
    """Convierte a entero de forma segura; devuelve ``default`` si no es válido."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def safe_redirect_target(target):
    """Evita redirecciones abiertas: solo acepta rutas internas relativas."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return None
    return target


# ---------------------------------------------------------------------------
# Alertas (avisos operativos) y auditoría
# ---------------------------------------------------------------------------
def alertas_actuales():
    """Resumen de alertas del usuario en sesión, memorizado por petición.

    Se expone a todas las plantillas para alimentar la campana de la barra
    superior y los contadores de la barra lateral.
    """
    from app.services.alertas_service import AlertasService

    if not current_user():
        return AlertasService.resumen_vacio()

    if not hasattr(g, "_techloan_alertas"):
        g._techloan_alertas = AlertasService.resumen()
    return g._techloan_alertas


def registrar_accion(accion, entidad, entidad_id=None, descripcion=""):
    """Anota una acción en el registro de auditoría con el usuario de la sesión.

    Nunca interrumpe el flujo: si la auditoría falla, la operación ya se realizó
    y el usuario no debe ver un error por ello.
    """
    AuditoriaService.registrar(
        usuario=current_user(),
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        descripcion=descripcion,
        direccion_ip=request.remote_addr,
    )


# ---------------------------------------------------------------------------
# Listados: búsqueda, orden y paginación
# ---------------------------------------------------------------------------
def _texto_de(registro):
    """Concatena los valores de texto de un registro para la búsqueda libre."""
    partes = []
    for valor in registro.values():
        if valor is None or isinstance(valor, (dict, list, tuple)):
            continue
        partes.append(str(valor))
    return " ".join(partes).lower()


def filtrar_texto(registros, consulta):
    """Filtra registros por texto libre en cualquiera de sus campos visibles."""
    consulta = (consulta or "").strip().lower()
    if not consulta:
        return registros
    return [registro for registro in registros if consulta in _texto_de(registro)]


def _clave_orden(valor):
    """Clave de ordenación tolerante a tipos mezclados.

    Devuelve una tupla ``(grupo, valor)``: los números van primero y ordenan
    numéricamente; el resto ordena alfabéticamente y sin distinguir mayúsculas.
    """
    if valor is None:
        return (2, "")
    if isinstance(valor, bool):
        return (0, int(valor))
    if isinstance(valor, (int, float)):
        return (0, valor)
    texto = str(valor).strip()
    try:
        return (0, float(texto.replace(",", ".")))
    except ValueError:
        return (1, texto.lower())


def preparar_listado(registros, columnas_ordenables=(), por_pagina_por_defecto=FILAS_POR_PAGINA):
    """Aplica búsqueda libre, ordenación y paginación a una lista de registros.

    Los parámetros llegan por la query string, de modo que cada estado del
    listado es un enlace compartible y sobrevive a una recarga:

    - ``q``          texto libre (busca en todos los campos visibles)
    - ``orden``      clave por la que ordenar
    - ``dir``        ``asc`` o ``desc``
    - ``pagina``      número de página (1-based)
    - ``por_pagina`` tamaño de página

    Devuelve un diccionario listo para la plantilla.
    """
    consulta = (request.args.get("q") or "").strip()
    orden = (request.args.get("orden") or "").strip()
    direccion = "desc" if (request.args.get("dir") or "asc").lower() == "desc" else "asc"
    pagina = max(1, parse_int(request.args.get("pagina"), 1) or 1)
    por_pagina = parse_int(request.args.get("por_pagina"), por_pagina_por_defecto)
    por_pagina = min(max(por_pagina or por_pagina_por_defecto, 5), 100)

    total_sin_filtrar = len(registros)

    registros = filtrar_texto(registros, consulta)

    if orden and orden in columnas_ordenables:
        registros = sorted(
            registros, key=lambda r: _clave_orden(r.get(orden)), reverse=(direccion == "desc")
        )

    total = len(registros)
    paginas = max(1, math.ceil(total / por_pagina))
    pagina = min(pagina, paginas)
    inicio = (pagina - 1) * por_pagina

    return {
        "filas": registros[inicio:inicio + por_pagina],
        "total": total,
        "total_sin_filtrar": total_sin_filtrar,
        "pagina": pagina,
        "paginas": paginas,
        "por_pagina": por_pagina,
        "desde": inicio + 1 if total else 0,
        "hasta": min(inicio + por_pagina, total),
        "q": consulta,
        "orden": orden,
        "dir": direccion,
        "hay_filtro": bool(consulta),
    }


def exportar_csv(nombre, encabezados, filas):
    """Devuelve una respuesta CSV descargable.

    Se usa punto y coma como separador y se antepone la marca de orden de bytes
    (BOM) para que Excel en español abra el archivo con las columnas y los
    acentos correctos sin pedir configuración adicional.
    """
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    escritor.writerow(encabezados)
    for fila in filas:
        escritor.writerow(["" if valor is None else valor for valor in fila])

    contenido = "\ufeff" + buffer.getvalue()
    return Response(
        contenido,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}.csv"'},
    )


def url_con(**cambios):
    """Construye una URL del endpoint actual cambiando solo algunos parámetros.

    Permite que los enlaces de ordenación y paginación conserven la búsqueda y
    el tamaño de página en lugar de reiniciarlos en cada clic.
    """
    parametros = request.args.to_dict()
    parametros.update(cambios)
    parametros = {clave: valor for clave, valor in parametros.items()
                  if valor not in (None, "", "None")}
    return url_for(request.endpoint, **parametros)
