# TECHLOAN — CONTEXTO DE PROYECTO PARA IA

> Documento de navegación para agentes de IA y futuras sesiones.
> Última actualización: 2026-10-08.
> **Fuente de requisitos académicos actual:** `Proyecto Práctico  Sistema Web CRUD con Flask y SQLite3.pdf`.

## Lectura obligatoria antes de modificar código

1. `01_PROJECT_CONTEXT.md` — propósito, caso de estudio y decisiones.
2. `02_CURRENT_STATE.md` — estado real implementado y evidencias.
3. `03_PDF_REQUIREMENTS.md` — requisitos del profesor y diferencias con el plan anterior.
4. `04_TARGET_ARCHITECTURE.md` — arquitectura objetivo web.
5. `05_MASTER_ROADMAP.md` — plan maestro ejecutable.
6. `06_AGENT_EXECUTION.md` — instrucciones para trabajar autónomamente.
7. `07_DECISIONS.md` — decisiones que NO deben revertirse sin justificación.
8. `08_OPEN_QUESTIONS.md` — dudas pendientes y riesgos.
9. `09_ACCEPTANCE_TESTS.md` — criterios para considerar terminado.
10. `MEMORY.md` — memoria compacta para recuperación de contexto.

## Regla principal

**No rehacer el backend desde cero.** El núcleo Flask + SQLite + servicios POO + validaciones + seguridad + reglas de reservas/préstamos ya construidos deben reutilizarse.

El cambio principal es de **presentación/entrega**:

- Antes: Tkinter como interfaz principal + Flask como API local.
- Ahora: **Flask + Jinja2 + HTML5 + CSS3 + JavaScript Vanilla** como aplicación web principal.
- SQLite3 permanece.
- Tkinter puede conservarse como prototipo/artefacto previo, pero no debe ser el centro de la entrega final si entra en conflicto con el PDF.

## Estado de lectura

El PDF tiene 4 páginas y fue leído directamente desde el archivo local del proyecto.
