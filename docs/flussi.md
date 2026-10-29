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

_Nessuno ancora._
