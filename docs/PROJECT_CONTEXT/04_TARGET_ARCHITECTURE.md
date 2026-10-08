# 04 — ARQUITECTURA OBJETIVO

## Principio

La aplicación final será una **web Flask server-rendered**, con JavaScript Vanilla para interactividad.

## Flujo

```
Navegador
   |
   | HTTP
   v
Flask / rutas web
   |
   +--> Jinja2 templates
   |
   +--> servicios POO existentes
            |
            v
        SQLite3
```

JavaScript podrá consumir endpoints JSON mediante `fetch()` cuando aporte valor.

## Estructura objetivo

```
Proyecto Final de Python/
├── app/
│   ├── models/
│   ├── services/
│   ├── routes/
│   ├── security/
│   ├── gui/                 # legado/prototipo, no prioridad
│   ├── server.py
│   └── database.py
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── auth/
│   ├── prestatarios/
│   ├── equipos/
│   ├── laboratorios/
│   ├── categorias/
│   ├── reservas/
│   ├── prestamos/
│   ├── historial/
│   └── usuarios/
├── static/
│   ├── css/
│   │   └── estilos.css
│   └── js/
│       ├── main.js
│       ├── confirmaciones.js
│       └── ...
├── database/
│   └── techloan.db
├── schema.sql
├── tests/
└── docs/
```

## Rutas web recomendadas

No modificar los endpoints API existentes sin necesidad.

Añadir un blueprint web separado, por ejemplo:

- `/`
- `/login`
- `/logout`
- `/prestatarios`
- `/prestatarios/crear`
- `/prestatarios/<id>/editar`
- `/prestatarios/<id>/eliminar`
- `/equipos`
- `/laboratorios`
- `/categorias`
- `/reservas`
- `/prestamos`
- `/historial`
- `/usuarios` si el alcance permite cerrar el CRUD.

## Seguridad web

Las rutas web deben:

- exigir sesión cuando corresponda;
- comprobar permisos;
- usar servicios existentes;
- no concatenar SQL;
- no aceptar `usuario_sistema_id` desde el navegador para decidir quién ejecutó una operación;
- usar el usuario de sesión;
- validar servidor aunque exista validación HTML;
- usar POST para acciones destructivas;
- confirmar eliminación mediante JavaScript;
- manejar errores sin mostrar trazas internas al usuario.

## Templates

`base.html` debe contener:

- `<!doctype html>`;
- idioma;
- viewport;
- navegación;
- mensajes flash;
- bloque de contenido;
- CSS;
- JS.

Cada módulo debe extender `base.html`.

## Responsive

Prioridad mínima:

- celular ~375px;
- tablet ~768px;
- escritorio ~1280px.

No hacer una interfaz basada exclusivamente en tablas rígidas.

## JavaScript

Debe demostrar explícitamente:

- confirmación de eliminación;
- manipulación DOM;
- validaciones útiles del cliente;
- mensajes/interacciones;
- opcionalmente fetch para operaciones seleccionadas.

## CSS

Preferir CSS propio.

No introducir Bootstrap/Tailwind salvo que el profesor lo permita y exista una razón concreta.

## API existente

Los endpoints `/api/...` son útiles para pruebas, integraciones y fetch.

No es obligatorio reemplazarlos por completo.

## Tkinter

No debe bloquear el desarrollo web.

Conservarlo mientras sea útil para comparar reglas y servicios. La decisión final sobre su permanencia se toma después de tener una web funcional.
