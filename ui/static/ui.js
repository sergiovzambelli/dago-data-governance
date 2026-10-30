// Comportamenti della UI: niente librerie, tutto funziona anche senza JavaScript (menu visibile, link e moduli normali).
(function () {
  "use strict";
  var KEY = "scorciatoie";  // preferenza dell'utente nel browser, non sul server

  function store(value) {
    try { if (value === undefined) return localStorage.getItem(KEY); localStorage.setItem(KEY, value); } catch (e) { return null; }
  }

  document.addEventListener("DOMContentLoaded", function () {
    // dopo una decisione il messaggio di conferma riceve il focus: i lettori di schermo lo leggono subito
    var msg = document.querySelector("[data-focus]");
    if (msg) msg.focus();

    // menu su telefono: senza JavaScript resta sempre visibile
    var shell = document.getElementById("shell");
    var toggle = document.querySelector(".menu-toggle");
    var menu = document.getElementById("menu-principale");
    if (shell && toggle && menu) {
      shell.classList.add("js");
      toggle.hidden = false;
      var workspace = document.querySelector(".workspace");
      var setOpen = function (open) {
        shell.classList.toggle("menu-open", open);
        toggle.setAttribute("aria-expanded", String(open));
        toggle.querySelector(".visually-hidden").textContent = open ? "Chiudi il menu" : "Apri il menu";
        // con il menu aperto il contenuto sotto non riceve il focus né viene letto (niente Tab "nascosti")
        if (workspace) workspace.inert = open;
        if (open) { var first = menu.querySelector("a"); if (first) first.focus(); }
      };
      toggle.addEventListener("click", function () { setOpen(!shell.classList.contains("menu-open")); });
      // "Vai alla navigazione": su telefono il menu è chiuso, quindi il link lo apre
      var skip = document.querySelector('a[href="#menu-principale"]');
      if (skip) skip.addEventListener("click", function (e) {
        if (getComputedStyle(menu).display === "none") { e.preventDefault(); setOpen(true); }
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && shell.classList.contains("menu-open")) { setOpen(false); toggle.focus(); }
      });
    }

    // menu compresso da desktop: la scelta resta nel browser
    var collapse = document.querySelector(".side-collapse");
    if (shell && collapse) {
      collapse.hidden = false;
      var setCollapsed = function (on) {
        shell.classList.toggle("side-collapsed", on);
        collapse.setAttribute("aria-expanded", String(!on));
        collapse.querySelector(".side-label").textContent = on ? "Espandi il menu" : "Comprimi il menu";
        try { localStorage.setItem("menu-compresso", on ? "si" : "no"); } catch (e) { /* senza salvataggio vale solo per questa pagina */ }
      };
      try { if (localStorage.getItem("menu-compresso") === "si") setCollapsed(true); } catch (e) { /* menu aperto */ }
      collapse.addEventListener("click", function () { setCollapsed(!shell.classList.contains("side-collapsed")); });
    }

    // scorciatoie da tastiera (WCAG 2.1.4): tasti singoli solo fuori dai campi, e si possono disattivare
    var panel = document.getElementById("scorciatoie");
    var button = document.querySelector("[data-shortcuts-toggle]");
    var state = panel && panel.querySelector(".shortcuts-state");
    var enabled = function () { return store() !== "no"; };
    var paint = function () {
      if (!button) return;
      button.textContent = enabled() ? "Disattiva le scorciatoie" : "Attiva le scorciatoie";
      if (state) state.textContent = enabled() ? "Le scorciatoie sono attive." : "Le scorciatoie sono disattivate.";
    };
    if (button) button.addEventListener("click", function () { store(enabled() ? "no" : "si"); paint(); });
    paint();

    document.addEventListener("keydown", function (e) {
      if (!enabled() || e.ctrlKey || e.metaKey || e.altKey) return;
      var t = e.target;
      if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT|BUTTON)$/.test(t.tagName))) return;
      if (e.key === "?" && panel) {
        panel.open = !panel.open;
        if (panel.open) panel.querySelector("summary").focus();
        e.preventDefault();
        return;
      }
      if (document.querySelector(".try-progress:not([hidden])")) return;  // durante l'analisi niente scorciatoie
      var el = document.querySelector('[data-key="' + e.key.toLowerCase() + '"]');
      if (!el) return;
      e.preventDefault();
      if (el.tagName === "DETAILS") {
        el.open = true;
        var field = el.querySelector("select, textarea, input:not([type=hidden]), button");
        (field || el.querySelector("summary")).focus();
      } else {
        el.click();
      }
    });

    tryProgress();
    a11yPanel();
  });

  // Pannello Accessibilità: le classi a11y-* sul documento cambiano lo stile; la scelta si salva nel browser.
  function a11yPanel() {
    var toggle = document.querySelector(".a11y-toggle");
    var panel = document.getElementById("a11y-panel");
    if (!toggle || !panel) return;
    var state = window.vaglioA11y || { key: "vaglio-a11y", prefs: {} };
    var prefs = state.prefs, root = document.documentElement;
    var status = panel.querySelector("[data-a11y-status]");
    var guide = document.querySelector(".reading-guide");

    function save() { try { localStorage.setItem(state.key, JSON.stringify(prefs)); } catch (e) { /* solo per questa pagina */ } }
    function apply() {
      panel.querySelectorAll("[data-a11y]").forEach(function (box) {
        var on = prefs[box.dataset.a11y] === true;
        box.checked = on;
        root.classList.toggle("a11y-" + box.dataset.a11y, on);
      });
      var size = prefs.testo === "125" || prefs.testo === "150" ? prefs.testo : "100";
      root.classList.remove("a11y-testo-125", "a11y-testo-150");
      if (size !== "100") root.classList.add("a11y-testo-" + size);
      var radio = document.getElementById("a11y-testo-" + size);
      if (radio) radio.checked = true;
    }
    function setOpen(open) {
      panel.hidden = !open;
      toggle.setAttribute("aria-expanded", String(open));
      if (open) panel.querySelector("#a11y-title").focus(); else toggle.focus();
    }

    apply();
    toggle.addEventListener("click", function () { setOpen(panel.hidden); });
    panel.querySelector(".a11y-close").addEventListener("click", function () { setOpen(false); });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape" && !panel.hidden) setOpen(false); });
    panel.addEventListener("change", function (e) {
      var t = e.target;
      if (t.dataset.a11y) { prefs[t.dataset.a11y] = t.checked; status.textContent = t.labels[0].textContent + (t.checked ? ": attivo" : ": disattivo"); }
      if (t.name === "a11y-testo") { prefs.testo = t.value; status.textContent = "Dimensione del testo: " + t.labels[0].textContent; }
      apply(); save();
    });
    panel.querySelector("[data-a11y-reset]").addEventListener("click", function () {
      Object.keys(prefs).forEach(function (k) { delete prefs[k]; });
      apply(); save();
      status.textContent = "Impostazioni ripristinate.";
    });
    // guida alla lettura: una banda orizzontale all'altezza del puntatore
    document.addEventListener("mousemove", function (e) {
      if (guide && root.classList.contains("a11y-guida")) guide.style.top = (e.clientY - 18) + "px";
    });
  }

  // Prova un file: analisi in background, barra che segue le fasi reali del server; alla fine la barra diventa la
  // scala Non conforme → Conforme e l'indicatore scorre fino al grado del documento.
  function tryProgress() {
    var form = document.querySelector("form[data-progress]");
    var box = document.getElementById("avanzamento");
    if (!form || !box || !window.fetch || !window.FormData) return;
    var track = box.querySelector(".tp-track"), fill = box.querySelector(".tp-fill"), marker = box.querySelector(".tp-marker");
    var label = box.querySelector(".tp-label"), detail = box.querySelector(".tp-detail");
    var announce = box.querySelector("[data-announce]"), steps = box.querySelectorAll(".tp-steps li");
    var ends = box.querySelector(".tp-ends"), open = box.querySelector(".tp-open");
    var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var STEP_MS = reduced ? 0 : 450;  // ogni fase resta visibile almeno così: le fasi veloci non spariscono

    function say(text) { announce.textContent = text; }
    function showPhase(n, names) {
      var pct = Math.round(100 * n / names.length);
      fill.style.width = pct + "%";
      track.setAttribute("aria-valuenow", String(pct));
      var name = names[Math.min(n, names.length) - 1] || "Avvio";
      track.setAttribute("aria-valuetext", "Fase " + n + " di " + names.length + ": " + name);
      label.textContent = name;
      detail.textContent = "fase " + n + " di " + names.length;
      steps.forEach(function (li) {
        var i = Number(li.dataset.step), state = i < n ? "fatta" : i === n ? "in corso" : "da fare";
        li.className = i < n ? "done" : i === n ? "current" : "";
        li.querySelector(".tp-state").textContent = ": " + state;
      });
      say("Fase " + n + " di " + names.length + ": " + name);
    }
    function zone(pos) {  // pos 0 = rosso (sinistra), 100 = verde (destra)
      return pos >= 75 ? "Conforme" : pos > 40 ? "In parte conforme" : "Non conforme";
    }
    function finish(state, url) {
      box.classList.add("tp-verdict");
      ends.hidden = false;
      var done = function () {
        label.textContent = state.etichetta;
        detail.textContent = state.grado === null ? "" : "conformità " + state.livello + ", " + state.grado + " su 100";
        track.setAttribute("aria-valuetext", "Esito: " + state.etichetta + (state.grado === null ? "" : ", conformità " + state.grado + " su 100"));
        say("Analisi completata. Esito: " + state.etichetta + (state.grado === null ? "." : ", conformità " + state.livello + "."));
        open.querySelector("a").href = url;
        open.hidden = false;
        open.querySelector("a").focus();
      };
      if (state.grado === null) { marker.hidden = true; done(); return; }
      var target = state.grado, start = null, DUR = reduced ? 0 : 1600;
      var frame = function (t) {
        if (start === null) start = t;
        var k = DUR ? Math.min(1, (t - start) / DUR) : 1, pos = target * (1 - Math.pow(1 - k, 3));
        marker.style.left = pos + "%";
        if (k < 1) { label.textContent = zone(pos); detail.textContent = ""; requestAnimationFrame(frame); }
        else done();
      };
      requestAnimationFrame(frame);
    }

    form.addEventListener("submit", function (e) {
      if (!form.checkValidity()) return;
      e.preventDefault();
      var data = new FormData(form), shown = 0, names = [];
      box.hidden = false;
      box.classList.remove("tp-verdict", "tp-error");
      open.hidden = true; ends.hidden = true; marker.hidden = false; marker.style.left = "0%"; fill.style.width = "0%";
      form.querySelector("button[type=submit]").disabled = true;
      box.scrollIntoView({ block: "nearest" });
      fetch(form.dataset.progress, { method: "POST", body: data, credentials: "same-origin" })
        .then(function (r) {
          if (!r.ok) { form.submit(); throw new Error("rifiutato"); }  // il server spiega l'errore nella sua pagina
          return r.json();
        })
        .then(function (job) {
          var poll = function () {
            fetch("/prova/stato/" + encodeURIComponent(job.lavoro), { credentials: "same-origin", cache: "no-store" })
              .then(function (r) { return r.json(); })
              .then(function (s) {
                names = s.fasi;
                // avanza di una fase alla volta verso quella vera del server
                if (shown < s.fase) { shown += 1; showPhase(shown, names); }
                if (s.fatto && s.errore) {
                  box.classList.add("tp-error"); label.textContent = s.errore; detail.textContent = ""; say(s.errore);
                  form.querySelector("button[type=submit]").disabled = false;
                  return;
                }
                if (s.fatto && shown >= s.fase) { finish(s, "/prova/risultato/" + encodeURIComponent(job.lavoro)); return; }
                setTimeout(poll, shown < s.fase ? STEP_MS : 400);
              });
          };
          poll();
        })
        .catch(function () {});
    });
  }
})();
