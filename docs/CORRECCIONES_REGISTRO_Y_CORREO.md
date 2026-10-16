# Correcciones del ciclo de registro y correo

Registro de los fallos encontrados, las pruebas que los reprodujeron y las
correcciones aplicadas. Todo quedó verificado con la suite de pruebas
(**63 comprobaciones, 0 errores**) y con el navegador real.

Fecha: 2026-10-16 · Rama de trabajo: sin commitear (a la espera de aprobación).

---

## Resumen

| # | Fallo | Dónde | Gravedad | Estado |
|---|---|---|---|---|
| 1 | La plantilla decía «Correo enviado» aunque el envío hubiera fallado | `templates/auth/revisar_correo.html` | **Alta** — engaña al usuario | Corregido |
| 2 | El formulario recortaba las contraseñas ( `form_fields` ) | `app/routes/web_common.py` | **Alta** — cambiaba la clave real | Corregido |
| 3 | No se podía ver la contraseña escrita | registro / perfil / usuarios | Media (usabilidad) | Corregido |
| 4 | Sin explicación de por qué falla la confirmación en producción | — | Media | Diagnosticador nuevo |
| 5 | El correo no llevaba `Date` ni `Message-ID` (lo exige el RFC) | `app/services/correo_service.py` | **Alta** — Proton lo descarta | Corregido |
| 6 | El enlace de confirmación medía 88 caracteres y se partía | `app/services/registro_service.py` | **Alta** — token truncado | Corregido |
| 7 | La página de error no decía qué token había recibido | `templates/auth/confirmar.html` | Media — no diagnosticable | Corregido |

---

## Evidencia que llevó a los fallos 5, 6 y 7

El 16/10/2026 Lorenzo probó el registro en producción con
`usezeoworks223@protonmail.com`. Las capturas mostraron dos cosas concluyentes:

1. **La aplicación decía «Correo enviado»** (aviso verde) → era el fallo 1, sin
   desplegar.
2. **La bandeja de Proton estaba vacía**: los dos únicos mensajes eran de Proton
   («Your Proton data has been deleted due to inactivity» y «Enhance your
   security»). El correo de TechLoan **nunca llegó**.

Y el dato que orientó todo: *«a otros que sí les llega no sé si era porque usaron
Gmail»*. Es decir, **a Gmail llega y a Proton no**. Cuando el envío funciona con
un proveedor y falla con otro, el problema casi nunca es la conexión SMTP (si
fallara, no llegaría a ninguno), sino **el contenido del mensaje**.

---

## 1. «Correo enviado» cuando el correo no se envió

### El fallo

`correo_service.enviar()` captura **cualquier** excepción de SMTP para que un
fallo de correo no tumbe el registro de la persona (decisión de diseño correcta).
Devuelve entonces:

```python
{"enviado": False, "modo": "smtp", "error": "...", "archivo": "..."}
```

Pero `templates/auth/revisar_correo.html` decidía **solo por el modo**:

```jinja
{% else %}          {# modo != 'demostracion', es decir: modo SMTP #}
<div class="aviso aviso--exito">
  <strong>Correo enviado.</strong>
```

O sea: si la contraseña de aplicación de Gmail era inválida, si el servidor
rechazaba la conexión o si se agotaba la cuota, el usuario veía **«Correo
enviado»** y se quedaba esperando un mensaje que nunca llegaría. La cuenta sí
quedaba creada, así que no había forma de recuperarse salvo acertar con
`/reenviar`.

Esto encaja con el síntoma reportado: *«varios compañeros reportaron problemas
para registrar»*.

### La corrección

La plantilla ahora mira `resultado.correo.enviado`, que es el dato real:

- **enviado** → aviso de éxito (como antes).
- **no enviado** → aviso de error (`aviso--peligro`), se explica que la cuenta
  quedó creada y se ofrece **el enlace directamente** para activarla, junto con
  el detalle técnico del error para el administrador.

Así el registro nunca se bloquea por un problema de correo.

---

## 2. Las contraseñas se recortaban sin avisar

### El fallo

`app/routes/web_common.py`:

```python
data = {name: (request.form.get(name) or "").strip() for name in names}
```

`form_fields` recortaba **todos** los campos, incluidos los de contraseña. Un
espacio al principio o al final de la clave desaparecía en silencio, de modo que
el hash guardado **no correspondía** a lo que la persona había tecleado.

El espacio es un carácter perfectamente válido de una contraseña, así que esto
era un fallo real, no una hipótesis.

