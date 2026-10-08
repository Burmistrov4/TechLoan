# MEMORY — TECHLOAN

> Memoria compacta para recuperar contexto cuando una sesión de IA pierda historial.
> Última actualización: 2026-10-08 (sesión 3, auditoría final).

## Proyecto

TechLoan es el proyecto final de Programación III (IUTEPI). **La entrega web está
terminada, verificada, documentada y empaquetada.** No quedan pendientes técnicos.

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
| Guía de exposición | `docs/GUIA_EXPOSICION.md` |
| Capturas de verificación | `docs/capturas/` |
| Paquete de entrega | `TechLoan_Proyecto_Final_Programacion_III.zip` |

## Cómo ejecutar

```bash
python init_db.py        # reconstruye database/techloan.db desde schema.sql
python run_server.py     # servidor en http://127.0.0.1:5000
```

Usuarios: `admin` / `Admin123!` (ADMINISTRADOR) y `operador` / `Operador123!` (OPERADOR).

Las fechas de los datos de prueba son **relativas a la fecha de ejecución**
(`date('now','localtime','+N days')`), así que nunca quedan vencidas. `init_db.py`
imprime las reservas cargadas y cómo demostrar el solapamiento.

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

Ninguno técnico. Solo preparación de la defensa:

1. Ensayar el recorrido de `docs/GUIA_EXPOSICION.md` §3.
2. Ejecutar `python init_db.py` el mismo día de la exposición.
3. Opcional: decidir si se excluye `docs/PROMPT_AUTONOMOUS_AGENT.md` del ZIP
   (documento de trabajo del agente, no documentación del proyecto).

## Estado final verificado

- Suite completa: **10 PASS / 0 FAIL** (también en copia limpia con venv nuevo).
- Navegador real: **56/56 comprobaciones OK**, 148 respuestas, **cero 5xx**.
- ZIP de entrega: íntegro, 142 archivos, 0 entradas prohibidas.
- `app/gui/` (Tkinter) intacto y **dentro** del ZIP.

## Regla para agentes

No asumir que una tarea está hecha solo porque existe código relacionado: verificar
funcionamiento ejecutando las pruebas.

No borrar trabajo existente sin necesidad. No instalar frameworks frontend.

No introducir complejidad que no aporta a la rúbrica.
