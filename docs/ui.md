# Interfaccia web per l'RPD

Cartella `ui/`, separata dal classificatore: legge solo il JSON prodotto da `python -m classifier.pipeline` e il CSV del registro dei trattamenti. Non importa nulla da `classifier/`, così backend e interfaccia evolvono senza toccarsi.

## Avvio

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-ui.txt        # Windows: .venv\Scripts\pip
UI_ENTE="Comune di Livorno" .venv/bin/python -m ui  # http://127.0.0.1:8000
```

| Variabile | Predefinito | Cosa fa |
|---|---|---|
| `UI_PREDIZIONI` | `data/pred_sviluppo.json` | JSON della pipeline; ricaricato da solo quando il file cambia |
| `UI_REGISTRO` | `data/Kit_team_hackathon_sfida_5/Registro_trattamenti.csv` | registro dei trattamenti (separatore `;`) |
| `UI_DOCUMENTI` | `data/Kit_team_hackathon_sfida_5/sviluppo` | cartella analizzata dalla pipeline: il dettaglio documento rilegge da qui il file per l'RPD (vuoto = mai) |
| `UI_BOZZE` | `data/bozze_sviluppo.json` | bozze di nuove schede (`make drafts`); lette all'avvio |
| `UI_DB` | `ui/var/decisioni.sqlite3` | registro delle decisioni (escluso da git) |
| `UI_ENTE` | `Comune` | nome dell'ente nell'intestazione |
| `UI_HOST`, `UI_PORTA` | `127.0.0.1`, `8000` | indirizzo di ascolto |
| `UI_UTENTI` | — | file degli utenti; obbligatorio se `UI_HOST` non è locale |
| `UI_SEGRETO` | casuale a ogni avvio | chiave dei token anti-CSRF (da fissare con più processi) |

Utenti: `python -m ui.users ui/var/utenti.json mario.rossi rpd` (la password, almeno 12 caratteri, viene chiesta senza mostrarla). Ruoli: `rpd` registra le decisioni, `operatore` consulta soltanto.

## Pagine

| Pagina | Requisito della specifica |
|---|---|
| **Compliance** `/` (prima Cruscotto) | documenti per esito, scostamento, scheda e settore (cartella sotto il server: `fileserver/Sociale/…` → Sociale); elenco dei documenti senza scheda. Conta i valori dopo la validazione |
| **Coda di validazione** `/coda` | documenti con dati personali non ancora validati, ordinati per rischio (esito, scostamenti, categorie particolari, esposizione) |
| **Inventario** `/documenti` | filtri per esito, scheda, scostamento e settore; 50 righe per pagina |
| **Documento** `/documenti/<id>` | evidenze: entità mascherate con posizione e confidenza, categorie, tre proposte con quota degli indizi (%) e motivazione, scostamenti spiegati con l'azione suggerita, scheda abbinata. Modulo di conferma o correzione e storico. **Solo RPD**: il file riletto da `UI_DOCUMENTI` con evidenziati dati personali, categorie e parole chiave, come in Prova un file (primi 5000 caratteri, `no-store`, mai salvato; avviso se l'impronta non coincide più); se la scheda manca, le stesse card di scelta (tre proposte con l'esito che ne deriverebbe, oppure Nuova scheda) |
| **Ricerca** `/ricerca` | per percorso, scheda, esito, scostamento, categoria, tipo di entità, motivazione. Il testo integrale non è indicizzato (la specifica chiede di non conservare copie integrali) |
| **Schede** `/schede` | registro dei trattamenti in uso: elenco con documenti abbinati e stato, nuova scheda (`/schede/nuova`), modifica, archiviazione e ripristino (`/schede/<codice>`), storico per scheda, esportazione `/schede/registro.csv` con tutte le colonne del registro |
| **Bozze di schede** `/bozze` | una bozza di scheda per tipo di documento senza scheda: l'RPD corregge i testi e approva o scarta; `/bozze/approvate.csv` scarica le approvate con le colonne del registro |
| **Prova un file** `/prova` | solo RPD: carica un file (cartella facoltativa) e vede il testo estratto con evidenziati dati personali, categorie particolari e parole chiave, le schede proposte, esito e scostamenti. Se la scheda manca sceglie una delle tre proposte (con l'esito che ne deriverebbe) oppure "Nuova scheda", già compilata: il documento entra nell'inventario come validato (`/prova/salva`). File e testo non vengono mai salvati. Serve `requirements.txt` oltre a `requirements-ui.txt`; permessi da `UI_PERMESSI` (predefinito: quelli del kit) |
| **Registro decisioni** `/decisioni` | tutte le conferme e correzioni, in sola aggiunta |
| **Esportazione** `/esporta.json`, `/esporta.csv` | risultati con le correzioni dell'RPD applicate |

Demo della specifica: dalla coda si apre un documento non conforme, poi uno senza scheda; si vedono le evidenze, si registra la correzione e il cruscotto si aggiorna.

## Pannello Accessibilità (feat/a11y-settings)

Pulsante rotondo sempre visibile in basso a destra (simbolo dell'accesso universale, `aria-expanded`, `aria-controls`) che apre il pannello "Accessibilità": dimensione del testo (normale, 125%, 150%), contrasto elevato, caratteri leggibili (Verdana), spaziatura del testo (valori WCAG 1.4.12), link evidenziati, animazioni ferme, cursore grande, guida alla lettura, bianco e nero, ripristino.

- Ogni scelta è una classe `a11y-*` sull'elemento `html`, definita in `ui/static/ui.css`: cambia davvero lo stile della pagina, non la copre con un livello sopra.
- `ui/static/a11y-init.js` nel `<head>` legge le scelte da `localStorage` (chiave `vaglio-a11y`) e le applica prima del disegno della pagina, quindi niente lampeggio; senza salvataggio disponibile la pagina resta normale. Le scelte non vanno al server.
- Il pannello non è modale: si chiude con × o Esc e il focus torna al pulsante; ogni cambio viene annunciato in una regione `aria-live`.
- Il pulsante fisso non copre ciò che riceve il focus: `scroll-padding-bottom` e spazio in fondo all'area di lavoro (WCAG 2.4.11).
- Verificato nel browser: contrasto elevato senza testi sotto 4,5:1, testo al 150% e spaziatura senza scorrimento orizzontale a 1440 e 375 px, scelte mantenute al ricaricamento.

## Verifica di accessibilità (feat/a11y-pass)

Controlli automatici nel browser su cruscotto, documento, inventario, Schede, Bozze e Prova un file: id duplicati, riferimenti ARIA, etichette, nomi di link e pulsanti, dimensione dei bersagli (2.5.8), ordine dei titoli, SVG e tabelle, riflusso a 320 px (1.4.10). Corretti:

- **Riflusso**: breadcrumb e pulsanti lunghi andavano su una riga e allargavano la pagina del documento a 380 px; ora vanno a capo.
- **Link con contesto** (2.4.4): i numeri della colonna "Documenti" in Schede dicono anche cosa contano ("6 documenti con la scheda T-PER-07").
- **Menu su telefono**: aperto, rende inerte il resto della pagina (il Tab non finisce sotto il menu); "Vai alla navigazione" lo apre invece di puntare a un menu nascosto.
- **Contrasto elevato di Windows** (`forced-colors`): bordi e colori di sistema per esiti, riquadri, barre, anello e indicatori.
- **Dichiarazione di accessibilità** in `/accessibilita`, linkata da ogni pagina: stato (parzialmente conforme), verifiche fatte, limiti noti, come segnalare un problema.

## Barra di avanzamento di Prova un file (feat/try-file-progress)

Con JavaScript, "Analizza" avvia l'analisi in background (`POST /prova/avvia`) e la pagina chiede lo stato ogni 0,4 secondi (`GET /prova/stato/<id>`). La barra segue le **fasi reali**, nell'ordine in cui avvengono sul server:

1. Lettura del file
2. Estrazione del testo (anche OCR)
3. Dati personali, categorie, scheda e controlli
4. Evidenziazione nel testo
5. Risultato

Ogni fase resta visibile almeno 0,45 secondi, così le fasi rapide non spariscono; l'ordine e il punto d'arrivo sono sempre quelli del server. Alla fine la barra diventa la scala **Non conforme → Conforme** (rosso → verde) e un indicatore scorre da sinistra fino al grado di conformità del file. Mentre passa, l'etichetta dice "Non conforme", "In parte conforme" o "Conforme"; poi si ferma sull'esito vero ("Non conforme, conformità media 45 su 100"). Il pulsante "Vedi il risultato" riceve il focus e apre `GET /prova/risultato/<id>`, leggibile **una sola volta**: poi il testo del documento viene cancellato dalla memoria.

- **Accessibilità**: `role="progressbar"` con `aria-valuenow` e `aria-valuetext` ("Fase 3 di 5: …", poi "Esito: Non conforme, conformità 45 su 100"); ogni fase annunciata in una regione `aria-live="polite"`; lo stato di ogni fase scritto anche a parole (fatta, in corso, da fare); con "riduci movimento" niente animazioni. Durante l'analisi le scorciatoie da tastiera sono sospese.
- **Senza JavaScript** il modulo funziona come prima (`POST /prova`, risultato nella stessa pagina).
- Se il server rifiuta il file (troppo grande, cartella non valida…), il modulo viene inviato normalmente e compare la pagina d'errore con la spiegazione.

## Indicatori di conformità (feat/compliance-gauge)

Indicatori a lancetta come un contachilometri (`ui/gauge.py`, SVG generato sul server): arco a 240° in sei settori dal rosso (a sinistra, non conforme) al verde (a destra, conforme).

| Documento | Grado (0-100) |
|---|---|
| Conforme | 100 |
| Scheda mancante | 30: la conformità non si può verificare |
| Non conforme | 70 meno il peso di ogni problema: diffusione 35, categoria non dichiarata 25, accesso eccessivo 25, conservazione scaduta 20 (minimo 0) |
| Nessun dato personale | nessun indicatore |

Livelli scritti a parole: **alta** (≥ 75), **media** (40-74), **bassa** (< 40). Il grado usa l'esito validato dall'RPD, se c'è.

- **Documento**: indicatore grande nel riquadro del verdetto, prima dell'esito.
- **Cruscotto**: conformità dell'archivio (media dei documenti con dati personali) accanto all'anello della validazione.
- **Settori**: indicatore piccolo in ogni riga della tabella "Documenti per settore".
- **Accessibilità**: ogni indicatore è un'immagine (`role="img"`) con il testo "Grado di conformità 74 su 100, media — archivio". Valore e livello sono scritti sotto o accanto all'arco, quindi i colori dei settori sono solo decorativi e chi non distingue il verde dal rosso legge comunque il risultato.
- I pesi sono scelte iniziali, da tarare con l'RPD (segnati come scorciatoia nel codice).

## Area di lavoro (feat/ui-workspace)

Decisione dell'utente: la UI è uno strumento di lavoro per l'RPD e non segue più lo stile istituzionale dei siti della PA. Scelte, tra le quattro direzioni proposte (strumento denso, revisione affiancata, cruscotto a dati, servizio essenziale): **revisione affiancata e cruscotto a dati, con le scorciatoie dello strumento denso**.

- **Guscio**: menu laterale scuro con le voci in due gruppi (Lavoro, Registro), utente (tondo con l'icona, nome e ruolo), esportazioni JSON e CSV come pulsanti e dichiarazione di accessibilità in fondo. Da desktop il pulsante "Comprimi il menu" (`aria-expanded`) lo riduce a una colonna di icone: i nomi delle voci restano per i lettori di schermo e come suggerimento al passaggio del mouse, la scelta resta nel browser (`localStorage`, chiave `menu-compresso`). Sotto i 992 px diventa una barra in alto con il pulsante "Apri il menu" (`aria-expanded`, Esc chiude e riporta il focus); senza JavaScript il menu resta sempre visibile.
- **Coda affiancata**: un documento da validare si apre con la coda a sinistra (documento corrente evidenziato con `aria-current`) e il documento a destra; "Conferma e vai al prossimo" aggiorna entrambi. Sotto i 1200 px la coda si nasconde e restano i pulsanti Precedente e Prossimo.
- **Scorciatoie**: <kbd>J</kbd> successivo, <kbd>K</kbd> precedente, <kbd>C</kbd> conferma e vai al prossimo, <kbd>E</kbd> apre la correzione con il focus su "Esito corretto", <kbd>?</kbd> mostra l'elenco. Non agiscono dentro i campi né con Ctrl, Alt e Cmd, sono indicate sui pulsanti e si disattivano dal pannello "Scorciatoie da tastiera" (WCAG 2.1.4; preferenza salvata nel browser, non sul server).
- **Cruscotto**: anello della validazione (`role="img"` con il testo "Validati X su Y") e quattro riquadri numerici (da validare, non conformi, senza scheda, con categorie particolari) che portano ai rispettivi elenchi.
- **Identità visiva**: carattere di sistema al posto di Titillium, blu `#1c4b62` per azioni e link (9,4:1), menu `#123444` con testo `#d5dee3` (9,6:1), giallo `#e8a519` per voce attiva e focus sul menu, rosso `#cd3318` come accento (palette in `asset/palette.jpg`). Contrasto misurato nel browser su cruscotto, coda, documento, inventario, ricerca, Prova un file, Schede, Bozze e registro: nessun testo sotto 4,5:1.
- **Bootstrap Italia 2.18.3** resta in `ui/static/vendor/` solo come base CSS (griglia, moduli, icone `sprites.svg`); il suo JavaScript non viene più caricato. `ui/static/fonts.css` e i font di Bootstrap Italia restano nel repository ma non sono più usati.
- Accessibilità (WCAG 2.1 AA): `lang="it"`, link "Vai al contenuto principale", un solo `h1` per pagina, etichette su ogni campo, tabelle con `caption` e `scope`, esiti scritti a parole e non solo a colori, `aria-current` su navigazione e paginazione, nessuno scorrimento orizzontale a 375 px.
- Testi in italiano semplice; ogni scostamento dice cosa significa e cosa può fare l'RPD.

