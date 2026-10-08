# Guía de exposición — TechLoan

> Documento operativo para la defensa del proyecto ante el profesor.
> Recorrido recomendado, comandos exactos, resultados esperados y plan de contingencia.

---

## 1. Lista de verificación previa (hacer la noche anterior)

- [ ] Entorno virtual creado e instalado: `pip install -r requirements.txt`
- [ ] Base de datos regenerada **el mismo día** de la exposición: `python init_db.py`
- [ ] Servidor probado: `python run_server.py` → abrir `http://127.0.0.1:5000`
- [ ] Login probado con **ambos** usuarios (`admin` y `operador`)
- [ ] Ensayado el flujo completo de la sección 3, cronometrado
- [ ] Capturas de respaldo en `docs/capturas/` (por si falla el equipo)
- [ ] Suite de pruebas ejecutada y en verde
- [ ] Tutorial guiado probado (se relanza desde el menú de usuario)
- [ ] Registro por correo probado y `database/buzon/` vacío antes de empezar

> **Importante:** ejecuta `python init_db.py` **el mismo día**. Las fechas de las reservas de
> demostración son relativas a la fecha de ejecución, así que siempre quedan en el futuro.

---

## 2. Comandos exactos

**Opción recomendada para una PC nueva:**

```text
iniciar.bat
```

No es necesario activar manualmente el entorno virtual: el lanzador portable lo crea,
instala las dependencias y levanta Flask.

**Flujo manual equivalente (si se desea mostrar el proceso al profesor):**

```bash
# 1. Crear y activar el entorno virtual solo la primera vez
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate         # Linux / macOS

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Reconstruir la base de datos desde schema.sql
python init_db.py

# 4. Arrancar el servidor
python run_server.py
```

Abrir en el navegador: **http://127.0.0.1:5000**

`init_db.py` imprime las reservas cargadas y en qué horarios conviene demostrar el
solapamiento. Anótalos: los necesitarás en el paso 12.

---

## 3. Recorrido de demostración (≈ 17–20 minutos)

### Paso 0 — Mostrar la estructura del proyecto (1 min)

Antes de arrancar, abre la carpeta y señala:

- `schema.sql` → script de creación de la base de datos.
- `init_db.py` → reconstruye la base de datos desde ese script.
- `templates/` y `static/` → HTML, CSS y JavaScript.
- `app/services/` → lógica de negocio y validaciones (POO).
- `app/gui/` → **prototipo Tkinter previo**, del que se reutilizó todo el backend.

Frase útil: *"La lógica de negocio está en servicios compartidos, así que las reglas son
únicas: las usan tanto la interfaz web como la API."*

### Paso 1 — Reconstruir la base de datos (1 min)

```bash
python init_db.py
```

Señala la salida: conteo por tabla e `integrity_check: ok`.
Frase útil: *"La base de datos se puede reconstruir desde cero con un solo comando a partir
de `schema.sql`, que incluye 21 registros de prueba."*

### Paso 2 — Arrancar el servidor y abrir la aplicación (1 min)

```bash
python run_server.py
```

Abrir `http://127.0.0.1:5000`. Aparece la **portada pública** del producto: el visitante ve
qué es TechLoan y solo desde ahí pasa al acceso. No redirige de entrada al login.

Frase útil: *"La raíz es pública: muestra la portada a quien no tiene sesión y el panel a quien
ya la tiene. Los módulos internos sí exigen sesión."*

### Paso 3 — Demostrar que las rutas están protegidas (30 s)

Con la barra de direcciones, intenta entrar directamente a `http://127.0.0.1:5000/prestatarios`.
Redirige al login con un mensaje. *"Sin sesión no se accede a ninguna ruta interna."*

### Paso 4 — Login correcto y panel (1 min)

Entra con **`admin` / `Admin123!`**.

Señala en el panel: las **6 tarjetas de indicadores** con contadores animados y los **3 gráficos
SVG** dibujados en el cliente (reservas por día, inventario por estado, ocupación por
laboratorio), más las próximas reservas y la actividad reciente.

