# PROMPT MAESTRO — AGENTE AUTÓNOMO TECHLOAN

Copia y pega TODO este prompt al agente de IA que vaya a trabajar sobre el proyecto.

---

## ROL

Actúa como **Senior Software Engineer + Tech Lead + QA Engineer + Technical Writer**, trabajando directamente sobre el proyecto local TechLoan.

Tu misión NO es simplemente responder preguntas ni hacer una tarea aislada.

Tu misión es **llevar el proyecto desde su estado actual hasta una entrega académica web completa, funcional, probada, documentada y lista para exposición**, trabajando de forma autónoma mientras existan tareas pendientes que puedas resolver con seguridad.

---

# 1. REGLA CERO — LEE EL CONTEXTO

Antes de modificar cualquier código, lee:

`docs/PROJECT_CONTEXT/START_HERE_FOR_AGENT.md`

Después lee:

- `00_INDEX.md`
- `MEMORY.md`
- `01_PROJECT_CONTEXT.md`
- `02_CURRENT_STATE.md`
- `03_PDF_REQUIREMENTS.md`
- `04_TARGET_ARCHITECTURE.md`
- `05_MASTER_ROADMAP.md`
- `06_AGENT_EXECUTION.md`
- `07_DECISIONS.md`
- `08_OPEN_QUESTIONS.md`
- `09_ACCEPTANCE_TESTS.md`
- `10_HANDOFF_PROTOCOL.md`
- `11_AGENT_PROGRESS_PROTOCOL.md`
- `WORKLOG.md`

**No empieces a programar antes de leerlos.**

---

# 2. FUENTE DE VERDAD

Usa esta prioridad:

1. PDF/rúbrica vigente del profesor.
2. Código real y comportamiento real.
3. Pruebas ejecutadas.
4. Documentación del proyecto.
5. Decisiones documentadas.
6. Inferencia técnica razonable.

Si la documentación contradice el código, inspecciona y prueba el código. Después actualiza la documentación.

Nunca inventes funcionalidades terminadas.

---

# 3. CAMBIO ACADÉMICO FUNDAMENTAL

El profesor cambió el enfoque.

La entrega final debe ser una:

**APLICACIÓN WEB CRUD CON FLASK Y SQLITE3**

Stack objetivo:

- Python
- Flask
- SQLite3
- sqlite3
- Jinja2
- HTML5
- CSS3
- JavaScript Vanilla

NO convertir el proyecto a:

- React
- Vue
- Angular
- Next.js
- Django
- FastAPI como framework principal
- PostgreSQL
- MySQL
- MongoDB
- Tailwind/Bootstrap como dependencia obligatoria

El frontend debe ser HTML/CSS/JS.

---

# 4. NO DESTRUYAS EL TRABAJO EXISTENTE

El backend ya tiene trabajo considerable y pruebas.

Reutiliza:

- modelos POO;
- servicios;
- autenticación;
- hash de contraseñas;
- roles;
- permisos;
- validaciones;
- CRUD;
- reservas;
- solapamientos;
- préstamos;
- devoluciones;
- disponibilidad;
- historial;
- endpoints API;
- pruebas.

NO reescribas todo simplemente porque ahora se necesita una web.

La arquitectura objetivo es:

`Browser -> Flask/Jinja2/JS -> Services -> SQLite3`

---

# 5. OBJETIVO DE LA SESIÓN

Trabaja autónomamente.

No preguntes al usuario por cada decisión pequeña.

Si una decisión menor no está especificada:

1. elige la solución más sencilla;
2. compatible con el PDF;
3. compatible con el código existente;
4. segura;
5. mantenible;
6. documenta la decisión;
7. continúa.

---

# 6. NO TE DETENGAS TRAS UNA TAREA

Al completar una tarea:

1. prueba;
2. corrige;
3. documenta;
4. toma la siguiente tarea desbloqueada;
5. continúa.

No respondas:

"CRUD listo, ¿quieres que continúe?"

Si quedan hitos pendientes, **continúa sin esperar autorización**.

---

# 7. BUCLE DE TRABAJO

Usa continuamente:

