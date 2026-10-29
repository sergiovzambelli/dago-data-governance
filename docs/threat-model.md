# Threat model

Metodo: STRIDE (Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege).
Aggiornato a ogni PR che aggiunge dati, input, endpoint, integrazioni, dipendenze o permessi. Le minacce non si cancellano: si chiudono.

## Asset
- Dati del kit in `data/`: documenti con dati personali (sintetici), etichette di valutazione riservate.

## Confini di fiducia
_Nessuno ancora (vedi `flussi.md`)._

## Minacce

| ID | Componente | STRIDE | Minaccia | Mitigazione | Stato | PR |
|----|------------|--------|----------|-------------|-------|----|
| T-001 | Repository | I | Segreti committati per errore | `.env` escluso da git | chiusa | chore/kit-data |
| T-002 | `data/` | I | Dati personali o etichette riservate pubblicati su GitHub | rischio accettato dal team: dati sintetici (LEGGIMI del kit), zip già nel repo | accettata | chore/kit-data |
| T-003 | `make data` | T | Archivio zip con percorsi `..` o assoluti (zip-slip) | estrazione con `zipfile` di Python, che li scarta | chiusa | chore/kit-data |
