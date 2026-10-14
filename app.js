
(function () {
  "use strict";


  function direccionApi() {
    if (typeof window.ECCI_API_BASE === "string") { return window.ECCI_API_BASE; }
    var local = location.hostname === "localhost" || location.hostname === "127.0.0.1";
    if (location.protocol === "file:" || (local && location.port !== "8000")) {
      return "http://localhost:8000";
    }
    return "";
  }
  var API = direccionApi();


  function crear(etiqueta, clase, texto) {
    var nodo = document.createElement(etiqueta);
    if (clase) { nodo.className = clase; }
    if (texto !== undefined && texto !== null) { nodo.textContent = texto; }
    return nodo;
  }


  function urlImagen(url) {
    if (typeof url !== "string") { return ""; }
    if (/^\/uploads\/[\w.-]+$/.test(url)) { return API + url; }
    if (/^https:\/\/res\.cloudinary\.com\/[\w-]+\/image\/upload\/[\w.\/-]+$/.test(url) && url.indexOf("..") === -1) { return url; }
    if (/^imagenes\/[\w.\/-]+$/.test(url) && url.indexOf("..") === -1) { return url; }
    return "";
  }

  function fondoImagen(nodo, url) {
    var u = urlImagen(url);
    if (u) { nodo.style.backgroundImage = "url('" + u + "')"; }
  }

  var MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  function fechaCorta(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) { return ""; }
    return d.getDate() + " " + MESES[d.getMonth()] + " " + d.getFullYear();
  }
  function hace(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) { return ""; }
    var min = Math.floor((Date.now() - d.getTime()) / 60000);
    if (min < 1) { return "Ahora"; }
    if (min < 60) { return "Hace " + min + " min"; }
    var h = Math.floor(min / 60);
    if (h < 24) { return "Hace " + h + " h"; }
    var dias = Math.floor(h / 24);
    if (dias === 1) { return "Ayer"; }
    if (dias < 30) { return "Hace " + dias + " días"; }
    return fechaCorta(iso);
  }
  function parrafos(texto) {
    return String(texto || "").split(/\n\s*\n/).map(function (p) { return p.trim(); }).filter(Boolean);
  }

  function mensajeDeError(cuerpo, estado) {
    if (cuerpo && typeof cuerpo.detail === "string") { return cuerpo.detail; }
    return "Algo salió mal (código " + estado + "). Intenta de nuevo.";
  }

  function pedir(ruta, opciones) {
    var control = new AbortController();
    var temporizador = setTimeout(function () { control.abort(); }, 12000);
    opciones = opciones || {};
    opciones.signal = control.signal;
    return fetch(API + ruta, opciones).then(
      function (resp) {
        clearTimeout(temporizador);
        return resp.json().catch(function () { return null; }).then(function (cuerpo) {
          if (!resp.ok) {
            var e = new Error(mensajeDeError(cuerpo, resp.status));
            e.estado = resp.status;
            throw e;
          }
          return cuerpo;
        });
      },
      function () {
        clearTimeout(temporizador);
        var e = new Error("No hay conexión con el servidor. Revisa que esté encendido (python main.py).");
        e.red = true;
        throw e;
      }
    );
  }

  /* ---------- Aviso superior ---------- */
  var aviso = null;
  function mostrarAviso(texto, esError, temporal) {
    if (!aviso) {
      aviso = crear("div");
      aviso.setAttribute("role", "status");
      aviso.style.cssText = "position:fixed;top:80px;left:16px;right:16px;z-index:5";
      document.body.appendChild(aviso);
    }
    aviso.textContent = texto;
    aviso.className = "w3-panel w3-card w3-round " + (esError ? "w3-pale-red w3-leftbar w3-border-red" : "w3-pale-yellow w3-leftbar w3-border-amber");
    aviso.hidden = false;
    if (temporal) {
      setTimeout(function () { if (aviso) { aviso.hidden = true; } }, 6000);
    }
  }

  /* ---------- Ventanas (modales de W3.CSS) ----------
     Un botón con data-abrir="id" abre la ventana; uno con data-cerrar la cierra. */
  function abrirVentana(id) {
    var ventana = document.getElementById(id);
    if (!ventana) { return; }
    ventana.style.display = "block";
    var cerrar = ventana.querySelector("[data-cerrar]");
    if (cerrar) { setTimeout(function () { cerrar.focus(); }, 30); }
  }
  function cerrarVentana() {
    document.querySelectorAll(".w3-modal").forEach(function (v) { v.style.display = "none"; });
  }
  function prepararBotones() {
    document.addEventListener("click", function (e) {
      var abrir = e.target.closest("[data-abrir]");
      if (abrir) { e.preventDefault(); abrirVentana(abrir.getAttribute("data-abrir")); return; }
      // Clic en el botón de cerrar o en el fondo oscuro de la ventana
      if (e.target.closest("[data-cerrar]") || e.target.classList.contains("w3-modal")) { cerrarVentana(); return; }
      // Botón ☰ del celular
      if (e.target.closest("[data-menu]")) { document.getElementById("menu-movil").classList.toggle("w3-show"); return; }
      if (e.target.closest("#menu-movil a")) { document.getElementById("menu-movil").classList.remove("w3-show"); }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { cerrarVentana(); }
    });
    // Flechas del carrusel de «Más noticias»
    var pista = document.getElementById("mas-noticias");
    document.querySelectorAll("[data-flecha]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var dir = Number(btn.getAttribute("data-flecha"));
        pista.scrollBy({ left: dir * pista.clientWidth * 0.8, behavior: "smooth" });
      });
    });
  }

  /* ---------- Lector de noticia completa ---------- */
  function abrirLector(id) {
    pedir("/api/noticias/" + encodeURIComponent(id)).then(
      function (n) {
        document.getElementById("leer-categoria").textContent = n.categoria;
        document.getElementById("leer-titulo").textContent = n.titulo;
        document.getElementById("leer-meta").textContent = "Por " + n.autor + " · " + fechaCorta(n.fecha);
        var imagen = document.getElementById("leer-imagen");
        var url = urlImagen(n.imagen_url);
        if (url) {
          imagen.src = url;
          imagen.alt = "Imagen de la noticia: " + n.titulo;
          imagen.hidden = false;
        } else {
          imagen.hidden = true;
          imagen.removeAttribute("src");
        }
        var texto = document.getElementById("leer-texto");
        texto.textContent = "";
        parrafos(n.contenido).forEach(function (p) { texto.appendChild(crear("p", null, p)); });
        abrirVentana("leer");
      },
      function (e) { mostrarAviso(e.message, true, true); }
    );
  }

  function enlaceALector(nodo, id) {
    nodo.href = "#";
    nodo.addEventListener("click", function (e) { e.preventDefault(); abrirLector(id); });
  }

  /* ---------- Pintar contenido ---------- */
  // Fecha legible para personas y en formato ISO para máquinas (<time datetime>)
  function fecha(texto, iso) {
    var hora = crear("time", null, texto);
    if (iso) { hora.setAttribute("datetime", iso); }
    return hora;
  }

  // Pie de la noticia: "Por autor · fecha"
  function firma(clase, autor, iso) {
    var pie = crear("footer", clase, "Por " + autor + " · ");
    pie.appendChild(fecha(fechaCorta(iso), iso));
    return pie;
  }

  function vacio(cont, texto) {
    cont.appendChild(crear("p", "w3-text-grey w3-padding", texto));
  }

  function pintarMas(lista) {
    var pista = document.getElementById("mas-noticias");
    if (!pista) { return; }
    pista.textContent = "";
    if (!lista.length) { vacio(pista, "Todavía no hay noticias publicadas."); return; }
    lista.forEach(function (n) {
      var tarjeta = crear("a", "w3-card w3-white w3-round w3-hover-shadow");
      var imagen = crear("div", "foto foto-mini");
      imagen.setAttribute("aria-hidden", "true");
      fondoImagen(imagen, n.imagen_url);
      tarjeta.appendChild(imagen);
      var cuerpo = crear("div", "w3-container w3-padding-small");
      cuerpo.appendChild(crear("span", "w3-small w3-text-ucr", n.categoria));
      cuerpo.appendChild(crear("p", "sin-margen", n.titulo)).style.fontWeight = "bold";
      var cuando = crear("small", "w3-text-grey");
      cuando.appendChild(fecha(hace(n.fecha), n.fecha));
      cuerpo.appendChild(cuando);
      tarjeta.appendChild(cuerpo);
      enlaceALector(tarjeta, n.id);
      pista.appendChild(tarjeta);
    });
  }

  function pintarPrincipales(lista) {
    var cont = document.getElementById("principales");
    if (!cont) { return; }
    cont.textContent = "";
    if (!lista.length) { vacio(cont, "Todavía no hay noticias publicadas. ¡Sé la primera persona en subir una!"); return; }
    lista.forEach(function (n) {
      var columna = crear("div", "w3-third w3-margin-bottom");
      var tarjeta = crear("article", "w3-card w3-white w3-round w3-hover-shadow");
      var imagen = crear("div", "foto");
      imagen.setAttribute("aria-hidden", "true");
      fondoImagen(imagen, n.imagen_url);

      var cuerpo = crear("div", "w3-container w3-padding");
      cuerpo.appendChild(crear("span", "w3-tag w3-ucr w3-round w3-small", n.categoria));
      var titulo = crear("h3", "w3-large");
      var enlace = crear("a", "w3-text-black", n.titulo);
      enlace.style.textDecoration = "none";
      enlaceALector(enlace, n.id);
      titulo.appendChild(enlace);
      cuerpo.appendChild(titulo);
      cuerpo.appendChild(crear("p", null, n.resumen));
      cuerpo.appendChild(firma("w3-small w3-text-grey", n.autor, n.fecha));

      tarjeta.appendChild(imagen);
      tarjeta.appendChild(cuerpo);
      columna.appendChild(tarjeta);
      cont.appendChild(columna);
    });
  }

  function pintarUltima(n) {
    var cont = document.getElementById("ultima-noticia");
    if (!cont) { return; }
    cont.textContent = "";
    if (!n) { cont.appendChild(crear("p", "w3-padding", "Todavía no hay una última noticia.")); return; }

    var url = urlImagen(n.imagen_url);
    if (url) {
      var figura = crear("figure", "w3-half sin-margen w3-margin-bottom");
      var foto = crear("img", "foto-ultima w3-round");
      foto.src = url;
      foto.alt = "Imagen de la noticia: " + n.titulo;
      figura.appendChild(foto);
      cont.appendChild(figura);
    }

    var texto = crear("div", url ? "w3-half" : "w3-col s12");
    texto.appendChild(crear("span", "w3-tag w3-celeste w3-round", n.categoria + " · Última hora"));
    texto.appendChild(crear("h3", "w3-xlarge", n.titulo));
    texto.appendChild(crear("p", "w3-large", n.resumen));
    var primero = parrafos(n.contenido)[0];
    if (primero) { texto.appendChild(crear("p", "w3-text-light-grey", primero)); }
    texto.appendChild(firma("w3-small w3-text-light-grey w3-margin-bottom", n.autor, n.fecha));
    var boton = crear("a", "w3-button w3-white w3-text-ucr w3-round", "Leer noticia completa");
    enlaceALector(boton, n.id);
    texto.appendChild(boton);
    cont.appendChild(texto);
  }

  var COLORES_AVATAR = ["w3-ucr", "w3-celeste", "w3-marino"];

  function pintarOpiniones(lista) {
    var hilo = document.getElementById("hilo");
    if (!hilo) { return; }
    hilo.textContent = "";
    if (!lista.length) { vacio(hilo, "Todavía no hay opiniones. ¡Sé la primera persona en opinar!"); return; }
    lista.forEach(function (o, i) {
      var articulo = crear("article", "w3-card w3-round w3-white w3-padding w3-margin-bottom");
      var cabecera = crear("header", "w3-bar");
      var avatar = crear("span", "w3-bar-item w3-circle w3-center " + COLORES_AVATAR[i % 3], Array.from(o.nombre || "?")[0].toUpperCase());
      avatar.style.cssText = "width:40px;height:40px;padding:8px 0;margin-right:8px";
      avatar.setAttribute("aria-hidden", "true");
      cabecera.appendChild(avatar);
      var quien = crear("div", "w3-bar-item w3-padding-small");
      quien.appendChild(crear("strong", null, o.nombre));
      quien.appendChild(document.createTextNode(" "));
      quien.appendChild(crear("span", "w3-tag w3-light-grey w3-round w3-small", o.tema));
      quien.appendChild(crear("br"));
      var hora = crear("time", "w3-small w3-text-grey", hace(o.fecha));
      hora.setAttribute("datetime", o.fecha);
      quien.appendChild(hora);
      cabecera.appendChild(quien);
      articulo.appendChild(cabecera);
      articulo.appendChild(crear("p", null, o.texto));

      var respuestas = zonaDeComentarios(o);
      var acciones = crear("footer");
      acciones.appendChild(botonMeGusta(o));
      acciones.appendChild(document.createTextNode(" "));
      acciones.appendChild(botonComentarios(respuestas, (o.comentarios || []).length));
      articulo.appendChild(acciones);
      articulo.appendChild(respuestas);
      hilo.appendChild(articulo);
    });
  }

  /* ---------- «Me gusta» y comentarios de las opiniones ---------- */
  // Cada navegador inventa un identificador anónimo; el servidor lo usa para no contar dos veces el mismo «me gusta»
  var visitante = null;
  function idVisitante() {
    if (visitante) { return visitante; }
    try { visitante = localStorage.getItem("ecci_visitante"); } catch (e) { visitante = null; }
    if (!/^[a-f0-9]{32}$/.test(visitante || "")) {
      var bytes = new Uint8Array(16);
      crypto.getRandomValues(bytes);
      visitante = Array.from(bytes, function (b) { return ("0" + b.toString(16)).slice(-2); }).join("");
      try { localStorage.setItem("ecci_visitante", visitante); } catch (e) {}
    }
    return visitante;
  }

  function pintarMeGusta(boton, likes, meGusta) {
    boton.textContent = "👍 " + likes;
    boton.setAttribute("aria-pressed", meGusta ? "true" : "false");
    boton.setAttribute("aria-label", (meGusta ? "Quitar me gusta" : "Me gusta") + " (" + likes + ")");
    boton.className = "w3-button w3-round w3-small " + (meGusta ? "w3-ucr" : "w3-light-grey");
  }

  function botonMeGusta(o) {
    var boton = crear("button");
    boton.type = "button";
    var meGusta = !!o.me_gusta;
    pintarMeGusta(boton, o.likes || 0, meGusta);
    boton.addEventListener("click", function () {
      boton.disabled = true;
      var opciones = comoJson({ visitante: idVisitante() });
      opciones.method = meGusta ? "DELETE" : "POST";
      pedir("/api/opiniones/" + encodeURIComponent(o.id) + "/me-gusta", opciones).then(
        function (r) {
          meGusta = r.me_gusta;
          pintarMeGusta(boton, r.likes, meGusta);
        },
        function (e) { mostrarAviso(e.message, true, true); }
      ).then(function () { boton.disabled = false; });
    });
    return boton;
  }

  function textoComentarios(n) {
    return "💬 " + n + (n === 1 ? " comentario" : " comentarios");
  }

  function botonComentarios(zona, n) {
    var boton = crear("button", "w3-button w3-light-grey w3-round w3-small", textoComentarios(n));
    boton.type = "button";
    boton.setAttribute("aria-expanded", "false");
    boton.addEventListener("click", function () {
      zona.hidden = !zona.hidden;
      boton.setAttribute("aria-expanded", zona.hidden ? "false" : "true");
    });
    return boton;
  }

  function zonaDeComentarios(o) {
    var zona = crear("div", "w3-margin-top");
    zona.hidden = true;

    (o.comentarios || []).forEach(function (c) {
      var item = crear("div", "w3-panel w3-light-grey w3-leftbar w3-border-ucr w3-round");
      var cabecera = crear("p", "sin-margen w3-padding-small");
      cabecera.appendChild(crear("strong", null, c.nombre));
      cabecera.appendChild(document.createTextNode(" "));
      var hora = crear("time", "w3-small w3-text-grey", hace(c.fecha));
      hora.setAttribute("datetime", c.fecha);
      cabecera.appendChild(hora);
      item.appendChild(cabecera);
      item.appendChild(crear("p", "sin-margen w3-padding-small", c.texto));
      zona.appendChild(item);
    });

    var formulario = crear("form", "w3-container w3-padding-small");
    var idNombre = "c-nombre-" + o.id;
    var idTexto = "c-texto-" + o.id;
    var etiquetaNombre = crear("label", null, "Nombre");
    etiquetaNombre.htmlFor = idNombre;
    var nombre = crear("input", "w3-input w3-border w3-round w3-margin-bottom");
    nombre.type = "text";
    nombre.id = idNombre;
    nombre.name = "nombre";
    nombre.maxLength = 40;
    nombre.required = true;
    var etiquetaTexto = crear("label", null, "Tu comentario");
    etiquetaTexto.htmlFor = idTexto;
    var texto = crear("textarea", "w3-input w3-border w3-round w3-margin-bottom");
    texto.id = idTexto;
    texto.name = "comentario";
    texto.rows = 2;
    texto.maxLength = 500;
    texto.required = true;
    var boton = crear("button", "w3-button w3-ucr w3-round", "Comentar");
    boton.type = "submit";

    formulario.appendChild(etiquetaNombre);
    formulario.appendChild(nombre);
    formulario.appendChild(etiquetaTexto);
    formulario.appendChild(texto);
    formulario.appendChild(boton);
    insertarTrampa(formulario);
    var mensaje = zonaDeMensaje(formulario, boton);

    formulario.addEventListener("submit", function (e) {
      e.preventDefault();
      var datos = {
        nombre: nombre.value,
        comentario: texto.value,
        sitio_web: formulario.elements.sitio_web.value
      };
      enviar(formulario, mensaje, "/api/opiniones/" + encodeURIComponent(o.id) + "/comentarios", comoJson(datos), function () {
        texto.value = "";
      });
    });
    zona.appendChild(formulario);
    return zona;
  }

  /* ---------- Videos (enlaces de YouTube) ---------- */
  var ID_YOUTUBE = /^[A-Za-z0-9_-]{11}$/;

  function reproducir(marco, v) {
    // El reproductor solo se carga al hacer clic: la página abre más rápido
    var iframe = crear("iframe", "video-marco");
    iframe.src = "https://www.youtube-nocookie.com/embed/" + v.youtube_id + "?autoplay=1&rel=0";
    iframe.title = v.titulo;
    iframe.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
    iframe.allowFullscreen = true;
    iframe.referrerPolicy = "strict-origin-when-cross-origin";
    marco.replaceWith(iframe);
  }

  function pintarVideos(lista) {
    var cont = document.getElementById("lista-videos");
    if (!cont) { return; }
    cont.textContent = "";
    lista = lista.filter(function (v) { return ID_YOUTUBE.test(v.youtube_id); });
    if (!lista.length) { vacio(cont, "Todavía no hay videos publicados. ¡Comparte el primero!"); return; }
    lista.forEach(function (v) {
      var columna = crear("div", "w3-third w3-margin-bottom");
      var articulo = crear("article", "w3-card w3-white w3-round w3-hover-shadow");
      var marco = crear("button", "video-marco w3-display-container");
      marco.type = "button";
      marco.setAttribute("aria-label", "Reproducir video: " + v.titulo);
      marco.style.backgroundImage = "url('https://i.ytimg.com/vi/" + v.youtube_id + "/hqdefault.jpg')";
      var play = crear("span", "w3-display-middle w3-text-white", "▶");
      play.setAttribute("aria-hidden", "true");
      marco.appendChild(play);
      marco.addEventListener("click", function () { reproducir(marco, v); });

      var cuerpo = crear("div", "w3-container w3-padding");
      cuerpo.appendChild(crear("h3", "w3-large sin-margen", v.titulo));
      if (v.descripcion) { cuerpo.appendChild(crear("p", null, v.descripcion)); }
      cuerpo.appendChild(crear("p", "w3-small w3-text-grey", v.categoria + " · " + fechaCorta(v.fecha) + " · Por " + v.autor));

      articulo.appendChild(marco);
      articulo.appendChild(cuerpo);
      columna.appendChild(articulo);
      cont.appendChild(columna);
    });
  }

  /* ---------- Formularios ---------- */
  // Campo escondido: las personas no lo ven, los robots de spam sí lo llenan
  function insertarTrampa(formulario) {
    var campo = document.createElement("input");
    campo.type = "text";
    campo.name = "sitio_web";
    campo.tabIndex = -1;
    campo.autocomplete = "off";
    campo.className = "w3-hide";
    campo.setAttribute("aria-hidden", "true");
    formulario.appendChild(campo);
  }

  function zonaDeMensaje(formulario, antesDe) {
    var m = crear("p", "mensaje");
    m.setAttribute("role", "status");
    m.setAttribute("aria-live", "polite");
    antesDe.parentNode.insertBefore(m, antesDe);
    return m;
  }
  function escribirMensaje(zona, texto, tipo) {
    zona.textContent = texto;
    var color = tipo === "ok" ? " w3-panel w3-pale-green w3-padding" : (tipo === "error" ? " w3-panel w3-pale-red w3-padding" : "");
    zona.className = "mensaje w3-round" + color;
  }

  function comoJson(datos) {
    return {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datos)
    };
  }

  // Cierra la ventana unos segundos después, si la persona no la cerró antes
  function cerrarLuego() {
    setTimeout(cerrarVentana, 4500);
  }

  // Envía un formulario: bloquea el botón mientras espera y muestra la respuesta
  function enviar(formulario, zona, ruta, opciones, alTerminar) {
    var boton = formulario.querySelector('button[type="submit"]');
    var textoBoton = boton.textContent;
    boton.disabled = true;
    boton.textContent = "Enviando…";
    escribirMensaje(zona, "", "");

    pedir(ruta, opciones).then(
      function (r) {
        escribirMensaje(zona, r.mensaje, "ok");
        alTerminar();
      },
      function (err) { escribirMensaje(zona, err.message, "error"); }
    ).then(function () {
      boton.disabled = false;
      boton.textContent = textoBoton;
    });
  }

  function prepararFormularioNoticia() {
    var formulario = document.querySelector("#subir form");
    if (!formulario) { return; }
    insertarTrampa(formulario);
    var zona = zonaDeMensaje(formulario, formulario.querySelector(".botones"));

    formulario.addEventListener("submit", function (e) {
      e.preventDefault();
      var archivo = formulario.querySelector('input[type="file"]');
      if (archivo && archivo.files[0] && archivo.files[0].size > 5 * 1024 * 1024) {
        escribirMensaje(zona, "La imagen supera los 5 MB. Elige una más liviana.", "error");
        return;
      }
      enviar(formulario, zona, "/api/noticias", { method: "POST", body: new FormData(formulario) }, function () {
        formulario.reset();
        cerrarLuego();
      });
    });
  }

  function prepararFormularioVideo() {
    var formulario = document.querySelector("#subir-video form");
    if (!formulario) { return; }
    insertarTrampa(formulario);
    var zona = zonaDeMensaje(formulario, formulario.querySelector(".botones"));

    formulario.addEventListener("submit", function (e) {
      e.preventDefault();
      var el = formulario.elements;
      var datos = {
        autor: el.autor.value,
        correo: el.correo.value,
        enlace: el.enlace.value,
        titulo: el.titulo.value,
        categoria: el.categoria.value,
        descripcion: el.descripcion.value,
        acepta: el.acepta.checked ? "on" : "",
        sitio_web: el.sitio_web ? el.sitio_web.value : ""
      };
      enviar(formulario, zona, "/api/videos", comoJson(datos), function () {
        formulario.reset();
        cerrarLuego();
      });
    });
  }

  function prepararFormularioOpinion() {
    var formulario = document.getElementById("form-opinion");
    if (!formulario) { return; }
    insertarTrampa(formulario);
    var zona = zonaDeMensaje(formulario, formulario.querySelector(".aviso"));

    formulario.addEventListener("submit", function (e) {
      e.preventDefault();
      var el = formulario.elements;
      var datos = {
        nombre: el.nombre.value,
        tema: el.tema.value,
        opinion: el.opinion.value,
        sitio_web: el.sitio_web ? el.sitio_web.value : ""
      };
      enviar(formulario, zona, "/api/opiniones", comoJson(datos), function () {
        el.opinion.value = "";
      });
    });
  }

  /* ---------- Carga inicial ---------- */
  function cargarContenido() {
    var peticiones = [
      pedir("/api/noticias?limite=12").then(function (r) { pintarMas(r.items); }),
      pedir("/api/noticias/aleatorias?n=3").then(pintarPrincipales),
      pedir("/api/noticias/ultima").then(pintarUltima, function (e) {
        if (e.estado === 404) { pintarUltima(null); return; }
        throw e;
      }),
      pedir("/api/opiniones?limite=20&visitante=" + idVisitante()).then(function (r) { pintarOpiniones(r.items); }),
      pedir("/api/videos?limite=6").then(function (r) { pintarVideos(r.items); })
    ];

    Promise.allSettled(peticiones).then(function (resultados) {
      var fallos = resultados.filter(function (r) { return r.status === "rejected"; });
      if (fallos.length === resultados.length) {
        var sinRed = fallos.some(function (f) { return f.reason && f.reason.red; });
        mostrarAviso(
          sinRed
            ? "No hay conexión con el servidor. Revisa que esté encendido (python main.py)."
            : "El servidor respondió con un error. " + fallos[0].reason.message,
          true,
          false
        );
        return;
      }
      if (fallos.length) { mostrarAviso("Parte del contenido no se pudo cargar. " + fallos[0].reason.message, true, true); }
    });
  }

  function iniciar() {
    prepararBotones();
    prepararFormularioNoticia();
    prepararFormularioOpinion();
    prepararFormularioVideo();
    cargarContenido();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
