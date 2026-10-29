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

### Architettura e tool (proposta, nulla ancora implementato)

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
        RULES[7 · 5 regole di conformità<br/>Python puro]
        ESITO{Esito}
    end

    subgraph LLM["LLM locale opzionale — Ollama, CPU"]
        GEN[modello istruito 7–8B<br/>categorie implicite · casi incerti]
        EMB[modello embedding<br/>similarità documento ↔ scheda]
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
    MATCH -. sotto soglia .-> EMB
    REG --> MATCH
    REG --> RULES
    PERM --> RULES
    ESITO -->|nessuna entità| E0[NESSUN_DATO_PERSONALE]
    ESITO -->|nessuna scheda sopra soglia| E1[SCHEDA_MANCANTE]
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
