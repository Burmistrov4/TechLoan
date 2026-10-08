/* ==========================================================================
   TechLoan — Interacciones de la portada pública
   --------------------------------------------------------------------------
   Aporta el movimiento de la landing page, todo con JavaScript Vanilla:

     1. Escena 3D del héroe: la captura se inclina siguiendo el puntero.
     2. Revelado progresivo de las secciones al desplazar (IntersectionObserver).
     3. Pestañas de los módulos, con cambio de ilustración.
     4. Desplazamiento suave para los enlaces internos.

   Respeta ``prefers-reduced-motion``: si el usuario pide menos movimiento, se
   desactivan la inclinación y las animaciones de aparición.
   ========================================================================== */

(function () {
  "use strict";

  var prefiereQuieto = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ========================================================================
     1. Escena 3D del héroe
     ====================================================================== */
  function inicializarEscena() {
    var escena = document.getElementById("escena-3d");
    var marco = document.getElementById("marco-3d");
    if (!escena || !marco || prefiereQuieto) return;

    var objetivo = { x: 0, y: 0 };
    var actual = { x: 0, y: 0 };
    var animando = false;

    function animar() {
      // Interpolación suave hacia el objetivo: da sensación de peso y evita
      // que el marco siga al puntero de forma nerviosa.
      actual.x += (objetivo.x - actual.x) * 0.09;
      actual.y += (objetivo.y - actual.y) * 0.09;

      marco.style.transform =
        "rotateY(" + actual.x.toFixed(3) + "deg) rotateX(" + actual.y.toFixed(3) + "deg)";

      if (Math.abs(objetivo.x - actual.x) > 0.01 || Math.abs(objetivo.y - actual.y) > 0.01) {
        window.requestAnimationFrame(animar);
      } else {
        animando = false;
      }
    }

    function arrancar() {
      if (!animando) {
        animando = true;
        window.requestAnimationFrame(animar);
      }
    }

    escena.addEventListener("mousemove", function (evento) {
      var caja = escena.getBoundingClientRect();
      var relX = (evento.clientX - caja.left) / caja.width - 0.5;
      var relY = (evento.clientY - caja.top) / caja.height - 0.5;
      objetivo.x = relX * 16;   // giro horizontal
      objetivo.y = -relY * 12;  // giro vertical
      arrancar();
    });

    escena.addEventListener("mouseleave", function () {
      objetivo.x = 0;
      objetivo.y = 0;
      arrancar();
    });
  }

  /* ========================================================================
     2. Revelado progresivo al desplazar
     ====================================================================== */
  function inicializarRevelado() {
    var nodos = Array.prototype.slice.call(document.querySelectorAll(".revelar"));
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
     ====================================================================== */
  function inicializarModulos() {
    var pestanas = Array.prototype.slice.call(document.querySelectorAll("[data-modulo]"));
    if (!pestanas.length) return;

    var imagen = document.getElementById("imagen-modulo-img");
    var fuente = document.querySelector("#imagen-modulo source");

    function activar(nombre) {
      pestanas.forEach(function (pestana) {
        pestana.setAttribute("aria-selected", pestana.dataset.modulo === nombre ? "true" : "false");
      });

      document.querySelectorAll(".modulo").forEach(function (modulo) {
        modulo.classList.toggle("activo", modulo.id === "modulo-" + nombre);
      });

      if (imagen) {
        imagen.src = "/static/img/mod-" + nombre + ".jpg";
        imagen.alt = "Módulo de " + nombre + " de TechLoan";
      }
      if (fuente) {
        fuente.srcset = "/static/img/mod-" + nombre + ".webp";
      }
    }

    pestanas.forEach(function (pestana) {
      pestana.addEventListener("click", function () { activar(pestana.dataset.modulo); });
    });
  }

  /* ========================================================================
     4. Desplazamiento suave de los enlaces internos
     ====================================================================== */
  function inicializarAnclas() {
    document.querySelectorAll('a[href^="#"]').forEach(function (enlace) {
      enlace.addEventListener("click", function (evento) {
        var destino = document.querySelector(enlace.getAttribute("href"));
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
    inicializarEscena();
    inicializarRevelado();
    inicializarModulos();
    inicializarAnclas();
  });
})();
