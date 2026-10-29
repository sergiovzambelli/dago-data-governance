# Diagrammi di flusso

Diagrammi Mermaid, aggiornati a ogni PR che cambia un flusso. Segnare i confini di fiducia (es. browser → server).

## Flusso di sviluppo

```mermaid
flowchart LR
    A[Branch feat/...] --> B[Test che fallisce]
    B --> C[Codice minimo, test passa]
    C --> D[Aggiorna docs: evoluzione, flussi, threat model]
    D --> E[PR su GitHub]
    E --> F{Verifica utente}
    F -- ok --> G[Merge su main]
    F -- da rivedere --> B
```

## Flussi dell'applicazione

### Architettura e tool (proposta; implementati: Scansione senza incrementale, Estrazione testo con OCR (EML con allegati), Entità con regex, Categorie particolari con dizionari, Abbinamento scheda top-3 senza soglia, Export JSON, Scorer)

Tutto gratuito, open source, eseguito in locale senza Internet. Il LLM è opzionale: la catena funziona anche solo con le regole.

```mermaid
flowchart TB
    subgraph SRC["Cartelle di rete (sola lettura) — confine di fiducia 1"]
        FS[(fileserver / srv-archivi)]
    end

    subgraph IN["Ingresso"]
        REG[Registro_trattamenti.xlsx/csv<br/>openpyxl · csv]
        PERM[permessi_cartelle.csv<br/>csv]
    end

    subgraph PIPE["Pipeline per file — Python 3.11"]
        SCAN[1 · Scansione<br/>pathlib · hashlib SHA-256<br/>incrementale su SQLite]
        EXT{2 · Estrazione testo}
        MD[markitdown<br/>PDF nativo · DOCX · XLSX · CSV · TXT]
        ODT[odfpy<br/>ODT]
        EML[email stdlib<br/>EML + allegati → ricorsione]
        OCR[ocrmypdf + Tesseract ita<br/>PDF scansionati · JPG]
        ENT[3 · Entità<br/>regex + python-stdnum CF/IBAN<br/>spaCy it_core_news_lg nomi/luoghi]
        CAT[4 · Categorie particolari<br/>dizionari parole chiave]
        LVL[5 · Livello 0–3<br/>regole esplicite]
        MATCH[6 · Abbinamento scheda<br/>percorso + parole chiave BM25<br/>top-3 con soglia]
        RULES[7 · 5 regole di conformità<br/>Python puro · data del documento da testo o nome file]
        ESITO{Esito}
    end

    subgraph LLM["LLM locale opzionale — Ollama, CPU o GPU, solo host locali"]
        GEN[qwen3:8b<br/>verifica la scheda nei casi dubbi · categorie implicite da fare]
    end

    subgraph STORE["Archivio"]
        DB[(SQLite + FTS5<br/>metadati · entità mascherate · estratti brevi)]
        LOG[(registro decisioni RPD)]
    end

    subgraph OUT["Uscite"]
        JSON[Export JSON / CSV<br/>formato di riferimento]
        SCORE[Scorer<br/>vs Etichette_sviluppo + validation_set]
    end

    subgraph WEB["Web — confine di fiducia 2: browser → server"]
        API[FastAPI + Jinja2]
        UI[Bootstrap Italia 2.x<br/>inventario · coda validazione · cruscotto · ricerca]
        RPD((RPD / operatore))
    end

    FS --> SCAN --> EXT
    EXT -->|testo nativo| MD
    EXT -->|ODT| ODT
    EXT -->|EML| EML
    EXT -->|testo assente| OCR
    MD & ODT & EML & OCR --> ENT --> CAT --> LVL --> MATCH --> RULES --> ESITO
    CAT -. dubbio .-> GEN
    MATCH -. "≤ 2 parole chiave e fuori cartella: verifica SI/NO, poi scelta" .-> GEN
    GEN -. scheda verificata o nessuna .-> RULES
    REG --> MATCH
    REG --> RULES
    PERM --> RULES
    ESITO -->|nessuna entità| E0[NESSUN_DATO_PERSONALE]
    ESITO -->|scheda migliore: ≤ 1 parola chiave e fuori cartella| E1[SCHEDA_MANCANTE]
    ESITO -->|0 scostamenti| E2[CONFORME]
    ESITO -->|≥1 scostamento| E3[NON_CONFORME]
    E0 & E1 & E2 & E3 --> DB
    DB --> JSON --> SCORE
    DB <--> API <--> UI <--> RPD
    API --> LOG

    subgraph DEP["Deploy: docker compose up — server senza GPU"]
        C1[container app<br/>Python + Tesseract + spaCy]
        C2[container ollama<br/>opzionale]
    end
```

