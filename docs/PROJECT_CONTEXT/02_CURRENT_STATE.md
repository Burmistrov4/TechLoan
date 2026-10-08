# 02 — ESTADO ACTUAL REAL

> Última actualización: 2026-10-08 (sesión 3, auditoría final).
> **Estado: TERMINADO Y EMPAQUETADO.** Ver `WORKLOG.md` para la evidencia completa.

## Estado general

El proyecto **cumple el requisito académico vigente**: es una aplicación web CRUD
funcional construida con Flask + SQLite3 + Jinja2 + HTML5 + CSS3 + JavaScript
Vanilla, que reutiliza íntegramente el backend, los servicios y las pruebas
heredados. Está verificado, documentado y empaquetado para la entrega.

## Interfaz principal (web)

### Infraestructura

| Elemento | Archivo |
|---|---|
| Blueprint web + permisos + CSRF | `app/routes/web_common.py` |
| Login / logout / panel | `app/routes/web_auth_routes.py` |
| CRUD web de las 5 entidades | `app/routes/web_crud_routes.py` |
| Reservas, préstamos, devoluciones, historial | `app/routes/web_operations_routes.py` |
| Plantilla base (HTML5, navbar, mensajes) | `templates/base.html` |
| CSS propio responsive | `static/css/estilos.css` |
| JavaScript Vanilla | `static/js/main.js` |
| Configuración del servidor | `app/server.py` |

`app/server.py` configura `template_folder` y `static_folder` apuntando a la
**raíz del proyecto**, tal como sugiere el PDF, y registra los manejadores de
error `400`, `403`, `404` y `500`.

### Rutas web implementadas

```
/                        Panel de inicio con indicadores
/login   (GET, POST)     Formulario de acceso
/logout  (POST)          Cierre de sesión

/crear                   Alta de prestatario        ← ruta del PDF
/editar/<id>             Edición de prestatario     ← ruta del PDF
/eliminar/<id> (POST)    Baja de prestatario        ← ruta del PDF

/prestatarios  + crear / <id>/editar / <id>/eliminar
/categorias    + crear / <id>/editar / <id>/eliminar
/laboratorios  + crear / <id>/editar / <id>/eliminar
/equipos       + crear / <id>/editar / <id>/eliminar
/usuarios      + crear / <id>/editar / <id>/eliminar   (solo ADMINISTRADOR)

/reservas               + /reservas/crear + /reservas/<id>/cancelar
/reservas/disponibilidad   (JSON consumido con fetch())
/prestamos              + /prestamos/crear + /prestamos/<id>/devolver
/historial              (filtros por tipo, estado, prestatario, recurso y fechas)
```

### Entregables académicos

- `schema.sql` (raíz): 7 tablas, PK, FK, `CHECK`, 7 índices y **21 registros de
  prueba** (mínimo exigido: 3).
  Las fechas de las reservas y préstamos de prueba son **relativas a la fecha de
  ejecución** (`date('now','localtime','+N days')`), por lo que **nunca quedan
  vencidas**, sea cual sea la fecha de la exposición.
- `init_db.py`: reconstruye la base de datos desde `schema.sql`, admite una ruta
  alterna e imprime las reservas cargadas y cómo demostrar el solapamiento.
- `README.md`: descripción, problema, stack, estructura (con tabla de equivalencia
  frente a la estructura sugerida por el enunciado), instalación, entorno virtual,
  dependencias, inicialización de BD, ejecución, URL, usuarios de prueba,
  funcionalidades, seguridad, pruebas y flujo de exposición.
- `docs/GUIA_EXPOSICION.md`: recorrido paso a paso para la defensa, plan de
  contingencia y respuestas a preguntas previsibles del profesor.
- `TechLoan_Proyecto_Final_Programacion_III.zip`: paquete de entrega (2,91 MB,
  142 archivos), sin `.venv`, `__pycache__`, `.pyc`, respaldos ni estado interno
  de agentes.
- `requirements.txt`: Flask 3.1.2, Werkzeug 3.1.3.

## Backend (conservado y ampliado)

### Servicios

Servicios POO para autenticación, usuarios, prestatarios, laboratorios,
categorías, equipos, reservas, préstamos, disponibilidad, historial y
**dashboard**. Se añadió `ReservationService.cancel()` (aditivo, no altera
ninguna regla existente).

### Seguridad

Validado por pruebas: SQL Injection en autenticación, hash `scrypt` de
contraseñas, no exposición de `password_hash`, roles y permisos, logout, sesión,
prevención de parameter tampering, registro público sin escalamiento, **token
CSRF en todos los `POST` web**, **eliminaciones solo por `POST`** y manejadores
de error propios que no filtran trazas.

### Reglas de negocio

Validadas por pruebas: duración estándar de 70 minutos, duración personalizada,
reservas, préstamos, devoluciones, disponibilidad, solapamientos, límites exactos
adyacentes, estados que bloquean/no bloquean e historial.

## Pruebas

| Archivo | Alcance | Estado |
|---|---|---|
| `tests/smoke_test.py` | Esquema, hash, solapamiento, arranque web | ✅ |
| `tests/test_web_phase6.py` | Integración web (113 peticiones, BD temporal) | ✅ |
| `tests/test_crud_phase5.py` | CRUD backend | ✅ |
| `tests/test_validations_phase5.py` | Validaciones | ✅ |
| `tests/test_security_phase5.py` | Seguridad | ✅ |
| `tests/test_overlap_phase5.py` | Solapamientos | ✅ |
| `tests/test_roles_phase5.py` | Roles y permisos | ✅ |
| `tests/test_historial_phase4.py` | Historial | ✅ |
| `tests/crud_test.py`, `tests/security_test.py` | Legado | ✅ |

**Resultados de la auditoría final:**

- Suite completa en el proyecto: **10 PASS / 0 FAIL**.
- Suite completa en copia limpia con entorno virtual nuevo: **10 PASS / 0 FAIL**.
- Navegador real (Chromium/Playwright): **56/56 comprobaciones OK**, 148
  respuestas observadas, **cero errores 5xx**, sin excepciones de JavaScript.
- Capturas de evidencia en `docs/capturas/` (43 imágenes).

## Interfaz Tkinter (legado)

`app/gui/` se conserva **intacto** como prototipo histórico y **se incluye en el
ZIP de entrega**, tal como se decidió en la auditoría final (resuelve Q-011).
No es la interfaz de entrega y no debe reescribirse.

## Pendientes

Ninguno técnico. Solo acciones de preparación de la defensa:

1. Ensayar el recorrido de `docs/GUIA_EXPOSICION.md` §3.
2. Ejecutar `python init_db.py` el mismo día de la exposición.
3. Decisión opcional: excluir `docs/PROMPT_AUTONOMOUS_AGENT.md` del ZIP si se
   prefiere no entregar documentos de trabajo del agente (por defecto se incluye).
