"""Pruebas de integración de la capa web (HTML/Jinja2) de TechLoan.

Cubre el ciclo CRUD completo por HTTP, la autenticación, la protección CSRF,
los permisos por rol, las reglas de negocio (solapamientos, préstamos y
devoluciones), el historial y la ausencia de errores 500.

Las pruebas se ejecutan contra una **base de datos temporal** construida desde
``schema.sql``, de modo que nunca se altera ``database/techloan.db``.

Uso::

    PYTHONPATH=. python tests/test_web_phase6.py
"""

import re
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import app.database as database  # noqa: E402

# --- Base de datos temporal aislada -----------------------------------------
_TMP_DIR = tempfile.mkdtemp(prefix="techloan_web_test_")
database.DATABASE_PATH = Path(_TMP_DIR) / "test_web.db"

from init_db import init_database as cargar_esquema  # noqa: E402
from app.server import create_app  # noqa: E402

cargar_esquema(database.DATABASE_PATH)
app = create_app()

ESTADOS_VISTOS = []


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _registrar(respuesta):
    ESTADOS_VISTOS.append(respuesta.status_code)
    return respuesta


def token_csrf(cliente, ruta="/login"):
    """Obtiene un token CSRF válido visitando una página del formulario."""
    respuesta = _registrar(cliente.get(ruta))
    coincidencia = re.search(
        r'name="_csrf_token" value="([^"]+)"', respuesta.get_data(as_text=True)
    )
    assert coincidencia, f"No se encontró el token CSRF en {ruta}"
    return coincidencia.group(1)


def entrar(cliente, username="admin", password="Admin123!"):
    token = token_csrf(cliente, "/login")
    respuesta = _registrar(
        cliente.post(
            "/login",
            data={"_csrf_token": token, "username": username, "password": password},
        )
    )
    return respuesta


def publicar(cliente, ruta, datos, ruta_token=None, seguir=True):
    """Envía un POST incluyendo automáticamente un token CSRF válido."""
    datos = dict(datos)
    datos["_csrf_token"] = token_csrf(cliente, ruta_token or ruta)
    return _registrar(cliente.post(ruta, data=datos, follow_redirects=seguir))


def texto(respuesta):
    return respuesta.get_data(as_text=True)


def afirmar(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)


# ===========================================================================
# 1. Autenticación y protección de rutas
# ===========================================================================
def test_autenticacion():
    cliente = app.test_client()

    # La raíz es la portada pública para visitantes; los módulos internos
    # siguen exigiendo sesión.
    respuesta = _registrar(cliente.get("/"))
    afirmar(respuesta.status_code == 200, "GET / sin sesión debe mostrar la portada")
    afirmar("TechLoan" in texto(respuesta), "La portada debe identificar el producto")
    afirmar("/login" in texto(respuesta), "La portada debe ofrecer acceso")

    respuesta = _registrar(cliente.get("/prestatarios"))
    afirmar(respuesta.status_code == 302, "Un módulo interno sin sesión debe redirigir")
    afirmar("/login" in respuesta.headers.get("Location", ""), "Debe redirigir a /login")

    afirmar(_registrar(cliente.get("/login")).status_code == 200, "GET /login debe responder 200")

    token = token_csrf(cliente, "/login")
    respuesta = _registrar(
        cliente.post("/login", data={"_csrf_token": token, "username": "admin", "password": "incorrecta"})
    )
    afirmar(respuesta.status_code == 401, "Credenciales inválidas deben devolver 401")

    afirmar(entrar(cliente).status_code == 302, "Login correcto debe redirigir")
    afirmar(_registrar(cliente.get("/")).status_code == 200, "GET / con sesión debe responder 200")
    afirmar(_registrar(cliente.get("/panel")).status_code == 200, "GET /panel debe responder 200")

    token = token_csrf(cliente, "/")
    afirmar(
        _registrar(cliente.post("/logout", data={"_csrf_token": token})).status_code == 302,
        "Logout debe redirigir",
    )
    afirmar(
        _registrar(cliente.get("/panel")).status_code == 302,
        "Tras el logout la sesión debe quedar cerrada",
    )

    print("FASE6_AUTENTICACION_OK")