Nada más entrar, la primera vez, **arranca solo el tutorial guiado**: 8 pasos que van
señalando el menú, la búsqueda, el tema, las alertas, el panel y la cuenta. Es la forma más
rápida de enseñar la aplicación sin explicar la interfaz a mano.

Frase útil: *"El sistema se explica solo: el recorrido se guarda por usuario y no vuelve a
aparecer, pero se puede repetir desde el menú de usuario."*

Dos detalles que lucen y son gratis de mostrar:

- Haz clic en el **botón de tema** de la cabecera → la interfaz pasa a oscuro y los gráficos se
  redibujan tomando los colores del tema. Recarga la página: **el tema elegido persiste**.
- Presiona **Ctrl+K** → se abre la **paleta de comandos**. Escribe `González`: encuentra al
  prestatario buscando en los datos reales del servidor. `Escape` la cierra.

Frase útil: *"Todo esto es HTML, CSS y JavaScript sin ninguna librería: los gráficos son SVG
generados en el cliente y el estado del tema vive en `localStorage`."*

### Paso 5 — Login incorrecto (30 s, opcional)

Cierra sesión, prueba con una contraseña errónea → *"Credenciales inválidas."*
Frase útil: *"El mensaje no revela si el usuario existe. La contraseña se compara contra su
hash, nunca en texto plano."*

### Paso 6 — CRUD completo de Prestatarios (3 min) ← **35 % de la rúbrica**

1. **Leer**: entra en *Prestatarios*. Hay 4 registros.
2. **Crear**: haz clic en *Nuevo prestatario* (fíjate que la URL es `/crear`). Rellena:
   - Cédula `V-88888888`, Nombre `Valentina`, Apellido `Demostración`
   - Tipo `Estudiante`, Teléfono `0414-8888888`, Correo `valentina.demo@correo.com`
   - Haz clic en *Guardar* → mensaje verde y el listado pasa a 5 registros.
3. **Validación**: intenta crear otra vez con la **misma cédula** → error
   *"La cédula ya está registrada."* *"Valida el servidor, no solo el navegador."*
4. **Actualizar**: haz clic en *Editar* en la fila creada (URL `/editar/<id>`), cambia el nombre a
   `Valentina Elena` y el tipo a `Profesor` → se refleja en el listado.
5. **Eliminar**: haz clic en *Eliminar* → **aparece el diálogo de confirmación de JavaScript**.
   Haz clic en *Cancelar* primero para mostrar que no borra, y luego *Aceptar*.
   → mensaje verde y el listado vuelve a 4 registros.

### Paso 7 — Categorías, Laboratorios y Equipos (2 min)

1. *Categorías* → *Nueva categoría*: `Demostración`.
2. *Laboratorios* → *Nuevo laboratorio*: `LAB-DEMO`, `Laboratorio de Demostración`,
   `Edificio C`, capacidad `25`, duración estándar `70`.
3. *Equipos* → *Nuevo equipo*: `EQ-DEMO`, categoría `Demostración`, laboratorio `LAB-DEMO`.

Frase útil: *"El equipo queda relacionado con su categoría y su laboratorio mediante claves
foráneas; el listado resuelve las relaciones y muestra los nombres."*

### Paso 8 — Reservas: duración estándar y hora de finalización (2 min) ← **15 % JavaScript**

*Reservas* → *Nueva reserva*.

1. Elige `LAB-01`.
2. Pon la **fecha de la primera reserva** (la que imprimió `init_db.py`).
3. Hora de inicio `08:00`, duración `70`.
4. Señala el recuadro **"Hora de finalización (calculada)"**: muestra `09:10` y se actualiza
   mientras escribes. *"Es manipulación del DOM con JavaScript."*
5. Cambia la duración a `30` y haz clic en *Usar duración estándar* → vuelve a `70`.

### Paso 9 — Solapamiento: rechazo y adyacencia (2 min) ← **regla de negocio clave**

1. Pon hora de inicio `08:30` y haz clic en **Verificar disponibilidad** →
   el navegador consulta el servidor con `fetch()` y responde en rojo que se superpone.
