/* ==========================================================================
   TechLoan — Gráficos SVG generados en el cliente
   --------------------------------------------------------------------------
   Dibuja gráficos de barras, anillo y barras horizontales usando SVG en línea,
   SIN librerías externas y SIN peticiones de red. Los datos llegan del servidor
   en atributos ``data-datos`` de cada contenedor.

   Ventajas de este enfoque para el proyecto:
     - Funciona sin conexión a internet.
     - Los colores se toman de las variables CSS, así que los gráficos cambian
       automáticamente con el tema claro/oscuro.
     - El SVG resultante es accesible y se imprime con calidad.

   Uso desde una plantilla:
     <div class="grafico-contenedor" data-grafico="barras" data-datos='[...]'></div>
   ========================================================================== */

(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";
  var contenedores = [];

  function variable(nombre, alternativa) {
    var valor = getComputedStyle(document.documentElement).getPropertyValue(nombre);
    return (valor || "").trim() || alternativa;
  }

  function paleta() {
    return [
      variable("--grafico-1", "#3b82f6"),
      variable("--grafico-2", "#8b5cf6"),
      variable("--grafico-3", "#22d3ee"),
      variable("--grafico-4", "#f59e0b"),
      variable("--grafico-5", "#10b981")
    ];
  }

  function leerDatos(nodo) {
    try {
      return JSON.parse(nodo.getAttribute("data-datos") || "[]");
    } catch (e) {
      return [];
    }
  }

  function svg(cadena) {
    return '<svg class="grafico" viewBox="0 0 640 220" preserveAspectRatio="xMidYMid meet" ' +
           'role="img">' + cadena + "</svg>";
  }

  /* ----------------------------------------------------------------------
     Gráfico de barras verticales
     -------------------------------------------------------------------- */
  function barras(nodo, serie) {
    if (!serie.length) {
      nodo.innerHTML = '<p class="vacio">Sin datos para representar.</p>';
      return;
    }

    var colores = paleta();
    var ancho = 640;
    var alto = 220;
    var margen = { arriba: 24, derecha: 12, abajo: 34, izquierda: 34 };
    var anchoUtil = ancho - margen.izquierda - margen.derecha;
    var altoUtil = alto - margen.arriba - margen.abajo;

    var maximo = Math.max.apply(null, serie.map(function (p) { return p.valor; }));
    maximo = Math.max(maximo, 1);

    var paso = anchoUtil / serie.length;
    var anchoBarra = Math.min(paso * 0.62, 34);

    var partes = [];

    // Líneas de referencia horizontales
    for (var i = 0; i <= 4; i++) {
      var y = margen.arriba + (altoUtil * i) / 4;
      partes.push('<line class="grafico__rejilla" x1="' + margen.izquierda + '" x2="' +
                  (ancho - margen.derecha) + '" y1="' + y.toFixed(1) + '" y2="' + y.toFixed(1) + '"/>');
    }

    serie.forEach(function (punto, indice) {
      var altura = (punto.valor / maximo) * altoUtil;
      var x = margen.izquierda + paso * indice + (paso - anchoBarra) / 2;
      var y = margen.arriba + altoUtil - altura;
      var color = punto.es_hoy ? colores[1] : colores[0];

      partes.push(
        '<rect class="grafico__barra" x="' + x.toFixed(1) + '" y="' + y.toFixed(1) +
        '" width="' + anchoBarra.toFixed(1) + '" height="' + Math.max(altura, 2).toFixed(1) +
        '" rx="4" fill="' + color + '" opacity="' + (punto.es_hoy ? 1 : 0.82) + '">' +
        "<title>" + punto.etiqueta + ": " + punto.valor + " reserva(s)</title></rect>"
      );

      if (punto.valor > 0) {
        partes.push('<text class="grafico__valor" x="' + (x + anchoBarra / 2).toFixed(1) +
                    '" y="' + (y - 6).toFixed(1) + '" text-anchor="middle" font-size="11">' +
                    punto.valor + "</text>");
      }

      partes.push('<text x="' + (x + anchoBarra / 2).toFixed(1) + '" y="' + (alto - 12) +
                  '" text-anchor="middle" font-size="10">' + punto.etiqueta + "</text>");
    });

    partes.push('<line class="grafico__eje" x1="' + margen.izquierda + '" x2="' +
                (ancho - margen.derecha) + '" y1="' + (margen.arriba + altoUtil) + '" y2="' +
                (margen.arriba + altoUtil) + '"/>');

    nodo.innerHTML = svg(partes.join(""));
  }

  /* ----------------------------------------------------------------------
     Gráfico de anillo (donut)
     -------------------------------------------------------------------- */
  function anillo(nodo, serie) {
    var total = serie.reduce(function (suma, punto) { return suma + punto.valor; }, 0);
    if (!total) {
      nodo.innerHTML = '<p class="vacio">Sin datos para representar.</p>';
      return;
    }

    var colores = paleta();
    var radio = 62;
    var grosor = 22;
    var circunferencia = 2 * Math.PI * radio;
    var desplazamiento = 0;

    var partes = ['<g transform="translate(110,110) rotate(-90)">'];
    serie.forEach(function (punto, indice) {
      var fraccion = punto.valor / total;
      var largo = fraccion * circunferencia;
      partes.push(
        '<circle r="' + radio + '" cx="0" cy="0" fill="none" stroke="' +
        colores[indice % colores.length] + '" stroke-width="' + grosor +
        '" stroke-dasharray="' + largo.toFixed(2) + " " + (circunferencia - largo).toFixed(2) +
        '" stroke-dashoffset="' + (-desplazamiento).toFixed(2) + '" stroke-linecap="butt">' +
        "<title>" + punto.etiqueta + ": " + punto.valor + "</title></circle>"
      );
      desplazamiento += largo;
    });
    partes.push("</g>");

    partes.push('<text x="110" y="104" text-anchor="middle" font-size="30" ' +
                'class="grafico__valor">' + total + "</text>");
    partes.push('<text x="110" y="126" text-anchor="middle" font-size="11">equipos</text>');

    var leyenda = '<ul class="leyenda" style="flex-direction:column;gap:.5rem">';
    serie.forEach(function (punto, indice) {
      var porcentaje = Math.round((punto.valor / total) * 100);
      leyenda += "<li class=\"leyenda__item\">" +
        '<span class="leyenda__punto" style="background:' + colores[indice % colores.length] + '"></span>' +
        "<span>" + punto.etiqueta + "</span>" +
        '<strong style="margin-inline-start:auto">' + punto.valor + " · " + porcentaje + "%</strong></li>";
    });
    leyenda += "</ul>";

    nodo.innerHTML =
      '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:1.5rem">' +
      '<svg class="grafico" viewBox="0 0 220 220" style="max-width:220px" role="img">' +
      partes.join("") + "</svg>" + leyenda + "</div>";
  }

  /* ----------------------------------------------------------------------
     Barras horizontales (ocupación por laboratorio)
     -------------------------------------------------------------------- */
  function barrasHorizontales(nodo, serie) {
    if (!serie.length) {
      nodo.innerHTML = '<p class="vacio">Sin datos para representar.</p>';
      return;
    }

    var colores = paleta();
    var maximo = Math.max.apply(null, serie.map(function (p) { return p.valor; }));
    maximo = Math.max(maximo, 1);

    var filas = serie.map(function (punto, indice) {
      var porcentaje = Math.max((punto.valor / maximo) * 100, punto.valor ? 4 : 0);
      var color = colores[indice % colores.length];
      return (
        '<li class="barra-horizontal">' +
        '<span class="barra-horizontal__etiqueta">' +
        '<b class="mono">' + punto.etiqueta + "</b>" +
        '<span class="dato-secundario">' + punto.detalle + "</span></span>" +
        '<span class="barra-horizontal__pista">' +
        '<span class="barra-horizontal__relleno" style="width:' + porcentaje.toFixed(1) +
        "%;background:" + color + '"></span></span>' +
        '<strong class="barra-horizontal__valor">' + punto.valor + "</strong></li>"
      );
    });

    nodo.innerHTML = '<ul class="barras-horizontales">' + filas.join("") + "</ul>";
  }

  /* ----------------------------------------------------------------------
     Arranque y redibujado
     -------------------------------------------------------------------- */
  function dibujar(nodo) {
    var tipo = nodo.getAttribute("data-grafico");
    var datos = leerDatos(nodo);

    if (tipo === "barras") barras(nodo, datos);
    else if (tipo === "anillo") anillo(nodo, datos);
    else if (tipo === "barras-horizontales") barrasHorizontales(nodo, datos);
  }

  function iniciar() {
    contenedores = Array.prototype.slice.call(document.querySelectorAll("[data-grafico]"));
    contenedores.forEach(dibujar);
  }

  function redibujar() {
    contenedores.forEach(dibujar);
  }

  window.TechLoanGraficos = { iniciar: iniciar, redibujar: redibujar };

  document.addEventListener("DOMContentLoaded", iniciar);
})();