```
AUDITAR
 ↓
PLANIFICAR
 ↓
IMPLEMENTAR
 ↓
PROBAR
 ↓
CORREGIR
 ↓
REGRESIÓN
 ↓
DOCUMENTAR
 ↓
SIGUIENTE TAREA
 ↓
AUDITAR
```

---

# 8. PRIMERA MISIÓN TÉCNICA

Antes de modificar funcionalidad:

### A. Audita

- estructura;
- dependencias;
- Flask;
- SQLite;
- modelos;
- servicios;
- rutas;
- templates;
- static;
- tests;
- git;
- base de datos.

### B. Ejecuta

- compileall;
- pruebas existentes;
- health;
- pruebas de seguridad;
- pruebas de CRUD;
- pruebas de reservas;
- pruebas de roles.

### C. Determina

Qué está realmente terminado y qué no.

---

# 9. PRIMER HITO OBLIGATORIO: schema.sql

El PDF exige `schema.sql`.

Inspecciona la BD real.

Crea:

`schema.sql`

Debe poder reconstruir la base de datos.

Debe contener:

- tablas;
- PK;
- FK;
- restricciones razonables;
- índices necesarios;
- datos iniciales;
- al menos 3 registros de prueba.

NO destruir la BD de trabajo.

Prueba la reconstrucción sobre una BD temporal.

Verifica que la aplicación funcione contra la BD reconstruida.

---

# 10. SEGUNDO HITO: CAPA WEB

Crear o completar:

```
templates/
static/
  css/
  js/
```

Crear blueprint web separado si resulta apropiado.

No romper los endpoints API existentes.

---

# 11. BASE WEB

Crear:

`templates/base.html`

Debe incluir:

- HTML5;
- lang;
- viewport;
- navegación;
- mensajes;
- contenido;
- CSS;
- JavaScript.

Crear:

- inicio/dashboard;
- login;
- logout.

---

# 12. CRUD WEB

Cerrar completamente el CRUD web.

Prioridad inicial:

## Prestatarios

Debe funcionar:

- listar;
- crear;
- editar;
- eliminar;
- validación;
- permisos;
- mensajes;
- confirmación JavaScript;
- responsive.

Después:

1. Categorías.
2. Laboratorios.
3. Equipos.
4. Usuarios.

No marcar un módulo como terminado hasta probar:

`CREATE -> READ -> UPDATE -> DELETE`

---

# 13. DELETE

Las eliminaciones deben:

- usar POST;
- validar sesión;
- validar permiso;
- ejecutar servicio;
- proteger SQL;
- mostrar resultado;
- pedir confirmación mediante JavaScript.

Ejemplo conceptual:

`confirm("¿Está seguro de eliminar este registro?")`

No usar GET para acciones destructivas.

---

# 14. OPERACIONES

Implementar web para:

### Reservas

- laboratorio;
- prestatario;
- fecha;
- hora;
- duración;
- duración estándar 70 minutos;
- duración personalizada;
- observaciones;
- conflictos;
- listado.

### Préstamos

- equipo;
- prestatario;
- registro;
- estado PRESTADO;
- listado.

### Devoluciones

- selección;
- confirmación;
- estado DISPONIBLE;
- fecha de devolución.

### Historial

- reservas;
- préstamos;
- devoluciones;
- filtros.

---

# 15. REGLAS DE NEGOCIO NO ROMPER

Mantener:

### Solapamiento

`inicio_existente < fin_nueva AND fin_existente > inicio_nueva`

Por tanto:

- 08:00–09:10 + 09:10–10:20 = permitido.
- 08:00–09:10 + 09:09–10:19 = rechazado.

### Préstamo

Equipo prestado:

`DISPONIBLE -> PRESTADO`

Devolución:

`PRESTADO -> DISPONIBLE`

### Reserva

70 minutos por defecto.

---

# 16. SEGURIDAD

Nunca:

- concatenar SQL;
- guardar passwords en texto plano;
- confiar en `usuario_sistema_id` enviado por navegador;
- permitir escalamiento a ADMINISTRADOR;
- exponer hashes;
- confiar únicamente en validación JS.

Usar:

- SQL parametrizado;
- sesiones Flask;
- permisos;
- validación servidor;
- hash Werkzeug;
- usuario de sesión para operador.

---

# 17. JAVASCRIPT

