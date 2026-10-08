# 11 — PROTOCOLO DE PROGRESO AUTÓNOMO

## Regla central

**No detenerse después de completar una sola tarea si existen tareas pendientes claramente definidas.**

Al terminar una tarea:

1. ejecutar pruebas;
2. corregir;
3. documentar;
4. seleccionar la siguiente tarea desbloqueada;
5. continuar.

## Bucle autónomo

```
INSPECCIONAR
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
SIGUIENTE HITO
    ↺
```

## Cuándo continuar automáticamente

Continuar si:

- la tarea actual pasa;
- la siguiente tarea tiene requisitos conocidos;
- no existe una decisión que requiera al usuario;
- el cambio es reversible;
- la solución es coherente con el PDF.

## Cuándo detenerse

Solo detenerse y documentar una pregunta cuando:

- falta un requisito académico ambiguo cuya interpretación cambia significativamente el alcance;
- existe riesgo de pérdida irreversible de datos;
- hay credenciales/secretos que el agente no debe inventar;
- dos requisitos entran en conflicto real;
- la máquina no permite continuar técnicamente.

Incluso entonces, dejar el proyecto en un estado recuperable y registrar la pregunta.

## Nunca usar como excusa

No detenerse porque:

- una tarea es larga;
- hay muchos archivos;
- hay que escribir bastante HTML;
- hay que ejecutar varias pruebas;
- una prueba falla;
- una parte necesita refactorización razonable.

Investigar, corregir y continuar.

## Evidencia

Cada hito debe tener evidencia:

- comando;
- prueba;
- resultado;
- archivo;
- o validación manual documentada.

## Calidad

No perseguir perfección prematura.

Primero funcionamiento correcto, después calidad.

## Al llegar al final

Ejecutar una revisión completa:

- requisitos PDF;
- CRUD;
- BD;
- seguridad;
- JS;
- responsive;
- pruebas;
- README;
- schema.sql;
- estructura;
- errores conocidos.

Solo entonces declarar el proyecto terminado.