2. Haz clic en *Guardar* → el servidor **también** lo rechaza con un mensaje claro.
   Frase útil: *"La comprobación del navegador es una comodidad; la que manda es la del
   servidor, que usa la misma regla."*
3. Ahora pon `10:20` (justo cuando termina la reserva anterior) → **se acepta**.
   Frase útil: *"Las franjas exactamente adyacentes no se consideran solapadas: la condición
   es `inicio_existente < fin_nueva Y fin_existente > inicio_nueva`."*

### Paso 10 — Préstamo y devolución (2 min)

1. *Préstamos* → *Nuevo préstamo*: equipo `EQ-DEMO`, prestatario María González.
2. Guardar → mensaje *"El equipo figura ahora como PRESTADO"*.
3. Ve a *Equipos* y señala que **EQ-DEMO está en PRESTADO**.
4. Vuelve a *Préstamos*, haz clic en *Devolver* → confirmación → mensaje
   *"El equipo vuelve a estar DISPONIBLE"*.
5. Vuelve a *Equipos* y muestra que **EQ-DEMO está DISPONIBLE** otra vez.

### Paso 11 — Historial con filtros (1 min)

*Historial*: aparecen reservas, préstamos y devoluciones juntos.
Aplica el filtro *Tipo de operación = Préstamo* → se reduce la lista.
Prueba una fecha futura (ej. `Desde 01/01/2030`) → aparece el **mensaje amigable** de
"no hay operaciones que coincidan".

### Paso 12 — Trazabilidad, cuenta propia y ayuda (2 min)

1. **Auditoría** (solo ADMINISTRADOR): el registro muestra quién hizo qué, con fecha, detalle
   e IP. Señala tu propio inicio de sesión, anotado hace un minuto.
   Frase útil: *"El registro sobrevive aunque el usuario se elimine: por eso `usuario_id` no
   tiene clave foránea a propósito."*
2. **Mi perfil** → cambio de contraseña, con la actual como comprobación.
3. **Guía de uso** → el manual de usuario dentro de la propia aplicación.
4. En *Reservas*, haz clic en **Comprobante** en una fila: se genera una ficha imprimible de la
   reserva.

### Paso 13 — Registro de una cuenta nueva (2 min, opcional)

Demuestra que el sistema no depende de que un administrador dé de alta a nadie:

1. *Cerrar sesión* y, en la pantalla de acceso, haz clic en **Crea una aquí**.
2. Rellena el formulario con un correo cualquiera y una contraseña válida.
3. Al enviar, la pantalla avisa de que hay que **confirmar el correo**. Como no hay servidor
   SMTP configurado, el sistema entra en **modo demostración**: muestra el enlace de
   confirmación ahí mismo y guarda el mensaje en `database/buzon/`.
4. Antes de confirmar, intenta iniciar sesión: **se rechaza**, y explica por qué. Ese es el
   punto de la funcionalidad.
5. Haz clic en **Confirmar mi cuenta ahora** y entra con el **correo** como identificador: funciona.

Frase útil: *"El enlace es de un solo uso y caduca. La cuenta se crea como operador, nunca
como administrador: nadie se concede permisos a sí mismo. Y si configuras las variables
`TECHLOAN_SMTP_*`, el mismo flujo manda el correo de verdad."*

> Enseñar `database/buzon/` refuerza el mensaje: el mensaje que "se habría enviado" queda
> ahí como evidencia.

### Paso 14 — Restricción administrativa (2 min) ← **seguridad y roles**

1. *Cerrar sesión*.
2. Entra como **`operador` / `Operador123!`**.
3. Señala el menú: **no aparece "Usuarios"**. Y en Prestatarios **no hay botones Eliminar**.
4. Intenta abrir `http://127.0.0.1:5000/usuarios` a mano → redirige con
   *"Tu rol no tiene permisos para realizar esa acción."*

### Paso 15 — Responsive (1 min)

Reduce la ventana del navegador (o usa F12 → modo dispositivo) a ~375 px:
- El menú se convierte en un botón que despliega con JavaScript.
- **Las tablas se convierten en tarjetas** apiladas, sin perder información.

### Paso 16 — Pruebas y cierre (1 min)

