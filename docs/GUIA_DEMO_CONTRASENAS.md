# Guía rápida — Demostrar en vivo que las contraseñas NO se guardan en texto plano

Para la defensa, si el profesor pide ver cómo se almacenan las contraseñas.
Todo se hace en **local**, sin depender de internet.

> **Idea clave para decir en voz alta:** no se puede “ver” la contraseña original,
> y eso es correcto: se guarda un **hash scrypt irreversible con salt aleatorio**.
> Lo que sí se demuestra es (1) que en la base no hay texto plano, (2) que el hash
> cambia cada vez y (3) que el sistema valida la contraseña comparando hashes.

---

## 0. Preparar el entorno (una vez)

```bash
.venv/Scripts/python.exe iniciar_servidor.py
```

- Abre el navegador en `http://127.0.0.1:5000`.
- Inicia sesión como **admin** (usuario `admin`, contraseña `Admin123!`).
- Entra por el menú **Administración → Visor SQLite3**
  (o directo: `http://127.0.0.1:5000/sistema/visor-sqlite`).

> El Visor solo lo ve el **administrador** (permiso `sistema.inspector`).

---

## 1. Ver los hashes guardados (2 clics)

1. Pestaña **«Hash de contraseñas»**.
2. Señala las columnas de la tabla `usuarios_sistema`:
   - **Algoritmo:** `scrypt`
   - **Parámetros:** `32768:8:1`
   - **Salt:** valor aleatorio por usuario
   - **Hash:** el resultado irreversible

**Qué decir:** «Aquí no hay ninguna columna con la contraseña; solo el hash y su
salt. No existe forma de “desencriptarla”, porque un hash no es reversible.»

---

## 2. Prueba “en caliente” del salt (lo más convincente)

1. Baja a **«Probador de hash»**.
2. Escribe una contraseña, por ejemplo `Clave123!`, y pulsa **«Generar hash»**.
3. Pulsa **«Generar hash»** otra vez con el **mismo** texto.

**Resultado:** salen **dos hashes distintos**.

**Qué decir:** «La misma contraseña produce hashes diferentes cada vez gracias al
salt aleatorio. Por eso dos usuarios con la misma clave tendrían hashes distintos,
y desde la base no se puede adivinar la contraseña.»

---

## 3. Registro en caliente (opcional, muy visual)

1. Como admin: **Administración → Usuarios → Nuevo usuario** (o «Crear cuenta»).
2. Crea un usuario con una contraseña reconocible (p. ej. `Prueba2026!`).
3. Vuelve al **Visor → Hash de contraseñas** y recarga la pestaña (clic en
   «Explorador de tablas» y de nuevo en «Hash de contraseñas»).

**Resultado:** la fila nueva muestra `scrypt:…`, **nunca** lo que se tecleó.

**Qué decir:** «Acabo de registrar esta cuenta; en la base solo quedó el hash.»

---

## 4. Explorador de tablas (si pregunta “¿y si hay texto plano en otro sitio?”)

1. Pestaña **«Explorador de tablas»** → tabla `usuarios_sistema`.
2. Se ve la columna `password_hash` y **no** existe ninguna columna `password`.
3. Muestra también `tokens_correo`: el **token aparece enmascarado** (seguridad).

**Qué decir:** «El visor es de solo lectura y además enmascara datos sensibles
como los tokens.»

---

## 5. Si el profesor pide “la base cruda” (terminal o DB Browser)

**Opción A — DB Browser for SQLite (gratis, visual):**
abrir `database/techloan.db` → tabla `usuarios_sistema` → columna `password_hash`.
Se ve `scrypt:32768:8:1$…`.

**Opción B — script del proyecto (sin tocar la BD):**

```bash
.venv/Scripts/python.exe demostrar_seguridad.py
```

Hace la demostración de hash scrypt, validaciones e inyección SQL en ~1 minuto.
Guion ampliado en `docs/DEMOSTRACION_SEGURIDAD.md`.

---

## 6. Frases de cierre (guion de 20 segundos)

- «La contraseña **nunca** se guarda: se guarda un **hash scrypt con salt**.»
- «Es **irreversible**: no se puede desencriptar, solo comparar.»
- «El **salt** hace que la misma clave genere hashes distintos.»
- «Al iniciar sesión, el sistema hashea lo que escribes y lo compara con el hash
  guardado; si coincide, entra.»

---

## Nota de seguridad para la exposición

- No publiques capturas con hashes reales de usuarios reales (aunque sean hashes,
  es buena práctica).
- El Visor es **solo para administradores** y es de **solo lectura**.
- En producción (`lorodev.pythonanywhere.com`) el Visor ya está disponible tras el
  último despliegue, en **Administración → Visor SQLite3**.