### La corrección

Se añadió el parámetro `no_recortar`:

```python
def form_fields(*names, empty_to_none=(), no_recortar=()):
    preservar = set(no_recortar)
    data = {}
    for name in names:
        valor = request.form.get(name) or ""
        data[name] = valor if name in preservar else valor.strip()
    ...
```

Y se usa en los dos sitios que recogen contraseñas:

- `app/routes/web_auth_routes.py` (registro) → `no_recortar=("password", "password_repetida")`
- `app/routes/web_extra_routes.py` (cambio de contraseña en el perfil) → los tres campos.

Los demás campos siguen recortándose igual: los servicios (`RegistroService`,
`UsuarioService`) hacen su propio `.strip()` internamente, así que el
comportamiento del resto del sistema no cambia.

---

## 3. No se podía ver la contraseña

### El fallo

Los campos de contraseña solo mostraban puntos. Con una política que exige
mayúscula, minúscula, número y símbolo, quien teclea no puede comprobar qué
escribió: un error de un carácter es imposible de detectar. Es el fallo que
reportaste al probar el registro.

### La corrección

En lugar de tocar las plantillas una por una, se añadió el **módulo 12** de
`static/js/main.js`: al cargar la página, pone un botón de ojo dentro de **cada**
`input[type="password"]` que encuentre. Cambia el `type` entre `password` y
`text` y vuelve a poner el foco en el campo.

Ventajas de hacerlo así:

- Cubre registro, perfil y alta de usuarios **sin duplicar marcado**.
- Cubre también cualquier formulario futuro que se añada.
- No cambia el valor que se envía al servidor: la validación sigue siendo la del
  servidor, que es la que manda.

Detalle de implementación: el botón se coloca dentro de un envoltorio
`.campo-contrasena` que contiene **solo el input**, y se centra con
`top: 50%; transform: translateY(-50%)`. Así no depende de la altura del rótulo
que haya encima (la primera versión usaba una medida fija y quedaba
desplazado).

---

## 4. Diagnosticador para producción

El ciclo de registro **funciona**: se verificó de punta a punta con un servidor
SMTP auténtico levantado en un hilo, configurando la aplicación igual que en
producción (`TECHLOAN_SMTP_*` + `TECHLOAN_URL_BASE`). El correo sale, el token
del cuerpo coincide con el de la base de datos y el enlace confirma la cuenta.

Por tanto, si en producción falla, la causa está en el **entorno**, no en la
lógica. Como ese entorno no se puede inspeccionar desde aquí, se creó
`deploy/diagnostico_registro.py`, que en la consola Bash de PythonAnywhere
informa de:

1. La ruta real de la base de datos que usa la aplicación.
2. Si hay SMTP configurado, con qué valores y **si la contraseña tiene espacios**
   (Google la entrega en grupos de 4 letras; hay que quitárselos).
3. La `URL_BASE`: si está mal, todos los enlaces apuntan a un dominio inexistente.
4. Las últimas cuentas creadas y su estado de confirmación.
5. Los últimos tokens: usados, caducados, y a qué cuenta pertenecen.
6. **La prueba que delata el fallo**: reconstruye el enlace que se habría enviado
   para cada cuenta pendiente y comprueba si ese token existe y está usable.
7. Si el servidor SMTP acepta la conexión y la autenticación.

Uso:

```bash
cd ~/TechLoan
python3 deploy/diagnostico_registro.py
```

No envía correos, no modifica nada y no muestra la contraseña.

---

## Pruebas

### Nueva: `tests/test_registro_smtp.py`

Verifica el ciclo completo **con SMTP real**, que es el camino que antes no
estaba cubierto (las pruebas existentes solo probaban el modo demostración):

- levanta un servidor SMTP auténtico en un hilo (con `AUTH LOGIN`, para que
  `smtplib.login()` funcione de verdad);
- configura la aplicación como en producción;
- comprueba que el correo sale por el socket;
- **decodifica el correo con `email.message_from_string(..., policy=default)`**;
- extrae el enlace y comprueba que el token existe en la base de datos, está sin
  usar y que al abrirlo la cuenta queda confirmada;
- comprueba que después se puede entrar con el correo.

**Lección que dejó esta prueba:** el cuerpo del correo va en
*quoted-printable*, que **parte las URLs largas** insertando un salto de línea
blando (`=` + CRLF). Buscar el enlace con una expresión regular sobre el mensaje
crudo devuelve un token truncado y un falso negativo. Hay que decodificar el
mensaje antes de extraer nada. La prueba incluye una comprobación explícita de
que el token no acaba en `=`.

