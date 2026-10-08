# 03 — ANÁLISIS DEL PDF DEL PROFESOR

## Fuente

`Proyecto Práctico  Sistema Web CRUD con Flask y SQLite3.pdf`

Documento de 4 páginas, leído localmente.

## Requisitos explícitos

### Backend

- Flask como micro-framework.
- Python.
- SQLite3.
- librería nativa `sqlite3`.
- consultas parametrizadas.
- conexiones adecuadamente gestionadas.
- rutas HTTP limpias.
- GET y POST como mínimo.
- ejemplo de rutas: `/`, `/crear`, `/editar/<id>`, `/eliminar/<id>`.

### Frontend

El cambio más importante:

- HTML5.
- CSS3.
- JavaScript Vanilla.
- HTML semántico.
- formularios con validación cliente.
- diseño responsive.
- interfaz limpia e intuitiva.
- manipulación DOM.
- confirmación JavaScript antes de eliminar.
- fetch es opcional/recomendado.

### CRUD

Debe demostrarse:

1. Crear.
2. Leer/visualizar.
3. Actualizar/editar.
4. Eliminar.
5. Confirmación antes de eliminar.

Debe existir mensaje amigable si no hay registros.

### Entregables

- código fuente completo;
- estructura limpia;
- `schema.sql`;
- al menos 3 registros de prueba en el script;
- `README.md`;
- instrucciones de instalación;
- instrucciones de inicialización;
- instrucciones de ejecución;
- descripción del problema.

## Rúbrica

| Criterio | Peso |
|---|---:|
| Funcionamiento CRUD | 35% |
| Modelado y conexión BD | 20% |
| Interfaz y UX HTML/CSS | 15% |
| Interactividad JavaScript | 15% |
| Estructura y buenas prácticas | 15% |

## Implicación para el proyecto existente

La arquitectura Tkinter original no satisface por sí sola el requisito de interfaz web.

### Decisión

No borrar Tkinter inmediatamente.

En su lugar:

1. conservar backend y servicios;
2. construir capa web;
3. validar la web;
4. actualizar documentación;
5. decidir al final si Tkinter queda como prototipo histórico o se elimina de la entrega.

## Interpretación arquitectónica recomendada

La estructura sugerida por el profesor es simple, pero no obliga a reducir el proyecto a un solo `app.py`.

Se recomienda mantener la arquitectura modular actual y añadir:

`templates/`

`static/css/`

`static/js/`

Esto cumple la intención del profesor y conserva la calidad POO ya desarrollada.

## Requisito de alcance

No convertir el proyecto en una aplicación empresarial innecesariamente compleja.

La meta es una **aplicación web académica completa, demostrable y estable**.
