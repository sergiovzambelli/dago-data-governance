# Threat model

Metodo: STRIDE (Spoofing, Tampering, Repudiation, Information disclosure, Denial of service, Elevation of privilege).
Aggiornato a ogni PR che aggiunge dati, input, endpoint, integrazioni, dipendenze o permessi. Le minacce non si cancellano: si chiudono.

## Asset
_Nessuno ancora._

## Confini di fiducia
_Nessuno ancora (vedi `flussi.md`)._

## Minacce

| ID | Componente | STRIDE | Minaccia | Mitigazione | Stato | PR |
|----|------------|--------|----------|-------------|-------|----|
| T-001 | Repository | I | Segreti committati per errore | `.env` escluso da git | aperta finché non esiste `.gitignore` | — |
