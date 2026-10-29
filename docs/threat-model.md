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
| T-010 | Entità | I | Valori in chiaro (CF, IBAN) esposti nell'export o nei log | l'export contiene solo il valore mascherato e la posizione; nessun log dei valori | chiusa | feat/entities |
| T-011 | Entità | D | Testo costruito per far esplodere le regex (ReDoS) | regex senza quantificatori annidati ambigui, finestre limitate (`{0,60}`) | chiusa | feat/entities |
| T-012 | Categorie | I | Evidenza della categoria (es. diagnosi) esposta a chi non deve vederla | l'evidenza è solo la parola chiave trovata, non il contesto; filtro per ruolo da fare in UI | aperta | feat/categories |
| T-013 | Estrazione EML | T/D | Allegato con nome malevolo (`../../x`) o email annidate all'infinito | dal nome dell'allegato si usa solo l'estensione, file scritto in una cartella temporanea; massimo 3 livelli di annidamento | chiusa | feat/categories-ext |
| T-014 | OCR | T | Nome di file che inietta opzioni o comandi in tesseract/ocrmypdf | comando come lista senza shell; percorso assoluto, quindi mai un argomento che inizia con `-` | chiusa | feat/ocr |
| T-015 | OCR | D | PDF con migliaia di pagine o immagine enorme che blocca l'analisi | timeout di 300 s per file, poi testo vuoto | chiusa | feat/ocr |
| T-016 | Registro trattamenti | T | Registro malformato o con parole chiave costruite per rallentare le regex | colonne obbligatorie verificate all'importazione; parole chiave trattate come testo letterale (`re.escape`) | chiusa | feat/matching |
| T-017 | Permessi cartelle | T | File dei permessi malformato o incompleto che nasconde un accesso eccessivo | colonne obbligatorie verificate; cartelle confrontate per segmenti interi (`Personale/PermessiVecchi` non eredita `Personale/Permessi`); vale la cartella più specifica | chiusa | feat/compliance |
| T-018 | Registro trattamenti | T | Scheda senza le colonne "Categorie particolari dichiarate" o "Diffusione" che fa sembrare conformi i documenti | default sicuro: colonna assente = niente dichiarato, quindi più scostamenti, non meno | chiusa | feat/compliance |
| T-020 | Data del documento | T | Nome del file o data nel testo alterati (es. file rinominato) per evitare o provocare CONSERVAZIONE_SCADUTA | la data scritta dopo il luogo nel testo vale più del nome del file; date future e impossibili scartate; la decisione resta all'RPD, che vede la data usata | aperta | feat/retention |
| T-021 | Data del documento | D | Testo costruito per rallentare la ricerca delle date | regex senza quantificatori annidati; contesto letto su una finestra fissa di 70 caratteri | chiusa | feat/retention |
| T-019 | Conformità | I | Cartella aperta a tutti non presente in `permessi_cartelle.csv`: ACCESSO_ECCESSIVO non segnalato | nessuna (una cartella non elencata non ha gruppi noti); da segnalare all'RPD come permesso sconosciuto | aperta | feat/compliance |
