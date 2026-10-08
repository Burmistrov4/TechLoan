# 10 — HANDOFF / CONTEXT RECOVERY PROTOCOL

## Propósito

Este proyecto está diseñado para que un agente de IA pueda continuar el trabajo incluso después de perder la conversación anterior.

## Orden de recuperación

Si eres un agente nuevo:

1. Lee `START_HERE_FOR_AGENT.md`.
2. Lee `MEMORY.md`.
3. Lee `02_CURRENT_STATE.md`.
4. Lee `05_MASTER_ROADMAP.md`.
5. Lee `09_ACCEPTANCE_TESTS.md`.
6. Solo después inspecciona código.

## Regla de verdad

Los archivos de contexto NO sustituyen la inspección del código.

Si un documento dice que algo está terminado pero el código demuestra lo contrario:

**el código + pruebas actuales son la fuente de verdad técnica.**

Actualiza el documento después.

## Al terminar cada bloque

Actualizar:

- `02_CURRENT_STATE.md`
- `MEMORY.md` si cambió información esencial
- `08_OPEN_QUESTIONS.md`
- `09_ACCEPTANCE_TESTS.md`
- `07_DECISIONS.md` si hubo una nueva decisión.

## Registro de trabajo

Crear/mantener:

`docs/PROJECT_CONTEXT/WORKLOG.md`

Cada entrada debe incluir:

- fecha/hora;
- agente;
- tarea;
- archivos modificados;
- pruebas ejecutadas;
- resultado;
- siguiente tarea;
- riesgos pendientes.

No escribir diarios interminables: solo información útil para recuperación.

## Si se agota el contexto

Antes de continuar en una nueva sesión:

1. guardar estado;
2. actualizar MEMORY;
3. actualizar CURRENT_STATE;
4. registrar siguiente acción exacta en WORKLOG.

## Si una tarea falla

No marcarla como completada.

Registrar:

- síntoma;
- causa probable;
- causa confirmada si se conoce;
- intento realizado;
- resultado;
- próximo experimento.

## Si el agente necesita tomar una decisión

Aplicar esta jerarquía:

1. PDF/rúbrica del profesor.
2. requisitos de este proyecto.
3. decisiones documentadas.
4. código y pruebas existentes.
5. solución simple y mantenible.

## Objetivo

La siguiente IA debe poder continuar el proyecto con la menor cantidad posible de preguntas al usuario.
