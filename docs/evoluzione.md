# Evoluzione del progetto

Voci più recenti in cima. Formato: data, PR, cosa cambia, decisioni e perché.

## 2026-10-29 — feat/compliance: 4 regole di conformità su 5
- `classifier/compliance.py`: con dati personali e una scheda, il documento è confrontato con la scheda. Almeno uno scostamento → NON_CONFORME.
  - CATEGORIA_NON_DICHIARATA: categoria rilevata assente dalle "Categorie particolari dichiarate" (ETNICA e SESSUALE del registro diventano ORIGINE_ETNICA e ORIENTAMENTO_SESSUALE).
  - LUOGO_NON_DICHIARATO: il percorso non sta in nessuna cartella dichiarata della scheda (segmenti interi).
  - ACCESSO_ECCESSIVO: la cartella più specifica in `permessi_cartelle.csv` è aperta a `GG_TUTTI_DIPENDENTI`.
  - DIFFUSIONE_NON_PREVISTA: file in una cartella `Pubblicazioni` o `OpenData` e scheda senza diffusione, oppure con categorie particolari.
- Decisione: CONSERVAZIONE_SCADUTA (13 casi su sviluppo) in una PR a parte, perché serve la data del documento letta nel testo.
- Decisione: senza scheda (SCHEDA_MANCANTE) nessun controllo, come nella specifica. Applicare ACCESSO_ECCESSIVO anche a quei file alzava F1 a 0,65, ma solo perché copriva i nostri errori di SCHEDA_MANCANTE; nelle etichette i veri documenti senza scheda non hanno scostamenti.
- Scorciatoie: livello di riservatezza non ancora calcolato, quindi ogni documento con dati personali vale come livello ≥ 2 (nessun falso positivo su sviluppo). "Destinato alla pubblicazione" solo dalla cartella: le determine da pubblicare all'albo (5 casi) restano da riconoscere dal testo.
- Quasi tutti gli errori restanti vengono dalle fasi prima: scheda sbagliata o SCHEDA_MANCANTE di troppo (es. log VPN e delega sindacale fuori posto).
- `make score` passa anche `permessi_cartelle.csv`; `python -m classifier.pipeline <cartella> [registro.csv [permessi.csv]]`.
- `data/pred_*.json` aggiornati applicando `compliance.check` alle predizioni salvate: i controlli usano solo percorso, scheda e categorie, già nel file.
- Punteggio: sviluppo 73,2 → **84,9** (F1 scostamenti 0,61, esito 0,77), validation 72,9 → **87,4** (F1 0,71, esito 0,78).

## 2026-10-29 — feat/missing-record: esito SCHEDA_MANCANTE
- `matching.is_missing_record`: un documento con dati personali è SCHEDA_MANCANTE se nessuna scheda ha indizi, oppure se la migliore ha **al massimo una parola chiave** e il file **non** sta in una sua cartella dichiarata. In quel caso `scheda` resta vuota; la scheda più vicina resta tra le proposte, per il controllo dell'RPD.
- Si contano le parole chiave e non il punteggio: il punteggio è una somma di pesi non normalizzata, che cambia con il registro.
- Regole provate su sviluppo (F1 SCHEDA_MANCANTE): punteggio della prima < 3,1 → 0,74; ≤ 1 parola chiave e fuori cartella → **0,755**; ≤ 2 parole chiave e fuori cartella → 0,806.
- Decisione: scelta la soglia 1. Con 2 i falsi positivi in più sono documenti fuori posto (LUOGO_NON_DICHIARATO) con testo chiaro, es. richiesta di cremazione in `Condivisa`: perderebbero la scheda che serve ai controlli di conformità (prossima PR).
- Restano 6 SCHEDA_MANCANTE non riconosciute (domande ERP e SAD che citano "ISEE" o "residenza" insieme ad altre parole chiave) e 7 falsi positivi (soprattutto documenti fuori posto con una sola parola chiave, es. log VPN in `Condivisa`).
- `data/pred_*.json` aggiornati applicando la regola alle predizioni salvate (la regola usa solo parole chiave e cartella della prima proposta, già presenti nella motivazione): su Windows mancavano markitdown e OCR per rigenerarli.
- Punteggio: sviluppo 59,4 → **73,2** (F1 0,755, esito 0,64), validation 57,9 → **72,9** (F1 0,80, esito 0,58).

