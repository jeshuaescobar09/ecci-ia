
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
    if (u) {
      nodo.style.background = "url('" + u + "') center / cover no-repeat";
      nodo.classList.add("con-foto");
    }
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
      aviso = crear("div", "aviso-pagina");
      aviso.setAttribute("role", "status");
      document.body.insertBefore(aviso, document.body.firstChild);
    }
    aviso.textContent = texto;
    aviso.className = "aviso-pagina" + (esError ? " error" : "");
    aviso.hidden = false;
    if (temporal) {
      setTimeout(function () { if (aviso) { aviso.hidden = true; } }, 6000);
    }
  }

  /* ---------- Ventanas (modales) ---------- */
  function hayVentanaAbierta() {
    return location.hash === "#subir" || location.hash === "#leer" || location.hash === "#subir-video";
  }
  function cerrarVentana() {
    // Un identificador que no existe cierra la ventana (:target) sin mover la página
    if (hayVentanaAbierta()) { location.hash = "#cerrado"; }
  }
  function prepararCierres() {
    document.addEventListener("click", function (e) {
      var objetivo = e.target.closest ? e.target.closest(".modal-fondo, .modal-cerrar, .modal .btn-fantasma") : null;
      if (objetivo) { e.preventDefault(); cerrarVentana(); }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") { cerrarVentana(); }
    });
    window.addEventListener("hashchange", function () {
      if (!hayVentanaAbierta()) { return; }
      var ventana = document.querySelector(location.hash);
      var cerrar = ventana ? ventana.querySelector(".modal-cerrar") : null;
      if (cerrar) { setTimeout(function () { cerrar.focus(); }, 30); }
    });
  }

  /* ---------- Lector de noticia completa ---------- */
  var lector = null;
  function prepararLector() {
    var ventana = crear("div", "modal");
    ventana.id = "leer";
    ventana.setAttribute("role", "dialog");
    ventana.setAttribute("aria-modal", "true");
    ventana.setAttribute("aria-labelledby", "leer-titulo");

    var fondo = crear("a", "modal-fondo");
    fondo.href = "#cerrado";
    fondo.setAttribute("aria-label", "Cerrar");

    var caja = crear("article", "modal-caja lector");
    var cerrar = crear("a", "modal-cerrar", "×");
    cerrar.href = "#cerrado";
    cerrar.setAttribute("aria-label", "Cerrar ventana");

    lector = {
      ventana: ventana,
      categoria: crear("span", "etiqueta"),
      titulo: crear("h2"),
      meta: crear("p", "meta"),
      imagen: document.createElement("img"),
      texto: crear("div", "lector-texto")
    };
    lector.titulo.id = "leer-titulo";
    lector.imagen.hidden = true;

    caja.appendChild(cerrar);
    caja.appendChild(lector.categoria);
    caja.appendChild(lector.titulo);
    caja.appendChild(lector.meta);
    caja.appendChild(lector.imagen);
    caja.appendChild(lector.texto);
    ventana.appendChild(fondo);
    ventana.appendChild(caja);
    document.body.appendChild(ventana);
  }

  function abrirLector(id) {
    pedir("/api/noticias/" + encodeURIComponent(id)).then(
      function (n) {
        lector.categoria.textContent = n.categoria;
        lector.titulo.textContent = n.titulo;
        lector.meta.textContent = "Por " + n.autor + " · " + fechaCorta(n.fecha);
        var url = urlImagen(n.imagen_url);
        if (url) {
          lector.imagen.src = url;
          lector.imagen.alt = "Imagen de la noticia: " + n.titulo;
          lector.imagen.hidden = false;
        } else {
          lector.imagen.hidden = true;
          lector.imagen.removeAttribute("src");
        }
        lector.texto.textContent = "";
        parrafos(n.contenido).forEach(function (p) { lector.texto.appendChild(crear("p", null, p)); });
        location.hash = "#leer";
      },
      function (e) { mostrarAviso(e.message, true, true); }
    );
  }

  function enlaceALector(nodo, id) {
    nodo.href = "#leer";
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

  function pintarMas(lista) {
    var pista = document.querySelector(".scroll-noticias");
    if (!pista) { return; }
    pista.textContent = "";
    if (!lista.length) {
      pista.appendChild(crear("p", "vacio", "Todavía no hay noticias publicadas."));
      return;
    }
    lista.forEach(function (n) {
      var tarjeta = crear("a", "mini");
      var imagen = crear("span", "mini-img");
      imagen.setAttribute("aria-hidden", "true");
      fondoImagen(imagen, n.imagen_url);
      tarjeta.appendChild(imagen);
      tarjeta.appendChild(crear("span", "mini-cat", n.categoria));
      tarjeta.appendChild(crear("strong", null, n.titulo));
      var cuando = crear("small");
      cuando.appendChild(fecha(hace(n.fecha), n.fecha));
      tarjeta.appendChild(cuando);
      enlaceALector(tarjeta, n.id);
      pista.appendChild(tarjeta);
    });
  }

  var DEGRADADOS = ["img-a", "img-b", "img-c"];
  function pintarPrincipales(lista) {
    var cont = document.querySelector(".grid-3");
    if (!cont) { return; }
    cont.textContent = "";
    if (!lista.length) {
      cont.appendChild(crear("p", "vacio", "Todavía no hay noticias publicadas. ¡Sé la primera persona en subir una!"));
      return;
    }
    lista.forEach(function (n, i) {
      var tarjeta = crear("article", "tarjeta");
      var imagen = crear("div", "tarjeta-img " + DEGRADADOS[i % DEGRADADOS.length]);
      imagen.setAttribute("aria-hidden", "true");
      fondoImagen(imagen, n.imagen_url);

      var cuerpo = crear("div", "tarjeta-cuerpo");
      cuerpo.appendChild(crear("span", "etiqueta", n.categoria));
      var titulo = crear("h3");
      var enlace = crear("a", null, n.titulo);
      enlaceALector(enlace, n.id);
      titulo.appendChild(enlace);
      cuerpo.appendChild(titulo);
      cuerpo.appendChild(crear("p", null, n.resumen));
      cuerpo.appendChild(firma("meta", n.autor, n.fecha));

      tarjeta.appendChild(imagen);
      tarjeta.appendChild(cuerpo);
      cont.appendChild(tarjeta);
    });
  }

  function pintarUltima(n) {
    var cont = document.querySelector(".ultima");
    if (!cont) { return; }
    cont.textContent = "";
    if (!n) {
      cont.style.gridTemplateColumns = "1fr";
      cont.appendChild(crear("p", "vacio vacio-claro", "Todavía no hay una última noticia."));
      return;
    }
    var url = urlImagen(n.imagen_url);
    if (url) {
      var figura = crear("figure", "ultima-foto");
      var foto = document.createElement("img");
      foto.src = url;
      foto.alt = "Imagen de la noticia: " + n.titulo;
      figura.appendChild(foto);
      cont.appendChild(figura);
      cont.style.gridTemplateColumns = "";
    } else {
      cont.style.gridTemplateColumns = "1fr";
    }

    var texto = crear("div", "ultima-texto");
    texto.appendChild(crear("span", "etiqueta etiqueta-clara", n.categoria + " · Última hora"));
    texto.appendChild(crear("h3", null, n.titulo));
    texto.appendChild(crear("p", "bajada", n.resumen));
    var primero = parrafos(n.contenido)[0];
    if (primero) { texto.appendChild(crear("p", null, primero)); }
    texto.appendChild(firma("meta meta-clara", n.autor, n.fecha));
    var boton = crear("a", "btn btn-claro", "Leer noticia completa");
    enlaceALector(boton, n.id);
    texto.appendChild(boton);
    cont.appendChild(texto);
  }

  function pintarOpiniones(lista) {
    var hilo = document.querySelector(".hilo");
    if (!hilo) { return; }
    hilo.textContent = "";
    if (!lista.length) {
      hilo.appendChild(crear("p", "vacio", "Todavía no hay opiniones. ¡Sé la primera persona en opinar!"));
      return;
    }
    lista.forEach(function (o, i) {
      var articulo = crear("article", "comentario");
      var clase = "avatar" + (i % 3 === 1 ? " av2" : (i % 3 === 2 ? " av3" : ""));
      var avatar = crear("div", clase, Array.from(o.nombre || "?")[0].toUpperCase());
      avatar.setAttribute("aria-hidden", "true");
      articulo.appendChild(avatar);

      var cuerpo = crear("div", "comentario-cuerpo");
      var cabecera = document.createElement("header");
      cabecera.appendChild(crear("strong", null, o.nombre));
      cabecera.appendChild(document.createTextNode(" "));
      cabecera.appendChild(crear("span", "tema", o.tema));
      var hora = crear("time", null, hace(o.fecha));
      hora.setAttribute("datetime", o.fecha);
      cabecera.appendChild(hora);
      cuerpo.appendChild(cabecera);
      cuerpo.appendChild(crear("p", null, o.texto));

      var respuestas = zonaDeComentarios(o);
      var acciones = crear("footer", "acciones");
      acciones.appendChild(botonMeGusta(o));
      acciones.appendChild(botonComentarios(respuestas, (o.comentarios || []).length));
      cuerpo.appendChild(acciones);
      cuerpo.appendChild(respuestas);
      articulo.appendChild(cuerpo);
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
    boton.classList.toggle("activo", meGusta);
  }

  function botonMeGusta(o) {
    var boton = crear("button", "btn-accion");
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
    var boton = crear("button", "btn-accion", textoComentarios(n));
    boton.type = "button";
    boton.setAttribute("aria-expanded", "false");
    boton.addEventListener("click", function () {
      zona.hidden = !zona.hidden;
      boton.setAttribute("aria-expanded", zona.hidden ? "false" : "true");
    });
    return boton;
  }

  function zonaDeComentarios(o) {
    var zona = crear("div", "respuestas");
    zona.hidden = true;

    (o.comentarios || []).forEach(function (c) {
      var item = crear("div", "respuesta");
      var cabecera = document.createElement("header");
      cabecera.appendChild(crear("strong", null, c.nombre));
      var hora = crear("time", null, hace(c.fecha));
      hora.setAttribute("datetime", c.fecha);
      cabecera.appendChild(hora);
      item.appendChild(cabecera);
      item.appendChild(crear("p", null, c.texto));
      zona.appendChild(item);
    });

    var formulario = crear("form", "form-comentario");
    var idNombre = "c-nombre-" + o.id;
    var idTexto = "c-texto-" + o.id;
    var etiquetaNombre = crear("label", null, "Nombre");
    etiquetaNombre.htmlFor = idNombre;
    var nombre = document.createElement("input");
    nombre.type = "text";
    nombre.id = idNombre;
    nombre.name = "nombre";
    nombre.maxLength = 40;
    nombre.required = true;
    var etiquetaTexto = crear("label", null, "Tu comentario");
    etiquetaTexto.htmlFor = idTexto;
    var texto = document.createElement("textarea");
    texto.id = idTexto;
    texto.name = "comentario";
    texto.rows = 2;
    texto.maxLength = 500;
    texto.required = true;
    var boton = crear("button", "btn btn-primario", "Comentar");
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
    var iframe = document.createElement("iframe");
    iframe.src = "https://www.youtube-nocookie.com/embed/" + v.youtube_id + "?autoplay=1&rel=0";
    iframe.title = v.titulo;
    iframe.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
    iframe.allowFullscreen = true;
    iframe.referrerPolicy = "strict-origin-when-cross-origin";
    marco.replaceWith(iframe);
  }

  function pintarVideos(lista) {
    var cont = document.querySelector(".grid-videos");
    if (!cont) { return; }
    cont.textContent = "";
    lista = lista.filter(function (v) { return ID_YOUTUBE.test(v.youtube_id); });
    if (!lista.length) {
      cont.appendChild(crear("p", "vacio", "Todavía no hay videos publicados. ¡Comparte el primero!"));
      return;
    }
    lista.forEach(function (v) {
      var articulo = crear("article", "video");
      var marco = crear("button", "video-marco con-miniatura");
      marco.type = "button";
      marco.setAttribute("aria-label", "Reproducir video: " + v.titulo);
      marco.style.backgroundImage = "url('https://i.ytimg.com/vi/" + v.youtube_id + "/hqdefault.jpg')";
      var play = crear("span", "play");
      play.setAttribute("aria-hidden", "true");
      marco.appendChild(play);
      marco.addEventListener("click", function () { reproducir(marco, v); });

      articulo.appendChild(marco);
      articulo.appendChild(crear("h3", null, v.titulo));
      if (v.descripcion) { articulo.appendChild(crear("p", "video-desc", v.descripcion)); }
      articulo.appendChild(crear("p", "meta", v.categoria + " · " + fechaCorta(v.fecha) + " · Por " + v.autor));
      cont.appendChild(articulo);
    });
  }

  // Ventana para compartir un video. Es una plantilla fija (no lleva texto de la gente),
  // por eso aquí sí se puede usar innerHTML. Las categorías deben coincidir con config.py.
  var PLANTILLA_VIDEO =
    '<a href="#cerrado" class="modal-fondo" aria-label="Cerrar"></a>' +
    '<div class="modal-caja">' +
    '  <a href="#cerrado" class="modal-cerrar" aria-label="Cerrar ventana">×</a>' +
    '  <h2 id="subir-video-titulo">Comparte un video</h2>' +
    '  <p class="modal-intro">Sube tu video a <strong>YouTube</strong> (puede ser «No listado») y pega aquí el enlace. ' +
    '  Quedará <strong>pendiente de aprobación</strong> hasta que un moderador lo revise.</p>' +
    '  <form action="#" method="post">' +
    '    <div class="campo-2">' +
    '      <div><label for="v-autor">Nombre del autor</label><input id="v-autor" name="autor" type="text" maxlength="80" required></div>' +
    '      <div><label for="v-correo">Correo institucional</label><input id="v-correo" name="correo" type="email" placeholder="nombre@ucr.ac.cr" required></div>' +
    '    </div>' +
    '    <label for="v-enlace">Enlace de YouTube</label>' +
    '    <input id="v-enlace" name="enlace" type="url" placeholder="https://youtu.be/..." required>' +
    '    <label for="v-titulo">Título del video</label>' +
    '    <input id="v-titulo" name="titulo" type="text" maxlength="120" required>' +
    '    <label for="v-cat">Categoría</label>' +
    '    <select id="v-cat" name="categoria">' +
    '      <option>Charla</option><option>Demostración</option><option>Proyecto estudiantil</option>' +
    '      <option>Evento</option><option>Tutorial</option>' +
    '    </select>' +
    '    <label for="v-desc">Descripción (opcional, máx. 300 caracteres)</label>' +
    '    <textarea id="v-desc" name="descripcion" rows="2" maxlength="300"></textarea>' +
    '    <label class="check"><input type="checkbox" name="acepta" required> ' +
    '      Confirmo que tengo permiso para compartir este video y acepto que sea revisado antes de publicarse.</label>' +
    '    <div class="modal-botones">' +
    '      <a href="#cerrado" class="btn btn-fantasma">Cancelar</a>' +
    '      <button type="submit" class="btn btn-primario">Enviar para revisión</button>' +
    '    </div>' +
    '  </form>' +
    '</div>';

  function prepararFormularioVideo() {
    var seccion = document.querySelector("#videos .contenedor");
    if (!seccion) { return; }

    var pie = crear("div", "videos-pie");
    var abrir = crear("a", "btn btn-primario", "+ Compartir un video");
    abrir.href = "#subir-video";
    pie.appendChild(abrir);
    seccion.appendChild(pie);

    var ventana = crear("div", "modal");
    ventana.id = "subir-video";
    ventana.setAttribute("role", "dialog");
    ventana.setAttribute("aria-modal", "true");
    ventana.setAttribute("aria-labelledby", "subir-video-titulo");
    ventana.innerHTML = PLANTILLA_VIDEO;
    document.body.appendChild(ventana);

    var formulario = ventana.querySelector("form");
    insertarTrampa(formulario);
    var zona = zonaDeMensaje(formulario, formulario.querySelector(".modal-botones"));

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
        cerrarLuego("#subir-video");
      });
    });
  }

  /* ---------- Formularios ---------- */
  function insertarTrampa(formulario) {
    var campo = document.createElement("input");
    campo.type = "text";
    campo.name = "sitio_web";
    campo.tabIndex = -1;
    campo.autocomplete = "off";
    campo.className = "trampa";
    campo.setAttribute("aria-hidden", "true");
    formulario.appendChild(campo);
  }

  function zonaDeMensaje(formulario, antesDe) {
    var m = formulario.querySelector(".mensaje");
    if (!m) {
      m = crear("p", "mensaje");
      m.setAttribute("role", "status");
      m.setAttribute("aria-live", "polite");
      antesDe.parentNode.insertBefore(m, antesDe);
    }
    return m;
  }
  function escribirMensaje(zona, texto, tipo) {
    zona.textContent = texto;
    zona.className = "mensaje " + tipo;
  }

  function comoJson(datos) {
    return {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datos)
    };
  }

  // Cierra la ventana unos segundos después, si la persona no la cerró antes
  function cerrarLuego(hash) {
    setTimeout(function () { if (location.hash === hash) { cerrarVentana(); } }, 4500);
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
    var zona = zonaDeMensaje(formulario, formulario.querySelector(".modal-botones"));

    formulario.addEventListener("submit", function (e) {
      e.preventDefault();
      var archivo = formulario.querySelector('input[type="file"]');
      if (archivo && archivo.files[0] && archivo.files[0].size > 5 * 1024 * 1024) {
        escribirMensaje(zona, "La imagen supera los 5 MB. Elige una más liviana.", "error");
        return;
      }
      enviar(formulario, zona, "/api/noticias", { method: "POST", body: new FormData(formulario) }, function () {
        formulario.reset();
        cerrarLuego("#subir");
      });
    });
  }

  function prepararFormularioOpinion() {
    var formulario = document.querySelector(".foro-form");
    if (!formulario) { return; }
    insertarTrampa(formulario);
    var nota = formulario.querySelector(".aviso");
    var zona = zonaDeMensaje(formulario, nota || formulario.lastChild);

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
            ? "Mostrando contenido de ejemplo: no hay conexión con el servidor."
            : "Mostrando contenido de ejemplo: el servidor respondió con un error. " + fallos[0].reason.message,
          false,
          false
        );
        return;
      }
      var nota = document.querySelector(".nota-dev");
      if (nota) { nota.hidden = true; }
      if (fallos.length) { mostrarAviso("Parte del contenido no se pudo cargar. " + fallos[0].reason.message, true, true); }
    });
  }

  function iniciar() {
    prepararLector();
    prepararCierres();
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
