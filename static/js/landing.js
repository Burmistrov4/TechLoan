/* ==========================================================================
   TechLoan — Interacciones de la portada pública
   --------------------------------------------------------------------------
   Movimiento de la landing page, todo con JavaScript Vanilla:

     1. Escenas 3D: escalado uniforme, inclinación con el puntero y giro
        arrastrando. Los objetos son DOM real con CSS 3D, no imágenes ni WebGL.
     2. Revelado progresivo de las secciones al desplazar (IntersectionObserver).
     3. Pestañas de los módulos: fundido cruzado entre los cuatro objetos 3D.
     4. Desplazamiento suave para los enlaces internos.

   Respeta ``prefers-reduced-motion``: si el usuario pide menos movimiento, la
   escena se queda quieta y los objetos dejan de girar.
   ========================================================================== */

(function () {
  "use strict";

  var prefiereQuieto = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function $(selector, ambito) {
    return (ambito || document).querySelector(selector);
  }

  function $$(selector, ambito) {
    return Array.prototype.slice.call((ambito || document).querySelectorAll(selector));
  }

  /* ========================================================================
     1. Escenas 3D
     ====================================================================== */
  var ANCHO_MUNDO = 520;           // el interior de la escena siempre mide 520 x 400
  var REPOSO = { x: -8, y: -16 };  // rotación cuando nadie interactúa

  function inicializarEscenas() {
    var escenas = $$(".e3d");
    if (!escenas.length) return;

    escenas.forEach(function (escena) {
      var escala = $(".e3d__escala", escena);
      var lienzo = $(".e3d__lienzo", escena);
      var mundo = $("[data-orbita]", escena);
      if (!escala || !lienzo) return;

      // --- Escalado: el interior trabaja en píxeles fijos y se reduce con scale() ---
      function ajustarEscala() {
        var ancho = escena.clientWidth;
        if (!ancho) return;
        escala.style.transform = "scale(" + (ancho / ANCHO_MUNDO).toFixed(4) + ")";
      }

      if ("ResizeObserver" in window) {
        new ResizeObserver(ajustarEscala).observe(escena);
      } else {
        window.addEventListener("resize", ajustarEscala);
      }
      ajustarEscala();

      if (!mundo || prefiereQuieto) return;

      var objetivo = { x: REPOSO.x, y: REPOSO.y };
      var actual = { x: REPOSO.x, y: REPOSO.y };
      var animando = false;
      var arrastrando = false;
      var ultimo = null;
      var temporizador = null;

      function pintar() {
        // Interpolación: da sensación de peso y evita que la escena siga al
        // puntero de forma nerviosa.
        actual.x += (objetivo.x - actual.x) * 0.12;
        actual.y += (objetivo.y - actual.y) * 0.12;
        lienzo.style.transform =
          "rotateX(" + actual.x.toFixed(3) + "deg) rotateY(" + actual.y.toFixed(3) + "deg)";

        if (Math.abs(objetivo.x - actual.x) > 0.02 || Math.abs(objetivo.y - actual.y) > 0.02) {
          window.requestAnimationFrame(pintar);
        } else {
          animando = false;
        }
      }

      function arrancar() {
        if (!animando) {
          animando = true;
          window.requestAnimationFrame(pintar);
        }
      }

      // Tras un rato sin tocar nada, la escena vuelve sola a su pose de reposo.
      function programarReposo() {
        window.clearTimeout(temporizador);
        temporizador = window.setTimeout(function () {
          objetivo.x = REPOSO.x;
          objetivo.y = REPOSO.y;
          arrancar();
        }, 2600);
      }

      escena.addEventListener("pointermove", function (evento) {
        if (arrastrando) {
          var dx = evento.clientX - ultimo.x;
          var dy = evento.clientY - ultimo.y;
          ultimo = { x: evento.clientX, y: evento.clientY };
          objetivo.y = Math.max(-72, Math.min(72, objetivo.y + dx * 0.42));
          objetivo.x = Math.max(-48, Math.min(48, objetivo.x - dy * 0.32));
          arrancar();
          return;
        }

        // En táctil no existe "pasar por encima": solo cuenta el arrastre.
        if (evento.pointerType === "touch") return;

        var caja = escena.getBoundingClientRect();
        if (!caja.width || !caja.height) return;
        var relX = (evento.clientX - caja.left) / caja.width - 0.5;
        var relY = (evento.clientY - caja.top) / caja.height - 0.5;
        objetivo.x = REPOSO.x - relY * 11;
        objetivo.y = REPOSO.y + relX * 20;
        arrancar();
      });

      mundo.addEventListener("pointerdown", function (evento) {
        arrastrando = true;
        ultimo = { x: evento.clientX, y: evento.clientY };
        mundo.classList.add("arrastrando");
        window.clearTimeout(temporizador);
        if (mundo.setPointerCapture) {
          try { mundo.setPointerCapture(evento.pointerId); } catch (e) { /* sin captura */ }
        }
      });

      function soltar(evento) {
        if (!arrastrando) return;
        arrastrando = false;
        mundo.classList.remove("arrastrando");
        if (mundo.releasePointerCapture && evento && evento.pointerId !== undefined) {
          try { mundo.releasePointerCapture(evento.pointerId); } catch (e) { /* ya liberado */ }
        }
        programarReposo();
      }

      mundo.addEventListener("pointerup", soltar);
      mundo.addEventListener("pointercancel", soltar);

      escena.addEventListener("pointerleave", function () {
        if (arrastrando) return;
        objetivo.x = REPOSO.x;
        objetivo.y = REPOSO.y;
        arrancar();
      });

      pintar();
    });
  }

  /* ========================================================================
     2. Revelado progresivo al desplazar
     ====================================================================== */
  function inicializarRevelado() {
    var nodos = $$(".revelar");
    if (!nodos.length) return;

    if (prefiereQuieto || !("IntersectionObserver" in window)) {
      nodos.forEach(function (nodo) { nodo.classList.add("visible"); });
      return;
    }

    var observador = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (entrada) {
        if (entrada.isIntersecting) {
          entrada.target.classList.add("visible");
          observador.unobserve(entrada.target);
        }
      });
    }, { threshold: 0.14, rootMargin: "0px 0px -60px 0px" });

    nodos.forEach(function (nodo) { observador.observe(nodo); });

    // Red de seguridad: si algo impidiera al observador disparar, el contenido
    // nunca debe quedarse invisible. A los 3 segundos se muestra lo que falte.
    window.setTimeout(function () {
      nodos.forEach(function (nodo) {
        if (!nodo.classList.contains("visible")) nodo.classList.add("visible");
      });
    }, 3000);
  }

  /* ========================================================================
     3. Pestañas de los módulos
     --------------------------------------------------------------------
     Cada pestaña activa su objeto 3D. El fundido cruzado lo resuelve el CSS
     (.e3d-modulo.activo), así que aquí solo se conmuta la clase.
     ====================================================================== */
  function inicializarModulos() {
    var pestanas = $$("[data-modulo]");
    if (!pestanas.length) return;

    var escenario = $("#imagen-modulo");
    var objetos = escenario ? $$("[data-objeto]", escenario) : [];

    function activar(nombre) {
      pestanas.forEach(function (pestana) {
        pestana.setAttribute("aria-selected", pestana.dataset.modulo === nombre ? "true" : "false");
      });

      $$(".modulo").forEach(function (modulo) {
        modulo.classList.toggle("activo", modulo.id === "modulo-" + nombre);
      });

      objetos.forEach(function (objeto) {
        objeto.classList.toggle("activo", objeto.dataset.objeto === nombre);
      });
    }

    pestanas.forEach(function (pestana) {
      pestana.addEventListener("click", function () { activar(pestana.dataset.modulo); });
    });
  }

  /* ========================================================================
     4. Desplazamiento suave de los enlaces internos
     ====================================================================== */
  function inicializarAnclas() {
    $$('a[href^="#"]').forEach(function (enlace) {
      enlace.addEventListener("click", function (evento) {
        var destino = $(enlace.getAttribute("href"));
        if (!destino) return;
        evento.preventDefault();
        destino.scrollIntoView({
          behavior: prefiereQuieto ? "auto" : "smooth",
          block: "start"
        });
        history.replaceState(null, "", enlace.getAttribute("href"));
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    inicializarEscenas();
    inicializarRevelado();
    inicializarModulos();
    inicializarAnclas();
  });
})();