```bash
PYTHONPATH=. python tests/test_web_phase6.py
```

Muestra que pasa completo. Y cierra con:

- `schema.sql` → 7 tablas, claves foráneas, índices y 21 registros de prueba.
- `README.md` → instalación, inicialización, ejecución y descripción del problema.

---

## 4. Plan de contingencia

| Si falla… | Qué hacer |
|---|---|
| El servidor no arranca | Revisa que el entorno virtual esté activado y que el puerto 5000 esté libre. Prueba `python run_server.py` desde la raíz del proyecto. |
| Error de base de datos | `python init_db.py` la reconstruye desde cero. No hay nada irrecuperable. |
| El navegador no abre | Prueba `http://localhost:5000` en lugar de `127.0.0.1`. |
| `import app` falla al ejecutar pruebas | Falta `PYTHONPATH=.` delante del comando. |
| Se cae el equipo o el proyector | Usa las capturas de `docs/capturas/`, que cubren todo el recorrido. |
| Se acaba el tiempo | Prioriza: pasos 6 (CRUD), 9 (solapamiento) y 14 (roles). Son los de mayor peso. |

---

## 5. Preguntas previsibles del profesor

**¿Por qué hay `app/` en vez de un solo `app.py`?**
Porque la lógica de negocio está en servicios POO reutilizables. Un solo archivo mezclaría
rutas, validaciones y SQL. El README incluye una tabla de equivalencia con la estructura
sugerida en el enunciado. Las rutas `/`, `/crear`, `/editar/<id>` y `/eliminar/<id>` existen
literalmente.

**¿Dónde está el `schema.sql`?**
En la raíz. Contiene 7 tablas con claves primarias, foráneas y restricciones `CHECK`,
7 índices y 21 registros de prueba (el enunciado pide mínimo 3).

**¿Cómo evitas la inyección SQL?**
Todas las consultas usan parámetros (`?`). Ninguna concatena datos del usuario.
Se puede demostrar: `tests/test_security_phase5.py` lo verifica.

**¿Las contraseñas están cifradas?**
Se almacenan como hash `scrypt` de Werkzeug, en un campo `VARCHAR(255)`, como pedía la
indicación. El hash nunca se envía al navegador.

**¿Qué pasa si dos personas reservan el mismo laboratorio a la misma hora?**
El servicio comprueba solapamientos antes de insertar y rechaza la segunda reserva.

**¿Y si dos personas envían la reserva al mismo tiempo?**
La comprobación y la inserción ocurren dentro de la misma conexión a SQLite. Para un sistema
de este alcance es suficiente; en un entorno con mucha concurrencia se añadiría una
restricción de unicidad o un bloqueo explícito. *(Sé honesto: reconocer el límite suma.)*

**¿Por qué JavaScript sin framework?**
Porque el enunciado pide JavaScript (Vanilla) y el proyecto debe seguir siendo explicable
en Programación III. Se usa para confirmaciones, validación en cliente, cálculo de la hora
final y `fetch()`.

**¿Qué es el CSRF?**
Un token de sesión que se incluye en todos los formularios. Sin él, un `POST` responde `400`.
Impide que otra web envíe formularios en nombre del usuario.

**¿Por qué hay código Tkinter si la entrega es web?**
Fue el prototipo inicial. De ahí se reutilizaron los servicios y las reglas de negocio. Se
conserva como evidencia de la evolución del proyecto.

**¿Por qué las fechas de las reservas son relativas?**
Para que los datos de demostración nunca queden vencidos. `schema.sql` usa
`date('now','localtime','+7 days')`.

---

## 6. Cifras para citar

| Dato | Valor |
|---|---|
| Tablas | 7 |
| Índices | 7 |
| Registros de prueba en `schema.sql` | 21 |
| Plantillas Jinja2 | 21 |
| Archivos de prueba | 10 |
| Peticiones HTTP verificadas en las pruebas web | 113 |
| Comprobaciones en navegador real | 56 |
| Respuestas 5xx en el recorrido completo | 0 |
| Dependencias externas | 2 (Flask, Werkzeug) |
