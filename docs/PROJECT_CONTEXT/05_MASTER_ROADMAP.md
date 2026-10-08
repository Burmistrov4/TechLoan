# 05 — PLAN MAESTRO DETALLADO

## Misión

Transformar el TechLoan existente en una aplicación web académica que cumpla literalmente el PDF del profesor, reutilizando el backend ya construido.

## FASE W0 — Auditoría antes de tocar

- [ ] Leer todos los documentos de `docs/PROJECT_CONTEXT`.
- [ ] Inspeccionar estructura real.
- [ ] Ejecutar compilación Python.
- [ ] Ejecutar regresión de pruebas backend.
- [ ] Revisar esquema real SQLite.
- [ ] Confirmar si existe `schema.sql`.
- [ ] Confirmar endpoints actuales.
- [ ] No modificar reglas de negocio durante esta fase.

**Salida:** diagnóstico breve y lista de discrepancias.

## FASE W1 — Capa web mínima

- [ ] Crear `templates/`.
- [ ] Crear `static/css/`.
- [ ] Crear `static/js/`.
- [ ] Crear blueprint de rutas web.
- [ ] Registrar blueprint.
- [ ] Crear `base.html`.
- [ ] Crear página de inicio.
- [ ] Crear navegación.
- [ ] Crear manejo de flash messages.
- [ ] Crear login web.
- [ ] Crear logout web.
- [ ] Conectar sesión Flask existente.
- [ ] Verificar permisos.

**Criterio:** navegador abre la aplicación y permite iniciar/cerrar sesión.

## FASE W2 — CRUD web académico mínimo

Implementar primero el CRUD que más claramente demuestra la rúbrica: **Prestatarios**.

### Crear

- formulario HTML;
- `required`;
- tipos correctos;
- validación server-side;
- servicio existente;
- redirección/mensaje.

### Leer

- tabla o cards;
- mensaje cuando no hay registros;
- datos legibles;
- navegación.

### Actualizar

- cargar registro;
- formulario precargado;
- validar;
- guardar;
- mensaje.

### Eliminar

- POST;
- permiso;
- servicio;
- confirmación JS obligatoria;
- mensaje.

**Criterio:** CRUD completo sin errores 500.

## FASE W3 — CRUD web completo del dominio

Después de cerrar Prestatarios:

- [ ] Categorías.
- [ ] Laboratorios.
- [ ] Equipos.
- [ ] Usuarios.

Para cada módulo:

1. listado;
2. crear;
3. editar;
4. eliminar;
5. validación;
6. permisos;
7. mensajes;
8. responsive;
9. manejo de errores;
10. prueba HTTP.

## FASE W4 — Operaciones de negocio

### Reservas

- [ ] crear reserva;
- [ ] elegir laboratorio;
- [ ] elegir prestatario;
- [ ] fecha;
- [ ] hora;
- [ ] duración;
- [ ] observaciones;
- [ ] mostrar hora final;
- [ ] rechazar solapamientos;
- [ ] mostrar error amigable;
- [ ] listar reservas.

### Préstamos

- [ ] seleccionar equipo disponible;
- [ ] seleccionar prestatario;
- [ ] registrar;
- [ ] estado PRESTADO;
- [ ] listar;
- [ ] devolver;
- [ ] confirmar devolución;
- [ ] estado DISPONIBLE.

### Historial

- [ ] filtros existentes;
- [ ] tabla responsive;
- [ ] mensajes vacíos.

## FASE W5 — JavaScript

Debe existir evidencia visible de JavaScript real.

- [ ] confirmación de eliminación;
- [ ] confirmación de devolución;
- [ ] validación cliente;
- [ ] feedback visual;
- [ ] manipulación DOM;
- [ ] fetch donde aporte valor.

No usar JS para reemplazar validación del servidor.

## FASE W6 — CSS/UX

- [ ] diseño consistente;
- [ ] navbar;
- [ ] formularios;
- [ ] botones;
- [ ] tablas/cards;
- [ ] mensajes;
- [ ] estados;
- [ ] navegación;
- [ ] responsive móvil;
- [ ] responsive tablet;
- [ ] escritorio;
- [ ] accesibilidad básica;
- [ ] labels asociados a inputs;
- [ ] focus visible;
- [ ] contraste razonable.

## FASE W7 — Base de datos académica

Crear/verificar `schema.sql`.

Debe:

- crear tablas necesarias;
- respetar claves;
- respetar relaciones;
- incluir datos iniciales;
- incluir al menos 3 registros de prueba;
- permitir reconstruir la BD desde cero.

Idealmente:

`DROP TABLE IF EXISTS`

en orden seguro o estrategia equivalente.

No destruir la BD real sin backup durante pruebas.

## FASE W8 — README

Actualizar README para el nuevo stack.

Debe explicar:

- qué es TechLoan;
- problema;
- stack;
- estructura;
- instalación;
- creación de entorno;
- `pip install -r requirements.txt`;
- inicialización de BD;
- ejecución;
- URL local;
- usuarios de prueba si corresponde;
- funcionalidades;
- seguridad;
- CRUD;
- JavaScript;
- responsive.

## FASE W9 — Pruebas

### Backend

- [ ] compileall.
- [ ] CRUD.
- [ ] validaciones.
- [ ] seguridad.
- [ ] roles.
- [ ] solapamientos.
- [ ] historial.

### Web

- [ ] health.
- [ ] login correcto.
- [ ] login incorrecto.
- [ ] logout.
- [ ] acceso sin sesión.
- [ ] CRUD crear.
- [ ] CRUD leer.
- [ ] CRUD editar.
- [ ] CRUD eliminar.
- [ ] confirmación JS.
- [ ] permisos.
- [ ] errores 4xx.
- [ ] ausencia de errores 500.

### Manual

- [ ] móvil.
- [ ] tablet.
- [ ] escritorio.
- [ ] flujo completo.

## FASE W10 — Preparación para exposición

Flujo recomendado:

1. Abrir navegador.
2. Mostrar login.
3. Iniciar como ADMINISTRADOR.
4. Mostrar dashboard.
5. Crear prestatario.
6. Editarlo.
7. Mostrarlo.
8. Eliminarlo con confirmación JS.
9. Crear/mostrar laboratorio.
10. Crear equipo.
11. Crear reserva.
12. Intentar reserva solapada y mostrar rechazo.
13. Registrar préstamo.
14. Devolver equipo.
15. Mostrar historial.
16. Mostrar seguridad/roles brevemente.
17. Mostrar estructura del proyecto.
18. Mostrar `schema.sql`.
19. Mostrar README.

## Regla de priorización

Si el agente tiene horas disponibles:

**Primero completar la rúbrica.**

Orden:

`CRUD > BD/schema > HTML/CSS > JS > buenas prácticas > extras`

No gastar horas en animaciones, 3D, arquitectura innecesaria o refactorizaciones estéticas antes de cerrar la rúbrica.

## Definition of Done

El proyecto solo se considera terminado cuando:

- la web funciona localmente;
- CRUD funciona;
- no hay errores 500 en flujo normal;
- SQLite se puede reconstruir;
- schema.sql existe;
- hay al menos 3 registros de prueba;
- JavaScript confirma eliminaciones;
- CSS es responsive;
- README permite ejecutar el proyecto;
- backend existente sigue pasando pruebas;
- roles/permisos funcionan;
- las reglas de negocio siguen funcionando.