# ===========================================================================
# 1b. Portada pública, manifiesto y búsqueda global
# ===========================================================================
def test_portada_y_busqueda():
    cliente = app.test_client()

    portada = _registrar(cliente.get("/"))
    afirmar(portada.status_code == 200, "La portada debe responder 200")
    html = texto(portada)
    for marca in ("TechLoan", "hero-3d", "landing.css", "landing.js", "Iniciar sesión"):
        afirmar(marca in html, f"La portada debe incluir «{marca}»")

    manifiesto = _registrar(cliente.get("/manifest.json"))
    afirmar(manifiesto.status_code == 200, "El manifiesto debe servirse")
    datos = manifiesto.get_json()
    afirmar(datos["short_name"] == "TechLoan", "El manifiesto debe identificar la app")
    afirmar(len(datos["icons"]) >= 2, "El manifiesto debe declarar iconos")

    afirmar(_registrar(cliente.get("/static/favicon.svg")).status_code == 200,
            "El favicon SVG debe servirse")

    # La búsqueda global exige sesión y devuelve grupos de resultados.
    afirmar(_registrar(cliente.get("/buscar?q=lab")).status_code == 302,
            "La búsqueda global sin sesión debe redirigir")

    entrar(cliente)
    respuesta = _registrar(cliente.get("/buscar?q=lab"))
    afirmar(respuesta.status_code == 200, "La búsqueda global debe responder 200")
    datos = respuesta.get_json()
    afirmar(datos["ok"] is True, "La búsqueda debe devolver ok")
    afirmar(len(datos["grupos"]) > 0, "Debe encontrar al menos un grupo")
    titulos = [item["titulo"] for grupo in datos["grupos"] for item in grupo["items"]]
    afirmar(any("LAB" in t or "Laboratorio" in t for t in titulos),
            f"Debe encontrar laboratorios: {titulos}")

    # Sin texto devuelve el menú de secciones.
    respuesta = _registrar(cliente.get("/buscar?q="))
    afirmar(len(respuesta.get_json()["grupos"]) > 0, "Sin texto debe ofrecer las secciones")

    print("FASE6_PORTADA_Y_BUSQUEDA_OK")


# ===========================================================================
# 1c. Listados: búsqueda, orden, paginación y exportación CSV
# ===========================================================================
def test_listados_avanzados():
    cliente = app.test_client()
    entrar(cliente)

    # Búsqueda libre
    respuesta = _registrar(cliente.get("/prestatarios?q=González"))
    afirmar(respuesta.status_code == 200, "La búsqueda debe responder 200")
    html = texto(respuesta)
    afirmar("González" in html, "Debe aparecer el registro buscado")
    afirmar("Tarazón" not in html and "V-45678901" not in html,
            "No deben aparecer registros que no coinciden")

    # Búsqueda sin resultados: mensaje específico de filtro
    respuesta = _registrar(cliente.get("/prestatarios?q=zzzzzz"))
    afirmar("Sin resultados" in texto(respuesta), "Debe avisar de que el filtro no encontró nada")

    # Ordenación ascendente y descendente
    asc = texto(_registrar(cliente.get("/prestatarios?orden=cedula&dir=asc")))
    desc = texto(_registrar(cliente.get("/prestatarios?orden=cedula&dir=desc")))
    afirmar(asc.index("V-12345678") < asc.index("V-45678901"), "El orden ascendente debe respetarse")
    afirmar(desc.index("V-45678901") < desc.index("V-12345678"), "El orden descendente debe respetarse")

    # Paginación
    respuesta = _registrar(cliente.get("/prestatarios?por_pagina=5"))
    afirmar(respuesta.status_code == 200, "El tamaño de página debe aceptarse")

    # Exportación CSV
    csv = _registrar(cliente.get("/prestatarios/exportar"))
    afirmar(csv.status_code == 200, "La exportación debe responder 200")
    afirmar("text/csv" in csv.headers.get("Content-Type", ""), "Debe servirse como CSV")
    afirmar("attachment" in csv.headers.get("Content-Disposition", ""), "Debe descargarse")
    cuerpo = csv.get_data(as_text=True)
    afirmar("Cédula" in cuerpo and "V-12345678" in cuerpo, "El CSV debe contener cabecera y datos")
    afirmar(cuerpo.startswith("\ufeff"), "El CSV debe incluir BOM para Excel")

    # La exportación respeta el filtro activo
    csv_filtrado = _registrar(cliente.get("/prestatarios/exportar?q=González"))
    afirmar("González" in csv_filtrado.get_data(as_text=True), "La exportación debe respetar el filtro")
    afirmar("V-45678901" not in csv_filtrado.get_data(as_text=True),
            "La exportación filtrada no debe incluir otros registros")

    print("FASE6_LISTADOS_AVANZADOS_OK")