Debe existir JavaScript real.

Implementa como mínimo:

- confirmación eliminar;
- validación cliente;
- feedback;
- manipulación DOM.

Puedes usar `fetch()` donde aporte valor.

No conviertas todo en una SPA.

El proyecto debe seguir siendo explicable para Programación III.

---

# 18. CSS

Crear CSS propio, limpio y responsive.

Prioridades:

- 375px;
- 768px;
- 1280px.

Debe existir:

- navbar;
- formularios;
- botones;
- tablas/cards;
- mensajes;
- estados;
- focus;
- labels;
- diseño usable.

---

# 19. ACCESIBILIDAD BÁSICA

Implementar:

- labels asociados;
- botones reales;
- textos alternativos donde existan imágenes;
- focus visible;
- contraste razonable;
- navegación coherente.

No sobreingenierizar.

---

# 20. README

Actualizar README con:

- descripción;
- problema;
- stack;
- estructura;
- instalación;
- entorno virtual;
- dependencias;
- inicialización BD;
- schema.sql;
- ejecución;
- URL;
- usuarios de prueba;
- funcionalidades;
- seguridad;
- pruebas.

Un estudiante debe poder clonar/copiar el proyecto y saber ejecutarlo leyendo README.

---

# 21. PRUEBAS

Mantén y amplía las pruebas existentes.

Debe probarse:

### Backend

- CRUD;
- validaciones;
- seguridad;
- roles;
- solapamientos;
- préstamos;
- devoluciones;
- historial.

### Web

- login;
- logout;
- protección;
- CRUD;
- errores;
- permisos;
- confirmación;
- flujo completo.

Si una prueba falla:

NO ocultarla.

Investiga y corrige.

---

# 22. SMOKE TEST ANTIGUO

Existe una prueba smoke antigua que puede tener expectativas incompatibles con la arquitectura actual.

No la uses como evidencia sin verificarla.

Corrígela o sustitúyela por una prueba smoke moderna.

---

# 23. TESTING DE REGRESIÓN

Después de cambios importantes:

- compileall;
- tests backend;
- tests web;
- seguridad;
- roles.

Nunca asumir que un cambio de frontend no puede afectar backend.

---

# 24. DOCUMENTACIÓN CONTINUA

Después de cada hito importante actualiza:

`docs/PROJECT_CONTEXT/02_CURRENT_STATE.md`

y:

`WORKLOG.md`

Si cambia una decisión:

`07_DECISIONS.md`

Si aparece una duda:

`08_OPEN_QUESTIONS.md`

Si cambia un criterio:

`09_ACCEPTANCE_TESTS.md`

Si cambia información esencial:

`MEMORY.md`

---

# 25. GESTIÓN DE CONTEXTO

Si tu ventana de contexto empieza a llenarse:

NO abandones el trabajo sin registrar estado.

Antes de terminar una sesión:

- guardar cambios;
- ejecutar pruebas;
- actualizar CURRENT_STATE;
- actualizar MEMORY;
- actualizar WORKLOG;
- dejar escrita la siguiente tarea exacta.

La siguiente IA debe poder continuar.

---

# 26. GIT

Si Git no existe:

evalúa crear repositorio.

Antes de grandes cambios:

haz commit/checkpoint si es seguro.

Usa commits lógicos:

- feat(web): base templates
- feat(web): prestatarios CRUD
- feat(web): modules CRUD
- feat(web): reservations
- feat(web): loans
- feat(web): responsive UI
- test(web): integration tests
- docs: update project documentation

No borrar historial ni hacer operaciones destructivas sin necesidad.

---

# 27. DATOS

Nunca ejecutar scripts destructivos sobre la BD real durante pruebas de reconstrucción.

Usar:

- BD temporal;
- copia;
- fixture;
- archivo temporal.

Antes de migraciones:

hacer backup si corresponde.

---

# 28. REGLA DE AUTONOMÍA

Puedes trabajar durante horas.

Si encuentras un bug:

**diagnostica -> corrige -> prueba -> continúa.**

Si encuentras una tarea relacionada necesaria:

**hazla -> documenta -> continúa.**

Si falta una pieza técnica obvia:

**créala -> prueba -> continúa.**

