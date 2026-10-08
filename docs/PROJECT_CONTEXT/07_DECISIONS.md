# 07 — DECISIONES DEL PROYECTO

## D-001 — Stack final

**Decisión:** Flask + SQLite3 + Jinja2 + HTML5 + CSS3 + JavaScript Vanilla.

**Motivo:** coincide con el PDF del profesor.

## D-002 — Backend existente se conserva

No reescribir servicios y reglas que ya funcionan.

**Motivo:** reduce riesgo y conserva trabajo validado.

## D-003 — Tkinter no será la interfaz final prioritaria

Se conserva como legado/prototipo hasta comprobar que no hace falta.

**Motivo:** el PDF exige aplicación web.

## D-004 — SQLite nativo

Usar `sqlite3`.

**Motivo:** requisito explícito.

## D-005 — SQL parametrizado

Usar placeholders `?`.

**Motivo:** requisito explícito y protección contra SQL Injection.

## D-006 — Password hash

Usar Werkzeug y guardar el hash en campo compatible con VARCHAR(255).

**Motivo:** las contraseñas no deben guardarse en texto plano.

## D-007 — JavaScript Vanilla

No React/Vue/Angular.

**Motivo:** el profesor solicita JS y el proyecto debe permanecer sencillo.

## D-008 — Jinja2

Usar templates server-rendered.

**Motivo:** Flask ya lo incorpora y coincide con la arquitectura del documento.

## D-009 — API existente

Mantener endpoints `/api` si son útiles.

**Motivo:** no existe necesidad de destruir una capa ya validada.

## D-010 — No sobreingeniería

La arquitectura puede ser modular, pero debe seguir siendo explicable por un estudiante de Programación III.

## D-011 — Rúbrica primero

El CRUD y los requisitos explícitos tienen prioridad sobre extras visuales.

## D-012 — Confirmación JS

Eliminar requiere confirmación visible mediante JavaScript.

**Motivo:** requisito obligatorio del PDF.

## D-013 — Responsive

La aplicación debe ser usable en celular y escritorio.

## D-014 — Usuarios vs prestatarios

Son entidades diferentes.

## D-015 — Reserva estándar

70 minutos por defecto, con personalización.

## D-016 — Solapamiento

Se mantiene la regla:

`inicio_existente < fin_nueva AND fin_existente > inicio_nueva`

Los intervalos exactamente adyacentes no se consideran solapados.

---

# Decisiones de la sesión de implementación web (2026-10-08)

## D-017 — `templates/` y `static/` en la raíz

**Decisión:** Flask se configura con `template_folder` y `static_folder`
apuntando a la raíz del proyecto, no a `app/`.

**Motivo:** el PDF propone literalmente `templates/` y `static/` al mismo nivel
que el servidor. Se cumple la intención del enunciado sin renunciar a la
arquitectura modular en `app/`.

## D-018 — Blueprint web sin prefijo de URL

**Decisión:** `web_bp` no lleva `url_prefix`, de modo que las rutas limpias del
PDF (`/`, `/crear`, `/editar/<id>`, `/eliminar/<id>`) existen tal cual.

**Motivo:** cumplimiento literal del requisito de rutas.

## D-019 — La entidad principal expone rutas cortas y con espacio de nombres

**Decisión:** Prestatarios responde tanto a `/crear`, `/editar/<id>`,
`/eliminar/<id>` (rutas del PDF) como a `/prestatarios/crear`,
`/prestatarios/<id>/editar` y `/prestatarios/<id>/eliminar` (coherentes con el
resto de módulos). Ambas reglas apuntan al mismo endpoint.

**Motivo:** satisfacer el enunciado sin crear una asimetría inexplicable entre
módulos.

## D-020 — Token CSRF propio, sin dependencias externas

**Decisión:** token de sesión de 32 bytes validado en un `before_request` del
blueprint web, comparado con `secrets.compare_digest`. No se añade Flask-WTF.

**Motivo:** mejora real de seguridad (15 % de buenas prácticas) sin introducir
una dependencia que el PDF no pide ni aumentar la complejidad del proyecto.

## D-021 — Eliminaciones exclusivamente por POST

**Decisión:** `/eliminar/<id>` y las rutas `<entidad>/<id>/eliminar` solo aceptan
`POST`. Un `GET` devuelve `405`.

**Motivo:** requisito explícito del prompt maestro y buena práctica.

## D-022 — El operador se toma siempre de la sesión

**Decisión:** el `usuario_sistema_id` de reservas y préstamos se lee de
`current_user()`, nunca de un campo del formulario.

**Motivo:** evita el parameter tampering. Ya era el criterio de la API; se
extiende a la web.

## D-023 — Consultas de conteo en un servicio propio

**Decisión:** los indicadores del panel viven en
`app/services/dashboard_service.py` en lugar de escribir SQL en las rutas web.

**Motivo:** mantener la arquitectura por capas (`Rutas → Servicios → SQLite3`) y
que ninguna ruta web contenga SQL.

## D-024 — Base de datos temporal en las pruebas web

**Decisión:** `tests/test_web_phase6.py` redirige `app.database.DATABASE_PATH` a
un archivo temporal y lo construye desde `schema.sql`.

**Motivo:** probar sin riesgo de destruir la base de datos de trabajo.

## D-025 — Sustitución de `tests/smoke_test.py`

**Decisión:** se reescribe por completo en lugar de parchearlo.

**Motivo:** el archivo original llamaba a `AuthService.register`, método que no
existe, y afirmaba que el usuario autenticado incluye `password_hash`, algo que
el servicio elimina deliberadamente. No era recuperable sin reescribirlo.

## D-026 — `ReservationService.cancel()` es aditivo

**Decisión:** se añade un método para cancelar reservas.

**Motivo:** permite demostrar que una reserva CANCELADA libera la franja horaria.
No modifica ninguna regla existente ni la firma de otros métodos. La regresión
backend se ejecutó después y pasó completa.

