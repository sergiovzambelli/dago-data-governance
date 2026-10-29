# Roadmap e stato delle PR

Punto di partenza per ogni nuova sessione (persona o agente): cosa è fatto, cosa viene dopo, regole imparate strada facendo.
Si aggiorna **in ogni PR**: la riga della PR passa in "Fatte" con il punteggio, e la prossima si sposta in cima a "Da fare".

## Come si misura

- `make data` estrae il kit; `make score` (con `LLM=qwen3:1.7b` o `LLM=qwen3:8b` per il modello locale sui casi dubbi) analizza sviluppo e validation e stampa le 6 metriche della giuria e il totale su 100.
- Pesi (specifica): esito 20 · richiamo categorie particolari 20 · scheda top-3 20 · F1 SCHEDA_MANCANTE 15 · F1 scostamenti 15 · precisione entità 10.
- Lo scorer non misura LUOGO_NON_DICHIARATO (`IGNORED` in `classifier/scorer.py`), su decisione dell'utente.
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
| #13 | feat/compliance | 4 regole su 5: categoria, luogo, accesso, diffusione → NON_CONFORME | 84,9 | 87,4 |
| #14 | feat/retention | CONSERVAZIONE_SCADUTA con la data del documento (testo, nome file) | **88,3** | **90,1** |
| #15 | feat/llm-matching | Modello locale (Ollama) sui casi dubbi di abbinamento, facoltativo e spento: con registro senza parole chiave 92 → 100/109 schede giuste | 88,3 (88,0 acceso) | 90,1 (88,7 acceso) |
| #16 | feat/ui | Interfaccia web per l'RPD in `ui/` (Bootstrap Italia 2.18.3), separata dal classificatore | – | – |
| #18 | feat/ui-ux | UI più leggibile e accessibile, flusso "conferma e vai al prossimo" | – | – |
| #17 | chore/llm-model-make | `make score LLM=qwen3:1.7b` o `LLM=qwen3:8b`: scelta del modello locale | 88,3 (91,6 con 1.7b) | 90,1 (88,3 con 1.7b) |
| – | feat/records | UI: pagina Schede (crea, modifica, archivia, ripristina, storico, esporta il registro in CSV) | – | – |
| #19 | feat/ui-refresh | UI: in alto ciò che conta (frase di sintesi, 5 più urgenti, verdetto del documento), stile con le HIG di Apple sopra Bootstrap Italia | – | – |
| #26 | feat/sector-view | UI: tabella dei documenti per settore nel cruscotto (cartella sotto il server) e filtro per settore nell'inventario | – (invariato) | – (invariato) |
| #25 | feat/no-location-check | Tolto il controllo LUOGO_NON_DICHIARATO da classificatore, UI e scorer, su decisione dell'utente | 89,8 (86,3 con lo scorer di prima) | 90,4 (86,7 con lo scorer di prima) |
| – | feat/try-file-visual | Prova un file: testo con evidenziati dati personali, categorie e parole chiave; senza scheda l'RPD sceglie tra le 3 proposte o crea una nuova scheda già compilata, e il documento entra nell'inventario | – (invariato) | – (invariato) |
| – | feat/try-file | UI: pagina "Prova un file", carica un documento e mostra i passi dell'analisi (testo, dati, categorie, schede, esito) senza salvarlo | – (invariato) | – (invariato) |
| #20 | feat/draft-records | Bozze di nuove schede del registro per i documenti SCHEDA_MANCANTE (`make drafts`, modello locale facoltativo) e pagina "Nuove schede" per l'approvazione dell'RPD | – (invariato) | – (invariato) |
| #24 | feat/semantic-drafts | Bozze: gruppi per nome file uniti per contenuto (embedding `bge-m3` locali + verifica del modello) e RAG sul registro: struttura, ufficio e software dalla scheda esistente più simile scelta dal modello | – (invariato) | – (invariato) |

Metriche dopo feat/retention (sviluppo): esito 0,83 · categorie 0,98 · scheda top-3 0,97 · F1 SCHEDA_MANCANTE 0,75 · F1 scostamenti 0,75 · precisione entità 1,0.

## Da fare (in ordine)

1. **chore/ente-config** — togliere dal codice ciò che vale solo per il kit di Livorno: "Livorno" nella data dopo il luogo (qualsiasi nome di luogo seguito da virgola), il gruppo `GG_TUTTI_DIPENDENTI`, le cartelle `Pubblicazioni`/`OpenData`, la data di riferimento 28/10/2026 (predefinita: oggi). In un file di configurazione dell'ente con valori predefiniti.
2. **feat/publication** — "destinato alla pubblicazione" anche dal testo, non solo dalla cartella: determine all'albo (5 casi di DIFFUSIONE_NON_PREVISTA mancati su sviluppo). Metrica: F1 scostamenti (15), esito.
3. **feat/level** — livello di riservatezza 0–3 con regole esplicite (serve ad ACCESSO_ECCESSIVO).
4. **feat/names** — nomi e indirizzi con spaCy `it_core_news_lg`: una ventina di documenti con soli nomi risulta ancora "senza dati personali".
5. **LLM locale, altri usi (opzionale)** — categorie implicite e abbinamenti incerti. Bozze di schede fatte (feat/draft-records, feat/semantic-drafts); da fare: rimettere nel registro le schede approvate senza copia a mano (e codice della bozza nel formato delle schede), RAG su normativa e conservazione quando c'è un massimario, embedding del solo oggetto del documento per distinguere i procedimenti, provare `qwen3:8b`.
6. **UI** — prima versione fatta (feat/ui, `docs/ui.md`). Da fare: ricerca nei limiti dei permessi dell'utente (T-034), HTTPS tramite proxy al deploy (T-026), dichiarazione di accessibilità AgID, verifica con lettore di schermo.
7. **Deploy** — `docker compose up` su server senza GPU (tesseract e ocrmypdf nel container), `publiccode.yml`, licenza EUPL-1.2.

## Decisioni prese

- Niente controllo del luogo (LUOGO_NON_DICHIARATO), decisione dell'utente, anche nello scorer: le etichette vengono lette senza il luogo e un documento non conforme solo per il luogo è atteso conforme. **I punteggi da qui in poi non sono confrontabili con quelli precedenti** né con una giuria che usa le etichette originali (con le etichette originali: 86,3 sviluppo, 86,7 validation). Le cartelle dichiarate restano per abbinare la scheda.
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
- **Modelli piccoli e esempi**: dando a qwen3:1.7b una scheda di esempio "per lo stile", ne copia denominazione e finalità. Niente esempi nel prompt, solo i documenti.
- `sviluppo/LEGGIMI.txt` non ha etichetta: lo scorer lo ignora con un avviso.
- **Windows**: `test_classify_skips_symlinks_outside_root` richiede il permesso di creare link simbolici (modalità sviluppatore) e senza markitdown installato la pipeline non parte. Lo scorer usa solo la libreria standard: `python -m classifier.scorer` funziona ovunque sulle `data/pred_*.json` salvate.
