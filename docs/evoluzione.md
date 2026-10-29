# Evoluzione del progetto

Voci più recenti in cima. Formato: data, PR, cosa cambia, decisioni e perché.

## 2026-10-29 — feat/extract: estrazione del testo
- `classifier/extract.py`: `extract_text(file)` restituisce il testo. PDF con testo, DOCX, XLSX, CSV, TXT ed EML passano da markitdown; gli ODT da `zipfile` + `defusedxml`, senza dipendenze nuove.
- Copertura sul dataset di sviluppo: 131/155 file con testo. I 24 vuoti sono 23 PDF scansionati e 1 JPG: servirà l'OCR (PR successiva).
- Un file illeggibile o corrotto restituisce testo vuoto, così la pipeline non si ferma.
- `requirements.txt` con versioni fissate.
- La pipeline non usa ancora il testo: il punteggio resta 9,3/100.

## 2026-10-29 — feat/baseline: scansione e punto zero
- `python -m classifier.pipeline <cartella>` scansiona la cartella in sola lettura (percorso relativo e SHA-256) e scrive una predizione per file nel formato JSON della specifica.
- Per ora la predizione è costante (`CONFORME`, la classe più frequente): è il punto zero da battere. `make score` misura sviluppo e validation set.
- Punto zero: **9,3/100** su sviluppo, **8,7/100** su validation set. Gli SHA-256 coincidono con le etichette (155/155).
- Lo scorer ora ignora con un avviso i file senza etichetta (es. `sviluppo/LEGGIMI.txt`) invece di bloccarsi: non spostano nessuna metrica.
- I link simbolici vengono saltati, così la scansione non esce dalla cartella indicata.

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