# ===========================================================================
# 2. Protección CSRF
# ===========================================================================
def test_csrf():
    cliente = app.test_client()
    entrar(cliente)

    respuesta = _registrar(cliente.post("/eliminar/1", data={}))
    afirmar(respuesta.status_code == 400, "Un POST sin token CSRF debe rechazarse con 400")

    respuesta = _registrar(
        cliente.post("/eliminar/1", data={"_csrf_token": "token-falso"})
    )
    afirmar(respuesta.status_code == 400, "Un token CSRF inválido debe rechazarse con 400")

    print("FASE6_CSRF_OK")


# ===========================================================================
# 3. CRUD de Prestatarios (incluye las rutas limpias del PDF)
# ===========================================================================
def test_crud_prestatarios():
    cliente = app.test_client()
    entrar(cliente)

    afirmar(_registrar(cliente.get("/prestatarios")).status_code == 200, "Listado 200")
    afirmar(_registrar(cliente.get("/crear")).status_code == 200, "GET /crear 200")

    datos = {
        "cedula": "V-77777777",
        "nombre": "Lucía",
        "apellido": "Prueba",
        "tipo": "ESTUDIANTE",
        "telefono": "0414-7777777",
        "email": "lucia.prueba@correo.com",
        "estado": "ACTIVO",
    }

    respuesta = publicar(cliente, "/crear", datos)
    afirmar(respuesta.status_code == 200, "Crear debe redirigir al listado")
    afirmar("Lucía Prueba" in texto(respuesta), "El prestatario creado debe aparecer en el listado")

    with database.get_connection() as db:
        fila = db.execute(
            "SELECT id FROM prestatarios WHERE cedula=?", ("V-77777777",)
        ).fetchone()
    afirmar(fila is not None, "El prestatario debe existir en la base de datos")
    id_creado = fila["id"]

    # READ por la ruta de edición (carga el registro)
    respuesta = _registrar(cliente.get(f"/editar/{id_creado}"))
    afirmar(respuesta.status_code == 200, "GET /editar/<id> debe responder 200")
    afirmar("V-77777777" in texto(respuesta), "El formulario debe venir precargado")

    # UPDATE
    datos["nombre"] = "Lucía Elena"
    datos["tipo"] = "PROFESOR"
    respuesta = publicar(cliente, f"/editar/{id_creado}", datos)
    afirmar("Lucía Elena" in texto(respuesta), "La edición debe reflejarse")
    afirmar("Profesor" in texto(respuesta), "El tipo debe actualizarse")

    # Validación del servidor
    respuesta = publicar(
        cliente,
        "/crear",
        {"cedula": "x", "nombre": "A", "apellido": "B", "tipo": "INVALIDO", "estado": "ACTIVO"},
        ruta_token="/crear",
        seguir=False,
    )
    afirmar(respuesta.status_code == 400, "Datos inválidos deben devolver 400")

    # DELETE (POST) — ruta limpia del PDF
    respuesta = publicar(cliente, f"/eliminar/{id_creado}", {}, ruta_token="/prestatarios")
    afirmar(respuesta.status_code == 200, "Eliminar debe redirigir al listado")
    afirmar("V-77777777" not in texto(respuesta), "El registro eliminado no debe aparecer")

    # DELETE por GET no está permitido
    respuesta = _registrar(cliente.get("/eliminar/1"))
    afirmar(respuesta.status_code == 405, "Eliminar por GET debe devolver 405")

    print("FASE6_CRUD_PRESTATARIOS_OK")