## 2026-10-29 — feat/matching: abbinamento al registro dei trattamenti
- `classifier/matching.py`: per ogni scheda, somma dei pesi delle parole chiave e tipologie documentali trovate nel testo (peso più alto per le parole rare tra le schede, `log(1 + N/df)`) + bonus 2 se il file sta in una cartella dichiarata. Top-3 con punteggio e motivazione ("cartella dichiarata; parole chiave: …").
- Misure su sviluppo per scegliere: solo percorso top-3 0,87; solo parole chiave 0,95; insieme 0,97. Il peso del percorso (da 0,5 a 8) non cambia la top-3: scelto 2, così il testo può battere una cartella sbagliata (documenti con LUOGO_NON_DICHIARATO).
- Le proposte si calcolano anche per i file "senza dati personali" (se il giudizio è sbagliato restano utili); la `scheda` scelta resta vuota per quei file.
- `make score` passa il registro; `python -m classifier.pipeline <cartella> [registro.csv]`.
- Punteggio: sviluppo 39,9 → **59,4** (top-3 0,97), validation 38,7 → **57,9** (top-3 0,96).

## 2026-10-29 — chore/roadmap: stato del progetto per ogni sessione
- Nuovo `docs/roadmap.md`: PR fatte con punteggio, prossime PR in ordine, decisioni e regole pratiche. `AGENTS.md` chiede di leggerlo all'inizio di ogni sessione e di aggiornarlo in ogni PR.

## 2026-10-29 — feat/ocr: OCR per scansioni e foto
- PDF senza strato di testo → `ocrmypdf --skip-text --sidecar` in italiano; immagini (JPG, PNG, TIFF) → `tesseract -l ita`.
- Dipendenze di sistema (non pip): `tesseract-ocr`, `tesseract-ocr-ita`, `ocrmypdf` (Debian 12: tesseract 5.3.0, ocrmypdf 14.0.1). Se mancano, il file resta senza testo e la pipeline prosegue.
- Richiamo categorie particolari: sviluppo 0,77 → **0,98**, validation 0,83 → **1,0**.
- Punteggio: sviluppo 35,6 → **39,9**, validation 35,2 → **38,7**. Analisi completa (222 file) in circa 1 minuto e 50 secondi su CPU.

## 2026-10-29 — feat/categories-ext: dizionari estesi ed EML decodificate
- EML lette con il modulo `email` della libreria standard: testo decodificato (prima "progn= osi"), intestazioni From/To/Cc/Subject/Date e **allegati** estratti a loro volta (massimo 3 livelli di email annidate).
- Dizionari estesi con il lessico della PA: radici corrette (`invalido`, `disabile`), accompagnamento, oncologia, demenza, salute mentale, RSA, misure cautelari, messa alla prova, esonero IRC, testimoni di Geova, permessi sindacali e altre sigle.
- Nuove categorie art. 9, assenti nelle etichette del kit, con nomi scelti da noi: ORIENTAMENTO_SESSUALE (unione civile), ORIGINE_ETNICA, POLITICHE, BIOMETRICI, GENETICI.
- Casella non spuntata di un modulo (`☐ …`) trattata come negazione: i moduli in bianco non producono più categorie.
- Test di regressione: nessuna categoria nei 13 documenti del kit senza dati personali.
- Regola di metodo: da qui i dizionari si correggono solo guardando lo sviluppo; il validation serve solo a misurare.
- Punteggio: sviluppo 35,4 → **35,6**, validation 34,9 → **35,2**. Il guadagno atteso è sui documenti mai visti della giuria.

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
