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
| T-004 | Scorer | T | File di predizioni malformato o con percorsi inventati che falsa il punteggio | i file non etichettati vengono ignorati (non entrano nelle metriche, avviso su stderr); i campi mancanti contano come errore | chiusa | feat/scorer, feat/baseline |
| T-005 | Scansione | I | Link simbolico nella cartella che porta a file fuori dal perimetro | link simbolici saltati; file aperti in sola lettura | chiusa | feat/baseline |
| T-006 | Scansione | D | File enorme che esaurisce la memoria durante l'hash | SHA-256 calcolato a blocchi da 1 MB | chiusa | feat/baseline |
| T-007 | Estrazione | D | ODT costruito come zip bomb o XML "billion laughs" | `content.xml` oltre 50 MB scartato; XML letto con `defusedxml` | chiusa | feat/extract |
| T-008 | Estrazione | T | File malevolo che sfrutta un difetto dei parser (pdfminer, mammoth, openpyxl) | versioni fissate in `requirements.txt`; errori trasformati in testo vuoto; da isolare in container senza rete (deploy) | aperta | feat/extract |
| T-009 | Dipendenze | T | Pacchetto PyPI compromesso o aggiornato di nascosto | versioni fissate; hash (`--require-hashes`) da aggiungere | aperta | feat/extract |