# ===========================================================================
# 4. CRUD de Categorías, Laboratorios, Equipos y Usuarios
# ===========================================================================
def test_crud_resto_entidades():
    cliente = app.test_client()
    entrar(cliente)

    for ruta in ("/categorias", "/laboratorios", "/equipos", "/usuarios"):
        afirmar(_registrar(cliente.get(ruta)).status_code == 200, f"GET {ruta} debe responder 200")

    # Categorías
    publicar(
        cliente, "/categorias/crear",
        {"nombre": "Categoría Prueba", "descripcion": "Creada por las pruebas"},
        ruta_token="/categorias/crear",
    )
    afirmar(
        "Categoría Prueba" in texto(_registrar(cliente.get("/categorias"))),
        "La categoría debe aparecer en el listado",
    )
    with database.get_connection() as db:
        cat_id = db.execute(
            "SELECT id FROM categorias WHERE nombre=?", ("Categoría Prueba",)
        ).fetchone()["id"]

    respuesta = publicar(
        cliente, f"/categorias/{cat_id}/editar",
        {"nombre": "Categoría Prueba Editada", "descripcion": ""},
        ruta_token=f"/categorias/{cat_id}/editar",
    )
    afirmar("Categoría Prueba Editada" in texto(respuesta), "La categoría debe editarse")

    # Laboratorios
    publicar(
        cliente, "/laboratorios/crear",
        {"codigo": "LAB-TEST", "nombre": "Laboratorio de Prueba", "ubicacion": "Aula Test",
         "capacidad": "15", "duracion_estandar_minutos": "70", "estado": "DISPONIBLE"},
        ruta_token="/laboratorios/crear",
    )
    afirmar(
        "LAB-TEST" in texto(_registrar(cliente.get("/laboratorios"))),
        "El laboratorio debe aparecer en el listado",
    )
    with database.get_connection() as db:
        lab_id = db.execute(
            "SELECT id FROM laboratorios WHERE codigo=?", ("LAB-TEST",)
        ).fetchone()["id"]

    # Equipos (con relaciones a categoría y laboratorio)
    publicar(
        cliente, "/equipos/crear",
        {"codigo": "EQ-TEST", "nombre": "Equipo de Prueba", "categoria_id": str(cat_id),
         "marca": "Marca", "modelo": "Modelo", "serial": "SERIE-TEST",
         "laboratorio_id": str(lab_id), "estado": "DISPONIBLE"},
        ruta_token="/equipos/crear",
    )
    respuesta = _registrar(cliente.get("/equipos"))
    afirmar("EQ-TEST" in texto(respuesta), "El equipo debe aparecer en el listado")
    afirmar("Categoría Prueba Editada" in texto(respuesta), "El equipo debe mostrar su categoría")

    with database.get_connection() as db:
        eq_id = db.execute("SELECT id FROM equipos WHERE codigo=?", ("EQ-TEST",)).fetchone()["id"]

    respuesta = publicar(
        cliente, f"/equipos/{eq_id}/editar",
        {"codigo": "EQ-TEST", "nombre": "Equipo de Prueba Editado", "categoria_id": str(cat_id),
         "marca": "Marca", "modelo": "Modelo", "serial": "SERIE-TEST",
         "laboratorio_id": str(lab_id), "estado": "DISPONIBLE"},
        ruta_token=f"/equipos/{eq_id}/editar",
    )
    afirmar("Equipo de Prueba Editado" in texto(respuesta), "El equipo debe editarse")

    # Usuarios del sistema
    publicar(
        cliente, "/usuarios/crear",
        {"nombre": "Usuario", "apellido": "Prueba", "username": "usuario_prueba",
         "email": "usuario.prueba@correo.com", "password": "Clave123!",
         "rol": "OPERADOR", "estado": "ACTIVO"},
        ruta_token="/usuarios/crear",
    )
    afirmar(
        "usuario_prueba" in texto(_registrar(cliente.get("/usuarios"))),
        "El usuario debe aparecer en el listado",
    )

    # El listado de usuarios NUNCA debe exponer el hash de la contraseña.
    afirmar(
        "password_hash" not in texto(_registrar(cliente.get("/usuarios"))),
        "El hash de la contraseña no debe exponerse",
    )

    # Limpieza en orden inverso a las dependencias
    publicar(cliente, f"/equipos/{eq_id}/eliminar", {}, ruta_token="/equipos")
    publicar(cliente, f"/categorias/{cat_id}/eliminar", {}, ruta_token="/categorias")
    publicar(cliente, f"/laboratorios/{lab_id}/eliminar", {}, ruta_token="/laboratorios")
    with database.get_connection() as db:
        usuario_id = db.execute(
            "SELECT id FROM usuarios_sistema WHERE username=?", ("usuario_prueba",)
        ).fetchone()["id"]
    publicar(cliente, f"/usuarios/{usuario_id}/eliminar", {}, ruta_token="/usuarios")

    print("FASE6_CRUD_ENTIDADES_OK")


