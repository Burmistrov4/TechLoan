/* ==========================================================================
   TechLoan — Tutorial guiado (walkthrough)
   --------------------------------------------------------------------------
   Recorrido interactivo por la interfaz para que un usuario nuevo entienda el
   sistema en menos de un minuto.

   Cómo funciona
     · El fondo se oscurece con un único elemento colocado sobre el elemento
       señalado y una sombra enorme alrededor: el foco es un agujero real.
     · Los pasos se declaran abajo. Si un paso apunta a un elemento que no
       existe en la página actual, se descarta sin más: el mismo tutorial sirve
       en cualquier pantalla.
     · Se lanza solo la primera vez que el usuario entra al panel, o cuando
       llega con ``?tutorial=1`` (enlace del menú de usuario y de la guía).
       El estado se guarda en localStorage.

   Todo es JavaScript Vanilla, sin dependencias.
   ========================================================================== */

(function () {
  "use strict";

  var CLAVE = "techloan-tutorial";

  /* ------------------------------------------------------------------------
     Pasos del recorrido
     --------------------------------------------------------------------- */
  var PASOS = [
    {
      titulo: "Bienvenido a TechLoan",
      texto: "Te muestro dónde está cada cosa en menos de un minuto. Puedes " +
             "salir cuando quieras y repetirlo luego desde tu menú de usuario."
    },
    {
      selector: ".lateral__nav",
      titulo: "Todo el sistema, agrupado por tareas",
      texto: "El menú separa lo general, la operación diaria, el catálogo y la " +
             "administración. Lo que tu rol no permite ver, sencillamente no aparece."
    },
    {
      selector: "#abrir-paleta",
      titulo: "Busca o salta a cualquier parte",
      texto: "Haz clic aquí o presiona <kbd>Ctrl</kbd>+<kbd>K</kbd> y escribe. " +
             "Encuentra secciones, acciones y también registros concretos: " +
             "prestatarios, equipos, laboratorios y reservas."
    },
    {
      selector: "#boton-tema",
      titulo: "Claro u oscuro, como prefieras",
      texto: "El tema que elijas se guarda en tu navegador: la próxima vez " +
             "entrarás directamente con él."
    },
    {
      selector: "#boton-alertas",
      titulo: "Lo que necesita tu atención",
      texto: "Aquí se acumulan los préstamos con demasiados días sin devolver, " +
             "las reservas de hoy y los laboratorios con más demanda."
    },
    {
      selector: ".tarjetas-tablero",
      titulo: "El panel, de un solo vistazo",
      texto: "Los indicadores resumen el estado del sistema, y debajo tienes los " +
             "gráficos de ocupación y la actividad reciente."
    },
    {
      selector: "#contenedor-usuario",
      titulo: "Tu cuenta",
      texto: "Desde aquí cambias tu contraseña, abres la guía de uso o cierras " +
             "la sesión. Y puedes volver a ver este tutorial cuando quieras."
    },
    {
      titulo: "Listo para empezar",
      texto: "Ya conoces lo esencial. Si más adelante te pierdes, la " +
             "<strong>Guía de uso</strong> del menú tiene el detalle de cada tarea."
    }
  ];

  var pasos = [];
  var indice = 0;
  var abierto = false;

  var capa = null;
  var foco = null;
  var tarjeta = null;
  var contador = null;
  var titulo = null;
  var texto = null;
  var progreso = null;
  var btnAnterior = null;
  var btnSiguiente = null;
  var btnSaltar = null;
  var btnCerrar = null;

  function $(selector) {
    return document.querySelector(selector);
  }

  /* ------------------------------------------------------------------------
     Colocación de la tarjeta
     --------------------------------------------------------------------- */
  function colocarTarjeta(caja) {
    var anchoTarjeta = tarjeta.offsetWidth;
    var altoTarjeta = tarjeta.offsetHeight;
    var vw = window.innerWidth;
    var vh = window.innerHeight;
    var hueco = 16;
    var izquierda;
    var arriba;

    if (caja.right < 340) {
      // Elemento pegado al borde izquierdo (barra lateral): a su derecha.
      izquierda = caja.right + hueco;
      arriba = caja.top;
    } else if (caja.bottom + hueco + altoTarjeta <= vh) {
      izquierda = caja.left;
      arriba = caja.bottom + hueco;
    } else {
      // No cabe debajo: se pone encima.
      izquierda = caja.left;
      arriba = caja.top - hueco - altoTarjeta;
    }

    izquierda = Math.max(hueco, Math.min(izquierda, vw - anchoTarjeta - hueco));
    arriba = Math.max(hueco, Math.min(arriba, vh - altoTarjeta - hueco));

    tarjeta.style.left = izquierda + "px";
    tarjeta.style.top = arriba + "px";
  }

  function colocarCentrada() {
    var anchoTarjeta = tarjeta.offsetWidth;
    var altoTarjeta = tarjeta.offsetHeight;
    tarjeta.style.left = Math.max(16, (window.innerWidth - anchoTarjeta) / 2) + "px";
    tarjeta.style.top = Math.max(16, (window.innerHeight - altoTarjeta) / 2) + "px";
  }

  /* ------------------------------------------------------------------------
     Navegación entre pasos
     --------------------------------------------------------------------- */
  function mostrar(nuevo) {
    indice = Math.max(0, Math.min(nuevo, pasos.length - 1));
    var paso = pasos[indice];

    contador.textContent = "Paso " + (indice + 1) + " de " + pasos.length;
    titulo.textContent = paso.titulo;
    texto.innerHTML = paso.texto;
    progreso.style.width = ((indice + 1) * 100 / pasos.length).toFixed(2) + "%";

    btnAnterior.disabled = indice === 0;
    btnSiguiente.textContent = indice === pasos.length - 1 ? "Terminar" : "Siguiente";

    var destino = paso.selector ? document.querySelector(paso.selector) : null;

    if (!destino) {
      // Paso sin elemento señalado: se oscurece todo y la tarjeta se centra.
      capa.classList.add("tutorial--centrado");
      foco.style.opacity = "0";
      colocarCentrada();
      btnSiguiente.focus();
      return;
    }

    capa.classList.remove("tutorial--centrado");
    foco.style.opacity = "1";

    // Desplazamiento instantáneo: así la medida es fiable. El movimiento lo
    // aporta el propio foco, que se desliza hasta su nueva posición.
    destino.scrollIntoView({ block: "center", behavior: "auto" });

    var caja = destino.getBoundingClientRect();
    var margen = 8;
    foco.style.top = (caja.top - margen) + "px";
    foco.style.left = (caja.left - margen) + "px";
    foco.style.width = (caja.width + margen * 2) + "px";
    foco.style.height = (caja.height + margen * 2) + "px";

    colocarTarjeta(caja);
    btnSiguiente.focus();
  }

  function reposicionar() {
    if (!abierto) return;
    var paso = pasos[indice];
    var destino = paso && paso.selector ? document.querySelector(paso.selector) : null;
    if (!destino) {
      colocarCentrada();
      return;
    }
    var caja = destino.getBoundingClientRect();
    var margen = 8;
    foco.style.top = (caja.top - margen) + "px";
    foco.style.left = (caja.left - margen) + "px";
    foco.style.width = (caja.width + margen * 2) + "px";
    foco.style.height = (caja.height + margen * 2) + "px";
    colocarTarjeta(caja);
  }

  /* ------------------------------------------------------------------------
     Abrir y cerrar
     --------------------------------------------------------------------- */
  function abrir(desdeElPrincipio) {
    if (abierto) return;
    abierto = true;
    capa.hidden = false;
    document.body.classList.add("tutorial-abierto");
    mostrar(desdeElPrincipio === false ? indice : 0);
  }

  function cerrar(marcarVisto) {
    if (!abierto) return;
    abierto = false;
    capa.hidden = true;
    capa.classList.remove("tutorial--centrado");
    document.body.classList.remove("tutorial-abierto");

    if (marcarVisto !== false) {
      try { localStorage.setItem(CLAVE, "visto"); } catch (e) { /* modo privado */ }
    }

    // Se limpia el parámetro de la URL para que recargar no relance el tutorial.
    if (/[?&]tutorial=1/.test(window.location.search)) {
      var limpia = window.location.search
        .replace(/([?&])tutorial=1(&?)/, function (todo, signo, cola) {
          return cola ? signo : "";
        })
        .replace(/[?&]$/, "");
      window.history.replaceState(null, "", window.location.pathname + limpia + window.location.hash);
    }
  }

  /* ------------------------------------------------------------------------
     Arranque
     --------------------------------------------------------------------- */
  function esElPanel() {
    return !!document.querySelector(".tarjetas-tablero");
  }

  function iniciar() {
    capa = $("#tutorial");
    if (!capa) return;

    foco = $("#tutorial-foco");
    tarjeta = $("#tutorial-tarjeta");
    contador = $("#tutorial-contador");
    titulo = $("#tutorial-titulo");
    texto = $("#tutorial-texto");
    progreso = $("#tutorial-progreso");
    btnAnterior = $("#tutorial-anterior");
    btnSiguiente = $("#tutorial-siguiente");
    btnSaltar = $("#tutorial-saltar");
    btnCerrar = $("#tutorial-cerrar");

    if (!foco || !tarjeta || !btnSiguiente) return;

    // Solo se conservan los pasos cuyo elemento existe en esta pantalla.
    pasos = PASOS.filter(function (paso) {
      return !paso.selector || !!document.querySelector(paso.selector);
    });
    if (!pasos.length) return;

    btnSiguiente.addEventListener("click", function () {
      if (indice === pasos.length - 1) cerrar();
      else mostrar(indice + 1);
    });
    btnAnterior.addEventListener("click", function () { mostrar(indice - 1); });
    btnSaltar.addEventListener("click", function () { cerrar(); });
    btnCerrar.addEventListener("click", function () { cerrar(); });

    // Clic en el velo (fuera de la tarjeta): se cierra.
    capa.addEventListener("click", function (evento) {
      if (evento.target === capa || evento.target === foco) cerrar();
    });

    document.addEventListener("keydown", function (evento) {
      if (!abierto) return;
      if (evento.key === "Escape") {
        evento.preventDefault();
        cerrar();
      } else if (evento.key === "ArrowRight") {
        evento.preventDefault();
        if (indice === pasos.length - 1) cerrar();
        else mostrar(indice + 1);
      } else if (evento.key === "ArrowLeft") {
        evento.preventDefault();
        mostrar(indice - 1);
      }
    });

    window.addEventListener("resize", reposicionar);
    window.addEventListener("scroll", function () {
      if (abierto) window.requestAnimationFrame(reposicionar);
    }, { passive: true });

    var porParametro = /[?&]tutorial=1/.test(window.location.search);
    var yaVisto = false;
    try { yaVisto = localStorage.getItem(CLAVE) === "visto"; } catch (e) { /* modo privado */ }

    if (porParametro || (esElPanel() && !yaVisto)) {
      // Pequeña espera: deja que la página termine de pintarse y de colocar los
      // gráficos antes de medir posiciones.
      window.setTimeout(function () { abrir(); }, 650);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
