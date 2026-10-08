# 09 — CRITERIOS DE ACEPTACIÓN

> Estado verificado el 2026-10-08 (auditoría final, sesión 3).
> La evidencia de cada punto está en `WORKLOG.md`.
> **Todos los criterios del PDF están cubiertos. No quedan pendientes técnicos.**

## Auditoría final — resultados medidos

| Verificación | Resultado |
|---|---|
| Suite completa en el proyecto | **10 PASS / 0 FAIL** |
| Suite completa en copia limpia con venv nuevo | **10 PASS / 0 FAIL** |
| Pruebas web (`test_web_phase6.py`) | 113 peticiones, **cero errores 500** |
| Navegador real (Chromium/Playwright) | **56/56 comprobaciones OK** |
| Respuestas HTTP observadas en el recorrido | 148, **cero 5xx** |
| Excepciones de JavaScript | 0 |
| Capturas de evidencia | 43 imágenes en `docs/capturas/` |
| Paquete de entrega | ZIP íntegro, 142 archivos, 0 entradas prohibidas |
| Reconstrucción desde cero (clon limpio) | init_db + suite + servidor + login: OK |

## Rúbrica

### CRUD — 35 % ✅

- [x] Crear funciona (formulario + validación servidor + servicio + redirección).
- [x] Leer funciona (tabla responsive; en móvil, tarjetas).
- [x] Editar funciona (formulario precargado).
- [x] Eliminar funciona (por `POST`).
- [x] Flujo normal sin errores 500 (113 peticiones verificadas).
- [x] Mensaje amigable cuando no hay datos (`estado-vacio` en todos los listados).
- [x] Confirmación JavaScript antes de eliminar (`window.confirm`).

### Base de datos — 20 % ✅

- [x] SQLite3 (librería nativa `sqlite3`).
- [x] `schema.sql` en la raíz del proyecto.
- [x] Claves primarias, claves foráneas y restricciones `CHECK`.
- [x] Índices en las consultas frecuentes (7 índices).
- [x] Consultas parametrizadas (`?`) en todo el código.
- [x] Conexiones gestionadas por operación (`contextmanager` con `commit`/`rollback`/`close`).
- [x] `PRAGMA foreign_keys = ON` en cada conexión.
- [x] 21 registros de prueba en `schema.sql` (mínimo exigido: 3).

### HTML/CSS — 15 % ✅

- [x] HTML5 semántico (`header`, `nav`, `main`, `section`, `article`, `table`, `caption`, `output`).
- [x] `lang="es"` y `meta viewport`.
- [x] Labels asociados a todos los campos (`for`/`id`).
- [x] Formularios claros, con ayudas y campos obligatorios marcados.
- [x] CSS propio, limpio y comentado por secciones.
- [x] Responsive móvil 375 px (verificado con capturas).
- [x] Responsive tablet 768 px.
- [x] Escritorio 1280 px.
- [x] Navegación usable, con enlace "Saltar al contenido principal".
- [x] Foco visible y contraste razonable.

### JavaScript — 15 % ✅

- [x] Vanilla JS, sin dependencias.
- [x] Confirmación antes de eliminar, cancelar y devolver.
- [x] Validación en el cliente con realimentación visual.
- [x] Manipulación del DOM (menú móvil, hora de finalización en vivo, cierre de mensajes).
- [x] Interacción visible (botón "Usar duración estándar", estados de carga).
- [x] `fetch()` a `/reservas/disponibilidad` para avisar de solapamientos.

### Buenas prácticas — 15 % ✅

- [x] Modularidad (rutas, servicios, seguridad y modelos separados).
- [x] POO (clases de dominio y servicios con métodos estáticos).
- [x] Rutas organizadas por responsabilidad en blueprints.
- [x] Comentarios pertinentes en Python, JavaScript y CSS.
- [x] README completo con instalación, inicialización, ejecución y descripción del problema.
- [x] Código entendible para Programación III.
- [x] Sin secretos expuestos ni hashes filtrados.

## Pruebas funcionales mínimas

### Autenticación ✅

- [x] Login válido → `302` al panel.
- [x] Login inválido → `401` con mensaje genérico.
- [x] Logout → cierra la sesión.
- [x] Ruta protegida sin sesión → `302` al login con `?next=`.

### Prestatarios ✅

- [x] Crear, listar, editar, eliminar y confirmación.
- [x] Rutas del PDF `/crear`, `/editar/<id>`, `/eliminar/<id>`.
- [x] Validación servidor → `400`.
- [x] `GET /eliminar/<id>` → `405`.

### Laboratorios / Categorías / Equipos ✅