# ===========================================================================
# 5. Reservas: duración estándar, solapamientos y disponibilidad
# ===========================================================================
def test_reservas():
    cliente = app.test_client()
    entrar(cliente)

    afirmar(_registrar(cliente.get("/reservas")).status_code == 200, "Listado de reservas 200")
    respuesta = _registrar(cliente.get("/reservas/crear"))
    afirmar(respuesta.status_code == 200, "Formulario de reserva 200")
    afirmar("70" in texto(respuesta), "La duración estándar de 70 minutos debe estar presente")

    base = {"laboratorio_id": "2", "prestatario_id": "1", "fecha": "2026-12-10"}

    # Reserva nueva: 08:00 + 70 min = 09:10
    publicar(
        cliente, "/reservas/crear",
        dict(base, hora_inicio="08:00", duracion_minutos="70", observaciones="Reserva de prueba"),
        ruta_token="/reservas/crear",
    )
    afirmar(
        "Reserva de prueba" in texto(_registrar(cliente.get("/reservas"))),
        "La reserva debe aparecer en el listado",
    )

    # Solapamiento: 08:30–09:40 se superpone con 08:00–09:10
    respuesta = publicar(
        cliente, "/reservas/crear",
        dict(base, hora_inicio="08:30", duracion_minutos="70"),
        ruta_token="/reservas/crear", seguir=False,
    )
    afirmar(respuesta.status_code == 400, "Un solapamiento debe rechazarse con 400")
    afirmar("superpone" in texto(respuesta), "Debe explicarse el motivo del rechazo")

    # Adyacencia exacta: 09:10–10:20 no se superpone
    respuesta = publicar(
        cliente, "/reservas/crear",
        dict(base, hora_inicio="09:10", duracion_minutos="70"),
        ruta_token="/reservas/crear",
    )
    afirmar(respuesta.status_code == 200, "Una reserva adyacente debe permitirse")

    # Duración personalizada
    respuesta = publicar(
        cliente, "/reservas/crear",
        dict(base, hora_inicio="11:00", duracion_minutos="45"),
        ruta_token="/reservas/crear",
    )
    afirmar(respuesta.status_code == 200, "La duración personalizada debe permitirse")
    afirmar("45 min" in texto(_registrar(cliente.get("/reservas"))), "Debe mostrarse la duración de 45 min")

    # Fecha pasada
    respuesta = publicar(
        cliente, "/reservas/crear",
        dict(base, fecha="2020-01-01", hora_inicio="08:00", duracion_minutos="70"),
        ruta_token="/reservas/crear", seguir=False,
    )
    afirmar(respuesta.status_code == 400, "Una fecha pasada debe rechazarse")

    # Endpoint JSON consumido por fetch()
    respuesta = _registrar(
        cliente.get(
            "/reservas/disponibilidad"
            "?laboratorio_id=2&fecha=2026-12-10&hora_inicio=08:00&hora_fin=09:10"
        )
    )
    afirmar(respuesta.status_code == 200, "El endpoint de disponibilidad debe responder 200")
    afirmar(respuesta.get_json()["disponible"] is False, "La franja ocupada debe marcarse como no disponible")

    respuesta = _registrar(
        cliente.get(
            "/reservas/disponibilidad"
            "?laboratorio_id=2&fecha=2026-12-10&hora_inicio=20:00&hora_fin=21:10"
        )
    )
    afirmar(respuesta.get_json()["disponible"] is True, "Una franja libre debe marcarse como disponible")

    # Cancelar reserva
    with database.get_connection() as db:
        reserva_id = db.execute(
            "SELECT id FROM reservas WHERE fecha='2026-12-10' AND hora_inicio='11:00'"
        ).fetchone()["id"]
    respuesta = publicar(cliente, f"/reservas/{reserva_id}/cancelar", {}, ruta_token="/reservas")
    afirmar(respuesta.status_code == 200, "Cancelar una reserva debe funcionar")
    afirmar("CANCELADA" in texto(respuesta), "El estado debe cambiar a CANCELADA")

    print("FASE6_RESERVAS_OK")


