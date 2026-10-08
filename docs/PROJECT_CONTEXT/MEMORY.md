# MEMORY — TECHLOAN

> Memoria compacta para recuperar contexto cuando una sesión de IA pierda historial.
> Última actualización: 2026-10-08 (sesión 2).

## Proyecto

TechLoan es el proyecto final de Programación III (IUTEPI). **La entrega web ya
está construida, probada y documentada.**

## Requisito del profesor

`Proyecto Práctico Sistema Web CRUD con Flask y SQLite3.pdf` exige:

**Flask + SQLite3 + Jinja2 + HTML5 + CSS3 + JavaScript Vanilla**

Rutas sugeridas: `/`, `/crear`, `/editar/<id>`, `/eliminar/<id>`.
Entregables: código fuente, `schema.sql` con **al menos 3 registros de prueba**, y `README.md`.

Rúbrica: CRUD 35 %, BD 20 %, HTML/CSS 15 %, JS 15 %, buenas prácticas 15 %.

## Decisión fundamental

NO se rehízo el backend. Se reutilizaron modelos, servicios, seguridad, roles,
permisos, reservas, préstamos, devoluciones, historial, validaciones y pruebas.
Encima se construyó la capa web con Jinja2.

## Arquitectura

```
Navegador → Flask (rutas web Jinja2 + API JSON /api) → Servicios POO → SQLite3
```

Las dos capas de entrada comparten los mismos servicios, así que las reglas de
negocio son únicas.

## Archivos clave de la entrega web

| Qué | Dónde |
|---|---|
| Esquema + datos de prueba | `schema.sql` (raíz) |
| Inicializador | `init_db.py` |
| Arranque | `run_server.py` |
| Servidor Flask | `app/server.py` |
| Blueprint web + CSRF + permisos | `app/routes/web_common.py` |
| Rutas de login/panel | `app/routes/web_auth_routes.py` |
| Rutas CRUD | `app/routes/web_crud_routes.py` |
| Rutas de operaciones | `app/routes/web_operations_routes.py` |
| Plantillas | `templates/` |
| CSS | `static/css/estilos.css` |
| JavaScript | `static/js/main.js` |
| Pruebas web | `tests/test_web_phase6.py` |
| Smoke moderno | `tests/smoke_test.py` |
| Capturas de verificación | `docs/capturas/` |

## Cómo ejecutar

```bash
python init_db.py        # reconstruye database/techloan.db desde schema.sql
python run_server.py     # servidor en http://127.0.0.1:5000
```

Usuarios: `admin` / `Admin123!` (ADMINISTRADOR) y `operador` / `Operador123!` (OPERADOR).

## Cómo probar

```bash
PYTHONPATH=. python tests/smoke_test.py
PYTHONPATH=. python tests/test_web_phase6.py
```

La regresión backend son los archivos `tests/test_*_phase*.py` (8 archivos, todos PASS).
**Las pruebas necesitan `PYTHONPATH=.`** para importar el paquete `app`.

## Reglas importantes (no romper)

- SQLite3 nativo, SQL parametrizado con `?`.
- Passwords como hash Werkzeug; nunca texto plano; nunca exponer `password_hash`.
- Prestatario ≠ usuario del sistema.
- Roles ADMINISTRADOR y OPERADOR; solo el administrador gestiona usuarios y elimina.
- Reserva estándar = 70 minutos; duración personalizable.
- Sin solapamientos; intervalos adyacentes sí permitidos.
- Solo bloquean los estados CONFIRMADA y ACTIVA.
- Préstamo: `DISPONIBLE → PRESTADO`. Devolución: `PRESTADO → DISPONIBLE`.
- El operador de una operación se toma de la sesión, nunca del formulario.
- Eliminaciones solo por `POST`.
- Todo `POST` web exige token CSRF.

## Pendientes

1. Repaso final de la rúbrica y ensayo del flujo de exposición.
2. Decidir si `app/gui/` (Tkinter, prototipo legado) se incluye en el paquete final.

## Regla para agentes

No asumir que una tarea está hecha solo porque existe código relacionado: verificar
funcionamiento ejecutando las pruebas.

No borrar trabajo existente sin necesidad. No instalar frameworks frontend.

No introducir complejidad que no aporta a la rúbrica.
