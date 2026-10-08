# 06 — INSTRUCCIONES PARA AGENTE AUTÓNOMO

## Objetivo

Puedes trabajar durante varias horas sin preguntar constantemente al usuario, siempre que respetes este documento y verifiques cada cambio.

## Protocolo obligatorio

### Antes de editar

1. Leer `00_INDEX.md`.
2. Leer `01_PROJECT_CONTEXT.md`.
3. Leer `02_CURRENT_STATE.md`.
4. Leer `03_PDF_REQUIREMENTS.md`.
5. Leer `04_TARGET_ARCHITECTURE.md`.
6. Leer `05_MASTER_ROADMAP.md`.
7. Revisar git/status si existe.
8. Inspeccionar archivos reales antes de asumir su contenido.

### Durante cada tarea

1. Hacer un cambio pequeño y coherente.
2. Ejecutar prueba relacionada.
3. Corregir errores.
4. Ejecutar regresión cuando el cambio pueda afectar backend.
5. Actualizar documentación de estado.
6. Marcar la tarea terminada solo con evidencia.

## Política de autonomía

El agente puede:

- crear templates;
- crear CSS;
- crear JS;
- crear rutas web;
- adaptar README;
- crear schema.sql;
- crear tests;
- refactorizar si es necesario;
- corregir bugs.

Debe evitar:

- cambiar el dominio sin razón;
- borrar funcionalidades ya probadas;
- cambiar permisos arbitrariamente;
- cambiar el stack exigido;
- instalar dependencias innecesarias;
- introducir frameworks frontend;
- reemplazar SQLite.

## Política de seguridad

Nunca:

- concatenar entrada del usuario en SQL;
- guardar contraseñas en texto plano;
- confiar en IDs de operador enviados desde HTML;
- permitir que un formulario público cree ADMINISTRADORES;
- mostrar password_hash;
- exponer secretos en templates;
- desactivar controles solo para hacer pasar una prueba.

## Política de pruebas

Cada cambio funcional debe tener:

- prueba automatizada o;
- prueba HTTP/manual documentada.

Si una prueba falla:

1. determinar si el fallo es del código o de la prueba;
2. corregir la causa;
3. volver a ejecutar;
4. no ocultar el fallo.

## Política de documentación

Actualizar cuando corresponda:

- `02_CURRENT_STATE.md`;
- `07_DECISIONS.md`;
- `08_OPEN_QUESTIONS.md`;
- `09_ACCEPTANCE_TESTS.md`;
- `MEMORY.md`.

## Política de commits

Si git está configurado:

hacer commits lógicos, por ejemplo:

- `feat(web): add base templates`
- `feat(web): add prestatarios CRUD`
- `feat(web): add responsive styles`
- `test(web): add CRUD integration tests`

No hacer commits gigantes sin sentido.

## Si queda tiempo

Después de cerrar la rúbrica:

- mejorar UX;
- accesibilidad;
- errores;
- responsive;
- limpieza;
- documentación;
- pruebas adicionales.

No hacer trabajo ornamental antes del núcleo.
