# START HERE — AGENTE DE IA

## Misión

Completar la transición de TechLoan desde una interfaz Tkinter previa hacia la **aplicación web exigida por el PDF del profesor**.

## Antes de trabajar

Lee obligatoriamente:

1. `00_INDEX.md`
2. `01_PROJECT_CONTEXT.md`
3. `02_CURRENT_STATE.md`
4. `03_PDF_REQUIREMENTS.md`
5. `04_TARGET_ARCHITECTURE.md`
6. `05_MASTER_ROADMAP.md`
7. `06_AGENT_EXECUTION.md`
8. `07_DECISIONS.md`
9. `08_OPEN_QUESTIONS.md`
10. `09_ACCEPTANCE_TESTS.md`
11. `MEMORY.md`

## Primera acción técnica

Auditar el estado real antes de editar.

Ejecutar:

- compileall;
- pruebas backend;
- inspección de SQLite;
- inspección de rutas;
- comprobación de `schema.sql`;
- comprobación de git.

## Trabajo prioritario

### Bloque A
Construir la infraestructura web:

- blueprint web;
- templates;
- base.html;
- login;
- logout;
- navegación;
- mensajes.

### Bloque B
Cerrar CRUD web de Prestatarios.

### Bloque C
Cerrar CRUD web de Categorías, Laboratorios, Equipos y Usuarios.

### Bloque D
Cerrar Reservas, Préstamos, Devoluciones e Historial.

### Bloque E
Responsive + JavaScript.

### Bloque F
schema.sql + README + pruebas + exposición.

## Condición de parada

No detenerse simplemente porque el backend ya funciona.

El backend ya está avanzado.

La tarea pendiente importante es **la entrega web**.

## Regla de seguridad

No modificar una regla de negocio validada sin ejecutar regresión.

## Regla de autonomía

Si una decisión menor no está definida:

1. elegir la solución más sencilla;
2. compatible con Flask/Jinja2/SQLite;
3. coherente con el PDF;
4. documentar la decisión;
5. continuar.

Solo detenerse ante una decisión que pueda cambiar sustancialmente el alcance académico.
