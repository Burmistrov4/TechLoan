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
  se convierten en tarjetas en celular, insignias de estado, foco visible.
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

---

## 2026-10-08 (sesión 3) — Auditoría final y empaquetado para la entrega

**Agente:** Aria (WorkBuddy AI).

### Trabajo realizado

**1. Fechas de demostración (corregido).** Las reservas y préstamos de prueba
tenían fechas fijas que podían quedar vencidas. Ahora se calculan respecto a la
fecha de ejecución:

- reservas: `date('now','localtime','+7 days')` y `+8 days`;
- préstamo activo: `datetime('now','localtime','-1 day')`;
- préstamo devuelto: `-18 days` y `-16 days`.

`init_db.py` imprime ahora las reservas cargadas y sugiere cómo demostrar el
solapamiento (`08:30` se rechaza) y la adyacencia exacta (`10:20` se acepta).

**2. Mejora de usabilidad detectada en la revisión visual.** Los desplegables de
laboratorios, equipos, categorías y prestatarios mostraban **solo el
identificador** (`LAB-01`, `EQ-001`, `V-12345678`), obligando a memorizar a qué
registro correspondía cada uno. Ahora muestran código y nombre:
`LAB-01 — Laboratorio de Informática 1`, `V-12345678 — María González`.

**3. Revisión visual completa en navegador real.** Recorrido de extremo a extremo
del flujo de exposición con Chromium: login (correcto e incorrecto), CRUD de las
cinco entidades con mensajes de resultado, validación del servidor, edición,
eliminación y devolución con confirmación JavaScript, solapamiento rechazado y
adyacencia aceptada, duración personalizada, cambio de estado
PRESTADO/DISPONIBLE, historial con filtros y estado vacío, restricción del rol
operador y responsive en 375/768/1280 px.

**4. Verificación de reconstrucción desde cero.** Exportación limpia con
`git archive` a una carpeta temporal, entorno virtual nuevo, `pip install -r
requirements.txt`, `python init_db.py`, suite completa y arranque real del
servidor con login. Resultado: **10/10 PASS** y aplicación operativa.

**5. Paquete de entrega.** `TechLoan_Proyecto_Final_Programacion_III.zip`
(2,91 MB, 142 archivos). Verificado: sin `.venv`, sin `__pycache__`, sin `.pyc`,
sin respaldos de BD, sin estado interno de agentes; incluye la base de datos de
demostración (validada con `integrity_check: ok`), el prototipo Tkinter y las
capturas de evidencia.

**6. Documentación.** Nuevo `docs/GUIA_EXPOSICION.md` con el recorrido paso a
paso, comandos exactos, plan de contingencia y respuestas a preguntas previsibles
del profesor. README ampliado con la tabla de equivalencia entre la estructura
sugerida por el enunciado y la del proyecto.

### Evidencia de ejecución

| Comando | Resultado |
|---|---|
| `python init_db.py` | 21 registros, `integrity_check: ok`, fechas de demo impresas |
| Suite completa en el proyecto | 10 PASS / 0 FAIL |
| Suite completa en copia limpia (venv nuevo) | 10 PASS / 0 FAIL |
| Navegador real (56 comprobaciones) | **56/56 OK**, 148 respuestas, **0 errores 5xx** |
| ZIP | integridad OK, 0 entradas prohibidas |

### Incidencias encontradas y resueltas

| Incidencia | Causa | Solución |
|---|---|---|
| Desplegables con solo el identificador | Se pasaba `'codigo'`/`'cedula'` como texto | Clave `etiqueta` con código y nombre |
| `date('now')` podía desfasar un día | Usa UTC | `date('now','localtime',…)` |
| Correos largos desbordaban la tarjeta en móvil | Falta de corte de palabra | `overflow-wrap: anywhere` + `min-width: 0` |

