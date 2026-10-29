# Regole per gli agenti — Hackathon sfida 5

Valgono per ogni agente (Claude Code, Codex, ecc.) che lavora su questo repo. Sono obbligatorie.

## 1. Controllo contesto: "Halo!"

Ogni risposta dell'agente inizia con `Halo!`.
Se manca, il contesto è stato compresso troppo e queste regole sono andate perse: l'utente deve fermare l'agente e fargli rileggere questo file.

## 2. Skill ponytail obbligatoria

Prima di qualsiasi lavoro sul codice, attiva la skill `ponytail` (livello `full`, salvo diversa indicazione).
In breve: la modifica più piccola che risolve davvero il problema, niente feature o astrazioni non richieste, ogni scorciatoia segnata con `// shortcut: <limite>, <quando migliorare>`.
Alla fine di ogni risposta: una o due righe su cosa non è stato fatto/verificato e sui rischi.

## 3. Flusso di lavoro: PR piccole su GitHub

- Repo: `https://github.com/michele702/Hackathon-sfida-5`, branch base `main`.
- Mai commit diretti su `main`. Ogni modifica passa da branch + Pull Request (`gh pr create`).
- Nome branch: `feat/<cosa>`, `fix/<cosa>`, `chore/<cosa>`.
- **Step brevi**: una PR = una funzionalità verificabile a mano in pochi minuti. Se una PR supera ~200 righe di diff, va spezzata.
- Ogni PR descrive: cosa fa, **come verificarla** (passi concreti), cosa resta fuori.
- Dopo aver aperto la PR, l'agente si ferma e aspetta il via dell'utente prima dello step successivo. Niente catene di PR non verificate.
- Commit in formato Conventional Commits (`feat: ...`, `fix: ...`).
- Ogni PR compila la checklist di `.github/pull_request_template.md`. Una PR con la checklist incompleta non si merge.

## 4. Test Driven Development

- Prima il test, poi il codice: scrivi il test, vedilo **fallire**, scrivi il minimo codice che lo fa passare, poi rifattorizza.
- Ogni PR con logica nuova o bug fix contiene i suoi test. Un bug fix parte da un test che riproduce il bug.
- La suite di test deve passare in locale prima di aprire la PR; nella descrizione della PR va il comando usato e l'esito.

## 5. Security by design

- La sicurezza si decide prima di scrivere codice, non dopo: per ogni nuova funzionalità chiediti quali dati tocca, chi può accedervi e cosa succede se l'input è malevolo.
- Validazione di ogni input ai confini di fiducia (form, API, file, variabili d'ambiente).
- Minimo privilegio, default sicuri (deny by default), nessun dato personale nei log.
- Dati personali trattati secondo GDPR: raccogliere solo ciò che serve.
- Riferimento: [OWASP Top 10](https://owasp.org/www-project-top-ten/) e [OWASP ASVS](https://owasp.org/www-project-application-security-verification-standard/).
- Niente segreti nel repo: chiavi e token in `.env` (escluso da git).

## 6. Documentazione sempre aggiornata (OBBLIGATORIO)

Ogni PR che cambia il comportamento del progetto **deve** aggiornare, nella stessa PR, i documenti in `docs/`. Nessuna eccezione: se un documento non va toccato, la PR lo dichiara esplicitamente nella checklist.

| File | Cosa contiene | Quando si aggiorna |
|------|---------------|--------------------|
| `docs/evoluzione.md` | Diario del progetto: cosa è stato aggiunto, decisioni prese e perché | Ogni PR, una voce in cima |
| `docs/flussi.md` | Diagrammi di flusso in Mermaid (utente, dati, componenti) | Ogni PR che aggiunge o cambia un flusso, una pagina, un'API o un componente |
| `docs/threat-model.md` | Threat model STRIDE: asset, confini di fiducia, minacce, mitigazioni | Ogni PR che aggiunge dati, input, endpoint, integrazioni, dipendenze o permessi |

- I diagrammi si scrivono in Mermaid dentro il markdown (GitHub li visualizza da solo): niente immagini esportate, che invecchiano.
- Il threat model segue i diagrammi: ogni confine di fiducia in `flussi.md` ha le sue minacce in `threat-model.md`.
- Una minaccia senza mitigazione resta nel threat model con stato `aperta`: non si cancella.

## 7. UI: standard della Pubblica Amministrazione italiana

Il prodotto è rivolto alla PA: si usa **Bootstrap Italia** (Designers Italia / AgID), non Bootstrap "liscio" né altri framework UI.

- Libreria: [Bootstrap Italia](https://italia.github.io/bootstrap-italia/) — npm `bootstrap-italia`, versione 2.x fissata a una release precisa (niente `@latest`).
- Componenti, griglia, colori, icone (`sprites.svg`) e font (Titillium Web, Roboto Mono) arrivano già dalla libreria: usarli, non ricrearli.
- Struttura pagina come i modelli Designers Italia: header istituzionale (slim header + header centrale con nome ente), breadcrumb, footer istituzionale.
- Riferimenti: [Designers Italia](https://designers.italia.it/), [UI Kit Italia](https://designers.italia.it/design-system/), [Linee guida di design per i siti e i servizi digitali della PA (AgID)](https://docs.italia.it/italia/designers-italia/design-linee-guida-docs/).
- **Accessibilità non negoziabile** (Legge Stanca, WCAG 2.1 AA): label su ogni campo, contrasto colori, navigazione da tastiera, `alt` sulle immagini, lingua `lang="it"`.
- Testi dell'interfaccia in italiano, linguaggio semplice e chiaro.

## 8. Varie

- Lingua di lavoro (PR, commit body, commenti di discussione, docs): italiano. Codice e nomi identificatori: inglese.
