# WORKLOG — TECHLOAN

## 2026-10-08 — Preparación para migración Web

### Trabajo realizado

- Se leyó el PDF académico vigente.
- Se confirmó cambio de enfoque hacia aplicación web.
- Se decidió conservar backend y reglas de negocio existentes.
- Se documentó arquitectura objetivo Flask + Jinja2 + HTML5 + CSS3 + JavaScript Vanilla.
- Se creó contexto persistente para agentes.
- Se creó roadmap web.
- Se identificó `schema.sql` como pendiente crítico.
- Se identificó `tests/smoke_test.py` como prueba antigua que debe corregirse/reemplazarse.
- Se identificó que Git no estaba configurado en la carpeta del proyecto durante la auditoría.

### Siguiente acción exacta

1. Auditar esquema real de SQLite.
2. Crear `schema.sql` reproducible sin alterar la BD de trabajo.
3. Añadir >=3 registros de prueba.
4. Probar reconstrucción en una BD temporal.
5. Comenzar blueprint web.
6. Crear `base.html`, login/logout y navegación.
7. Implementar primero CRUD web de Prestatarios.

### Restricción

No volver a desarrollar Tkinter salvo que sea necesario para conservar compatibilidad o recuperar alguna regla.

---

## 2026-10-08 (sesión 2) — Entrega web completa

**Agente:** Aria (WorkBuddy AI).

### Auditoría previa (evidencia)

- `compileall` sobre `app/`, `tests/`, `run_server.py`, `run_tkinter.py`: sin errores.
- Pruebas backend ejecutadas con `PYTHONPATH=.`:
  `test_crud_phase5`, `test_validations_phase5`, `test_security_phase5`,
  `test_overlap_phase5`, `test_roles_phase5`, `test_historial_phase4`,
  `crud_test`, `security_test` → **8/8 PASS**.
- Estado real de `database/techloan.db`: 7 tablas, **sin índices**, sin datos de
  negocio y un único usuario de prueba (`security_admin`) con contraseña
  desconocida. No existía `schema.sql`.
- Confirmado que `tests/smoke_test.py` estaba obsoleto: llamaba a
  `AuthService.register` (método inexistente) y esperaba `password_hash` dentro
  del usuario autenticado (el servicio lo elimina a propósito).
- Git **no** estaba inicializado.

### Trabajo realizado

**BLOQUE 2 — Base de datos académica**

- Creado `schema.sql` en la raíz a partir del esquema real: 7 tablas con PK, FK,
  restricciones `CHECK`, 7 índices, `DROP TABLE IF EXISTS` en orden seguro y
  datos de prueba (2 usuarios, 4 prestatarios, 3 categorías, 3 laboratorios,
  4 equipos, 3 reservas, 2 préstamos).
- Los hashes de `admin` / `operador` se generaron con Werkzeug (162 caracteres,
  compatibles con `VARCHAR(255)`) y se verificaron con `check_password_hash`.
- Creado `init_db.py`: reconstruye la BD desde `schema.sql`, admite una ruta
  alterna y muestra el conteo por tabla + `integrity_check`.
- Reconstrucción probada en una BD temporal: sin violaciones de FK
  (`PRAGMA foreign_key_check` vacío) e integridad `ok`.
- **Respaldo previo** de la BD de trabajo en
  `database/techloan.db.backup-20261008` antes de reconstruirla con datos de
  demostración.

**BLOQUE 3 a 8 — Capa web**

- `app/server.py` configura `template_folder` y `static_folder` en la **raíz**
  (como pide el PDF) y registra el blueprint web además de la API existente.
- Nuevos módulos: `app/routes/web_common.py` (blueprint, permisos, CSRF),
  `web_auth_routes.py` (login/logout/panel), `web_crud_routes.py`
  (CRUD de las 5 entidades), `web_operations_routes.py`
  (reservas, préstamos, devoluciones, historial).
- Nuevo servicio `app/services/dashboard_service.py` con los indicadores del panel.
- Nuevo método `ReservationService.cancel()` (aditivo, no altera reglas previas).
- 21 plantillas Jinja2 en `templates/` (base, panel, login, 5 módulos CRUD,
  reservas, préstamos, historial, errores y parciales reutilizables).
- `static/css/estilos.css`: CSS propio mobile-first, 375/768/1280 px, tablas que
  se convierten en tarjetas en móvil, insignias de estado, foco visible.
- `static/js/main.js`: menú móvil, cierre de mensajes, `confirm()` antes de
  eliminar/cancelar/devolver, validación con realimentación visual, cálculo en
  vivo de la hora de finalización y `fetch()` a `/reservas/disponibilidad`.
- Rutas limpias del PDF para la entidad principal: `/crear`, `/editar/<id>`,
  `/eliminar/<id>`.
- Optimización en `app/security/permissions.py`: el usuario de sesión se memoriza
  en `flask.g` para no repetir la consulta en cada enlace del menú.

**BLOQUE 11 — Documentación**

- `README.md` reescrito por completo para el stack web.

**BLOQUE 12 — Pruebas**

- `tests/smoke_test.py` **sustituido** por una versión moderna.
- Nuevo `tests/test_web_phase6.py`: 113 peticiones HTTP verificadas, **cero errores
  500**, sobre una base de datos temporal aislada.
- Regresión backend completa: **8/8 PASS** tras los cambios.
- Verificación en navegador real (Chromium + Playwright): **31/31 comprobaciones
  OK**, incluidas responsive en 375/768/1280 px, confirmación JavaScript, cálculo
  de hora final y `fetch()` de disponibilidad. Capturas en `docs/capturas/`.

### Evidencia de ejecución

| Comando | Resultado |
|---|---|
| `python init_db.py` | 7 tablas, 21 registros, `integrity_check: ok` |
| `PYTHONPATH=. python tests/smoke_test.py` | `SMOKE_TEST_OK` |
| `PYTHONPATH=. python tests/test_web_phase6.py` | `FASE6_PRUEBA_WEB_COMPLETA_OK` |
| Regresión backend (8 archivos) | 8/8 PASS |
| `node verify_techloan.cjs` | 31/31 OK |

### Siguiente acción exacta

1. Repasar la rúbrica punto por punto (ver `09_ACCEPTANCE_TESTS.md`).
2. Ensayar el flujo de exposición de `README.md` §12.
3. Decisión pendiente: si se conserva `app/gui/` (Tkinter) como prototipo histórico
   dentro del ZIP de entrega o se excluye.

### Riesgos pendientes

- `app/gui/` (Tkinter) sigue en el repositorio como legado. No bloquea la entrega
  web y no debe reescribirse.
- Los tests de fase 5 usan la BD de trabajo y crean/eliminan registros. Se
  recomienda ejecutar `python init_db.py` después para dejar la BD en estado de
  demostración.
