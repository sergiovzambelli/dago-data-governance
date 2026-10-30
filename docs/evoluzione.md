# Evoluzione del progetto

Voci più recenti in cima. Formato: data, PR, cosa cambia, decisioni e perché.

## 2026-10-30 — fix/gauge-verde-destra: verde a destra negli indicatori
- Richiesta dell'utente: negli indicatori di conformità il verde va a destra e il rosso a sinistra, come un contachilometri che sale. Girati il contachilometri (`ui/gauge.py`: settori e lancetta, 0 a sinistra e 100 a destra) e la scala finale di Prova un file (gradiente, etichette agli estremi, indicatore che scorre fino al grado).
- Soglie dei livelli invariate (alta ≥ 75, media ≥ 40).

## 2026-10-30 — feat/a11y-settings: pannello Accessibilità
- Richiesta dell'utente: un pannello come quello dei siti pubblici, con contrasto elevato, testo grande e caratteri grandi. Aggiunte anche spaziatura del testo, link evidenziati, animazioni ferme, cursore grande, guida alla lettura, bianco e nero e ripristino. Dettagli in `docs/ui.md`.
- Decisione: preferenze che cambiano lo stile vero (classi CSS) e restano nel browser dell'utente, non un "overlay" che promette di sistemare l'accessibilità: quella di base resta nel sito per tutti.
- Corretti durante la prova: testo del menu nero su nero in contrasto elevato, filtro bianco e nero che spostava il pulsante fisso, pulsante che poteva coprire l'elemento con il focus su telefono.

## 2026-10-30 — feat/brand-vaglio: il prodotto si chiama Vaglio
- Nome scelto: **Vaglio** (da *vagliare*: esaminare e separare ciò che va tenuto da ciò che va corretto), con il descrittore "Patrimonio informativo". Alternative scartate: Lancetta, Custode, Mappa dati. Non è stata fatta una ricerca di marchi registrati: da fare prima di usarlo fuori dall'hackathon.
- Brand kit salvato in `docs/brand/` (guida, `tokens.json`, logo, copertina) e pubblicato come artifact privato. I token sono i valori reali di `ui/static/ui.css`; un test controlla che i colori principali coincidano.
- Nell'app: nome nel titolo delle pagine, nel menu e nella barra su telefono; logo al posto dell'icona generica; favicon SVG.

## 2026-10-30 — feat/a11y-pass: verifica e correzioni di accessibilità
- Audit nel browser con controlli automatici su sei pagine e prova manuale a 320 px, con tastiera e menu su telefono. Trovati e corretti: riflusso della pagina del documento (breadcrumb e pulsanti), link solo numerici in Schede, Tab che finiva sotto il menu aperto, link "Vai alla navigazione" verso un menu nascosto, nessun supporto al contrasto elevato di Windows.
- Nuova pagina `/accessibilita` (dichiarazione di accessibilità, come chiedono le linee guida AgID): dichiara lo strumento "parzialmente conforme" perché manca ancora la prova con lettori di schermo.