# ===========================================================================
# 6. Préstamos y devoluciones
# ===========================================================================
def test_prestamos_y_devoluciones():
    cliente = app.test_client()
    entrar(cliente)

    afirmar(_registrar(cliente.get("/prestamos")).status_code == 200, "Listado de préstamos 200")

    with database.get_connection() as db:
        equipo = db.execute(
            "SELECT id, codigo FROM equipos WHERE estado='DISPONIBLE' ORDER BY id LIMIT 1"
        ).fetchone()
    afirmar(equipo is not None, "Debe existir un equipo disponible para la prueba")
    equipo_id, equipo_codigo = equipo["id"], equipo["codigo"]

    # Registrar préstamo
    respuesta = publicar(
        cliente, "/prestamos/crear",
        {"equipo_id": str(equipo_id), "prestatario_id": "1", "observaciones": "Préstamo de prueba"},
        ruta_token="/prestamos/crear",
    )
    afirmar(respuesta.status_code == 200, "Registrar un préstamo debe funcionar")

    with database.get_connection() as db:
        estado = db.execute(
            "SELECT estado FROM equipos WHERE id=?", (equipo_id,)
        ).fetchone()["estado"]
    afirmar(estado == "PRESTADO", f"El equipo debe pasar a PRESTADO (estado actual: {estado})")

    with database.get_connection() as db:
        prestamo_id = db.execute(
            "SELECT id FROM prestamos_equipos WHERE equipo_id=? AND estado='ACTIVO'", (equipo_id,)
        ).fetchone()["id"]

    # Un equipo ya prestado no puede prestarse de nuevo
    respuesta = publicar(
        cliente, "/prestamos/crear",
        {"equipo_id": str(equipo_id), "prestatario_id": "1", "observaciones": ""},
        ruta_token="/prestamos/crear", seguir=False,
    )
    afirmar(respuesta.status_code == 400, "No debe prestarse un equipo no disponible")

    # Devolución
    respuesta = publicar(cliente, f"/prestamos/{prestamo_id}/devolver", {}, ruta_token="/prestamos")
    afirmar(respuesta.status_code == 200, "La devolución debe funcionar")

    with database.get_connection() as db:
        fila = db.execute(
            "SELECT estado, fecha_devolucion FROM prestamos_equipos WHERE id=?", (prestamo_id,)
        ).fetchone()
        estado_equipo = db.execute(
            "SELECT estado FROM equipos WHERE id=?", (equipo_id,)
        ).fetchone()["estado"]

    afirmar(fila["estado"] == "DEVUELTO", "El préstamo debe quedar como DEVUELTO")
    afirmar(fila["fecha_devolucion"], "Debe registrarse la fecha de devolución")
    afirmar(estado_equipo == "DISPONIBLE", f"El equipo debe volver a DISPONIBLE (actual: {estado_equipo})")

    print(f"FASE6_PRESTAMOS_OK (equipo {equipo_codigo})")


# ===========================================================================
# 7. Historial con filtros
# ===========================================================================
def test_historial():
    cliente = app.test_client()
    entrar(cliente)

    afirmar(_registrar(cliente.get("/historial")).status_code == 200, "Historial 200")
    afirmar(
        _registrar(cliente.get("/historial?tipo=RESERVA")).status_code == 200,
        "Filtro por tipo 200",
    )
    afirmar(
        _registrar(cliente.get("/historial?tipo=PRESTAMO&estado=TODOS")).status_code == 200,
        "Filtro por estado 200",
    )
    afirmar(
        _registrar(cliente.get("/historial?recurso=LAB-02")).status_code == 200,
        "Filtro por recurso 200",
    )

    respuesta = _registrar(
        cliente.get("/historial?fecha_desde=2026-12-31&fecha_hasta=2026-01-01")
    )
    afirmar(respuesta.status_code == 200, "Un rango de fechas inválido no debe producir un error 500")

    print("FASE6_HISTORIAL_OK")


# ===========================================================================
# 8. Permisos por rol
# ===========================================================================
def test_permisos_operador():
    cliente = app.test_client()
    entrar(cliente, "operador", "Operador123!")

    afirmar(_registrar(cliente.get("/")).status_code == 200, "El operador debe ver el panel")
    afirmar(_registrar(cliente.get("/prestatarios")).status_code == 200, "El operador ve prestatarios")

    # Sin permiso de lectura sobre usuarios
    afirmar(
        _registrar(cliente.get("/usuarios", follow_redirects=False)).status_code == 302,
        "El operador no debe acceder a /usuarios",
    )
    # Sin permiso de escritura sobre laboratorios
    afirmar(
        _registrar(cliente.get("/laboratorios/crear", follow_redirects=False)).status_code == 302,
        "El operador no debe crear laboratorios",
    )
    # Sin permiso de eliminación
    respuesta = publicar(cliente, "/eliminar/1", {}, ruta_token="/prestatarios")
    afirmar(
        "permisos" in texto(respuesta).lower(),
        "El operador debe recibir un aviso de permisos insuficientes al eliminar",
    )

    # El menú no debe ofrecer el módulo de usuarios
    html = texto(_registrar(cliente.get("/")))
    afirmar('href="/usuarios"' not in html, "El menú del operador no debe incluir Usuarios")
    afirmar('href="/prestatarios"' in html, "El menú del operador debe incluir Prestatarios")

    # El operador sí puede escribir prestatarios
    afirmar(
        _registrar(cliente.get("/prestatarios/crear")).status_code == 200,
        "El operador debe poder crear prestatarios",
    )

    print("FASE6_PERMISOS_OK")


