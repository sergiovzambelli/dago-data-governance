// Dopo una decisione il messaggio di conferma riceve il focus: i lettori di schermo lo leggono subito.
document.addEventListener("DOMContentLoaded", function () {
  var el = document.querySelector("[data-focus]");
  if (el) el.focus();
});