## Leggibilità e flusso di lavoro

Dove Bootstrap Italia non bastava per leggibilità o accessibilità, `ui/static/ui.css` lo sostituisce (scelta dell'utente: la leggibilità prima dell'aderenza alla libreria).

- **Colori degli esiti** propri, con contrasto misurato nel browser: "Scheda mancante" passa da 2,39:1 (badge di Bootstrap Italia con testo scuro) a 6,8:1; tutti i testi delle pagine principali sono ≥ 4,5:1.
- **Tabelle**: nome del file in evidenza e cartella sotto, codice della scheda con il suo nome, problemi come etichette, stato a parole. I percorsi vanno a capo dopo `_`, `-`, `/`, `.` (`<wbr>`) invece che a metà parola. Sotto i 768 px ogni riga diventa una scheda con l'etichetta di ogni campo: niente scorrimento orizzontale.
- **Coda**: numerata, priorità a parole (Alta, Media, Bassa) con i motivi (es. "3 scostamenti · Salute · aperto a tutti i dipendenti") al posto del punteggio, pulsante "Inizia dal primo", pagine da 50.
- **Documento**: in alto la sintesi (esito, scheda, problemi, stato) e la posizione nella coda ("3 di 130 da validare"), con il link "Prossimo da validare" (spazio sotto i pulsanti prima del verdetto). Poi la decisione: conferma con un clic, anche "e vai al prossimo"; la correzione sta in un pannello `<details>` aperto solo per le schede mancanti. Dopo il salvataggio il messaggio di conferma riceve il focus (`ui/static/ui.js`), così i lettori di schermo lo annunciano.
- **Etichette dei campi** sempre visibili sopra il campo, al posto di quelle flottanti di Bootstrap Italia, che si sovrapponevano al testo.
- I riquadri dei problemi sono in Titillium e non in Lora; il testo è lungo al massimo 75 caratteri per riga; il focus è un bordo giallo di 3 px su tutti gli elementi; con `prefers-reduced-motion` le animazioni sono spente.
- **Cruscotto**: avanzamento della validazione e pulsante per iniziare; problemi e schede come barre con il numero scritto. Nessun avviso di modalità locale: resta solo "solo su questo computer" accanto all'utente nel menu.
- **Inventario**: filtri attivi elencati, ognuno da togliere da solo. **Ricerca**: esempi cliccabili. **Registro**: date `29/10/2026 14:01 UTC` e azioni a parole.

