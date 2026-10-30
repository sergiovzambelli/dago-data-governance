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
      var setOpen = function (open) {
        shell.classList.toggle("menu-open", open);
        toggle.setAttribute("aria-expanded", String(open));
        toggle.querySelector(".visually-hidden").textContent = open ? "Chiudi il menu" : "Apri il menu";
        if (open) { var first = menu.querySelector("a"); if (first) first.focus(); }
      };
      toggle.addEventListener("click", function () { setOpen(!shell.classList.contains("menu-open")); });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && shell.classList.contains("menu-open")) { setOpen(false); toggle.focus(); }
      });
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
  });

  // Prova un file: analisi in background, barra che segue le fasi reali del server; alla fine la barra diventa la
  // scala Conforme → Non conforme e l'indicatore scorre fino al grado del documento.
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
    function zone(pos) {  // pos 0 = verde (sinistra), 100 = rosso (destra)
      return pos <= 25 ? "Conforme" : pos < 60 ? "In parte conforme" : "Non conforme";
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
      var target = 100 - state.grado, start = null, DUR = reduced ? 0 : 1600;
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
