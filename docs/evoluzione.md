# Evoluzione del progetto

Voci più recenti in cima. Formato: data, PR, cosa cambia, decisioni e perché.

## 2026-10-29 — feat/categories: categorie particolari e giudiziarie
- `classifier/categories.py`: dizionari di espressioni per SALUTE, GIUDIZIARI, RELIGIOSE, SINDACALE, con evidenza e posizione nel testo. Coprono anche i casi solo descritti ("cardiochirurgia", "Servizio per le dipendenze", "rito islamico", "associazione per la cremazione").
- Regole contro i falsi allarmi: negazione vicina ("non sono presenti persone con invalidità"), "ordinanza sindacale" (= del sindaco) esclusa, spazi che valgono anche come a capo nei PDF.
- Decisione: chi dichiara l'assenza di condanne per i reati dell'art. 80/94 del codice appalti dà comunque un dato giudiziario (come nelle etichette); "non aver riportato condanne" generico no.
- Decisione: una categoria particolare descritta rende il documento "con dati personali" anche senza identificativi. Costo: i moduli in bianco che nominano una categoria (2 file) risultano con dati personali.
- Sui file con testo il richiamo è 73/73 (sviluppo) e 34/34 (validation); le categorie mancanti sono nelle scansioni (serve OCR).
- Punteggio: sviluppo **19,9 → 35,4**, validation **18,7 → 34,9**.

## 2026-10-29 — feat/entities: dati personali con regole
- `classifier/entities.py`: codice fiscale e IBAN con verifica del carattere di controllo (scritta a mano, niente dipendenze), email, telefono, data di nascita, nome dopo Sig./Sig.ra, indirizzo IP, matricola. Ogni entità ha tipo, posizione, valore mascherato e confidenza.
- La pipeline estrae il testo e cerca le entità: nessuna entità in un testo leggibile → `NESSUN_DATO_PERSONALE`. Un file senza testo (scansione) resta "con dati personali", perché non si può escludere.
- Punteggio: sviluppo **9,3 → 19,9**, validation **8,7 → 18,7**. Precisione entità 1,0; tutti i 13 documenti senza dati personali riconosciuti.
- Scartata la regola "Nome Cognome" con le maiuscole: colpiva 12 dei 13 documenti senza dati personali (delibere, ordinanze). I nomi liberi richiedono un modello (spaCy, PR futura).
- Restano 20+ documenti con soli nomi o indirizzi classificati per errore come senza dati personali.

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