### Suite completa

```
test_crud_phase5        4 comprobaciones OK
test_historial_phase4   1
test_overlap_phase5     7
test_registro_phase7    7
test_registro_smtp      1   (nueva)
test_roles_phase5       6
test_security_phase5    7
test_validations_phase5 8
test_web_phase6         13
crud_test               1
security_test           1
smoke_test              7
                        ----------
                        63 comprobaciones, 0 errores
```

### Verificación en navegador (Playwright/Chromium)

| Pantalla | Campos de contraseña | Botones | Correcto |
|---|---|---|---|
| `/login` | 1 | 1 | sí |
| `/registro` | 2 | 2 | sí |
| `/perfil` | 3 | 3 | sí |
| `/usuarios/crear` | 1 | 1 | sí |

- El botón cambia `password` ↔ `text` y **conserva el valor escrito**.
- El botón queda **dentro del campo** (comprobado por caja de posición, en X e Y).
- **0 errores de consola** en las cuatro pantallas.

---

## 5. El correo no llevaba `Date` ni `Message-ID`

### El fallo

`app/services/correo_service.py` construía el mensaje así:

```python
mensaje = EmailMessage()
mensaje["Subject"] = asunto
mensaje["From"] = SMTP_FROM
mensaje["To"] = destinatario
mensaje.set_content(texto)
```

Sin `Date` y sin `Message-ID`. **El RFC 5322 exige ambas cabeceras** en todo
mensaje de correo.

Gmail las añade por su cuenta cuando le falta alguna, así que el mensaje llega.
Proton Mail —que es notoriamente estricto con el spam y con el cumplimiento del
estándar— **descarta o archiva** el mensaje. Es exactamente el patrón observado:
funciona con Gmail, falla con Proton.

### La corrección

```python
mensaje["From"] = f"TechLoan <{SMTP_FROM}>"     # nombre legible, no solo la dirección
mensaje["Reply-To"] = SMTP_FROM
mensaje["Date"] = format_datetime(datetime.now().astimezone())
mensaje["Message-ID"] = make_msgid(domain=SMTP_FROM.split("@")[-1])
mensaje["Auto-Submitted"] = "auto-generated"
```

- `From` con nombre: los filtros de spam puntúan mejor un remitente con nombre.
- `Date` y `Message-ID`: cumplimiento del RFC; sin ellos los receptores
  estrictos rechazan.
- `Auto-Submitted: auto-generated`: declara que es transaccional, no masivo.

---

## 6. El enlace de confirmación se partía por quoted-printable

### El fallo

El cuerpo del correo se codifica en **quoted-printable**, que parte cualquier
línea de más de **76 caracteres** insertando un salto de línea blando (`=` seguido
de CRLF).

Con token de 32 bytes, el enlace medía:

```
https://lorodev.pythonanywhere.com/confirmar/a-dIdxlNfR0LodlALC8kPB9bihtTtzEWnCIYmekXazQ
└──────────────────────── 88 caracteres ────────────────────────┘
```

**88 > 76, así que se partía por la mitad.** Los clientes que renderizan el HTML
lo decodifican y el botón funciona, pero:

- la URL **en texto plano** aparece cortada, y quien la copia y pega copia un
  token truncado;
- algunos clientes muestran el enlace partido;
- si alguien reenvía el correo como texto, se pierde.

Esto explica el otro síntoma: *«al momento de presionar el enlace de
confirmación la página aún les dice que no pudieron confirmar su cuenta»*.

### La corrección

Dos cambios, medidos:

1. **Token más corto**: `secrets.token_urlsafe(24)` en lugar de 32. Sigue siendo
   **192 bits de entropía**, inconcebible de adivinar por fuerza bruta para un
   valor de un solo uso que caduca en 24 horas.
2. **Ruta corta `/c/<token>`** en lugar de `/confirmar/<token>`.

Resultado:

```
https://lorodev.pythonanywhere.com/c/iVl1-CU1iGJ3iluNGJghi8M3icYPtaXp
└──────────────────── 69 caracteres ────────────────────┘
```

**69 ≤ 76: cabe en una sola línea.** Ningún cliente puede partirlo.

> **Compatibilidad:** la ruta larga `/confirmar/<token>` **se conserva** como
> alias. Los enlaces ya enviados siguen funcionando; solo los nuevos usan la
> corta. Ambas apuntan a la misma vista.