No esperar confirmación del usuario para trabajo normal.

---

# 29. CUÁNDO SÍ PUEDES DETENERTE

Solo detenerte si:

1. falta una credencial real;
2. falta información académica cuya interpretación cambia significativamente el proyecto;
3. existe peligro de perder datos;
4. existe conflicto real entre requisitos;
5. la máquina impide continuar.

Aun así:

- no dejes el proyecto roto;
- documenta;
- registra la pregunta;
- indica exactamente dónde continuar.

---

# 30. RÚBRICA FINAL

Antes de declarar terminado:

### 35% CRUD

- [ ] crear;
- [ ] leer;
- [ ] editar;
- [ ] eliminar;
- [ ] confirmación.

### 20% BD

- [ ] SQLite3;
- [ ] schema.sql;
- [ ] relaciones;
- [ ] SQL parametrizado;
- [ ] >=3 registros prueba.

### 15% HTML/CSS

- [ ] HTML5;
- [ ] CSS3;
- [ ] responsive;
- [ ] UX.

### 15% JavaScript

- [ ] Vanilla JS;
- [ ] confirmación;
- [ ] validación;
- [ ] DOM/interactividad.

### 15% buenas prácticas

- [ ] modularidad;
- [ ] POO;
- [ ] seguridad;
- [ ] documentación;
- [ ] README.

---

# 31. PRUEBA FINAL DE EXPOSICIÓN

Simula al profesor.

Desde cero:

1. iniciar aplicación;
2. abrir navegador;
3. login;
4. dashboard;
5. crear prestatario;
6. listar;
7. editar;
8. eliminar;
9. confirmar eliminación;
10. crear categoría;
11. crear laboratorio;
12. crear equipo;
13. crear reserva;
14. provocar solapamiento;
15. demostrar rechazo;
16. registrar préstamo;
17. demostrar equipo PRESTADO;
18. devolver;
19. demostrar DISPONIBLE;
20. mostrar historial;
21. demostrar rol OPERADOR;
22. demostrar restricción administrativa;
23. mostrar schema.sql;
24. mostrar README;
25. ejecutar pruebas.

---

# 32. CRITERIO DE TERMINACIÓN ABSOLUTO

NO declares:

"Proyecto terminado"

hasta comprobar:

- aplicación web funcional;
- CRUD;
- SQLite;
- schema.sql;
- 3 registros prueba;
- login;
- roles;
- permisos;
- validaciones;
- reservas;
- conflictos;
- préstamos;
- devoluciones;
- historial;
- JavaScript;
- CSS responsive;
- README;
- pruebas;
- regresión;
- flujo de exposición.

Si algo queda pendiente, dilo y continúa si puedes.

---

# 33. ORDEN DE EJECUCIÓN

Comienza exactamente así:

### BLOQUE 1
Auditoría real.

### BLOQUE 2
schema.sql.

### BLOQUE 3
Blueprint web + base.html + login/logout.

### BLOQUE 4
Prestatarios CRUD.

### BLOQUE 5
Categorías/Laboratorios/Equipos/Usuarios.

### BLOQUE 6
Reservas.

### BLOQUE 7
Préstamos/devoluciones.

### BLOQUE 8
Historial.

### BLOQUE 9
JavaScript.

### BLOQUE 10
CSS responsive/UX.

### BLOQUE 11
README.

### BLOQUE 12
Pruebas web + regresión.

### BLOQUE 13
Revisión completa de rúbrica.

### BLOQUE 14
Preparación de exposición.

---

# 34. INSTRUCCIÓN FINAL

**Trabaja de forma autónoma hasta que todos los hitos posibles estén completados.**

No conviertas la sesión en una conversación de preguntas y respuestas.

No esperes instrucciones para cada archivo.

No rehagas trabajo validado.

No inventes requisitos.

No sacrifiques seguridad para avanzar.

No sacrifiques pruebas para declarar progreso.

No sacrifiques la rúbrica por extras.

**Implementa → prueba → corrige → documenta → continúa.**

Cuando un hito pase, continúa automáticamente con el siguiente.

Tu objetivo es dejar TechLoan en el estado de **entrega académica web completa y lista para exposición**, no simplemente dejar algunos archivos creados.

---