> Las dos incidencias detectadas en la verificación en navegador (el menú
> colapsado a 768 px y los 400/401 en consola) resultaron ser **aserciones
> incorrectas del script de verificación**, no defectos de la aplicación: las 9
> secciones del menú no caben a 768 px, y los 400/401 provienen de las pruebas
> negativas deliberadas (login incorrecto, cédula duplicada, reserva solapada).

### Siguiente acción exacta

1. Ensayar el recorrido de `docs/GUIA_EXPOSICION.md` §3 y cronometrarlo.
2. Regenerar la base de datos con `python init_db.py` el día de la exposición.
3. Decisión abierta: si se quiere excluir `docs/PROMPT_AUTONOMOUS_AGENT.md` del
   ZIP (es un documento de trabajo del agente, no documentación del proyecto).
   Por defecto se incluye, por transparencia.

### Estado

**Proyecto terminado y empaquetado.** No quedan tareas técnicas pendientes.

---

## 2026-10-08 (sesión 4) — Interfaz premium

**Agente:** Aria (WorkBuddy AI).

Sobre la base web ya entregada se elevó la interfaz a un producto presentable ante
el jurado, **sin tocar las reglas de negocio**: se reutilizaron íntegramente los
servicios POO existentes y solo se añadieron capas de presentación y dos servicios
de apoyo.

### Qué se añadió

- **Portada pública** (`templates/landing.html`, `static/css/landing.css`,
  `static/js/landing.js`): presentación del producto con escena 3D por paralaje de
  ratón, revelado por desplazamiento y pestañas de módulos. La raíz `/` deja de
  redirigir al login: muestra la portada al visitante y el panel a quien tiene sesión.
- **Sistema de diseño** (`static/css/estilos.css` reescrito, ~1.900 líneas): tema
  claro y oscuro con persistencia en `localStorage`, tipografía y escala de
  espaciado propias, y tres puntos de ruptura (375 / 820 / 1440 px).
- **Shell de la aplicación** (`templates/base_app.html`, `base_publico.html`,
  `parciales/`): barra lateral, cabecera con campana de alertas, menús emergentes y
  un parcial de iconos SVG en línea (sin librerías externas).
- **Panel analítico**: 6 indicadores con contadores animados y 3 gráficos SVG
  dibujados en el cliente (`static/js/graficos.js`), que se redibujan al cambiar de
  tema.
- **Paleta de comandos (Ctrl+K)** sobre un endpoint de búsqueda global (`/buscar`).
- **Listados avanzados**: búsqueda con retardo, orden por columna, paginación y
  exportación a CSV con BOM, todo reflejado en la URL para que el estado sea
  compartible.
- **Reservas**: línea de tiempo de las franjas ocupadas del día y sugerencias de
  franjas alternativas libres, más comprobante imprimible.
- **Servicios nuevos**: `alertas_service.py` (préstamos vencidos, reservas de hoy,
  laboratorios saturados) y `auditoria_service.py` (registro de actividad tolerante
  a fallos, con tabla e índices propios en `schema.sql`).
- **Módulos de auditoría, perfil y guía de uso** (`/auditoria`, `/perfil`, `/ayuda`).
- **PWA ligera**: `manifest.json`, iconos y favicon propios.
- **`docs/MANUAL_DE_USUARIO.md`**: manual de uso completo en 10 secciones.

### Verificación

| Comprobación | Resultado |
|---|---|
| Suite completa | **10 PASS / 0 FAIL** |
| Navegador real (Chromium/Playwright) | **47/47 OK**, 85 respuestas, **0 errores 5xx**, sin excepciones JS |
| Capturas | `docs/capturas/` regeneradas para la interfaz nueva |

---

## 2026-10-08 (sesión 5) — Verificación final del servidor y cierre

**Agente:** Aria (WorkBuddy AI).

La sesión anterior se interrumpió al levantar el servidor para la comprobación
final. Se retomó el trabajo desde ahí.

### Diagnóstico del "cuelgue"