## 2026-10-30 — feat/try-file-progress: barra di avanzamento in Prova un file
- Richiesta dell'utente: in Prova un file una barra "tipo download" che avanza durante l'analisi, dice le fasi e alla fine indica conforme o non conforme.
- L'analisi gira in background (`/prova/avvia`, `/prova/stato/<id>`, `/prova/risultato/<id>`): la barra segue le 5 fasi reali del server, poi diventa la scala dal verde al rosso e l'indicatore scorre fino al grado di conformità, con l'etichetta che cambia lungo la strada. Dettagli in `docs/ui.md`.
- Decisione: fasi reali e non un'animazione a tempo, perché l'estrazione (e l'OCR delle scansioni) può durare da un secondo a minuti. Ogni fase resta visibile almeno 0,45 s solo per leggibilità.
- Decisione: il risultato con il testo del documento resta in memoria al massimo 15 minuti e si legge una sola volta; lo stato interrogato dalla pagina non contiene testo. Nuove minacce T-050…T-053.
- Indicatore di conformità anche nel risultato di Prova un file, come nella pagina del documento.
- Provata dal vivo nel browser: fasi, scala, etichette "Conforme → In parte conforme" e risultato aperto; nessuno scorrimento orizzontale a 375 px.

## 2026-10-30 — feat/compliance-gauge: indicatori a lancetta del grado di conformità
- Richiesta dell'utente: indicatori visivi del grado di conformità, dal verde (conforme) al rosso (non conforme), come i contachilometri di un'immagine di riferimento.
- `ui/gauge.py`: grado 0-100 per documento (conforme 100, scheda mancante 30, non conforme 70 meno il peso dei problemi) e SVG a sei settori con lancetta. Indicatori nel verdetto del documento, nel cruscotto (archivio) e nella tabella dei settori. Dettagli in `docs/ui.md`.
- Decisione: il grado misura quanto il documento rispetta la sua scheda, non la probabilità che l'esito sia giusto. Scheda mancante a 30 perché senza scheda non si può verificare niente. Pesi scelti a mano, da tarare con l'RPD.
- Accessibilità: valore e livello (alta, media, bassa) sempre scritti; l'indicatore ha un testo alternativo completo; i colori dei settori sono decorativi. Contrasto dei testi verificato nel browser; nessuno scorrimento orizzontale a 375 px.

## 2026-10-30 — feat/ui-workspace: la UI diventa un'area di lavoro
- Richiesta dell'utente: un'interfaccia diversa dallo stile istituzionale. Proposte quattro direzioni (strumento denso, revisione affiancata, cruscotto a dati, servizio essenziale); scelta la combinazione consigliata: revisione affiancata + cruscotto a dati + scorciatoie da tastiera.
- Menu laterale al posto di header e footer istituzionali; coda di validazione accanto al documento; scorciatoie J, K, C, E e ? disattivabili; cruscotto con anello della validazione e quattro riquadri numerici. Dettagli in `docs/ui.md` ("Area di lavoro").
- Decisione: Bootstrap Italia resta solo come base CSS (griglia, moduli, icone), per non riscrivere le pagine Schede, Bozze e Prova un file; il suo JavaScript non si carica più. La regola 7 di `AGENTS.md` ora descrive l'area di lavoro, così un agente non ripristina lo stile istituzionale.
- Verifiche nel browser: contrasto ≥ 4,5:1 su 9 pagine (menu compreso), menu su telefono con focus ed Esc, nessuno scorrimento orizzontale a 375 px, scorciatoie J e K provate dal vivo, E e C con eventi simulati (lo strumento di prova non inoltrava in modo affidabile alcuni tasti).

## 2026-10-29 — feat/doc-view: il dettaglio documento come Prova un file
- Richiesta dell'utente: un file aperto dal cruscotto (o da coda e inventario) deve essere mostrato come in Prova un file.
- Decisioni (dell'utente): sì al testo evidenziato nel dettaglio, solo per l'RPD; per i documenti senza scheda, le stesse card di scelta.
- Il file viene riletto dalla cartella analizzata (`UI_DOCUMENTI`, predefinita la cartella `sviluppo` del kit), estratto e rianalizzato con la stessa funzione di Prova un file (`analysis()` in `ui/app.py`, estratta da `/prova`). Parti di pagina comuni in `ui/templates/_file.html`. Le card passano da `/prova/salva`, già firmato: la nota della decisione dice da dove arriva la scelta.
- Sicurezza: percorso risolto anche nei link simbolici e accettato solo dentro la cartella; massimo 20 MB; l'operatore vede solo i valori mascherati; pagina `no-store`, testo mai salvato. Se l'impronta SHA-256 non coincide più con quella dell'analisi compare un avviso e le card non vengono mostrate.
- Verifica sul kit: la rianalisi della UI coincide con `pred_sviluppo.json` su 156 documenti su 156; pagina in 0,1 s (3 s la prima volta, 0,6 s per una scansione con OCR).
- Trovato: senza `.venv` i test della UI vengono saltati in blocco (`importorskip("fastapi")`). Il "1 skipped" delle PR precedenti era tutta `tests/test_ui.py`: si lanciano con `.venv/bin/python -m pytest`.

## 2026-10-29 — feat/sector-view: documenti per settore
- Richiesta dell'utente: una vista per settore. Prima una prova su Sociale (25 file, tutte le schede): 81,0 contro 88,3 di tutto lo sviluppo, quindi il settore è utile per vedere dove il classificatore sbaglia di più.
- Decisioni (dell'utente): il settore è la **cartella** sotto il server (`fileserver/Sociale/…` → Sociale), non la struttura della scheda, perché c'è anche per i file senza scheda. Vista = tabella nel cruscotto (file, conformi, non conformi, senza scheda) e filtro nell'inventario, niente pagina nuova.
- Limite: anche `Condivisa`, `Pubblicazioni` e `OpenData` risultano settori, perché sono cartelle sotto il server. Un file caricato senza cartella sta in "Senza cartella".
- Punteggio invariato: la pipeline non cambia.

## 2026-10-29 — feat/no-location-check: niente più errore di luogo
- Richiesta dell'utente: togliere il controllo di dove stanno i documenti e non mostrare più l'errore di luogo. Scelta dell'utente tra tre opzioni (solo Prova un file, solo UI, anche classificatore): **anche nel classificatore**.
- `classifier/compliance.py` non produce più LUOGO_NON_DICHIARATO; la UI non lo conosce più (anche nelle predizioni vecchie viene ignorato). Le cartelle dichiarate restano: servono all'abbinamento della scheda e a decidere SCHEDA_MANCANTE.
- Misura (`make score`, sole regole): sviluppo 88,3 → **86,3**, validation 90,1 → **86,7**. Cala F1 scostamenti (sviluppo 0,75 → 0,65) e un po' l'esito (0,83 → 0,81): i documenti fuori posto che avevano solo questo problema ora risultano conformi, mentre le etichette della giuria li danno non conformi. Lo scorer non cambia.
- Predizioni `data/pred_*.json` rigenerate.
- Seconda richiesta dell'utente: "anche la giuria non deve basarsi su questo". `classifier/scorer.py` ignora LUOGO_NON_DICHIARATO nelle etichette e nelle predizioni; un documento atteso NON_CONFORME solo per il luogo diventa atteso CONFORME. Con questo scorer: sviluppo **89,8**, validation **90,4** (F1 scostamenti 0,83; esito 0,85 e 0,84).
- Attenzione: il punteggio della giuria vera dipende dalle sue etichette, non da questo scorer. Se la giuria misura ancora il luogo, il valore realistico resta 86,3 / 86,7.

## 2026-10-29 — feat/semantic-drafts: gruppi per contenuto e schede simili (RAG sul registro)
- Richiesta dell'utente: il raggruppamento per nome file è grezzo; provare raggruppamento semantico e RAG. Decisione (dell'utente): una sola PR.
- Embedding locali con Ollama `bge-m3` (multilingue), stesso `OllamaClient` solo verso host locali. `make drafts` usa `EMBED=bge-m3` di default; senza modello, o se gli embedding falliscono (avviso su stderr), si torna ai gruppi per nome file.
- **Taratura sui dati di sviluppo**: i documenti dello stesso tipo hanno coseno ≥ 0,78; ma i centri di "concessione loculo" e "domanda loculo" (da unire) sono a 0,759, ERP e "fondo affitti" (trattamenti diversi) a 0,754. Gli embedding del testo intero misurano l'ufficio e l'argomento, non il procedimento: nessuna soglia separa i due casi. Scelta: **ibrido** come per gli abbinamenti, "recupera e verifica". Si parte dai gruppi per nome file; due gruppi si uniscono da soli sopra 0,85, tra 0,70 e 0,85 solo se il modello risponde SI a "stesso procedimento?".
- Esito su sviluppo: nessuna unione (anche llama3.1 dice che le due "loculo" sono procedimenti diversi). 15 bozze come prima: il meccanismo è provato dai test, non ancora dai dati.
- **RAG sul registro**: per ogni gruppo le 3 schede del registro più vicine per contenuto vanno nel prompt; il modello ne indica una dello stesso ufficio (`scheda_simile`) o NESSUNA. Se la sceglie, struttura responsabile, ufficio e software vengono copiati, restano "da verificare" e l'Origine dice da quale scheda arrivano. Codici fuori dalle 3 recuperate ignorati.
- Qualità della scheda simile (giudizio nostro, il kit non ha etichette): qwen3:1.7b circa 6 giuste su 14 (prende quasi sempre la prima); llama3.1 (8B) circa 8 su 15, 2 discutibili, 3 sbagliate (ERP → Anagrafe, anagrafe canina → Anagrafe, reclami → Verbali), 2 NESSUNA. `data/bozze_sviluppo.json` rigenerato con `LLM=llama3.1`, circa 11 minuti.
- Problema di sistema trovato: con GPU da 4 GB e il modello di chat caricato, `bge-m3` a metà sulla GPU restituisce NaN (Ollama 0.13 risponde errore 500). Gli embedding girano sempre su CPU (`num_gpu: 0`).
- Fuori: RAG su normativa e conservazione (nel kit non c'è un massimario né un piano di conservazione: senza fonte il modello inventerebbe); codice della bozza compatibile con la pagina Schede (`NUOVA-CONCESSIONE-LOCULO` non rispetta il formato dei codici).
- Punteggio invariato: la pipeline non cambia.

## 2026-10-29 — feat/try-file-visual: il file evidenziato e la scelta della scheda
- Richiesta dell'utente: vedere il file con evidenziate le informazioni trovate; se la scheda manca, proporre le tre schede o "Nuova scheda", che crea una scheda già compilata.
- Testo estratto con evidenziati dati personali (rosso), categorie particolari (viola) e parole chiave delle schede proposte (blu). Ogni tipo ha anche un bordo diverso e un'etichetta per i lettori di schermo: il colore non è l'unico segnale.
- Decisione (dell'utente): scegliere una scheda **aggiunge il documento all'inventario**, già validato dall'RPD. Si conserva solo la predizione (valori mascherati, nessun testo né file) nella tabella `caricati`, in sola aggiunta; la decisione va nel registro delle decisioni con una nota sull'origine.
- L'analisi torna dal browser firmata (HMAC con la chiave del server e il nome dell'utente): il server non tiene stato tra il caricamento e la scelta, e nessuno può cambiare esito, scheda o percorso nel modulo. Dopo un riavvio senza `UI_SEGRETO` la firma non vale più: si ricarica il file.
- La scelta sta subito sotto l'esito, a tutta larghezza: una card per proposta (codice, nome, barra della quota degli indizi, esito che ne deriverebbe, pulsante "Usa questa scheda" in fondo) e una card tratteggiata per la nuova scheda (richiesta dell'utente: più visibile e ben definita).
- Per ogni scheda proposta la pagina mostra già l'esito che avrebbe il documento ("con questa scheda: non conforme: accesso eccessivo").
- Nuova scheda: compilata con `classifier/drafts.py` (cartella, gruppo di accesso, categorie rilevate, diffusione NO, tipologia e parole chiave dal nome del file), codice `NUOVA-…` reso valido e unico. Base giuridica e finalità restano all'RPD, che viene portato sulla scheda appena creata. Modello locale non usato qui.
- Un file caricato con lo stesso percorso di uno analizzato dalla pipeline lo sostituisce nell'inventario.

## 2026-10-29 — feat/try-file: provare un file dalla UI
- Richiesta dell'utente: una nuova pagina dove caricare un file e vedere l'elaborazione fatta su di esso.
- Pagina **Prova un file** (`/prova`, solo RPD): carica il file, cartella sul file server facoltativa, e mostra in ordine testo estratto (primi 5000 caratteri), dati personali mascherati, categorie particolari, tre schede più vicine con motivazione, esito e scostamenti.
- `classifier/pipeline.py`: il corpo del ciclo diventa `analyze(rel, text, …)`, usato sia da `classify` sia dalla UI. Predizioni di sviluppo identiche byte per byte.
- Decisioni: il file sta solo in una cartella temporanea cancellata subito dopo, con nome fisso (dall'utente si prende solo l'estensione); niente nell'inventario né nel database. Si usa il registro in uso nella UI (con le modifiche delle Schede). Modello locale spento in questa pagina.
- Richiesta dell'utente: il punteggio delle schede non si capiva. Ora la UI (anche nel dettaglio documento) mostra la quota degli indizi: punteggio della scheda diviso la somma delle proposte, in percentuale, con una riga che dice che non è una probabilità. Il punteggio grezzo resta nel JSON.
- Decisione che cambia una regola precedente: la UI ora importa da `classifier/` (solo in questa pagina, con import al momento della richiesta: senza `requirements.txt` le altre pagine funzionano) e mostra il testo del documento a chi lo ha caricato (T-041).

## 2026-10-29 — feat/records: gestione delle schede del registro
- Richiesta dell'utente: una pagina per vedere le schede del registro, crearne di nuove, modificarle, archiviarle.
- Decisioni (dell'utente): salvataggio in SQLite con storico, il CSV del registro resta com'è; eliminare = archiviare, con ripristino; nuova PR da `main`.
- Perché così: il registro dei trattamenti (art. 30 GDPR) deve restare tracciabile, e il CSV del kit è anche l'ingresso del classificatore e dei punteggi: scriverlo dalla UI cambierebbe le misure senza che nessuno lo veda. La PR #20 aveva già scelto di non scriverlo.
- Le modifiche valgono subito nella UI; per l'analisi si esporta il registro in CSV. Il collegamento "bozza approvata → nuova scheda" resta fuori.

## 2026-10-29 — feat/draft-records: bozze di nuove schede per i documenti senza scheda
- `classifier/drafts.py` (`make drafts`, dopo `make score`): per i documenti SCHEDA_MANCANTE propone una scheda del registro **per tipo di documento**. Il tipo viene dal nome del file senza date, numeri e cognomi (`SCIA_vicinato_20260124_202.pdf` → `scia_vicinato`), così le domande SAD finite in `Condivisa` stanno con quelle di `Sociale/Disabilita`.
- Il sistema compila ciò che sa: cartella prevalente del gruppo (un documento fuori posto non diventa un percorso dichiarato), gruppo di accesso da `permessi_cartelle.csv`, categorie particolari rilevate, diffusione NO. Il modello locale, se attivo (`LLM=qwen3:1.7b`), propone denominazione, finalità, interessati, categorie di dati, tipologie, parole chiave e una base giuridica da un elenco chiuso (art. 6 lett. a, b, c, e). Fonti normative, struttura, ufficio e conservazione restano sempre da scrivere all'RPD e sono segnati "da verificare".
- Controlli sulla risposta del modello: campi su una riga, al massimo 500 caratteri; scartati se contengono entità riconosciute (CF, IBAN, …) o un "Nome Cognome" presente nei documenti; parole chiave tenute solo se compaiono nei documenti; base giuridica fuori elenco ignorata.
- Prova su sviluppo con qwen3:1.7b: 27 documenti → 15 bozze in circa 75 s. Con una scheda di esempio nel prompt il modello ne copiava denominazione e finalità (SCIA → "Appalti di lavori", reclami → "Incidenti stradali"): tolta. Senza esempio le denominazioni sono pertinenti ("Domanda di assistenza domiciliare", "SCIA per l'apertura di un esercizio di vicinato"), ma il modello metteva nomi veri negli interessati: da qui il filtro dei nomi.
- UI: pagina **Nuove schede** (`/bozze`). L'RPD corregge i campi testuali e approva o scarta; decisioni nella tabella `bozze` del registro SQLite, in sola aggiunta. Le schede approvate si scaricano in `/bozze/approvate.csv` con le stesse colonne del registro. Base giuridica, denominazione e finalità obbligatorie per approvare.
- Decisione: la UI non scrive nel registro dei trattamenti. È il riferimento dei controlli di conformità: una modifica passa dall'RPD, che incolla le righe approvate.
- Decisione (dell'utente): una sola PR per classificatore, UI e documentazione, invece delle due PR piccole previste da AGENTS.md.
- Punteggio invariato: la pipeline non cambia.

## 2026-10-29 — feat/ui-refresh: le informazioni importanti per prime
- Richiesta dell'utente: UI più attuale e che metta in evidenza ciò che conta. Dalle schermate: nel cruscotto i numeri da cui partire erano allo stesso livello dell'elenco delle 30 schede; nel documento esito, problemi e dati trovati erano sparsi in tre punti, e 12 righe di codici fiscali spingevano in basso il resto.
- Primo passo: "Da guardare subito" con i 5 più urgenti, verdetto in alto nel documento, valori mascherati in un pannello.
- Secondo passo, su richiesta dell'utente ("non avere paura a stravolgere la visual"): stile rifatto con la skill apple-design (HIG di Apple come principi per il web). Frase di sintesi al posto delle tessere numeriche, liste raggruppate, un colore per significato (viola per le categorie particolari), intestazione chiara, focus blu. Dettagli e contrasti in `docs/ui.md`.
- Decisione: Bootstrap Italia resta (griglia, icone, font, intestazione e piè di pagina istituzionali, temi chiari della libreria); cambia lo strato di stile sopra. Niente tema scuro: i componenti della libreria non lo supportano.

## 2026-10-29 — chore/llm-model-make: scelta del modello da `make`
- `make score LLM=qwen3:1.7b` (o `LLM=qwen3:8b`) accende il modello locale sui casi dubbi; `make score` senza `LLM` resta con le sole regole. Il modello passa a `CLASSIFIER_LLM_MODEL`, già letto dalla pipeline: nessuna modifica al codice Python.
- Misure con `qwen3:1.7b` (Quadro T1000 4 GB, tutto in GPU; circa 11 minuti per sviluppo + validation, contro meno di 2 minuti con le sole regole): sviluppo 88,3 → **91,6**, validation 90,1 → **88,3**. Stesso schema del modello 8b: migliora sviluppo, peggiora validation.
- Decisione: il modello resta spento di default e le predizioni salvate restano quelle delle sole regole.
- Nota di sistema: un `CUDA_VISIBLE_DEVICES=` vuoto nell'override systemd di Ollama nascondeva la GPU (tutto su CPU, molto più lento). Va tolto e il servizio riavviato.

## 2026-10-29 — feat/ui-ux: leggibilità, accessibilità e flusso di validazione
- Analisi della UI nel browser: contrasto insufficiente su "Scheda mancante" (2,39:1), nomi dei file persi nei percorsi, priorità come numero senza significato, nessun modo di passare al documento successivo, modulo di decisione con campi sempre attivi, tabelle che sul telefono scorrevano di lato, etichette flottanti sovrapposte, avviso ripetuto su ogni pagina, date in formato tecnico.
- Correzioni descritte in `docs/ui.md` ("Leggibilità e flusso di lavoro"). La più utile: "Conferma la proposta e vai al prossimo" e la posizione nella coda, che evitano di tornare all'elenco dopo ogni documento.
- Decisione (dell'utente): leggibilità e accessibilità prima dell'aderenza a Bootstrap Italia. Restano la libreria, la struttura dei modelli Designers Italia e i font; colori degli esiti, tabelle, etichette dei campi e riquadri sono personalizzati in `ui/static/ui.css`.
- Verificata nel browser: contrasto ≥ 4,5:1 su tutti i testi di cruscotto, coda, inventario, documento e registro; nessuno scorrimento orizzontale a 375 px; flusso "conferma e vai al prossimo" provato con il focus sul messaggio.

## 2026-10-29 — feat/ui: interfaccia web per l'RPD
- Nuova cartella `ui/` (FastAPI + Jinja2 + Bootstrap Italia 2.18.3 in locale): cruscotto, coda di validazione per rischio, inventario con filtri, pagina del documento con le evidenze e la conferma o correzione dell'RPD, ricerca, registro delle decisioni, esportazione JSON e CSV. Dettagli in `docs/ui.md`.
- Decisione: la UI legge solo il JSON della pipeline e il CSV del registro, senza importare `classifier/`. Dipendenze in `requirements-ui.txt`, non in `requirements.txt`; nessuna modifica a `Makefile` e `.gitignore` della radice. Così backend e UI si sviluppano in parallelo senza conflitti.
- Decisione: registro delle decisioni in SQLite in sola aggiunta; l'ultima decisione su un file vale solo se l'impronta SHA-256 non è cambiata.
- Verificata nel browser a 1280 e 375 px: corretti un'intestazione `Referrer-Policy` che faceva inviare `Origin: null` ai moduli, il contrasto del footer e lo scorrimento orizzontale causato dai percorsi lunghi.

## 2026-10-29 — feat/llm-matching: modello locale per i casi dubbi (facoltativo)
- `classifier/llm.py`: client Ollama scritto con la libreria standard (nessuna dipendenza nuova), solo verso host locali. `decide()`: il modello verifica la prima proposta delle regole (SI/NO sulla finalità della scheda); se la scarta sceglie lui tra tutte le schede o dice NESSUNA, e la sua scelta viene a sua volta verificata. Codici fuori dal registro ignorati. Se il modello non risponde valgono le regole.
- Il modello legge denominazione, finalità e documenti tipici delle schede, non le parole chiave: sono queste che cambiano da un ente all'altro.
- Si usa solo nei casi dubbi (`matching.is_doubtful`: prima proposta con ≤ 2 parole chiave e fuori cartella), circa 1 documento su 4. Attivazione: `CLASSIFIER_LLM_MODEL=qwen3:8b` (e `CLASSIFIER_LLM_URL`, predefinito `http://localhost:11434`). **Spento di default.**
- Misure con `qwen3:8b` (RTX 4070 portatile, circa 3 s a verifica; testo da `pdftotext` e libreria standard):
  - da solo, senza regole: scheda giusta o NESSUNA in 97/118 documenti di sviluppo; tende a forzare l'abbinamento (domande SAD → contributi economici, reclami URP → verbali);
  - **registro senza la colonna "Parole chiave"** (prova di robustezza per altri enti): regole 92/109 su sviluppo e 37/48 su validation; regole + modello sui dubbi **100/109** e **43/48**;
  - registro completo del kit: punteggio sviluppo 88,3 → 88,0, validation 90,1 → 88,7. Le parole chiave del kit sono scritte per questi documenti e il modello aggiunge errori sulle domande SAD (assegnate a T-SOC-01) quanto ne corregge (log VPN, scrutatori, accesso agli atti).
- Decisione: modello facoltativo e spento; da accendere con registri senza parole chiave o con parole chiave povere. Le predizioni salvate restano quelle delle sole regole.
- Provato un prompt più severo ("stesso settore o stesso ISEE non bastano"): sviluppo 87,9, nessun miglioramento. Scartato per non adattare il prompt a questo kit.

## 2026-10-29 — feat/retention: CONSERVAZIONE_SCADUTA, la quinta regola
- `classifier/dates.py`: `document_date(percorso, testo)` cerca la data del documento in quest'ordine: data dopo il luogo o un'etichetta ("Livorno, 12 marzo 2026", "Data: …"), poi data nel nome del file (AAAAMMGG), poi data più recente nel testo. Escluse le date di nascita ("nato … il", "Nome (23/02/1991)"), le date future e quelle impossibili (31/02).
- Strategie misurate su sviluppo (data esatta su 155 file): solo nome file 132, solo testo 127, **ordine scelto 134**. La data di modifica dei file non serve: nello zip del kit vale 28/10/2026 per tutti.
- `compliance.check` riceve la data: scaduto se data + "Conservazione in anni" della scheda è anteriore al 28/10/2026 (il giorno stesso non conta; 29 febbraio → 28). Mai con conservazione illimitata, vuota o data sconosciuta.
- Risultato su CONSERVAZIONE_SCADUTA: sviluppo 11/13, validation 5/7, **nessun falso positivo**. I casi mancati hanno la scheda sbagliata a monte (SCHEDA_MANCANTE o "senza dati personali").
- `data/pred_*.json` aggiornati applicando `compliance.check` e `document_date` alle predizioni salvate, con il testo estratto da `pdftotext` e dalla libreria standard: su Windows mancavano markitdown e OCR. Per le scansioni senza testo vale la data nel nome del file.
- Punteggio: sviluppo 84,9 → **88,3** (F1 scostamenti 0,75, esito 0,83), validation 87,4 → **90,1** (F1 0,81, esito 0,84).

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
