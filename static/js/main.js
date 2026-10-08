/* ==========================================================================
   TechLoan — JavaScript principal (Vanilla JS, sin dependencias)
   --------------------------------------------------------------------------
   Módulos:
     1. Menú de navegación móvil
     2. Mensajes flash (cierre manual)
     3. Confirmación antes de acciones críticas (eliminar / devolver / cancelar)
     4. Validación de formularios en el lado del cliente
     5. Cálculo de la hora de finalización de una reserva
     6. Comprobación de disponibilidad con fetch()
     7. Protección contra el doble envío de formularios

   Todas las comprobaciones de este archivo son una MEJORA de la experiencia de
   usuario: la validación y las reglas de negocio definitivas se ejecutan
   siempre en el servidor (Flask + servicios + SQLite3).
   ========================================================================== */

(function () {
  "use strict";

  /* ========================================================================
     1. Menú de navegación móvil
     ====================================================================== */
  function inicializarMenu() {
    var boton = document.getElementById("menu-boton");
    var menu = document.getElementById("menu-principal");
    if (!boton || !menu) {
      return;
    }

    boton.addEventListener("click", function () {
      var abierto = menu.classList.toggle("abierto");
      boton.setAttribute("aria-expanded", abierto ? "true" : "false");
    });

    // Al pasar a escritorio el menú vuelve a su estado normal.
    window.addEventListener("resize", function () {
      if (window.innerWidth >= 900) {
        menu.classList.remove("abierto");
        boton.setAttribute("aria-expanded", "false");
      }
    });
  }

  /* ========================================================================
     2. Mensajes flash: botón de cierre
     ====================================================================== */
  function inicializarMensajes() {
    var botones = document.querySelectorAll(".mensaje__cerrar");
    Array.prototype.forEach.call(botones, function (boton) {
      boton.addEventListener("click", function () {
        var mensaje = boton.closest(".mensaje");
        if (mensaje && mensaje.parentNode) {
          mensaje.parentNode.removeChild(mensaje);
        }
      });
    });
  }

  /* ========================================================================
     3. Confirmación antes de acciones críticas
     --------------------------------------------------------------------
     Los formularios de eliminar, cancelar y devolver llevan el atributo
     data-confirmar con el texto a mostrar. Se usa window.confirm(), tal como
     exige el PDF del proyecto.
     ====================================================================== */
  function inicializarConfirmaciones() {
    var formularios = document.querySelectorAll("form[data-confirmar]");
    Array.prototype.forEach.call(formularios, function (formulario) {
      formulario.addEventListener("submit", function (evento) {
        var mensaje = formulario.getAttribute("data-confirmar");
        if (mensaje && !window.confirm(mensaje)) {
          evento.preventDefault();
          return false;
        }
        return true;
      });
    });
  }

  /* ========================================================================
     4. Validación en el lado del cliente
     --------------------------------------------------------------------
     Se apoya en los atributos HTML5 (required, type, min, max, pattern) y
     añade realimentación visual mediante la clase .invalido.
     ====================================================================== */
  function inicializarValidacion() {
    var formularios = document.querySelectorAll("form[data-validar]");

    Array.prototype.forEach.call(formularios, function (formulario) {
      var campos = formulario.querySelectorAll("input, select, textarea");

      Array.prototype.forEach.call(campos, function (campo) {
        // El navegador dispara 'invalid' cuando el valor no cumple las reglas.
        campo.addEventListener("invalid", function () {
          campo.classList.add("invalido");
        });

        // Al corregir el valor, se retira el aviso.
        campo.addEventListener("input", function () {
          if (campo.checkValidity()) {
            campo.classList.remove("invalido");
          }
        });

        campo.addEventListener("blur", function () {
          if (!campo.checkValidity()) {
            campo.classList.add("invalido");
          } else {
            campo.classList.remove("invalido");
          }
        });
      });

      // Si el envío se bloquea por validación, se enfoca el primer campo con error.
      formulario.addEventListener("submit", function (evento) {
        if (!formulario.checkValidity()) {
          evento.preventDefault();
          var primero = formulario.querySelector(":invalid");
          if (primero) {
            primero.focus();
          }
          return false;
        }
        return true;
      });
    });
  }

  /* ========================================================================
     5. Cálculo de la hora de finalización de una reserva
     --------------------------------------------------------------------
     Manipulación del DOM: se lee la hora de inicio y la duración y se
     actualiza el elemento <output> en tiempo real.
     ====================================================================== */
  function minutosAHora(totalMinutos) {
    var horas = Math.floor(totalMinutos / 60);
    var minutos = totalMinutos % 60;
    return (horas < 10 ? "0" : "") + horas + ":" + (minutos < 10 ? "0" : "") + minutos;
  }

  function horaAMinutos(hora) {
    var partes = String(hora).split(":");
    if (partes.length !== 2) {
      return null;
    }
    var horas = parseInt(partes[0], 10);
    var minutos = parseInt(partes[1], 10);
    if (isNaN(horas) || isNaN(minutos)) {
      return null;
    }
    return horas * 60 + minutos;
  }

  function inicializarFormularioReserva() {
    var formulario = document.getElementById("formulario-reserva");
    if (!formulario) {
      return;
    }

    var selectLaboratorio = document.getElementById("campo-laboratorio_id");
    var campoFecha = document.getElementById("campo-fecha");
    var campoHoraInicio = document.getElementById("campo-hora_inicio");
    var campoDuracion = document.getElementById("campo-duracion_minutos");
    var salida = document.getElementById("campo-hora_fin_calculada");
    var botonEstandar = document.getElementById("boton-duracion-estandar");
    var botonDisponibilidad = document.getElementById("boton-disponibilidad");
    var resultado = document.getElementById("resultado-disponibilidad");

    // Mapa { id_laboratorio: duración_estándar } inyectado por Flask.
    var duraciones = {};
    try {
      duraciones = JSON.parse(formulario.getAttribute("data-duraciones") || "{}");
    } catch (error) {
      duraciones = {};
    }
    var urlDisponibilidad = formulario.getAttribute("data-url-disponibilidad") || "";

    function duracionDelLaboratorio() {
      if (!selectLaboratorio) {
        return null;
      }
      var valor = duraciones[selectLaboratorio.value];
      return typeof valor === "number" ? valor : null;
    }

    function actualizarHoraFin() {
      if (!salida || !campoHoraInicio || !campoDuracion) {
        return;
      }
      var inicio = horaAMinutos(campoHoraInicio.value);
      var duracion = parseInt(campoDuracion.value, 10);

      if (inicio === null || isNaN(duracion) || duracion <= 0) {
        salida.textContent = "—";
        return;
      }
      if (inicio + duracion > 1439) {
        salida.textContent = "Excede el día";
        return;
      }
      salida.textContent = minutosAHora(inicio + duracion);
    }

    function horaFinCalculada() {
      var inicio = horaAMinutos(campoHoraInicio ? campoHoraInicio.value : "");
      var duracion = parseInt(campoDuracion ? campoDuracion.value : "", 10);
      if (inicio === null || isNaN(duracion)) {
        return "";
      }
      return minutosAHora(inicio + duracion);
    }

    // Al elegir laboratorio se propone su duración estándar.
    if (selectLaboratorio) {
      selectLaboratorio.addEventListener("change", function () {
        var estandar = duracionDelLaboratorio();
        if (estandar !== null && campoDuracion) {
          campoDuracion.value = estandar;
        }
        actualizarHoraFin();
      });
    }

    if (botonEstandar) {
      botonEstandar.addEventListener("click", function () {
        var estandar = duracionDelLaboratorio();
        if (estandar !== null && campoDuracion) {
          campoDuracion.value = estandar;
          campoDuracion.classList.remove("invalido");
        }
        actualizarHoraFin();
      });
    }

    [campoHoraInicio, campoDuracion].forEach(function (campo) {
      if (campo) {
        campo.addEventListener("input", actualizarHoraFin);
        campo.addEventListener("change", actualizarHoraFin);
      }
    });

    // --- Comprobación de disponibilidad con fetch() -----------------------
    if (botonDisponibilidad && resultado) {
      botonDisponibilidad.addEventListener("click", function () {
        var laboratorio = selectLaboratorio ? selectLaboratorio.value : "";
        var fecha = campoFecha ? campoFecha.value : "";
        var inicio = campoHoraInicio ? campoHoraInicio.value : "";
        var fin = horaFinCalculada();

        if (!laboratorio || !fecha || !inicio || !fin) {
          resultado.className = "resultado-disponibilidad es-error";
          resultado.textContent =
            "Completa laboratorio, fecha, hora de inicio y duración para poder verificar.";
          return;
        }

        resultado.className = "resultado-disponibilidad cargando";
        resultado.textContent = "Consultando disponibilidad…";

        var parametros = new URLSearchParams({
          laboratorio_id: laboratorio,
          fecha: fecha,
          hora_inicio: inicio,
          hora_fin: fin,
        });

        fetch(urlDisponibilidad + "?" + parametros.toString(), {
          headers: { "Accept": "application/json" },
        })
          .then(function (respuesta) {
            if (!respuesta.ok) {
              throw new Error("Respuesta del servidor: " + respuesta.status);
            }
            return respuesta.json();
          })
          .then(function (datos) {
            resultado.className =
              "resultado-disponibilidad " + (datos.disponible ? "es-ok" : "es-error");
            resultado.textContent =
              (datos.disponible ? "✔ " : "✖ ") + datos.mensaje +
              " (franja " + inicio + " – " + fin + ")";
          })
          .catch(function () {
            resultado.className = "resultado-disponibilidad es-error";
            resultado.textContent =
              "No se pudo verificar la disponibilidad. Inténtalo de nuevo.";
          });
      });
    }

    actualizarHoraFin();
  }

  /* ========================================================================
     6. Protección contra el doble envío
     ====================================================================== */
  function inicializarAntiDobleEnvio() {
    var formularios = document.querySelectorAll("form[data-validar]");
    Array.prototype.forEach.call(formularios, function (formulario) {
      formulario.addEventListener("submit", function () {
        var boton = formulario.querySelector('button[type="submit"]');
        if (boton) {
          window.setTimeout(function () {
            boton.disabled = true;
            boton.textContent = "Guardando…";
          }, 0);
        }
      });
    });
  }

  /* ========================================================================
     Arranque
     ====================================================================== */
  document.addEventListener("DOMContentLoaded", function () {
    inicializarMenu();
    inicializarMensajes();
    inicializarConfirmaciones();
    inicializarValidacion();
    inicializarFormularioReserva();
    inicializarAntiDobleEnvio();
  });
})();
