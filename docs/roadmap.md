# Roadmap e stato delle PR

Punto di partenza per ogni nuova sessione (persona o agente): cosa è fatto, cosa viene dopo, regole imparate strada facendo.
Si aggiorna **in ogni PR**: la riga della PR passa in "Fatte" con il punteggio, e la prossima si sposta in cima a "Da fare".

## Come si misura

- `make data` estrae il kit; `make score` analizza sviluppo e validation e stampa le 6 metriche della giuria e il totale su 100.
- Pesi (specifica): esito 20 · richiamo categorie particolari 20 · scheda top-3 20 · F1 SCHEDA_MANCANTE 15 · F1 scostamenti 15 · precisione entità 10.
- **Si corregge guardando solo il dataset di sviluppo**; il validation set serve solo a misurare (altrimenti il suo punteggio non è più "alla cieca").

## Fatte

| PR | Branch | Cosa | Sviluppo | Validation |
|----|--------|------|---------:|-----------:|
| #1 | chore/kit-data | `make data`, dati del kit versionati in `data/` | – | – |
| #2 | feat/scorer | Scorer con le 6 metriche (`classifier/scorer.py`) | – | – |
| #3 | feat/baseline | Scansione cartella + predizione costante (punto zero) | 9,3 | 8,7 |
| #4 | feat/extract | Testo da PDF, DOCX, XLSX, CSV, TXT, EML, ODT | 9,3 | 8,7 |
| #5, #6 | feat/entities | CF e IBAN con controllo, email, telefono, nascita, Sig./Sig.ra, IP, matricola → NESSUN_DATO_PERSONALE | 19,9 | 18,7 |
| #7 | feat/categories | Categorie particolari con dizionari, negazioni | 35,4 | 34,9 |
| #8 | feat/categories-ext | Dizionari estesi, categorie art. 9 nuove, EML decodificate con allegati, caselle `☐` | 35,6 | 35,2 |
| #9 | feat/ocr | OCR (ocrmypdf, tesseract `ita`) per scansioni e foto | 39,9 | 38,7 |
| #10 | chore/roadmap | Questo file | – | – |
| #11 | feat/matching | Top-3 schede da parole chiave pesate + cartella dichiarata, con motivazione | 59,4 | 57,9 |
| #12 | feat/missing-record | SCHEDA_MANCANTE se la scheda migliore ha ≤ 1 parola chiave ed è fuori dalle cartelle dichiarate | 73,2 | 72,9 |
| #13 | feat/compliance | 4 regole su 5: categoria, luogo, accesso, diffusione → NON_CONFORME | **84,9** | **87,4** |

Metriche dopo feat/compliance (sviluppo): esito 0,77 · categorie 0,98 · scheda top-3 0,97 · F1 SCHEDA_MANCANTE 0,75 · F1 scostamenti 0,61 · precisione entità 1,0.

## Da fare (in ordine)

1. **feat/retention** — CONSERVAZIONE_SCADUTA: data del documento letta nel testo + "Conservazione in anni" della scheda, rispetto al 28/10/2026; mai con conservazione illimitata. 13 casi su sviluppo. Nella stessa PR: "destinato alla pubblicazione" anche dal testo (determine all'albo, 5 casi di DIFFUSIONE_NON_PREVISTA). Metrica: F1 scostamenti (15), esito.
2. **feat/level** — livello di riservatezza 0–3 con regole esplicite (serve ad ACCESSO_ECCESSIVO).
3. **feat/names** — nomi e indirizzi con spaCy `it_core_news_lg`: una ventina di documenti con soli nomi risulta ancora "senza dati personali".
4. **LLM locale (Ollama, opzionale)** — categorie implicite e abbinamenti incerti.
5. **UI** — FastAPI + Jinja2 + Bootstrap Italia 2.x: inventario, coda di validazione, cruscotto, ricerca, registro decisioni RPD.
6. **Deploy** — `docker compose up` su server senza GPU (tesseract e ocrmypdf nel container), `publiccode.yml`, licenza EUPL-1.2.

## Decisioni prese

- Un file senza testo leggibile non è mai "senza dati personali" (meglio un falso allarme che un dato ignorato).
- Una categoria particolare descritta rende il documento "con dati personali" anche senza identificativi.
- Precisione entità misurata per file (le etichette non hanno le posizioni).
- Dichiarazioni sui requisiti penali di gara (art. 80/94 codice appalti) = dato giudiziario anche se negative, come nelle etichette.
- Nomi delle categorie art. 9 assenti dalle etichette scelti da noi: ORIENTAMENTO_SESSUALE, ORIGINE_ETNICA, POLITICHE, BIOMETRICI, GENETICI.
- Niente dipendenze per poche righe (controllo CF e IBAN scritti a mano); `requirements.txt` con versioni fissate.

## Regole pratiche imparate

- **Dati**: nulla escluso da git tranne `.env` e cache Python (scelta del team). Anche `data/pred_*.json` è versionato.
- **Merge**: li fa l'utente. L'agente non può fare merge né force-push (bloccati dai permessi): per allineare un branch usa `git merge origin/main`.
- **PR in pila**: aprire sempre con base `main`, anche se il branch parte da un'altra PR non ancora unita (il diff si riduce da solo dopo l'unione). Con base su un altro branch la #5 è finita dentro `feat/extract` invece che su `main` ed è servita la #6 per recuperarla.
- **Dipendenze di sistema**: `sudo apt install tesseract-ocr tesseract-ocr-ita ocrmypdf` (Debian 12). Senza, l'OCR resta vuoto ma tutto il resto funziona.
- `sviluppo/LEGGIMI.txt` non ha etichetta: lo scorer lo ignora con un avviso.
- **Windows**: `test_classify_skips_symlinks_outside_root` richiede il permesso di creare link simbolici (modalità sviluppatore) e senza markitdown installato la pipeline non parte. Lo scorer usa solo la libreria standard: `python -m classifier.scorer` funziona ovunque sulle `data/pred_*.json` salvate.