- [x] Crear, listar, editar y eliminar en los tres módulos.
- [x] Equipos con relación a categoría y laboratorio (se muestran los nombres relacionados).

### Usuarios ✅

- [x] CRUD completo, solo para ADMINISTRADOR.
- [x] El hash de la contraseña nunca aparece en el listado.
- [x] No se puede eliminar al último administrador activo.

### Reservas ✅

- [x] Crear y listar.
- [x] Duración estándar de 70 minutos (autocompletada desde el laboratorio).
- [x] Duración personalizada (probado con 45 y 90 minutos).
- [x] Conflicto rechazado con `400` y mensaje explicativo.
- [x] Adyacencia exacta permitida (09:10 tras 08:00–09:10).
- [x] Fecha pasada rechazada.
- [x] Cancelación de reserva.
- [x] Disponibilidad vía `fetch()`.

### Préstamos ✅

- [x] Prestar un equipo disponible.
- [x] El equipo pasa a `PRESTADO`.
- [x] Un equipo ya prestado no puede volver a prestarse (`400`).
- [x] Devolver → el equipo vuelve a `DISPONIBLE`.
- [x] Se registra la fecha de devolución.

### Historial ✅

- [x] Aparecen reservas, préstamos y devoluciones.
- [x] Filtros por tipo, estado, prestatario, recurso y rango de fechas.
- [x] Un rango de fechas inválido no produce error 500.

## Seguridad

- [x] Inyección SQL: consultas parametrizadas.
- [x] Hash de contraseñas (`scrypt`, ≤ 255 caracteres).
- [x] Sin exposición de `password_hash`.
- [x] Roles y permisos verificados por prueba.
- [x] Token CSRF: `POST` sin token → `400`.
- [x] Eliminaciones solo por `POST`.
- [x] Operador tomado de la sesión, no del formulario.
- [x] Errores `400/403/404/500` con páginas propias, sin trazas.

## Calidad

- [x] `compileall` sin errores.
- [x] Regresión backend: 8/8 archivos de prueba en PASS.
- [x] Pruebas web: `FASE6_PRUEBA_WEB_COMPLETA_OK` (113 peticiones, cero 500).
- [x] Smoke test moderno: `SMOKE_TEST_OK`.
- [x] Verificación manual en navegador real: 56/56 comprobaciones OK.
- [x] Capturas responsive en `docs/capturas/` (375, 768 y 1280 px).
- [x] Reconstrucción verificada en copia limpia con entorno virtual nuevo.
- [x] Cero errores críticos conocidos.

## Empaquetado y entrega

- [x] `TechLoan_Proyecto_Final_Programacion_III.zip` generado (2,91 MB, 142 archivos).
- [x] Sin `.venv`, `__pycache__`, `*.pyc`, respaldos de BD ni estado interno de agentes.
- [x] Incluye base de datos de demostración validada (`integrity_check: ok`).
- [x] Incluye el prototipo Tkinter (`app/gui/`, 11 archivos).
- [x] Incluye `schema.sql`, `README.md`, `init_db.py`, `requirements.txt`, tests y documentación.
- [x] `docs/GUIA_EXPOSICION.md` con recorrido, contingencias y preguntas previsibles.

## Revisión final del flujo de exposición

- [x] `python init_db.py` reconstruye la base de datos e imprime las reservas de demostración.
- [x] `python run_server.py` levanta el servidor en `http://127.0.0.1:5000`.
- [x] Login como `admin` y como `operador` (probado en navegador real).
- [x] CRUD completo demostrable en cada módulo, con mensajes de resultado.
- [x] Reserva de 70 minutos con hora de finalización calculada en vivo.
- [x] Solapamiento rechazado con mensaje claro; adyacencia exacta aceptada.
- [x] Préstamo y devolución con cambio de estado verificado en pantalla.
- [x] Historial con filtros y estado vacío amigable.
- [x] Restricción administrativa del rol operador visible y verificada.
- [x] Responsive correcto en 375, 768 y 1280 px (1/2/3 columnas en formularios).
- [x] `schema.sql` y `README.md` presentes y correctos.

## Experiencia de demostración

- [x] Los desplegables muestran código **y** nombre (no solo el identificador).
- [x] Todos los mensajes flash son claros y en español.
- [x] El diálogo de confirmación nombra el registro concreto que se va a eliminar.
- [x] Las fechas de demostración nunca quedan vencidas (son relativas a la fecha de ejecución).
- [x] La navegación indica la sección activa y respeta los permisos del rol.
- [x] Sin desbordamiento horizontal en móvil.
