// Preferenze di accessibilità scelte dall'utente: applicate prima che la pagina venga disegnata (niente lampeggio).
// Salvate solo in questo browser; se il salvataggio non è disponibile la pagina resta quella normale.
(function () {
  "use strict";
  var KEY = "vaglio-a11y";
  var prefs = {};
  try { prefs = JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (e) { prefs = {}; }
  var root = document.documentElement;
  ["contrasto", "leggibile", "spaziatura", "link", "animazioni", "cursore", "guida", "grigi"].forEach(function (k) {
    if (prefs[k] === true) root.classList.add("a11y-" + k);
  });
  if (prefs.testo === "125" || prefs.testo === "150") root.classList.add("a11y-testo-" + prefs.testo);
  window.vaglioA11y = { key: KEY, prefs: prefs };
})();
