# Evoluzione del progetto

Voci più recenti in cima. Formato: data, PR, cosa cambia, decisioni e perché.

## 2026-10-29 — feat/scorer: misura delle 6 metriche della giuria
- `python -m classifier.scorer <etichette.csv> <predizioni.json>` stampa le 6 metriche (0–1) e il totale pesato su 100, con i pesi della specifica.
- Un file etichettato che manca nelle predizioni conta come errore; un file predetto che non è nelle etichette blocca il calcolo.
- Decisione: le etichette non hanno la posizione delle entità, quindi la "precisione sulle entità" si misura per file (quota dei file con entità che hanno davvero dati personali). Senza entità predette vale 0, così non si prendono punti gratis.

## 2026-10-29 — chore/kit-data: estrazione dati del kit
- `make data` estrae il kit in `data/` e il validation set in `data/validation/`.
- `data/` è versionato su GitHub (scelta del team): i dati personali sono sintetici e lo zip del kit era già nel repo; `make data` lo rigenera.
- Uso dei dati: `Etichette_sviluppo` per mettere a punto, `Etichette_valutazione_RISERVATO` solo per misurare.
- Nota: `sviluppo/LEGGIMI.txt` non ha etichetta (155 file etichettati su 156).

## 2026-10-29 — setup iniziale
- Aggiunte regole per gli agenti (`AGENTS.md`), template PR e documenti in `docs/`.
- Decisioni: Bootstrap Italia per la UI, TDD, security by design, PR piccole.
