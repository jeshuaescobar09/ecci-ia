/* =========================================================
   Animaciones al hacer scroll (estilo CodePen)
   - Los elementos aparecen cuando entran en pantalla.
   - Los grupos de tarjetas aparecen uno tras otro (en cascada).
   - Barra de progreso arriba y parallax en la foto principal.
   También anima las noticias que app.js agrega después de cargar.
   ========================================================= */
(function () {
  "use strict";

  var sinMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (sinMovimiento || !("IntersectionObserver" in window)) { return; }

  /* Qué se anima y cómo. "cascada" = retraso extra para cada hermano. */
  var REGLAS = [
    { selector: ".seccion-titulo",            tipo: "anim-desenfoque" },
    { selector: ".mas-noticias-cabecera",     tipo: "anim-subir" },
    { selector: ".mini",                      tipo: "anim-derecha",  cascada: 80 },
    { selector: ".grid-3 > *",                tipo: "anim-subir",    cascada: 150 },
    { selector: ".ultima-foto",               tipo: "anim-izquierda" },
    { selector: ".ultima-texto",              tipo: "anim-derecha",  cascada: 0, retraso: 150 },
    { selector: ".grid-videos > *",           tipo: "anim-voltear",  cascada: 150 },
    { selector: ".foro-form",                 tipo: "anim-izquierda" },
    { selector: ".hilo > *",                  tipo: "anim-subir",    cascada: 120 },
    { selector: ".cta-fila > *",              tipo: "anim-zoom",     cascada: 150 },
    { selector: ".site-footer .footer-fila",  tipo: "anim-subir" }
  ];

  var observador = new IntersectionObserver(function (entradas) {
    entradas.forEach(function (e) {
      if (e.isIntersecting) {
        e.target.classList.add("visible");
        observador.unobserve(e.target);   /* se anima solo una vez */
      }
    });
  }, { threshold: 0.15, rootMargin: "0px 0px -40px 0px" });

  function marcar() {
    REGLAS.forEach(function (regla) {
      document.querySelectorAll(regla.selector).forEach(function (el) {
        if (el.dataset.anim || el.closest(".modal")) { return; }
        el.dataset.anim = "1";
        var posicion = Array.prototype.indexOf.call(el.parentNode.children, el);
        var retraso = (regla.retraso || 0) + (regla.cascada || 0) * Math.min(posicion, 6);
        el.style.setProperty("--retraso", retraso + "ms");
        el.classList.add("anim", regla.tipo);
        observador.observe(el);
      });
    });
  }

  marcar();

  /* app.js pinta las noticias reales después: las animamos también */
  var pendiente = false;
  new MutationObserver(function () {
    if (pendiente) { return; }
    pendiente = true;
    requestAnimationFrame(function () { pendiente = false; marcar(); });
  }).observe(document.querySelector("main") || document.body, { childList: true, subtree: true });

  /* Barra de progreso + parallax, actualizados una vez por cuadro */
  var barra = document.createElement("div");
  barra.className = "barra-progreso";
  barra.setAttribute("aria-hidden", "true");
  document.body.appendChild(barra);

  var esperando = false;
  function alHacerScroll() {
    var total = document.documentElement.scrollHeight - window.innerHeight;
    barra.style.transform = "scaleX(" + (total > 0 ? window.scrollY / total : 0) + ")";

    var foto = document.querySelector(".ultima-foto img");
    if (foto) {
      var caja = foto.parentNode.getBoundingClientRect();
      var centro = caja.top + caja.height / 2 - window.innerHeight / 2;
      foto.style.setProperty("--parallax", (centro * -0.08).toFixed(1) + "px");
    }
    esperando = false;
  }
  window.addEventListener("scroll", function () {
    if (!esperando) { esperando = true; requestAnimationFrame(alHacerScroll); }
  }, { passive: true });
  alHacerScroll();
})();