## Interfaccia web (ui/)

Dettagli in [ui.md](ui.md). La UI legge i file prodotti dal classificatore; solo la pagina "Prova un file" lo chiama direttamente (`classifier.pipeline.analyze`).

```mermaid
flowchart LR
    PIPE[classifier.pipeline] -->|data/pred_*.json| UI
    REG[(Registro_trattamenti.csv)] --> UI
    subgraph UI["ui/ — FastAPI + Jinja2 + Bootstrap Italia 2.18.3 (file locali)"]
        AUTH{utente?<br/>Basic + PBKDF2<br/>oppure solo 127.0.0.1}
        PAG[cruscotto · coda · inventario<br/>documento · ricerca · registro]
        DEC[decisione RPD<br/>ruolo rpd + token CSRF + Origin]
        SCH[schede: crea · modifica · archivia<br/>ruolo rpd + token CSRF + Origin]
        EXP[esporta JSON / CSV]
    end
    U((RPD / operatore)) -->|confine di fiducia: browser → server| AUTH --> PAG
    PAG --> DEC -->|solo aggiunte| DB[(ui/var/decisioni.sqlite3)]
    DB --> PAG
    DB --> EXP
    PAG --> SCH -->|versioni, solo aggiunte| DB
    REG -.->|mai scritto| SCH
    DB -->|CSV + versioni| REGOUT["/schede/registro.csv"] -.->|a mano| PIPE
```

### Prova un file (feat/try-file)

```mermaid
flowchart LR
    U((RPD)) -->|confine di fiducia: file caricato<br/>ruolo rpd + CSRF + Origin, max 20 MB| P["POST /prova"]
    P -->|nome fisso + estensione| TMP[(cartella temporanea)]
    REG[registro in uso<br/>CSV + versioni] --> TMP
    TMP --> EX[extract_text<br/>OCR se serve] --> AN[analyze: entità · categorie<br/>schede · controlli]
    PERM[(permessi_cartelle.csv)] --> AN
    AN -->|pagina no-store, nulla salvato| U
    TMP -.->|cancellata a fine richiesta| X[ ]
```

## Bozze di nuove schede (feat/draft-records)

```mermaid
flowchart LR
    PRED[data/pred_sviluppo.json] -->|esito SCHEDA_MANCANTE| GRP[raggruppa per tipo di documento<br/>nome file senza date, numeri, cognomi]
    FS[(cartella analizzata<br/>sola lettura)] -->|testo, solo file dentro la cartella| GRP
    PERM[permessi_cartelle.csv] --> SYS
    GRP --> SYS[campi noti: cartella prevalente,<br/>gruppo di accesso, categorie, diffusione NO]
    GRP -. "fino a 3 estratti — solo host locali" .-> LLM[Ollama<br/>campi descrittivi in JSON]
    LLM -. risposta non fidata .-> VAL{validazione<br/>una riga · 500 car. · niente entità né nomi<br/>parole chiave presenti nei documenti<br/>base giuridica da elenco chiuso}
    SYS & VAL --> BOZ[data/bozze_sviluppo.json]
    BOZ --> UIB
    subgraph UIB["ui/ — pagina Nuove schede"]
        FORM[RPD corregge i campi<br/>approva o scarta<br/>ruolo rpd + CSRF + Origin]
        CSV["/bozze/approvate.csv<br/>colonne del registro"]
    end
    FORM -->|solo aggiunte| DB[(tabella bozze<br/>ui/var/decisioni.sqlite3)]
    DB --> CSV -->|copia a mano dell'RPD| REG[(Registro_trattamenti.csv)]
```