# ===========================================================================
# 8b. Auditoría, perfil, ayuda y comprobante
# ===========================================================================
def test_auditoria_perfil_ayuda_comprobante():
    cliente = app.test_client()
    entrar(cliente)

    # --- Auditoría (solo administrador) ---
    respuesta = _registrar(cliente.get("/auditoria"))
    afirmar(respuesta.status_code == 200, "La auditoría debe responder 200")
    html = texto(respuesta)
    afirmar("Registro de actividad" in html, "Debe mostrarse el título del registro")
    afirmar("ACCEDER" in html or "Inicio de sesión" in html,
            "El acceso del propio usuario debe figurar en la auditoría")

    afirmar(_registrar(cliente.get("/auditoria?accion=CREAR")).status_code == 200,
            "El filtro por acción debe funcionar")
    afirmar(_registrar(cliente.get("/auditoria?entidad=prestatario")).status_code == 200,
            "El filtro por entidad debe funcionar")

    csv = _registrar(cliente.get("/auditoria/exportar"))
    afirmar(csv.status_code == 200 and "text/csv" in csv.headers.get("Content-Type", ""),
            "La auditoría debe exportarse a CSV")

    # --- Perfil ---
    afirmar(_registrar(cliente.get("/perfil")).status_code == 200, "El perfil debe responder 200")

    # Contraseña actual incorrecta → 400
    respuesta = publicar(
        cliente, "/perfil",
        {"password_actual": "incorrecta", "password_nueva": "Nueva123!",
         "password_repetida": "Nueva123!"},
        ruta_token="/perfil", seguir=False,
    )
    afirmar(respuesta.status_code == 400, "Una contraseña actual incorrecta debe rechazarse")

    # Confirmación que no coincide → 400
    respuesta = publicar(
        cliente, "/perfil",
        {"password_actual": "Admin123!", "password_nueva": "Nueva123!",
         "password_repetida": "Otra123!"},
        ruta_token="/perfil", seguir=False,
    )
    afirmar(respuesta.status_code == 400, "La confirmación debe coincidir")

    # --- Ayuda ---
    respuesta = _registrar(cliente.get("/ayuda"))
    afirmar(respuesta.status_code == 200, "La guía de uso debe responder 200")
    afirmar("Atajos de teclado" in texto(respuesta), "La guía debe explicar los atajos")

    # --- Comprobante de reserva ---
    with database.get_connection() as db:
        reserva_id = db.execute("SELECT id FROM reservas ORDER BY id LIMIT 1").fetchone()["id"]
    respuesta = _registrar(cliente.get(f"/reservas/{reserva_id}/comprobante"))
    afirmar(respuesta.status_code == 200, "El comprobante debe responder 200")
    html = texto(respuesta)
    afirmar("Comprobante de reserva" in html, "Debe identificarse como comprobante")
    afirmar("LAB-01" in html, "Debe mostrar el laboratorio reservado")

    respuesta = _registrar(cliente.get("/reservas/999999/comprobante"))
    afirmar(respuesta.status_code == 302, "Un comprobante inexistente debe redirigir")

    print("FASE6_AUDITORIA_PERFIL_AYUDA_OK")


# ===========================================================================
# 8c. Sugerencias inteligentes de horario
# ===========================================================================
def test_sugerencias_en_formulario():
    cliente = app.test_client()
    entrar(cliente)

    with database.get_connection() as db:
        fecha = db.execute(
            "SELECT fecha FROM reservas WHERE laboratorio_id=1 ORDER BY hora_inicio LIMIT 1"
        ).fetchone()["fecha"]

    # El endpoint devuelve la ocupación del día y alternativas cuando hay choque.
    respuesta = _registrar(
        cliente.get(
            "/reservas/disponibilidad"
            f"?laboratorio_id=1&fecha={fecha}&hora_inicio=08:30&hora_fin=09:40&duracion=70"
        )
    )
    afirmar(respuesta.status_code == 200, "El endpoint de disponibilidad debe responder 200")
    datos = respuesta.get_json()
    afirmar(datos["disponible"] is False, "La franja consultada debe estar ocupada")
    afirmar(len(datos["ocupacion"]) >= 2, "Debe informar de las franjas ocupadas del día")
    afirmar(len(datos["sugerencias"]) >= 1, "Debe proponer alternativas libres")
    horas = [s["hora_inicio"] for s in datos["sugerencias"]]
    afirmar("08:00" not in horas and "08:30" not in horas,
            f"No debe sugerir franjas ocupadas: {horas}")
    afirmar("10:20" in horas, f"Debe incluir la franja libre tras las reservas: {horas}")

    # Al guardar una reserva solapada, el formulario vuelve con las alternativas.
    respuesta = publicar(
        cliente, "/reservas/crear",
        {"laboratorio_id": "1", "prestatario_id": "1", "fecha": fecha,
         "hora_inicio": "08:30", "duracion_minutos": "70"},
        ruta_token="/reservas/crear", seguir=False,
    )
    afirmar(respuesta.status_code == 400, "La reserva solapada debe rechazarse")
    html = texto(respuesta)
    afirmar("alternativa" in html, "El formulario debe ofrecer franjas alternativas")
    afirmar("Franjas libres más cercanas" in html, "Debe explicarse qué son las alternativas")

    print("FASE6_SUGERENCIAS_OK")


