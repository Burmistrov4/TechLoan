# Demostración de seguridad (guion para la defensa)

Este documento explica cómo mostrar, **en un minuto y en vivo**, las tres cosas
que un jurado suele pedir en este tipo de proyectos:

1. que las **contraseñas se guardan como hash** (no en texto plano),
2. que las **validaciones** se ejecutan en el servidor,
3. que las **inyecciones SQL** no funcionan.

Todo está reunido en un único script que **no modifica la base de datos**.

---

## 1. Ejecutar la demostración

```bash
python demostrar_seguridad.py
```

El script imprime tres bloques. Nada de lo que hace escribe en la base de datos:
solo lee y ejecuta intentos que el propio sistema rechaza.

---

## 2. Qué muestra cada bloque

### Bloque 1 — Las contraseñas se guardan como hash

- Lee la tabla `usuarios_sistema` y muestra la columna **`password_hash`**.
- El valor empieza por `scrypt:32768:8:1$…`: es un **hash scrypt** con sal
  aleatoria, generado por Werkzeug.
- Comprueba que la **longitud es 162 caracteres**, dentro de la columna
  **`VARCHAR(255)`**.
- Comprueba que **ninguna contraseña aparece en claro** en la columna.
- Genera un hash de ejemplo y demuestra que `check_password_hash()` **solo
  valida la contraseña correcta** y devuelve `False` con cualquier otra.

**Frase para el jurado:** *«La columna se llama `password_hash`, es
`VARCHAR(255)` y guarda un hash scrypt con sal. Del hash no se puede recuperar la
contraseña; solo se puede comprobar si coincide con la que escribe el usuario.»*

### Bloque 2 — Validaciones del servidor

Envía datos inválidos a los servicios y muestra el mensaje de rechazo:

- cédula con formato inválido, nombre con números, tipo inexistente,
- contraseñas débiles (corta, sin mayúscula, sin símbolo),
- correo mal formado,
- capacidad de laboratorio igual a cero.

**Frase para el jurado:** *«La validación del navegador es una comodidad; la que
manda es la del servidor, en `app/services/`. Aunque alguien salte el HTML y
envíe el formulario a mano, el sistema lo rechaza igual.»*

### Bloque 3 — Inyección SQL

Intenta entrar con cargas clásicas de inyección:

```
admin' OR '1'='1
admin'--
' OR 1=1 --
admin'; DROP TABLE usuarios_sistema; --
```

Todas son **rechazadas**. Además:

- comprueba que la tabla `usuarios_sistema` **sigue intacta** (el `DROP` no se
  ejecutó),
- explica la diferencia con una concatenación ingenua,
- recorre el código fuente y confirma que **ninguna consulta interpola entrada
  del usuario** (todas usan marcadores `?`).

**Frase para el jurado:** *«Todas las consultas van parametrizadas con `?`; la
entrada se trata como dato, nunca como código. Por eso la inyección no tiene
efecto.»*

---

## 3. Demostración manual (por si prefieren ver la base de datos)

1. Abre `database/techloan.db` con **DB Browser for SQLite**
   (ver `docs/GUIA_BASE_DE_DATOS.md`).
2. Pestaña **Datos** → tabla `usuarios_sistema`.
3. Señala la columna **`password_hash`**: valores largos que empiezan por
   `scrypt:…`, longitud 162, en una columna `VARCHAR(255)`.
4. Contrasta con la columna **`username`**: ahí sí está el nombre de usuario, pero
   **nunca la contraseña**.

---

## 4. Dónde está cada defensa en el código

| Defensa | Archivo |
|---|---|
| Hash de contraseñas (scrypt) | `app/services/usuario_service.py`, `app/services/registro_service.py` |
| Verificación de contraseñas | `app/services/auth_service.py` |
| Columna `VARCHAR(255)` | `schema.sql` (`usuarios_sistema.password_hash`) |
| Validaciones de servidor | `app/services/*.py` (función `_validate` de cada servicio) |
| Consultas parametrizadas | todas las llamadas `db.execute("… ? …", (valor,))` |
| Permisos por rol | `app/services/auth_service.py` (`can`) |
| CSRF en formularios | `app/routes/web_common.py` |
| Aviso de hash en pruebas | `tests/smoke_test.py` (`assert fila["password_hash"].startswith("scrypt:")`) |

---

## 5. Preguntas previsibles y respuesta corta

- **¿Se puede descifrar el hash?** No. scrypt es una función de un solo sentido;
  se compara, no se descifra.
- **¿Por qué 255 y no 256?** 255 es el largo clásico de `VARCHAR` en MySQL/SQLite
  para cadenas cortas; el hash ocupa 162, así que sobra espacio. El valor se
  declara en `schema.sql` y el tope se controla con `PASSWORD_HASH_MAX_LENGTH`.
- **¿Y si dos usuarios eligen la misma contraseña?** Los hashes son distintos
  porque cada uno lleva una **sal** aleatoria.
- **¿La validación del HTML no basta?** No: se puede saltar. Por eso se repite en
  el servidor.
- **¿SQLite aguanta producción?** Para este proyecto sí (un centro de formación);
  el código está aislado en `app/database.py`, así que migrar a otro motor es
  cambiar esa capa, no toda la aplicación.
