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
  });
})();