El servidor **no estaba roto**: se había lanzado en primer plano y `flask run` no
termina nunca, por lo que el proceso quedaba bloqueado. Arrancado como proceso en
segundo plano, responde correctamente en `http://127.0.0.1:5000`.

### Bug real encontrado y corregido

- **`GET /ayuda` sin sesión devolvía 500.** La vista no exigía sesión, pero
  `ayuda.html` hereda `base_app.html`, el shell autenticado, que accede a
  `usuario_actual.nombre`. Sin sesión, `current_user()` es `None` y la plantilla
  lanzaba `UndefinedError`. No lo detectaba la suite porque solo probaba `/ayuda`
  con sesión iniciada.
- **Corrección:** `@login_required` en la ruta (la página pertenece al shell
  autenticado; el enlace del pie de la página de error ya solo se muestra con sesión).
- **Prueba de regresión:** nueva comprobación que **barre las 57 rutas GET del mapa
  de rutas sin sesión** y exige que ninguna devuelva 500. La suite pasó de 150 a
  **208 peticiones verificadas**.

### Verificación final (evidencia)

| Comprobación | Resultado |
|---|---|
| Servidor en marcha y `GET /health` | 200 `{"ok": true}` |
| Rutas internas sin sesión | 302 → `/login` (antes, `/ayuda` daba 500) |
| Suite completa | **10 PASS / 0 FAIL** |
| Navegador real (Chromium/Playwright) | **47/47 OK**, 85 respuestas, **0 errores 5xx**, sin excepciones JS |
| Barrido de rutas GET anónimas | **57 rutas**, ninguna 500 |
| ZIP extraído + venv nuevo + `pip install` | **10 PASS / 0 FAIL** |
| Servidor desde el ZIP | `/health` 200, `/` 200, `/ayuda` 302, `/login` 200, CSS 200 |
| Integridad del ZIP | OK, **192 entradas**, **0 entradas prohibidas** |

### Documentación y empaquetado

- `docs/GUIA_EXPOSICION.md` actualizado: el paso 2 ya no dice que la raíz redirija
  al login (ahora muestra la portada pública) y se añadió el paso 12 con auditoría,
  perfil, guía de uso y comprobante (recorrido renumerado a 15 pasos).
- `docs/PROJECT_CONTEXT/02_CURRENT_STATE.md` actualizado a la interfaz premium.
- ZIP de entrega **reconstruido**: el anterior era anterior a la interfaz premium.

### Siguiente acción exacta

1. Ensayar el recorrido de `docs/GUIA_EXPOSICION.md` §3 y cronometrarlo.
2. Regenerar la base de datos con `python init_db.py` el mismo día de la exposición.
3. Decisión abierta: si se quiere excluir `docs/PROMPT_AUTONOMOUS_AGENT.md` del ZIP.

### Estado

**TERMINADO.** No quedan pendientes técnicos.

---

## 2026-10-08 (sesión 6) — Escenas 3D, tutorial guiado, registro por correo

**Agente:** Aria (WorkBuddy AI).

### Contexto

Lorenzo pidió cinco cosas sobre la interfaz y, después, revisar el acceso: no había podido
iniciar sesión. Se atendió todo en este orden.

### Diagnóstico del acceso (causa real)

Las credenciales `admin` / `Admin123!` y `operador` / `Operador123!` **sí autenticaban**
(verificado contra la base de datos con `AuthService.authenticate`). El problema era otro:
**no había ningún proceso escuchando en el puerto 5000**, así que el formulario no tenía a
quién enviar. El servidor que se había dejado abierto en la sesión anterior murió con ella.

Comprobado también que `iniciar.bat` → `start.py` arranca el servidor correctamente: es la
vía documentada y la que conviene usar.

### Cambios en la interfaz

- **Equipo en la portada.** «María González» pasa a **Evelyn** (coordinadora de laboratorios)
  y se añaden **Lorenzo Roca** y **Adrián Cedeño** con sus roles.
