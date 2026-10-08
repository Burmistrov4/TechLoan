# 08 — DUDAS, RIESGOS Y PENDIENTES

> Última actualización: 2026-10-08 (sesión 2). Varias dudas quedaron **resueltas**
> durante la implementación; se marcan como tales.

## Resueltas

### Q-001 — Alcance exacto del CRUD ✅ RESUELTA

El PDF habla de gestionar "una entidad del mundo real". Se implementó el CRUD web
completo de las cinco entidades del dominio (prestatarios, categorías,
laboratorios, equipos, usuarios) y **Prestatarios** actúa como entidad principal,
con las rutas limpias del enunciado (`/crear`, `/editar/<id>`, `/eliminar/<id>`).

### Q-002 — ¿Estructura exactamente igual a la sugerida? ✅ RESUELTA

La estructura es orientativa. Se conserva la arquitectura modular en `app/` y se
añaden `templates/` y `static/` en la raíz, como sugiere el PDF. Decisión D-017.

### Q-004 — ¿API o rutas HTML? ✅ RESUELTA

Ambas. La web (Jinja2) cumple el PDF; la API JSON `/api/...` se conserva para el
cliente Tkinter, las pruebas y, en un caso, para `fetch()`.
Decisión D-019 y `web_operations_routes.py`.

### Q-005 — `schema.sql` ✅ RESUELTA

Creado en la raíz, con 7 tablas, PK, FK, `CHECK`, 7 índices y 21 registros de
prueba (mínimo exigido: 3). Reconstrucción verificada en base de datos temporal y
respaldo de la BD de trabajo antes de reconstruirla.

### Q-006 — `smoke_test.py` ✅ RESUELTA

Sustituido por completo por una prueba moderna (decisión D-025). Verifica
esquema, claves foráneas, hash de contraseñas, regla de solapamiento y arranque
de la aplicación web.

### Q-007 — Usuarios web ✅ RESUELTA

El CRUD de usuarios es exclusivo del rol ADMINISTRADOR. El operador no ve el
módulo en el menú y sus peticiones se redirigen con aviso. No existe registro
público en la web, por lo que no hay vía de escalada a ADMINISTRADOR.

### Q-008 — CSRF ✅ RESUELTA

Se implementó un token CSRF de sesión sin dependencias externas (decisión D-020).

### Q-009 — Autenticación ✅ RESUELTA

Se usa la sesión Flask existente y se revalida el usuario contra la base de datos
en cada petición, memorizando el resultado en `flask.g` para no repetir la
consulta.

### Q-010 — Dependencias ✅ RESUELTA

`requirements.txt` sigue conteniendo únicamente `Flask` y `Werkzeug`. No se añadió
ninguna dependencia.

## Resueltas en la auditoría final (sesión 3)

### Q-011 — ¿Se incluye `app/gui/` (Tkinter) en el paquete de entrega? ✅ RESUELTA

**Decisión:** se incluye **intacto** en el ZIP, junto con el resto del código.

**Motivo:** no resta a la rúbrica y demuestra la evolución del proyecto (de ahí
se reutilizaron los servicios y las reglas de negocio). La entrega sigue siendo
la aplicación web, y así queda claro en el README y en `docs/GUIA_EXPOSICION.md`.

**Acción tomada:** `app/gui/` (11 archivos `.py`) está en
`TechLoan_Proyecto_Final_Programacion_III.zip` y **no se ha modificado ni
eliminado**.

### Q-012 — Fechas de las reservas de demostración ✅ RESUELTA

**Decisión:** las fechas de prueba son **relativas a la fecha de ejecución**.

`schema.sql` usa `date('now','localtime','+7 days')` y `+8 days` para las
reservas, y `datetime('now','localtime','-N days')` para los préstamos.

**Motivo:** elimina de raíz el problema de que los datos de demostración queden
vencidos, sin importar cuándo se realice la exposición.

**Acción tomada:** `init_db.py` imprime las reservas cargadas y sugiere cómo
demostrar el solapamiento (08:30 se rechaza) y la adyacencia exacta (10:20 se
acepta).

### Q-013 — ¿Se entregan los documentos de trabajo del agente?

**Situación:** `docs/PROMPT_AUTONOMOUS_AGENT.md` es un documento de instrucciones
de trabajo, no documentación del proyecto.

**Decisión por defecto:** se incluye, por transparencia.

**Alternativa:** excluirlo del ZIP si se prefiere entregar solo documentación del
proyecto. No afecta a la rúbrica en ningún caso.

**Acción:** requiere decisión de Lorenzo si quiere cambiar el comportamiento por
defecto.

## Riesgos

### R-001 — Los tests de fase 5 escriben en la BD de trabajo

Crean y eliminan registros de prueba en `database/techloan.db`. Tras ejecutarlos
conviene reconstruir la BD de demostración:

```bash
python init_db.py
```

**Mitigación aplicada:** las pruebas web nuevas (`test_web_phase6.py`) usan una
base de datos temporal y no tocan la BD de trabajo.

### R-002 — El riesgo principal ya no es el backend

El backend estaba avanzado. El riesgo detectado en la auditoría inicial (gastar el
tiempo refactorizando en lugar de construir la web) quedó neutralizado: la capa
web está construida y verificada, y no se reescribió ninguna regla de negocio.