# ===========================================================================
# 8d. Rutas internas sin sesión: nunca un error 500
# ===========================================================================
def test_sin_500_anonimo():
    """Ninguna ruta GET puede reventar para un visitante sin sesión.

    Comprobación que faltaba: ``/ayuda`` vive en el shell autenticado
    (``base_app.html``), así que sin sesión debe redirigir al acceso, no devolver
    500. Se recorre todo el mapa de rutas GET para que el fallo no reaparezca en
    otra vista con la misma dependencia.
    """
    cliente = app.test_client()

    # Caso concreto que motivó la prueba.
    respuesta = _registrar(cliente.get("/ayuda"))
    afirmar(respuesta.status_code == 302, "GET /ayuda sin sesión debe redirigir al acceso")
    afirmar("/login" in respuesta.headers.get("Location", ""), "Debe redirigir a /login")

    # Barrido general: cualquier ruta GET registrada, sin sesión.
    revisadas = 0
    for regla in app.url_map.iter_rules():
        if "GET" not in regla.methods or regla.endpoint == "static":
            continue
        ruta = regla.rule
        if "<" in ruta:
            # Parámetros sustituidos por valores plausibles: lo relevante es que
            # la vista no explote antes de validar la existencia del dato.
            ruta = re.sub(r"<(?:int:)?\w+>", "1", ruta)
        respuesta = _registrar(cliente.get(ruta))
        afirmar(
            respuesta.status_code != 500,
            f"GET {ruta} sin sesión devolvió 500 (se esperaba 200/302/400/404)",
        )
        revisadas += 1

    afirmar(revisadas >= 20, f"El barrido debe cubrir el mapa de rutas (revisadas: {revisadas})")
    print(f"FASE6_SIN_500_ANONIMO_OK ({revisadas} rutas GET revisadas sin sesión)")


# ===========================================================================
# 9. Recursos estáticos, errores y ausencia de 500
# ===========================================================================
def test_estaticos_errores_y_sin_500():
    cliente = app.test_client()
    entrar(cliente)

    afirmar(
        _registrar(cliente.get("/static/css/estilos.css")).status_code == 200,
        "La hoja de estilos debe servirse",
    )
    afirmar(
        _registrar(cliente.get("/static/js/main.js")).status_code == 200,
        "El JavaScript debe servirse",
    )

    afirmar(_registrar(cliente.get("/ruta-que-no-existe")).status_code == 404, "404 esperado")
    afirmar(_registrar(cliente.get("/health")).status_code == 200, "Health 200")

    # La plantilla base debe ser HTML5 con los elementos exigidos.
    html = texto(_registrar(cliente.get("/")))
    afirmar(html.lstrip().startswith("<!DOCTYPE html>"), "Debe ser HTML5 con doctype")
    afirmar('lang="es"' in html, "Debe declarar el idioma")
    afirmar('name="viewport"' in html, "Debe ser responsive (meta viewport)")
    afirmar("estilos.css" in html, "Debe enlazar el CSS propio")
    afirmar("main.js" in html, "Debe incluir el JavaScript propio")
    afirmar("<nav" in html and "<main" in html and "<header" in html, "Debe usar HTML semántico")

    afirmar(500 not in ESTADOS_VISTOS, "Ninguna petición debe devolver un error 500")

    print("FASE6_ESTATICOS_Y_ERRORES_OK")
    print(f"FASE6_SIN_ERRORES_500_OK ({len(ESTADOS_VISTOS)} peticiones verificadas)")


# ===========================================================================
# Ejecución
# ===========================================================================
def main():
    print(f"Base de datos de prueba: {database.DATABASE_PATH}")
    test_autenticacion()
    test_portada_y_busqueda()
    test_listados_avanzados()
    test_csrf()
    test_crud_prestatarios()
    test_crud_resto_entidades()
    test_reservas()
    test_sugerencias_en_formulario()
    test_prestamos_y_devoluciones()
    test_historial()
    test_auditoria_perfil_ayuda_comprobante()
    test_permisos_operador()
    test_sin_500_anonimo()
    test_estaticos_errores_y_sin_500()
    print("FASE6_PRUEBA_WEB_COMPLETA_OK")


if __name__ == "__main__":
    main()