- **Español de Venezuela.** Auditoría completa del texto: «resolvéis» → «se resuelve»,
  «pulsa» → «haz clic en» / «presiona» (teclas), «fichero» → «archivo», «móvil» → «celular»,
  «0 €» → «$0». Corregido en plantillas, JavaScript y toda la documentación.
- **Escenas 3D interactivas.** La imagen plana del héroe y las cuatro ilustraciones de módulos
  se sustituyen por **geometría CSS 3D** (`preserve-3d`), sin WebGL ni librerías: un tablero
  con indicadores y gráficos, cubos volumétricos girando, prismas extruidos y anillos
  concéntricos. La escena se inclina con el puntero y **se gira arrastrando**.
- **Transiciones suaves.** El cambio de pestaña de módulo ya no salta de imagen a imagen:
  fundido cruzado entre los cuatro objetos 3D. El revelado al desplazar se suaviza (760 ms con
  curva de salida y un punto de escala).
- **Tutorial guiado.** Recorrido de 8 pasos que arranca solo la primera vez que se entra al
  panel, con foco real sobre cada elemento (sombra gigante alrededor, no cuatro paneles),
  tarjeta explicativa, barra de progreso, navegación con teclado y botones. Se guarda por
  navegador y se relanza desde el menú de usuario y la guía de uso (`?tutorial=1`).
- **Credenciales fuera del frontend.** La pantalla de acceso ya no muestra los usuarios de
  prueba: solo indica dónde están. Viven en el README y en el manual.

### Registro de usuarios con confirmación por correo

- Tabla `tokens_correo` (un solo uso, con caducidad) y columna `usuarios_sistema.email_confirmado`
  (`DEFAULT 1`, para que las cuentas creadas por un administrador y las ya existentes sigan
  entrando; el autoregistro inserta 0).
- **Migración automática** en `init_database()`: añade la columna si falta, sin recrear tablas.
- `RegistroService` (alta, token, confirmación, reenvío) y `CorreoService` (SMTP real o **modo
  demostración**: guarda el mensaje en `database/buzon/` y el enlace se muestra en pantalla).
- El autoregistro crea siempre **OPERADOR**: nadie se concede privilegios.
- El acceso admite **usuario o correo**. Sin confirmar no se entra, y se explica por qué (ese
  aviso solo se da a quien ya acertó la contraseña).
- Rutas nuevas: `/registro`, `/confirmar/<token>`, `/reenviar`.

### Verificación

| Comprobación | Resultado |
|---|---|
| Suite completa (11 archivos) | **11 PASS / 0 FAIL** |
| `tests/test_registro_phase7.py` (nuevo) | Alta, token, confirmación, acceso con correo, rechazo sin confirmar, validaciones, duplicados, token inválido/caducado/reusado y reenvío |
| Navegador: tutorial y 3D | **33/33 OK** |
| Navegador: registro por correo | **18/18 OK**, 0 respuestas 5xx |
| Migración sobre la base de datos real | columna y tabla creadas, usuarios existentes confirmados |

### Trampas nuevas

- **Flask con `debug=False` cachea las plantillas.** Editar un `.html` y recargar no basta: hay
  que reiniciar el servidor. Costó un diagnóstico en falso («el tutorial no arranca» cuando en
  realidad `tutorial.js` no se estaba sirviendo).
- El enlace de confirmación es **absoluto** (lo construye `URL_BASE`, porque va en un correo),
  así que en las pruebas no hay que volver a prefijarlo con el host.

### Siguiente acción exacta

1. Ensayar el recorrido de `docs/GUIA_EXPOSICION.md` §3 (ahora 17 pasos) y cronometrarlo.
2. Regenerar la base de datos con `python init_db.py` el mismo día de la exposición.
3. Decisión abierta (heredada): incluir o no `docs/PROMPT_AUTONOMOUS_AGENT.md` en el ZIP.

### Estado

**TERMINADO.** No quedan pendientes técnicos.