## Le informazioni importanti per prime

Secondo giro sulla UI, con il metodo della skill [apple-design](https://github.com/dickwu/apple-design-skill) (Human Interface Guidelines di Apple applicate a una web app: principi, colore, tipografia, layout, accessibilità). Ogni pagina mostra in alto ciò su cui l'RPD deve agire, il dettaglio sotto.

- **Token** in `ui/static/ui.css`: sfondo raggruppato `#f5f5f7` e riquadri bianchi; testo `#1d1d1f` (16,8:1), secondario `#636366` (6,0:1). **Un colore, un significato**: blu `#0066cc` solo per link e azioni, rosso per non conforme e problemi, ambra per scheda mancante, verde per conforme e validato, grigio per nessun dato, viola `#6b3fa0` (7,4:1) per le categorie particolari, che prima condividevano il rosso con i problemi.
- **Cruscotto**: l'elemento firma è una frase in italiano semplice, "35 non conformi, 27 senza scheda e 89 con categorie particolari", con ogni numero colorato che porta all'elenco. Sostituisce le tessere con il numero grande, che la skill indica come schema da template. Sotto c'è l'avanzamento della validazione con il pulsante per partire, poi "I più urgenti": i primi 5 della coda come lista raggruppata con chevron, cliccabile su tutta la riga. Gli esiti sono in una barra unica; le schede oltre l'ottava stanno in un pannello da aprire.
- **Documento**: verdetto in alto (esito grande nel suo colore, frase con i problemi, a destra scheda, categorie e dati per tipo come lista raggruppata). Problemi in una lista unica con "Cosa fare" evidenziato. Valori mascherati in un pannello oltre 5 righe.
- **Componenti**: intestazione con i temi chiari di Bootstrap Italia (`theme-light`, `theme-light-desk`), barra istituzionale blu invariata; pulsanti ed etichette a capsula; triangoli di apertura sui `<details>`; tabelle come liste raggruppate; etichette dei campi senza maiuscolo.
- **Focus**: anello blu di 3 px (5,6:1 sul bianco) al posto di quello giallo (1,9:1, sotto il 3:1 richiesto per gli indicatori grafici).
- Fuori: tema scuro (i componenti di Bootstrap Italia non lo prevedono), font: resta Titillium Web, carattere della PA.

## Schede del registro

- **Il CSV del registro non viene mai scritto.** Le schede in uso sono le righe del CSV (`UI_REGISTRO`) con sopra le versioni salvate dall'RPD nella tabella `schede` di `ui/var/decisioni.sqlite3`: creazione, modifica, archiviazione e ripristino, ognuna con autore e data, in sola aggiunta (trigger che vietano modifica e cancellazione).
- Le modifiche valgono subito in tutta la UI: nome della scheda nelle tabelle, scelta nella correzione, filtri. Una scheda **archiviata** non si può più scegliere; i documenti già abbinati la mantengono. Si ripristina dalla sua pagina.
- Il codice non si cambia dopo la creazione e non si riusa, nemmeno se la scheda è archiviata.
- **Per l'analisi**: "Esporta il registro (CSV)" scarica le schede in uso con le colonne del kit; si passa al classificatore (`python -m classifier.pipeline <cartella> registro_trattamenti.csv`).
- Modulo diviso in gruppi (trattamento, finalità e base giuridica, dati e interessati, dove stanno i documenti, conservazione, abbinamento automatico) con le spiegazioni dei campi che il classificatore usa: cartelle, categorie particolari, conservazione in anni, parole chiave.

## Sicurezza

- Senza file degli utenti la UI si rifiuta di partire su un indirizzo non locale. Con il file: autenticazione HTTP Basic, password PBKDF2-SHA256 (310.000 iterazioni) e confronto a tempo costante.
- Decisioni solo con ruolo `rpd`, token anti-CSRF legato all'utente e controllo dell'intestazione `Origin`.
- Schede: solo ruolo `rpd`, con gli stessi controlli delle decisioni. Codice nel formato `T-URP-01` (anche negli URL), obbligatori denominazione, finalità e base giuridica, diffusione e consenso solo SI o NO, conservazione in anni numerica o «Illimitata / non calcolabile», categorie particolari come codici in maiuscolo; testo senza caratteri di controllo, massimo 1000 caratteri per campo.
- Valori della decisione validati (esito tra i 4 ammessi, scheda presente nel registro, nota di massimo 500 caratteri senza caratteri di controllo). Registro SQLite con trigger che vietano modifica e cancellazione.
- Il JSON della pipeline è validato all'avvio; gli URL usano un identificativo opaco, non il percorso del file.
- Intestazioni: CSP senza script inline né risorse esterne, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy: same-origin`, `Cache-Control: no-store`. Log di accesso spento, perché gli URL della ricerca possono contenere termini sensibili.
- CSV esportato protetto dalle formule (celle che iniziano con `=`, `+`, `-`, `@`).
