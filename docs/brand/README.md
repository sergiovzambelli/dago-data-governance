# DaGo

Ogni file, la sua scheda, il suo grado di conformità.

> Brand kit di DaGo. In questa cartella: questa guida, `tokens.json` (colori, caratteri, spazi, raggi), i loghi `dago-*.svg` (copie da `asset/`) e `copertina.html` (la copertina del kit; usa le variabili dei token, quindi si vede a colori solo nella versione pubblicata). Nell'app i token corrispondono alle variabili in cima a `ui/static/ui.css` e i loghi sono in `ui/static/brand/`: se cambi un valore qui, cambialo anche lì.

DaGo è lo strumento con cui l'RPD di un ente pubblico scopre quali dati personali stanno nelle cartelle di rete, li abbina al registro dei trattamenti e decide cosa correggere. È un'**area di lavoro**: chi la usa valida decine di documenti di fila, quindi ogni scelta di forma serve a decidere più in fretta e senza errori.

## Nome

**DaGo** (prima si chiamava Vaglio; il nome è cambiato per decisione dell'utente).

- Si scrive sempre **DaGo**: D e G maiuscole, il resto minuscolo, mai tutto maiuscolo, mai tradotto.
- Senza articolo quando è il nome dello strumento: "apri DaGo", "DaGo propone T-PER-07".
- Il descrittore è **Patrimonio informativo**: va sotto o accanto al nome quando chi legge non conosce lo strumento (intestazioni, documenti, presentazioni); dentro l'app basta "DaGo".

## Principi

1. **Prima la decisione, poi il dettaglio.** In cima a ogni pagina c'è ciò che serve per decidere (esito, scheda, problemi); evidenze e testo vengono dopo.
2. **Il valore è sempre scritto.** Colori, barre e lancette aiutano a vedere, ma il numero e la parola ci sono sempre ("Non conforme, conformità bassa 10 su 100").
3. **Accessibile per legge, non per scelta.** WCAG 2.1 AA e Legge 4/2004: contrasto ≥ 4,5:1, tutto da tastiera, nessuno scorrimento orizzontale a 320 px.
4. **Il sistema propone, l'RPD decide.** Le proposte si presentano come tali ("proposto dal sistema"); la decisione è un'azione esplicita e registrata.
5. **Niente dati in chiaro senza bisogno.** Valori mascherati di default; il testo integrale solo all'RPD e mai conservato.

## Tono di voce

Italiano semplice, frasi corte, verbi all'inizio. Si parla di ciò che la persona riconosce (cartelle, schede, documenti), non di come è fatto il sistema.

| Sì | No |
|---|---|
| Conferma la proposta e vai al prossimo | Procedi con la validazione del record |
| Il file non si trova in nessuna cartella dichiarata nella scheda. | Violazione del vincolo di localizzazione. |
| Analisi non riuscita: il file potrebbe essere danneggiato. | Errore 500: eccezione non gestita. |
| 27 senza scheda | 27 record con esito SCHEDA_MANCANTE |
| Solo l'RPD può confermare o correggere l'esito. | Permesso negato. |

- **Pulsanti**: verbo + oggetto, 2–6 parole ("Valida i 132 rimasti", "Registra la correzione").
- **Errori**: cosa è successo e cosa fare, in una frase, senza scuse e senza codici.
- **Numeri**: cifre arabe, separatore decimale virgola ("4,5:1"), date `29/10/2026`.
- **Termini fissi**: esito, scheda, scostamento (nell'interfaccia "problema"), categoria particolare, RPD, registro dei trattamenti. Non alternarli con sinonimi.

## Logo

Il marchio è uno **scudo con tre barre** (dall'alto giallo, crema o blu, rosso corto): i dati classificati e messi in ordine, protetti. Il logo è lo scudo con il nome, "Da" nel colore del testo e "Go" in giallo, già in tracciati. Dettagli in `asset/LEGGIMI-brand-dago.md`.

| File | Uso |
|---|---|
| `dago-logo.svg` | scudo e nome su fondi chiari |
| `dago-logo-negativo.svg` | scudo e nome su fondi blu: menu e barra su telefono dell'app |
| `dago-marchio.svg` | solo scudo su fondi chiari: favicon |
| `dago-marchio-negativo.svg` | solo scudo su fondi blu: menu compresso |

- **Nell'app** il logo sta da solo in cima al menu, senza descrittore né nome dell'ente sotto.
- **Area di rispetto**: un quarto della larghezza dello scudo su ogni lato.
- **Misura minima**: 24 px di altezza da solo; 32 px con il nome.
- **Sfondi**: su `card`, `page` o `side`. Mai su foto o su uno dei colori degli esiti.
- **Non**: ruotarlo, cambiare l'ordine o i colori delle barre, metterci ombre o gradienti.

## Colori

Un colore = un significato. La palette viene da `asset/palette.jpg`: **blu** `#1C4B62` e **giallo** `#E8A519` sono i colori principali del marchio, il **rosso** `#CD3318` è l'accento e si usa poco (non conforme, problemi, arco del logo). Verde, ambra e grigio sono **solo** gli esiti, il viola **solo** le categorie particolari. Il giallo non porta mai testo su fondi chiari: sta sui fondi scuri (menu) o come filetto e segno.

| Ruolo | Token | Uso |
|---|---|---|
| Marchio e azioni | `blue-700`, `blue-800`, `blue-50` | pulsanti primari, link, focus; 9,4:1 sul bianco |
| Marchio, secondo colore | `yellow` | voce attiva e focus sul menu (6,1:1 su `side`), filetto dei riquadri, logo |
| Accento | `red` | non conforme e problemi; 5,1:1 con il bianco |
| Struttura | `side`, `side-ink`, `side-muted` | menu laterale blu scuro e barra in alto |
| Superfici | `page`, `card`, `sep`, `fill` | sfondo crema, riquadri, separatori, binari |
| Testo | `ink`, `muted` | 16,4:1 e 6,1:1 sul bianco |
| Esiti | `green`, `amber`, `red`, `grey` | capsule piene con testo bianco, sempre con la parola |
| Categorie particolari | `purple` | etichette "Salute", "Giudiziari"… |
| Indicatori | `gauge-1` … `gauge-6` | settori della scala di conformità, solo decorativi |

Regole: un testo sta solo sui fondi indicati nella sua nota; i colori che devono distinguersi (esiti) differiscono anche in luminosità, e la parola è sempre scritta, quindi bastano anche a chi non distingue il verde dal rosso. I token `gauge-3` e `gauge-4` non portano mai testo.

## Indicatori di conformità

La scala va da **rosso a sinistra** (non conforme, 0) a **verde a destra** (conforme, 100) in sei settori, con lancetta e perno scuri; rosso e giallo sono quelli della palette. Il grado: conforme 100; scheda mancante 30; non conforme 70 meno il peso dei problemi. Sotto o accanto all'arco ci sono sempre il numero e il livello a parole: **alta** (≥ 75, testo `green`), **media** (40–74, `amber`), **bassa** (< 40, `red`). La stessa scala diventa una barra orizzontale alla fine dell'analisi di un file.

## Caratteri

Il carattere di sistema (`sans`) per tutto: si legge bene, è già sul computer di chi lavora e non va scaricato. `mono` solo per codici fiscali mascherati, percorsi e impronte. Gerarchia data da dimensione e peso, mai dal colore: titoli 700, testo 400, etichette 600. Testo lungo al massimo 75 caratteri per riga.

## Icone

Icone a tratto della libreria `sprites.svg` di Bootstrap Italia (`it-files`, `it-check-circle`, `it-error`…), a 1,15 rem nel menu e 1 rem nel testo, colore `currentColor`. Sempre accanto a una parola; da sole solo con un nome accessibile. Niente emoji.

## Accessibilità

- Contrasto ≥ 4,5:1 per i testi, 3:1 per bordi di controlli e anelli di focus; focus visibile su ogni elemento interattivo (3 px `blue-700`, `yellow` sul menu scuro).
- Scorciatoie a tasto singolo (J, K, C, E, ?) disattivabili e mai attive nei campi.
- Bersagli di almeno 24 × 24 px; riflusso a 320 px; `prefers-reduced-motion` e colori forzati di Windows rispettati.
- Ogni grafico (anello, indicatore, barra) ha un testo alternativo con il valore.
