# Manual de usuario — TechLoan

Guía de uso de la plataforma de gestión de reservas y préstamos de recursos tecnológicos.

> **¿Tienes prisa?** Ve directamente a [Primeros pasos](#2-primeros-pasos). Si quieres
> entender las reglas antes de tocar nada, lee [Reglas del sistema](#6-reglas-del-sistema).

---

## Índice

1. [Qué es TechLoan](#1-qué-es-techloan)
2. [Primeros pasos](#2-primeros-pasos)
3. [La interfaz](#3-la-interfaz)
4. [Tareas paso a paso](#4-tareas-paso-a-paso)
5. [Atajos de teclado](#5-atajos-de-teclado)
6. [Reglas del sistema](#6-reglas-del-sistema)
7. [Roles y permisos](#7-roles-y-permisos)
8. [Preguntas frecuentes](#8-preguntas-frecuentes)
9. [Solución de problemas](#9-solución-de-problemas)
10. [Glosario](#10-glosario)

---

## 1. Qué es TechLoan

TechLoan organiza dos cosas que suelen llevarse con papel o por mensajería informal:

- **La agenda de los laboratorios.** Quién reserva qué espacio, qué día y a qué hora.
- **El inventario de equipos.** Qué hay, en qué estado y quién lo tiene prestado.

Con esas dos piezas resueltas desaparecen los tres problemas de siempre: las **dobles
reservas**, los **equipos perdidos** y la **falta de trazabilidad** de lo que ocurrió.

### Cómo se organiza la información

```
Prestatario ──recibe──> Reserva ──de──> Laboratorio
     │
     └──recibe──> Préstamo ──de──> Equipo ──pertenece a──> Categoría
                                        └──se ubica en──> Laboratorio
```

En palabras: un **prestatario** (una persona) recibe una **reserva** de un
**laboratorio** o un **préstamo** de un **equipo**. Los equipos se clasifican por
**categoría** y pueden estar asignados a un laboratorio.

---

## 2. Primeros pasos

### 2.1 Iniciar sesión

Abre el navegador en **http://127.0.0.1:5000**. Verás la portada del producto; haz clic en
**Iniciar sesión** (o ve directamente a `/login`).

Puedes identificarte con tu **nombre de usuario o con tu correo**: da igual cuál uses, la
contraseña es la misma.

### 2.1.1 Crear tu propia cuenta

Si no tienes cuenta, en la pantalla de acceso hay un enlace a **Crear una cuenta**
(`/registro`):

1. Rellena nombre, apellido, nombre de usuario, correo y contraseña.
2. Al enviar el formulario se crea la cuenta y se te manda un **enlace de confirmación** por
   correo. Hasta que no lo abras, no podrás entrar: el sistema te lo dirá si lo intentas.
3. Abre el enlace y ya puedes iniciar sesión.

Tu cuenta se crea con el rol **operador**: reservas, préstamos y catálogo. Los permisos de
administración los reparte un administrador desde el módulo *Usuarios*.

> Si el enlace caduca o no te llega, usa **No confirmé mi correo** en la pantalla de acceso
> para pedir uno nuevo. El anterior deja de funcionar.

> **Sin servidor de correo configurado** (lo normal en una demostración local), el mensaje no
> sale: se guarda en `database/buzon/` y el enlace aparece en pantalla al terminar el
> registro. Así se puede ver el flujo completo sin internet.

### 2.2 Usuarios de prueba

| Usuario | Contraseña | Qué puede hacer |
|---|---|---|
| `admin` | `Admin123!` | Todo: gestión completa, usuarios y auditoría |
| `operador` | `Operador123!` | El día a día, sin administración del sistema |

Si vas a probar el sistema por primera vez, entra como `admin`: verás todos los módulos.

### 2.3 Lo que verás al entrar

El **panel de inicio** con seis indicadores, tres gráficos y la actividad reciente. Es la
pantalla desde la que se trabaja.

La primera vez, además, arranca solo un **tutorial guiado** de 8 pasos que va señalando cada
parte de la interfaz. Puedes saltarlo con *Saltar el tutorial* o cerrarlo con `Esc`. No
volverá a aparecer; si quieres verlo otra vez, está en tu menú de usuario
(**Ver el tutorial**) y en la guía de uso.

---

## 3. La interfaz

La pantalla se divide en tres zonas:

```
┌──────────────┬────────────────────────────────────────────────┐
│              │  Barra superior: búsqueda, tema, alertas,      │
│  Barra       │  tu usuario                                    │
│  lateral     ├────────────────────────────────────────────────┤
│              │                                                │
│  (módulos)   │  Contenido del módulo                          │
│              │                                                │
└──────────────┴────────────────────────────────────────────────┘
```

### 3.1 Barra lateral

Los módulos están agrupados por para qué sirven:

| Grupo | Módulos |
|---|---|
| **General** | Inicio · Historial |
| **Operación** | Reservas · Préstamos |
| **Catálogo** | Prestatarios · Equipos · Laboratorios · Categorías |
| **Administración** | Usuarios · Auditoría *(solo administradores)* |
| **Ayuda** | Guía de uso |

Un número junto a **Reservas** o **Préstamos** indica avisos pendientes.

### 3.2 Barra superior

- **Buscar o ir a…** — abre la búsqueda global (también con `Ctrl`+`K`).
- **Sol / luna** — cambia entre tema claro y oscuro. Tu elección se recuerda.
- **Campana** — avisos: préstamos vencidos, reservas de hoy, laboratorios saturados.
- **Tu nombre** — menú con *Mi perfil*, *Guía de uso*, **Ver el tutorial** y
  *Cerrar sesión*.

### 3.3 Los listados

Todos los listados funcionan igual, y eso es a propósito:

- **Buscar**: escribe en el recuadro de búsqueda; el listado se filtra solo. Busca en
  todos los campos, así que da igual si recuerdas el código o el nombre.
- **Ordenar**: haz clic en el encabezado de una columna. Vuelve a hacer clic en él para invertir el orden.
- **Paginar**: los controles aparecen al pie cuando hay más registros que los que caben.
- **Exportar CSV**: descarga lo que tienes filtrado en ese momento. Se abre en Excel
  directamente, con los acentos y las columnas correctos.
- **Estado vacío**: si no hay registros, verás un mensaje que lo explica y, si procede, un
  botón para crear el primero.

---

## 4. Tareas paso a paso

### 4.1 Registrar un prestatario

1. Ve a **Prestatarios** → **Nuevo prestatario**.
2. Rellena cédula, nombre, apellido y tipo (estudiante, profesor, empleado u otro).
3. Teléfono y correo son opcionales, pero facilitan el contacto.
4. Haz clic en **Guardar prestatario**.

> **Ojo:** la cédula es única. Si ya existe, el sistema te avisará y no guardará el duplicado.

### 4.2 Preparar el catálogo

Hazlo en este orden, porque cada paso depende del anterior:

1. **Categorías** → *Nueva categoría* (por ejemplo, «Computación»).
2. **Laboratorios** → *Nuevo laboratorio*: código, nombre, ubicación, capacidad y
   **duración estándar** de sus reservas (70 minutos por defecto).
3. **Equipos** → *Nuevo equipo*: código, nombre, categoría, laboratorio, marca, modelo y
   serial.

### 4.3 Crear una reserva

1. Ve a **Reservas** → **Nueva reserva**.
2. Elige **laboratorio** y **prestatario**. Solo aparecen los laboratorios disponibles y
   los prestatarios activos.
3. Indica **fecha** (no se admiten fechas pasadas) y **hora de inicio**.
4. Ajusta la **duración**: al elegir el laboratorio se propone su duración estándar, pero
   puedes cambiarla.
5. Observa el recuadro **Hora de finalización**: se calcula sola mientras escribes.
6. Consulta la **ocupación del día**: la barra muestra en azul las franjas ya reservadas.
7. Haz clic en **Verificar disponibilidad** para comprobarlo antes de guardar, o directamente
   **Guardar reserva**.

**Si el horario está ocupado**, el sistema te lo dirá y te ofrecerá las **franjas libres
más cercanas**. Haz clic en la que te sirva y se aplicará sola: no tienes que empezar de nuevo.

### 4.4 Cancelar una reserva

En el listado de reservas, haz clic en **Cancelar** en la fila correspondiente y confirma. La
franja queda libre de inmediato para que otro pueda reservarla.

### 4.5 Imprimir un comprobante

En el listado de reservas, haz clic en **Comprobante**. Se abre una vista limpia con todos los
datos y un botón **Imprimir** que respeta el diseño (también sirve para guardar en PDF).

### 4.6 Prestar un equipo

1. Ve a **Préstamos** → **Nuevo préstamo**.
2. Elige un **equipo disponible** y el **prestatario** que lo recibe.
3. Añade observaciones si hace falta y haz clic en **Registrar préstamo**.

El equipo pasa automáticamente a **PRESTADO** y desaparece de la lista de disponibles.
Nadie podrá prestarlo de nuevo hasta que vuelva.

> **Atajo:** desde el listado de **Equipos**, el botón *Prestar* de cada fila disponible
> lleva al mismo formulario.

### 4.7 Registrar una devolución

En **Préstamos**, localiza el préstamo en la tabla de *Préstamos activos* y haz clic en
**Devolver**. Confirma el diálogo.

El equipo vuelve a **DISPONIBLE** y se guarda la fecha de devolución.

### 4.8 Consultar el historial

Ve a **Historial**. Ahí aparecen juntas las reservas, los préstamos y las devoluciones.

Filtra por tipo de operación, estado, prestatario, recurso o rango de fechas. Puedes
combinar filtros y exportar el resultado a CSV.

### 4.9 Consultar la auditoría *(solo administradores)*

Ve a **Auditoría**. Verás cada acción registrada con su autor, su fecha y su detalle:
altas, modificaciones, bajas, préstamos, devoluciones, cancelaciones, accesos y
exportaciones.

Es útil cuando alguien pregunta «¿quién cambió esto y cuándo?». El registro conserva el
nombre del usuario aunque su cuenta se haya eliminado después.

### 4.10 Cambiar tu contraseña

Menú de usuario (arriba a la derecha) → **Mi perfil** → rellena los tres campos y haz clic en
**Actualizar contraseña**.

Se te pide la contraseña actual como comprobación: tener la sesión abierta no basta.

La nueva contraseña debe tener al menos 8 caracteres, con una mayúscula, una minúscula,
un número y un carácter especial.

### 4.11 Gestionar usuarios *(solo administradores)*

Ve a **Usuarios** → **Nuevo usuario**. Asigna nombre, usuario, correo, contraseña y rol.

Al editar un usuario puedes dejar la contraseña en blanco para conservarla.

> **Protección:** no se puede eliminar al último administrador activo. El sistema lo impide
> para que nunca te quedes fuera.

---

## 5. Atajos de teclado

| Atajo | Acción |
|---|---|
| `Ctrl` + `K` | Abrir la búsqueda global |
| `/` | Igual que lo anterior (salvo escribiendo en un campo) |
| `↑` `↓` | Moverse por los resultados de la búsqueda |
| `Enter` | Abrir el resultado seleccionado |
| `Esc` | Cerrar la búsqueda, los menús o limpiar el campo de búsqueda de un listado |

La búsqueda global no solo salta entre secciones: también encuentra **registros
concretos**. Escribe el apellido de un prestatario, el código de un equipo o una fecha de
reserva y aparecerán directamente.

---

## 6. Reglas del sistema

### 6.1 No se permiten reservas solapadas

Dos reservas del mismo laboratorio y fecha se consideran solapadas cuando se cumple:

```
hora de inicio de la existente < hora de fin de la nueva
                    Y
hora de fin de la existente   > hora de inicio de la nueva
```

En la práctica:

| Caso | Franjas | Resultado |
|---|---|---|
| Adyacentes | 08:00–09:10 y 09:10–10:20 | ✅ **Permitido** |
| Solapadas | 08:00–09:10 y 09:09–10:19 | ❌ **Rechazado** |

Una reserva que **termina justo cuando empieza otra** no es un solapamiento: es
aprovechamiento del tiempo.

Solo bloquean las reservas en estado **CONFIRMADA** o **ACTIVA**. Al cancelar una reserva,
su franja queda libre inmediatamente.

### 6.2 Estados de una reserva

| Estado | Significado | ¿Bloquea la franja? |
|---|---|---|
| CONFIRMADA | Reserva vigente | Sí |
| ACTIVA | En curso | Sí |
| FINALIZADA | Ya ocurrió | No |
| CANCELADA | Anulada | No |

### 6.3 Estados de un equipo

| Estado | Significado |
|---|---|
| DISPONIBLE | Se puede prestar |
| PRESTADO | Está fuera; no se puede prestar ni eliminar |
| MANTENIMIENTO | En reparación |
| DAÑADO | Averiado |
| INACTIVO | Fuera de servicio |

Al prestar: `DISPONIBLE → PRESTADO`. Al devolver: `PRESTADO → DISPONIBLE`.

### 6.4 Avisos automáticos

El sistema vigila por ti y avisa en la campana:

- **Préstamos vencidos**: equipos con más de **7 días** sin devolverse. Aparecen
  destacados en rojo con los días transcurridos y un botón para devolverlos.
- **Reservas de hoy**: cuántas hay programadas.
- **Laboratorios saturados**: los que acumulan **5 reservas o más** en la próxima semana.

### 6.5 No se puede reservar en el pasado

El selector de fecha no admite fechas anteriores a hoy.

---

## 7. Roles y permisos

| Acción | ADMINISTRADOR | OPERADOR |
|---|:---:|:---:|
| Ver el panel y el historial | ✅ | ✅ |
| Gestionar prestatarios (crear y editar) | ✅ | ✅ |
| Eliminar prestatarios | ✅ | ❌ |
| Ver laboratorios, categorías y equipos | ✅ | ✅ |
| Crear y editar laboratorios, categorías y equipos | ✅ | ❌ |
| Eliminar del catálogo | ✅ | ❌ |
| Crear reservas y cancelarlas | ✅ | ✅ |
| Registrar préstamos y devoluciones | ✅ | ✅ |
| Gestionar usuarios del sistema | ✅ | ❌ |
| Consultar la auditoría | ✅ | ❌ |

El **OPERADOR** no ve en el menú los módulos que no le corresponden, y si intenta abrir
una dirección prohibida escribiéndola a mano, el sistema lo devuelve con un aviso.

Los permisos se comprueban contra la base de datos en **cada acción**, así que un cambio
de rol o la desactivación de una cuenta surten efecto de inmediato.

---

## 8. Preguntas frecuentes

**¿Necesito internet?**
No. Todo funciona en tu equipo: el servidor, la base de datos y los estilos. Internet solo
hace falta para instalar las dependencias la primera vez.

**¿Dónde se guardan los datos?**
En un único archivo: `database/techloan.db`. Copiarlo es hacer una copia de seguridad
completa.

**¿Puedo perder información si algo falla?**
Mientras tengas una copia del archivo `.db`, no. Si el archivo se corrompiera, `python
init_db.py` reconstruye el esquema desde cero (pero perderías los datos reales, así que
haz copia antes).

**¿Por qué no me deja eliminar un laboratorio?**
Porque tiene equipos o reservas asociadas. Elimínalos o reasígnalos primero. Es una
protección para no dejar registros huérfanos.

**¿Por qué no me deja eliminar un usuario?**
Si es el último administrador activo, el sistema lo impide. Debe quedar siempre alguien
con acceso total.

**¿Puedo prestar un equipo que ya está prestado?**
No. Solo aparecen en el formulario los equipos en estado DISPONIBLE.

**¿Qué pasa si dos personas reservan la misma hora al mismo tiempo?**
La comprobación y el guardado se hacen en la misma operación, así que la segunda petición
ve la primera y se rechaza. Además, quien la intentó recibe alternativas.

**¿Puedo usar TechLoan en el celular?**
Sí. La interfaz se adapta: en pantallas pequeñas las tablas se convierten en tarjetas y el
menú lateral se abre como un cajón.

**¿Cómo cambio entre tema claro y oscuro?**
Con el botón de sol/luna de la barra superior. Tu preferencia se recuerda entre sesiones.
Si nunca lo has tocado, el sistema usa la preferencia de tu sistema operativo.

**¿Las contraseñas se guardan de forma segura?**
Se guardan como hash cifrado (scrypt). Nadie puede leerlas, ni siquiera un administrador.

---

## 9. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| «Credenciales inválidas» con la contraseña correcta | Usuario inactivo o contraseña cambiada | Pide a un administrador que revise tu cuenta en *Usuarios* |
| No veo el módulo *Usuarios* ni *Auditoría* | Tu rol es OPERADOR | Es el comportamiento previsto; pide el rol de administrador |
| No aparece un equipo en el formulario de préstamo | No está DISPONIBLE | Revisa su estado en *Equipos* |
| El selector de fecha rechaza la fecha | Es anterior a hoy | No se permiten reservas en el pasado |
| El listado aparece vacío | Hay un filtro activo | Haz clic en *Limpiar* junto al buscador |
| No veo el botón *Eliminar* | Tu rol no lo permite | Es el comportamiento previsto para OPERADOR |
| El menú lateral no se cierra en el celular | — | Haz clic fuera del menú, sobre el fondo oscurecido |
| La página se ve sin estilos | El servidor no está sirviendo los archivos estáticos | Recarga con `Ctrl`+`F5` |
| El servidor no arranca | Puerto 5000 ocupado | Cierra otra instancia o cambia el puerto en `app/config.py` |
| «No module named 'app'» al ejecutar pruebas | Falta el prefijo de ruta | Ejecuta con `PYTHONPATH=. python tests/…` |

---

## 10. Glosario

| Término | Significado |
|---|---|
| **Prestatario** | Persona que recibe una reserva o un préstamo. No tiene cuenta en el sistema. |
| **Usuario del sistema** | Persona con credenciales para operar TechLoan (administrador u operador). |
| **Reserva** | Asignación de un laboratorio a un prestatario en una fecha y franja horaria. |
| **Préstamo** | Entrega de un equipo a un prestatario, con devolución pendiente. |
| **Devolución** | Registro de la entrega del equipo prestado; lo devuelve al estado disponible. |
| **Solapamiento** | Cruce de dos franjas horarias del mismo laboratorio y fecha. |
| **Franja adyacente** | Una reserva termina exactamente cuando empieza la siguiente. No es solapamiento. |
| **Holgura** | Tiempo libre que queda alrededor de una franja sugerida. |
| **Auditoría** | Registro histórico de quién hizo qué y cuándo. |
| **Estado** | Situación actual de un registro (activo, disponible, prestado, cancelada…). |
| **CSV** | Formato de archivo de texto con columnas separadas por punto y coma; se abre en Excel. |
| **Tema** | Apariencia clara u oscura de la interfaz. |

---

*TechLoan — Proyecto final de Programación III · IUTEPI*
