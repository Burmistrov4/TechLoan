# 01 — CONTEXTO DEL PROYECTO

## Nombre

**TechLoan — Sistema Web de Gestión de Reservas y Préstamos de Recursos Tecnológicos**

## Objetivo académico

Proyecto final de Programación III. Debe demostrar:

- Python.
- Flask.
- SQLite3.
- CRUD completo.
- HTML5 semántico.
- CSS3 responsive.
- JavaScript Vanilla.
- Validación cliente/servidor.
- Consultas SQL parametrizadas.
- Código organizado, modular, limpio y documentado.
- Aplicación ejecutable localmente sin infraestructura externa obligatoria.

## Caso de estudio

TechLoan gestiona:

- usuarios del sistema;
- prestatarios;
- categorías;
- laboratorios;
- equipos;
- reservas de laboratorios;
- préstamos individuales de equipos;
- devoluciones;
- disponibilidad;
- historial.

Los **usuarios del sistema** son ADMINISTRADOR u OPERADOR y tienen credenciales.

Los **prestatarios** representan a las personas que reciben una reserva/préstamo y no necesitan una cuenta del sistema.

## Regla académica crítica

El documento del profesor se denomina:

`Proyecto Práctico  Sistema Web CRUD con Flask y SQLite3.pdf`

El PDF define explícitamente una **aplicación web**, no una aplicación Tkinter.

Por tanto, la interfaz final debe ser web y debe contener como mínimo:

- `templates/`
- `static/css/`
- `static/js/`
- Flask routes.
- SQLite3.
- formularios.
- tabla/cards de registros.
- editar.
- eliminar con confirmación JavaScript.

## Qué conservar

El backend existente tiene bastante trabajo útil:

- modelos POO;
- servicios;
- conexión SQLite;
- Flask;
- autenticación;
- hash de contraseñas;
- roles;
- permisos;
- validaciones;
- reservas;
- detección de solapamientos;
- préstamos;
- devoluciones;
- disponibilidad;
- historial;
- pruebas automatizadas.

## Qué cambiar

La capa de presentación debe migrar de:

`Tkinter -> servicios`

a:

`Browser -> Flask/Jinja2/JS -> servicios -> SQLite`

La API JSON existente puede mantenerse y aprovecharse donde sea útil, pero no debe impedir una navegación web tradicional con Jinja2 si el requisito académico espera rutas como `/`, `/crear`, `/editar/<id>`, `/eliminar/<id>`.

## Prioridad

1. Cumplimiento literal del PDF.
2. Funcionamiento correcto.
3. CRUD demostrable.
4. Seguridad.
5. Responsive/UX.
6. Calidad arquitectónica.
7. Extras solamente después de cumplir la rúbrica.

## No hacer

- No introducir React/Vue/Angular.
- No introducir una base de datos externa.
- No introducir un framework CSS pesado sin necesidad.
- No sustituir SQLite.
- No reescribir todo el backend solo por estética.
- No eliminar las pruebas existentes sin reemplazarlas.
- No afirmar que una funcionalidad está terminada sin evidencia.
