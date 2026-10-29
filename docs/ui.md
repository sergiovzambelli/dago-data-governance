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
| `UI_DB` | `ui/var/decisioni.sqlite3` | registro delle decisioni (escluso da git) |
| `UI_ENTE` | `Comune` | nome dell'ente nell'intestazione |
| `UI_HOST`, `UI_PORTA` | `127.0.0.1`, `8000` | indirizzo di ascolto |
| `UI_UTENTI` | — | file degli utenti; obbligatorio se `UI_HOST` non è locale |
| `UI_SEGRETO` | casuale a ogni avvio | chiave dei token anti-CSRF (da fissare con più processi) |

Utenti: `python -m ui.users ui/var/utenti.json mario.rossi rpd` (la password, almeno 12 caratteri, viene chiesta senza mostrarla). Ruoli: `rpd` registra le decisioni, `operatore` consulta soltanto.

## Pagine

| Pagina | Requisito della specifica |
|---|---|
| **Cruscotto** `/` | documenti per esito, scostamento e scheda; elenco dei documenti senza scheda. Conta i valori dopo la validazione |
| **Coda di validazione** `/coda` | documenti con dati personali non ancora validati, ordinati per rischio (esito, scostamenti, categorie particolari, esposizione) |
| **Inventario** `/documenti` | filtri per esito, scheda e scostamento; 50 righe per pagina |
| **Documento** `/documenti/<id>` | evidenze: entità mascherate con posizione e confidenza, categorie, tre proposte con punteggio e motivazione, scostamenti spiegati con l'azione suggerita, scheda abbinata. Modulo di conferma o correzione e storico |
| **Ricerca** `/ricerca` | per percorso, scheda, esito, scostamento, categoria, tipo di entità, motivazione. Il testo integrale non è indicizzato (la specifica chiede di non conservare copie integrali) |
| **Registro decisioni** `/decisioni` | tutte le conferme e correzioni, in sola aggiunta |
| **Esportazione** `/esporta.json`, `/esporta.csv` | risultati con le correzioni dell'RPD applicate |

Demo della specifica: dalla coda si apre un documento non conforme, poi uno senza scheda; si vedono le evidenze, si registra la correzione e il cruscotto si aggiorna.

## Linee guida seguite

- **Bootstrap Italia 2.18.3** in `ui/static/vendor/` (CSS, JS, icone `sprites.svg`, font Titillium Web, Roboto Mono e Lora con le licenze): nessuna CDN, funziona senza Internet. I font sono dichiarati in `ui/static/fonts.css` invece che con `bootstrapItalia.loadFonts`, che inserisce stili inline.
- Struttura dei modelli Designers Italia: slim header con il nome dell'ente, header centrale, barra di navigazione che diventa menu laterale su telefono, breadcrumb, footer istituzionale.
- Accessibilità (WCAG 2.1 AA): `lang="it"`, link "Vai al contenuto principale", un solo `h1` per pagina, etichette su ogni campo, tabelle con `caption` e `scope`, esiti scritti a parole e non solo a colori, `aria-current` su navigazione e paginazione, nessuno scorrimento orizzontale a 375 px.
- Testi in italiano semplice; ogni scostamento dice cosa significa e cosa può fare l'RPD.

## Sicurezza

- Senza file degli utenti la UI si rifiuta di partire su un indirizzo non locale. Con il file: autenticazione HTTP Basic, password PBKDF2-SHA256 (310.000 iterazioni) e confronto a tempo costante.
- Decisioni solo con ruolo `rpd`, token anti-CSRF legato all'utente e controllo dell'intestazione `Origin`.
- Valori della decisione validati (esito tra i 4 ammessi, scheda presente nel registro, nota di massimo 500 caratteri senza caratteri di controllo). Registro SQLite con trigger che vietano modifica e cancellazione.
- Il JSON della pipeline è validato all'avvio; gli URL usano un identificativo opaco, non il percorso del file.
- Intestazioni: CSP senza script inline né risorse esterne, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy: same-origin`, `Cache-Control: no-store`. Log di accesso spento, perché gli URL della ricerca possono contenere termini sensibili.
- CSV esportato protetto dalle formule (celle che iniziano con `=`, `+`, `-`, `@`).
