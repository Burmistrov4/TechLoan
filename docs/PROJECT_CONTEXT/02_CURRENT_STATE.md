# 02 — ESTADO ACTUAL REAL

> Última actualización: 2026-10-08 (sesión 2).
> **La entrega web está construida y verificada.** Ver `WORKLOG.md` para la evidencia.

## Estado general

El proyecto **cumple el requisito académico vigente**: es una aplicación web CRUD
funcional construida con Flask + SQLite3 + Jinja2 + HTML5 + CSS3 + JavaScript
Vanilla, que reutiliza íntegramente el backend, los servicios y las pruebas
existentes.

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
/historial              (con filtros por tipo, estado, prestatario, recurso y fechas)
```

### Entregables académicos

- `schema.sql` en la raíz: 7 tablas, PK, FK, `CHECK`, 7 índices y **21 registros
  de prueba** (muy por encima del mínimo de 3 exigido).
- `init_db.py`: reconstruye la base de datos desde `schema.sql`.
- `README.md`: descripción, problema, stack, estructura, instalación, entorno
  virtual, dependencias, inicialización de BD, ejecución, URL, usuarios de
  prueba, funcionalidades, seguridad y pruebas.
- `requirements.txt`: Flask 3.1.2, Werkzeug 3.1.3.

## Backend (conservado y ampliado)

### Flask

- `app/server.py` con `SECRET_KEY`, `SESSION_COOKIE_HTTPONLY=True`,
  `SESSION_COOKIE_SAMESITE="Lax"`, inicialización de SQLite, blueprints de
  autenticación, CRUD, operaciones, reservas y web, y `/health`.

### Base de datos

- `database/techloan.db` (SQLite3) reconstruida desde `schema.sql`.
- Respaldo de la versión anterior: `database/techloan.db.backup-20261008`.

### Servicios

Servicios POO para autenticación, usuarios, prestatarios, laboratorios,
categorías, equipos, reservas, préstamos, disponibilidad, historial y
**dashboard** (nuevo). Se añadió `ReservationService.cancel()`.

### Seguridad

Validado por pruebas:

- SQL Injection en autenticación.
- Hash de contraseñas (`scrypt`) y longitud compatible con `VARCHAR(255)`.
- No exposición de `password_hash`.
- Roles y permisos.
- Logout y sesión.
- Prevención de parameter tampering (el operador se toma de la sesión).
- Registro público sin escalamiento a ADMINISTRADOR.
- **Nuevo:** token CSRF en todos los `POST` web.
- **Nuevo:** eliminaciones solo por `POST` (un `GET` responde `405`).
- **Nuevo:** manejadores de error propios que no filtran trazas.

### Reglas de negocio

Validadas por pruebas: duración estándar de 70 minutos, duración personalizada,
reservas, préstamos individuales, devoluciones, disponibilidad, solapamientos,
límites exactos adyacentes, estados que bloquean/no bloquean e historial.

## Pruebas

| Archivo | Alcance | Estado |
|---|---|---|
| `tests/smoke_test.py` | Esquema, hash, solapamiento, arranque web | ✅ reescrito, pasa |
| `tests/test_web_phase6.py` | Integración web completa (113 peticiones, BD temporal) | ✅ nuevo, pasa |
| `tests/test_crud_phase5.py` | CRUD backend | ✅ pasa |
| `tests/test_validations_phase5.py` | Validaciones | ✅ pasa |
| `tests/test_security_phase5.py` | Seguridad | ✅ pasa |
| `tests/test_overlap_phase5.py` | Solapamientos | ✅ pasa |
| `tests/test_roles_phase5.py` | Roles y permisos | ✅ pasa |
| `tests/test_historial_phase4.py` | Historial | ✅ pasa |
| `tests/crud_test.py`, `tests/security_test.py` | Legado | ✅ pasan |

Verificación en navegador real (Chromium + Playwright): **31/31 comprobaciones
OK**. Capturas en `docs/capturas/`.

## Interfaz Tkinter (legado)

`app/gui/` se conserva como prototipo histórico. **No es la interfaz de entrega**
y no debe reescribirse. Su permanencia dentro del ZIP final es una decisión
abierta (ver `08_OPEN_QUESTIONS.md`).

## Pendientes

- Repaso final de la rúbrica y ensayo del flujo de exposición.
- Decidir si `app/gui/` se incluye o se excluye del paquete de entrega.