---

## 7. La página de error no era diagnosticable

### El fallo

Cuando la confirmación fallaba, la página decía «No se pudo confirmar la cuenta»
y el motivo, pero **no decía qué token había recibido**. Sin eso era imposible
distinguir:

- el enlace llegó **truncado** (culpa del correo),
- el token **caducó**,
- el token **nunca existió** (culpa de la base de datos).

### La corrección

- Se **registra en la bitácora de auditoría** cada intento rechazado, con los
  primeros caracteres del token y el motivo.
- La página de error **muestra el código recibido**, su longitud, y avisa si es
  menor de 32 caracteres («el enlace llegó cortado: pide uno nuevo»).

No es un dato sensible: el token es de un solo uso y ya no sirve para nada.

---

## 8. Prueba de envío real

Nueva: `deploy/prueba_envio_real.py`.

El diagnóstico anterior comprobaba la conexión SMTP, pero **no enviaba nada**.
Este script sí envía un correo auténtico y distingue los dos fallos que parecen
el mismo:

1. **Gmail no acepta el envío** → contraseña inválida, cuenta sin verificar,
   cuota agotada o puerto bloqueado.
2. **Gmail acepta pero no llega** → problema del destinatario o de su filtro.

Uso:

```bash
cd ~/TechLoan
python3 deploy/prueba_envio_real.py lorenzoroca333@gmail.com
python3 deploy/prueba_envio_real.py lorenzoroca333@gmail.com alguien@protonmail.com
```

Informa del resultado de `send_message()` destinatario por destinatario, y
recuerda comprobar la carpeta «Enviado» de Gmail: si el mensaje está ahí, salió.

---

## Verificación

### Navegador (Playwright/Chromium)

| Comprobación | Resultado |
|---|---|
| Enlace mostrado usa la ruta corta `/c/` | sí (56 caracteres en local) |
| Enlace cabe en una línea (≤ 76) | **sí** |
| Confirmación con la ruta corta | **CONFIRMADA** |
| Enlace inválido indica el código recibido | **sí**, y su longitud |
| Ruta antigua `/confirmar/` sigue respondiendo | **sí** |
| Errores de consola | 0 (los dos 400 son peticiones deliberadas a enlaces inválidos) |

### Suite completa

**63 comprobaciones, 0 errores** en 12 archivos de prueba.

Las dos pruebas de registro se ampliaron para aceptar **ambas rutas**
(`/confirmar/` y `/c/`) y para **exigir que el enlace quepa en 76 caracteres**,
de modo que este fallo no pueda volver a colarse sin que salte una prueba.

---

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `app/routes/web_common.py` | `form_fields` con parámetro `no_recortar` |
| `app/routes/web_auth_routes.py` | registro sin recortar contraseñas; ruta `/c/`; auditoría de intentos fallidos |
| `app/routes/web_extra_routes.py` | perfil: contraseñas sin recortar |
| `app/services/correo_service.py` | cabeceras `Date`, `Message-ID`, `Reply-To`, `Auto-Submitted`, `From` con nombre |
| `app/services/registro_service.py` | `TOKEN_BYTES = 24`; enlace con ruta corta |
| `templates/auth/revisar_correo.html` | distingue envío real de envío fallido |
| `templates/auth/confirmar.html` | muestra el token recibido cuando falla |
| `static/js/main.js` | módulo 12: botón de ver/ocultar contraseña |
| `static/css/estilos.css` | estilos del botón |
| `tests/test_registro_smtp.py` | **nuevo**: ciclo con SMTP real |
| `tests/test_registro_phase7.py` | acepta ambas rutas; exige enlace ≤ 76 caracteres |
| `deploy/diagnostico_registro.py` | **nuevo**: diagnóstico en producción |
| `deploy/prueba_envio_real.py` | **nuevo**: envío real con informe por destinatario |

---

## Pendiente

**Nada de esto está en producción.** Los cambios son locales y **no se ha hecho
commit** (a la espera de aprobación). Mientras tanto, el servidor sigue con el
código anterior, que es el que decía «Correo enviado» sin comprobarlo.

Para subirlo, ver `docs/ACTUALIZAR_EN_PRODUCCION.md`. Después, en la consola Bash
de PythonAnywhere:

```bash
cd ~/TechLoan && git pull origin main
python3 deploy/prueba_envio_real.py lorenzoroca333@gmail.com alguien@protonmail.com
python3 deploy/diagnostico_registro.py
```
