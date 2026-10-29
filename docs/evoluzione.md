# Evoluzione del progetto

Voci più recenti in cima. Formato: data, PR, cosa cambia, decisioni e perché.

## 2026-10-29 — chore/kit-data: estrazione dati del kit
- `make data` estrae il kit in `data/` e il validation set in `data/validation/`.
- `data/` è versionato su GitHub (scelta del team): i dati personali sono sintetici e lo zip del kit era già nel repo; `make data` lo rigenera.
- Uso dei dati: `Etichette_sviluppo` per mettere a punto, `Etichette_valutazione_RISERVATO` solo per misurare.
- Nota: `sviluppo/LEGGIMI.txt` non ha etichetta (155 file etichettati su 156).

## 2026-10-29 — setup iniziale
- Aggiunte regole per gli agenti (`AGENTS.md`), template PR e documenti in `docs/`.
- Decisioni: Bootstrap Italia per la UI, TDD, security by design, PR piccole.
