/* ==========================================================================
   TechLoan — JavaScript de la aplicación (Vanilla JS, sin dependencias)
   --------------------------------------------------------------------------
   Módulos:
     1.  Tema claro / oscuro con persistencia
     2.  Barra lateral (cajón en celular, plegable en escritorio)
     3.  Menús emergentes (usuario y alertas)
     4.  Notificaciones emergentes (toasts)
     5.  Paleta de comandos (Ctrl+K)
     6.  Confirmación antes de acciones críticas
     7.  Validación de formularios en el cliente
     8.  Búsqueda con retardo en los listados
     9.  Formulario de reserva: hora final, línea de tiempo y alternativas
     10. Contadores animados
     11. Protección contra el doble envío
     12. Botón de ver/ocultar la contraseña

   Todas las comprobaciones de este archivo son una MEJORA de la experiencia de
   usuario: la validación y las reglas de negocio definitivas se ejecutan
   siempre en el servidor (Flask + servicios + SQLite3).
   ========================================================================== */

(function () {
  "use strict";

  var raiz = document.documentElement;
  var CONFIG = window.TECHLOAN || {};

  function $(selector, ambito) {
    return (ambito || document).querySelector(selector);
  }

  function $$(selector, ambito) {
    return Array.prototype.slice.call((ambito || document).querySelectorAll(selector));
  }

  /* ========================================================================
     1. Tema claro / oscuro
     ====================================================================== */
  function inicializarTema() {
    var boton = $("#boton-tema");
    if (!boton) return;

    boton.addEventListener("click", function () {
      var nuevo = raiz.getAttribute("data-tema") === "oscuro" ? "claro" : "oscuro";
      raiz.setAttribute("data-tema", nuevo);
      try { localStorage.setItem("techloan-tema", nuevo); } catch (e) { /* modo privado */ }

      var meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute("content", nuevo === "oscuro" ? "#060a13" : "#f4f7fc");

      // Los gráficos se redibujan para adoptar los colores del nuevo tema.
      if (window.TechLoanGraficos) window.TechLoanGraficos.redibujar();
    });
  }

  /* ========================================================================
     2. Barra lateral
     ====================================================================== */
  function inicializarLateral() {
    var lateral = $("#lateral");
    var boton = $("#boton-lateral");
    var velo = $("#lateral-velo");
    if (!lateral || !boton) return;

    if (raiz.classList.contains("prefiere-lateral-oculto") && window.innerWidth >= 1024) {
      document.body.classList.add("lateral-oculto");
    }

    function esEscritorio() { return window.innerWidth >= 1024; }

    function abrirCajon(abierto) {
      lateral.classList.toggle("abierto", abierto);
      if (velo) velo.classList.toggle("visible", abierto);
      boton.setAttribute("aria-expanded", abierto ? "true" : "false");
    }

    boton.addEventListener("click", function () {
      if (esEscritorio()) {
        var oculto = document.body.classList.toggle("lateral-oculto");
        try { localStorage.setItem("techloan-lateral", oculto ? "oculto" : "visible"); } catch (e) { /* ignorar */ }
      } else {
        abrirCajon(!lateral.classList.contains("abierto"));
      }
    });

    if (velo) {
      velo.addEventListener("click", function () { abrirCajon(false); });
    }

    window.addEventListener("resize", function () {
      if (esEscritorio()) abrirCajon(false);
    });
  }

  /* ========================================================================
     3. Menús emergentes
     ====================================================================== */
  function inicializarMenus() {
    var pares = [
      { boton: $("#boton-usuario"), menu: $("#menu-usuario") },
      { boton: $("#boton-alertas"), menu: $("#menu-alertas") }
    ].filter(function (par) { return par.boton && par.menu; });

    if (!pares.length) return;

    function cerrarTodos(excepto) {
      pares.forEach(function (par) {
        if (par !== excepto) {
          par.menu.classList.remove("abierto");
          par.boton.setAttribute("aria-expanded", "false");
        }
      });
    }

    pares.forEach(function (par) {
      par.boton.addEventListener("click", function (evento) {
        evento.stopPropagation();
        var abierto = par.menu.classList.toggle("abierto");
        par.boton.setAttribute("aria-expanded", abierto ? "true" : "false");
        cerrarTodos(par);
      });
    });

    document.addEventListener("click", function () { cerrarTodos(null); });
    document.addEventListener("keydown", function (evento) {
      if (evento.key === "Escape") cerrarTodos(null);
    });
  }

  /* ========================================================================
     4. Notificaciones emergentes
     ====================================================================== */
  function cerrarNotificacion(nodo) {
    if (!nodo || nodo.classList.contains("saliendo")) return;
    nodo.classList.add("saliendo");
    window.setTimeout(function () {
      if (nodo.parentNode) nodo.parentNode.removeChild(nodo);
    }, 260);
  }

  function inicializarNotificaciones() {
    $$("[data-notificacion]").forEach(function (nodo) {
      var cerrar = $(".notificacion__cerrar", nodo);
      if (cerrar) {
        cerrar.addEventListener("click", function () { cerrarNotificacion(nodo); });
      }
      // Las de éxito e información se retiran solas; los errores permanecen
      // hasta que el usuario los lee.
      if (!nodo.classList.contains("notificacion--error")) {
        window.setTimeout(function () { cerrarNotificacion(nodo); }, 6500);
      }
    });
  }

  /* ========================================================================
     5. Paleta de comandos (Ctrl+K)
     ====================================================================== */
  function inicializarPaleta() {
    var paleta = $("#paleta");
    var entrada = $("#paleta-entrada");
    var resultados = $("#paleta-resultados");
    if (!paleta || !entrada || !resultados) return;

    var items = [];
    var seleccionado = 0;
    var temporizador = null;

    function pintar(grupos) {
      resultados.innerHTML = "";
      items = [];

      if (!grupos.length) {
        resultados.innerHTML = '<p class="paleta__vacio">Sin resultados. Prueba con otro término.</p>';
        entrada.setAttribute("aria-expanded", "false");
        return;
      }

      grupos.forEach(function (grupo) {
        var titulo = document.createElement("p");
        titulo.className = "paleta__grupo";
        titulo.textContent = grupo.titulo;
        resultados.appendChild(titulo);

        grupo.items.forEach(function (item) {
          var boton = document.createElement("button");
          boton.type = "button";
          boton.className = "paleta__item";
          boton.setAttribute("role", "option");
          boton.setAttribute("aria-selected", "false");
          boton.dataset.url = item.url;

          var tituloItem = document.createElement("b");
          tituloItem.textContent = item.titulo;
          var detalle = document.createElement("small");
          detalle.textContent = item.subtitulo || "";

          boton.appendChild(tituloItem);
          boton.appendChild(detalle);
          boton.addEventListener("click", function () { abrir(item.url); });
          boton.addEventListener("mouseenter", function () {
            seleccionado = items.indexOf(boton);
            resaltar();
          });
          resultados.appendChild(boton);
          items.push(boton);
        });
      });

      seleccionado = 0;
      resaltar();
      entrada.setAttribute("aria-expanded", "true");
    }

    function resaltar() {
      items.forEach(function (item, indice) {
        item.setAttribute("aria-selected", indice === seleccionado ? "true" : "false");
      });
      var actual = items[seleccionado];
      if (actual && actual.scrollIntoView) actual.scrollIntoView({ block: "nearest" });
    }

    function abrir(url) {
      if (!url) return;
      if (url === "#tema") {
        cerrar();
        var botonTema = $("#boton-tema");
        if (botonTema) botonTema.click();
        return;
      }
      window.location.href = url;
    }

    function consultar(texto) {
      if (!CONFIG.urlBuscar) return;
      fetch(CONFIG.urlBuscar + "?q=" + encodeURIComponent(texto), {
        headers: { Accept: "application/json" }
      })
        .then(function (respuesta) { return respuesta.ok ? respuesta.json() : { grupos: [] }; })
        .then(function (datos) { pintar(datos.grupos || []); })
        .catch(function () {
          resultados.innerHTML = '<p class="paleta__vacio">No se pudo consultar el servidor.</p>';
        });
    }

    function abrirPaleta() {
      paleta.classList.add("abierto");
      entrada.value = "";
      entrada.focus();
      consultar("");
    }

    function cerrar() {
      paleta.classList.remove("abierto");
    }

    var disparador = $("#abrir-paleta");
    if (disparador) disparador.addEventListener("click", abrirPaleta);

    paleta.addEventListener("click", function (evento) {
      if (evento.target === paleta) cerrar();
    });

    entrada.addEventListener("input", function () {
      window.clearTimeout(temporizador);
      temporizador = window.setTimeout(function () { consultar(entrada.value.trim()); }, 140);
    });

    entrada.addEventListener("keydown", function (evento) {
      if (evento.key === "ArrowDown") {
        evento.preventDefault();
        seleccionado = Math.min(seleccionado + 1, items.length - 1);
        resaltar();
      } else if (evento.key === "ArrowUp") {
        evento.preventDefault();
        seleccionado = Math.max(seleccionado - 1, 0);
        resaltar();
      } else if (evento.key === "Enter") {
        evento.preventDefault();
        if (items[seleccionado]) abrir(items[seleccionado].dataset.url);
      } else if (evento.key === "Escape") {
        cerrar();
      }
    });

    // Atajo global: Ctrl+K o Cmd+K abre la paleta; "/" también, salvo que el
    // foco esté en un campo de formulario.
    document.addEventListener("keydown", function (evento) {
      var enCampo = /^(INPUT|TEXTAREA|SELECT)$/.test(evento.target.tagName || "");

      if ((evento.ctrlKey || evento.metaKey) && evento.key.toLowerCase() === "k") {
        evento.preventDefault();
        if (paleta.classList.contains("abierto")) cerrar();
        else abrirPaleta();
      } else if (evento.key === "/" && !enCampo) {
        evento.preventDefault();
        abrirPaleta();
      } else if (evento.key === "Escape" && paleta.classList.contains("abierto")) {
        cerrar();
      }
    });
  }

  /* ========================================================================
     6. Confirmación antes de acciones críticas
     ====================================================================== */
  function inicializarConfirmaciones() {
    $$("form[data-confirmar]").forEach(function (formulario) {
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
     7. Validación en el cliente
     ====================================================================== */
  function inicializarValidacion() {
    $$("form[data-validar]").forEach(function (formulario) {
      $$("input, select, textarea", formulario).forEach(function (campo) {
        campo.addEventListener("invalid", function () { campo.classList.add("invalido"); });
        campo.addEventListener("input", function () {
          campo.classList.toggle("invalido", !campo.checkValidity());
        });
        campo.addEventListener("blur", function () {
          campo.classList.toggle("invalido", !campo.checkValidity());
        });
      });

      formulario.addEventListener("submit", function (evento) {
        if (!formulario.checkValidity()) {
          evento.preventDefault();
          var primero = $(":invalid", formulario);
          if (primero) primero.focus();
          return false;
        }
        return true;
      });
    });
  }

  /* ========================================================================
     8. Búsqueda con retardo en los listados
     ====================================================================== */
  function inicializarBusquedaViva() {
    $$("form[data-buscar-auto]").forEach(function (formulario) {
      var entrada = $('input[name="q"]', formulario);
      if (!entrada) return;

      var temporizador = null;
      var original = entrada.value;

      entrada.addEventListener("input", function () {
        window.clearTimeout(temporizador);
        temporizador = window.setTimeout(function () {
          if (entrada.value.trim() !== original.trim()) formulario.submit();
        }, 420);
      });

      entrada.addEventListener("keydown", function (evento) {
        if (evento.key === "Escape") {
          entrada.value = "";
          formulario.submit();
        }
      });
    });
  }

  /* ========================================================================
     9. Formulario de reserva
     --------------------------------------------------------------------
     - Calcula la hora de finalización en vivo.
     - Dibuja la línea de tiempo del día con las franjas ya ocupadas.
     - Consulta la disponibilidad con fetch() y ofrece horarios alternativos.
     ====================================================================== */
  function aMinutos(hora) {
    var partes = String(hora || "").split(":");
    if (partes.length !== 2) return null;
    var horas = parseInt(partes[0], 10);
    var minutos = parseInt(partes[1], 10);
    if (isNaN(horas) || isNaN(minutos)) return null;
    return horas * 60 + minutos;
  }

  function aHora(total) {
    var horas = Math.floor(total / 60);
    var minutos = total % 60;
    return (horas < 10 ? "0" : "") + horas + ":" + (minutos < 10 ? "0" : "") + minutos;
  }

  function inicializarFormularioReserva() {
    var formulario = $("#formulario-reserva");
    if (!formulario) return;

    var selectLaboratorio = $("#campo-laboratorio_id");
    var campoFecha = $("#campo-fecha");
    var campoHora = $("#campo-hora_inicio");
    var campoDuracion = $("#campo-duracion_minutos");
    var salida = $("#campo-hora_fin_calculada");
    var botonEstandar = $("#boton-duracion-estandar");
    var botonDisponibilidad = $("#boton-disponibilidad");
    var resultado = $("#resultado-disponibilidad");
    var linea = $("#linea-tiempo");
    var alternativas = $("#alternativas");

    var duraciones = {};
    try {
      duraciones = JSON.parse(formulario.getAttribute("data-duraciones") || "{}");
    } catch (e) {
      duraciones = {};
    }
    var urlDisponibilidad = formulario.getAttribute("data-url-disponibilidad") || "";

    function duracionDelLaboratorio() {
      var valor = duraciones[selectLaboratorio ? selectLaboratorio.value : ""];
      return typeof valor === "number" ? valor : null;
    }

    function horaFinCalculada() {
      var inicio = aMinutos(campoHora ? campoHora.value : "");
      var duracion = parseInt(campoDuracion ? campoDuracion.value : "", 10);
      if (inicio === null || isNaN(duracion) || duracion <= 0) return "";
      return aHora(inicio + duracion);
    }

    function actualizarHoraFin() {
      if (!salida) return;
      salida.textContent = horaFinCalculada() || "—";
    }

    // --- Línea de tiempo del día ---
    function pintarLineaTiempo(ocupacion) {
      if (!linea) return;
      var apertura = 7 * 60;
      var cierre = 21 * 60;
      var total = cierre - apertura;

      if (!ocupacion || !ocupacion.length) {
        linea.innerHTML = '<p class="ayuda">No hay reservas para ese día: la jornada está completa disponible.</p>';
        return;
      }

      var html = '<div class="linea-tiempo__barra" role="img" aria-label="Ocupación del día">';
      ocupacion.forEach(function (franja) {
        var inicio = aMinutos(franja.hora_inicio);
        var fin = aMinutos(franja.hora_fin);
        if (inicio === null || fin === null) return;
        var izquierda = Math.max(0, (inicio - apertura) * 100 / total);
        var ancho = Math.max(1.5, (fin - inicio) * 100 / total);
        html += '<span class="linea-tiempo__franja" style="left:' + izquierda.toFixed(2) +
                "%;width:" + ancho.toFixed(2) + '%" title="' +
                franja.hora_inicio + " – " + franja.hora_fin + '"></span>';
      });
      html += "</div>";
      html += '<div class="linea-tiempo__escala"><span>07:00</span><span>11:00</span>' +
              "<span>15:00</span><span>21:00</span></div>";
      linea.innerHTML = html;
    }

    function consultarOcupacion() {
      if (!urlDisponibilidad || !selectLaboratorio || !campoFecha) return;
      var laboratorio = selectLaboratorio.value;
      var fecha = campoFecha.value;
      if (!laboratorio || !fecha) {
        pintarLineaTiempo([]);
        return;
      }

      var parametros = new URLSearchParams({ laboratorio_id: laboratorio, fecha: fecha });
      fetch(urlDisponibilidad + "?" + parametros.toString(), { headers: { Accept: "application/json" } })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (datos) { if (datos) pintarLineaTiempo(datos.ocupacion); })
        .catch(function () { /* informativo: si falla, no se interrumpe el formulario */ });
    }

    if (selectLaboratorio) {
      selectLaboratorio.addEventListener("change", function () {
        var estandar = duracionDelLaboratorio();
        if (estandar !== null && campoDuracion) campoDuracion.value = estandar;
        actualizarHoraFin();
        consultarOcupacion();
      });
    }
    if (campoFecha) campoFecha.addEventListener("change", consultarOcupacion);

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

    [campoHora, campoDuracion].forEach(function (campo) {
      if (!campo) return;
      campo.addEventListener("input", actualizarHoraFin);
      campo.addEventListener("change", actualizarHoraFin);
    });

    // --- Verificación con fetch() y alternativas ---
    if (botonDisponibilidad && resultado) {
      botonDisponibilidad.addEventListener("click", function () {
        var laboratorio = selectLaboratorio ? selectLaboratorio.value : "";
        var fecha = campoFecha ? campoFecha.value : "";
        var inicio = campoHora ? campoHora.value : "";
        var fin = horaFinCalculada();
        var duracion = parseInt(campoDuracion ? campoDuracion.value : "", 10);

        if (!laboratorio || !fecha || !inicio || !fin) {
          resultado.className = "resultado-disponibilidad es-error";
          resultado.textContent = "Completa laboratorio, fecha, hora de inicio y duración.";
          return;
        }

        resultado.className = "resultado-disponibilidad cargando";
        resultado.textContent = "Consultando disponibilidad…";

        var parametros = new URLSearchParams({
          laboratorio_id: laboratorio,
          fecha: fecha,
          hora_inicio: inicio,
          hora_fin: fin,
          duracion: duracion
        });

        fetch(urlDisponibilidad + "?" + parametros.toString(), { headers: { Accept: "application/json" } })
          .then(function (r) {
            if (!r.ok) throw new Error(String(r.status));
            return r.json();
          })
          .then(function (datos) {
            pintarLineaTiempo(datos.ocupacion);
            resultado.className = "resultado-disponibilidad " + (datos.disponible ? "es-ok" : "es-error");
            resultado.textContent = (datos.disponible ? "✔ " : "✖ ") + datos.mensaje +
                                    " (franja " + inicio + " – " + fin + ")";

            if (!alternativas) return;
            alternativas.innerHTML = "";

            if (datos.sugerencias && datos.sugerencias.length) {
              var titulo = document.createElement("p");
              titulo.className = "ayuda";
              titulo.textContent = "Franjas libres más cercanas (haz clic en una para usarla):";
              alternativas.appendChild(titulo);

              var fila = document.createElement("div");
              fila.className = "alternativas__fila";
              datos.sugerencias.forEach(function (sugerencia) {
                var boton = document.createElement("button");
                boton.type = "button";
                boton.className = "alternativa";
                var fuerte = document.createElement("b");
                fuerte.textContent = sugerencia.hora_inicio + " – " + sugerencia.hora_fin;
                var pequeno = document.createElement("small");
                pequeno.textContent = "libre hasta " + sugerencia.libre_hasta;
                boton.appendChild(fuerte);
                boton.appendChild(pequeno);
                boton.addEventListener("click", function () {
                  if (campoHora) campoHora.value = sugerencia.hora_inicio;
                  actualizarHoraFin();
                  resultado.className = "resultado-disponibilidad es-ok";
                  resultado.textContent = "Franja aplicada: " + sugerencia.hora_inicio + " – " +
                                          sugerencia.hora_fin + ". Ya puedes guardar la reserva.";
                });
                fila.appendChild(boton);
              });
              alternativas.appendChild(fila);
            }
          })
          .catch(function () {
            resultado.className = "resultado-disponibilidad es-error";
            resultado.textContent = "No se pudo verificar la disponibilidad. Inténtalo de nuevo.";
          });
      });
    }

    actualizarHoraFin();
    consultarOcupacion();

    // Las alternativas que el servidor ya dibujó (cuando rechazó una reserva por
    // solapamiento) se comportan igual que las que llegan por fetch().
    $$(".alternativa[data-hora]").forEach(function (boton) {
      boton.addEventListener("click", function () {
        if (campoHora) campoHora.value = boton.getAttribute("data-hora");
        actualizarHoraFin();
        if (resultado) {
          resultado.className = "resultado-disponibilidad es-ok";
          resultado.textContent = "Franja aplicada: " + boton.getAttribute("data-hora") +
                                  ". Ya puedes guardar la reserva.";
        }
      });
    });
  }

  /* ========================================================================
     10. Contadores animados
     ====================================================================== */
  function inicializarContadores() {
    var nodos = $$("[data-contador]");
    if (!nodos.length) return;

    function animar(nodo) {
      var destino = parseFloat(nodo.getAttribute("data-contador")) || 0;
      var duracion = 750;
      var inicio = null;

      function paso(marca) {
        if (inicio === null) inicio = marca;
        var avance = Math.min((marca - inicio) / duracion, 1);
        // Suavizado de salida: arranca rápido y frena al final.
        var suave = 1 - Math.pow(1 - avance, 3);
        nodo.textContent = Math.round(destino * suave).toLocaleString("es-VE");
        if (avance < 1) window.requestAnimationFrame(paso);
        else nodo.textContent = destino.toLocaleString("es-VE");
      }
      window.requestAnimationFrame(paso);
    }

    if (!("IntersectionObserver" in window)) {
      nodos.forEach(animar);
      return;
    }

    var observador = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (entrada) {
        if (entrada.isIntersecting) {
          animar(entrada.target);
          observador.unobserve(entrada.target);
        }
      });
    }, { threshold: 0.35 });

    nodos.forEach(function (nodo) { observador.observe(nodo); });
  }

  /* ========================================================================
     11. Protección contra el doble envío
     ====================================================================== */
  function inicializarAntiDobleEnvio() {
    $$("form[data-validar]").forEach(function (formulario) {
      formulario.addEventListener("submit", function () {
        var boton = $('button[type="submit"]', formulario);
        if (!boton) return;
        window.setTimeout(function () {
          boton.disabled = true;
          boton.classList.add("cargando");
          boton.textContent = "Guardando…";
        }, 0);
      });
    });
  }

  /* ========================================================================
     Arranque
     ====================================================================== */
  /* ======================================================================
     12. Botón de ver/ocultar la contraseña

     Sin esto, quien escribe una contraseña con mayúsculas, números y símbolos
     no puede comprobar qué tecleó: los puntos no permiten detectar un error.
     El botón se añade a TODOS los input[type=password] de la página, así que
     cubre registro, perfil y alta de usuarios sin tocar las plantillas.

     Es solo una mejora de la experiencia: el valor que se envía al servidor es
     exactamente el mismo, y la validación sigue siendo la del servidor.
     ====================================================================== */
  function inicializarVerContrasena() {
    var OJO = "M12 5c-5 0-9 4.5-10 7 1 2.5 5 7 10 7s9-4.5 10-7c-1-2.5-5-7-10-7zm0 " +
              "11a4 4 0 110-8 4 4 0 010 8zm0-1.6a2.4 2.4 0 100-4.8 2.4 2.4 0 000 4.8z";
    var OJO_TACHADO =
      "M3 3l18 18M12 5c-5 0-9 4.5-10 7 1 2.5 5 7 10 7 1.6 0 3-.4 4.3-1M12 5c5 0 9 4.5 10 7-.4 1-1.2 2.2-2.3 3.4M12 16a4 4 0 01-4-4";

    function icono(ruta) {
      var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      svg.setAttribute("viewBox", "0 0 24 24");
      svg.setAttribute("width", "18");
      svg.setAttribute("height", "18");
      svg.setAttribute("fill", "none");
      svg.setAttribute("stroke", "currentColor");
      svg.setAttribute("stroke-width", "1.7");
      svg.setAttribute("stroke-linecap", "round");
      svg.setAttribute("stroke-linejoin", "round");
      svg.setAttribute("aria-hidden", "true");
      var trazado = document.createElementNS("http://www.w3.org/2000/svg", "path");
      trazado.setAttribute("d", ruta);
      svg.appendChild(trazado);
      return svg;
    }

    var campos = document.querySelectorAll('input[type="password"]');
    for (var i = 0; i < campos.length; i++) {
      (function (campo) {
        // No repetir el botón si la página ya lo trae.
        if (campo.dataset.conBotonVer) { return; }
        campo.dataset.conBotonVer = "1";

        var boton = document.createElement("button");
        boton.type = "button";
        boton.className = "boton-ver-contrasena";
        boton.setAttribute("aria-label", "Mostrar la contraseña");
        boton.setAttribute("aria-pressed", "false");
        boton.appendChild(icono(OJO));

        boton.addEventListener("click", function () {
          var visible = campo.type === "text";
          campo.type = visible ? "password" : "text";
          boton.setAttribute("aria-pressed", visible ? "false" : "true");
          boton.setAttribute("aria-label", visible ? "Mostrar la contraseña"
                                                   : "Ocultar la contraseña");
          while (boton.firstChild) { boton.removeChild(boton.firstChild); }
          boton.appendChild(icono(visible ? OJO : OJO_TACHADO));
          campo.focus();
        });

        // El botón se coloca dentro de un envoltorio que contiene SOLO el input,
        // para poder centrarlo sobre el campo sin depender de la altura del
        // rótulo (.campo es una columna con el label encima).
        var contenedor = campo.closest(".campo");
        if (!contenedor) {
          contenedor = campo.parentNode;
        }
        var envoltorio = document.createElement("span");
        envoltorio.className = "campo-contrasena";
        campo.parentNode.insertBefore(envoltorio, campo);
        envoltorio.appendChild(campo);
        envoltorio.appendChild(boton);
      })(campos[i]);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    inicializarTema();
    inicializarLateral();
    inicializarMenus();
    inicializarNotificaciones();
    inicializarPaleta();
    inicializarConfirmaciones();
    inicializarValidacion();
    inicializarBusquedaViva();
    inicializarFormularioReserva();
    inicializarContadores();
    inicializarAntiDobleEnvio();
    inicializarVerContrasena();
  });
})();
