"""Analizza una cartella (in sola lettura) e produce una predizione per file nel formato della specifica.

Uso: python -m classifier.pipeline <cartella> [registro.csv [permessi_cartelle.csv]] > predizioni.json
Modello locale facoltativo: CLASSIFIER_LLM_MODEL=qwen3:8b [CLASSIFIER_LLM_URL=http://localhost:11434]
"""
import hashlib
import json
import os
import sys
from pathlib import Path

from classifier.categories import find_categories
from classifier.compliance import check, load_permissions
from classifier.dates import document_date
from classifier.entities import find_entities
from classifier.extract import extract_text
from classifier.llm import OllamaClient, decide
from classifier.matching import is_doubtful, is_missing_record, load_register, match


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _ask_model(llm, records, proposals, text):
    """Il modello decide il caso dubbio: (proposte aggiornate, scheda mancante) oppure None se non risponde."""
    decision = decide(llm, records, proposals, text)
    if decision is None:
        return None
    code, reason = decision
    if code is None:
        return proposals, True
    rest = [p for p in proposals if p["scheda"] != code]
    first = next((p for p in proposals if p["scheda"] == code), {"scheda": code, "punteggio": 0.0, "motivazione": ""})
    note = f"modello locale: {reason}"
    first = {**first, "motivazione": f"{first['motivazione']}; {note}" if first["motivazione"] else note}
    return [first, *rest][:3], False


def classify(root, register=(), permissions=(), llm=None):
    root = Path(root)
    records = {r["codice"]: r for r in register}
    results = []
    for path in sorted(root.rglob("*")):
        # niente link simbolici: potrebbero portare fuori dalla cartella analizzata
        if path.is_symlink() or not path.is_file():
            continue
        text = extract_text(path)
        entities = find_entities(text)
        categories = sorted(c["categoria"] for c in find_categories(text))
        # senza testo (scansione, file illeggibile) non si può escludere la presenza di dati personali;
        # una categoria particolare descritta riguarda una persona anche senza identificativi
        # shortcut: un modulo in bianco che nomina una categoria risulta "con dati personali"
        personal = bool(entities or categories) or not text.strip()
        rel = path.relative_to(root).as_posix()
        # proposte anche senza dati personali: se quel giudizio è sbagliato (es. soli nomi) restano utili
        proposals = match(register, rel, text)
        # senza registro non si può dire che manca la scheda
        missing = personal and bool(register) and is_missing_record(register, rel, text)
        # caso dubbio: decide il modello locale, se c'è e risponde; altrimenti restano le regole
        if llm and personal and register and text.strip() and is_doubtful(register, rel, text):
            answer = _ask_model(llm, records, proposals, text)
            if answer:
                proposals, missing = answer
        # con SCHEDA_MANCANTE la più vicina resta tra le proposte, per il controllo dell'RPD
        record = records[proposals[0]["scheda"]] if proposals and personal and not missing else None
        # i controlli confrontano il documento con la sua scheda: senza scheda non ci sono scostamenti
        deviations = check(record, rel, categories, permissions, document_date(rel, text)) if record else []
        if missing:
            esito = "SCHEDA_MANCANTE"
        elif personal:
            esito = "NON_CONFORME" if deviations else "CONFORME"
        else:
            esito = "NESSUN_DATO_PERSONALE"
        results.append({
            "file": rel,
            "sha256": _sha256(path),
            "dati_personali": personal,
            "entita": entities,
            "categorie_particolari": categories,
            "livello": None,
            "proposte": proposals,
            "scheda": record["codice"] if record else None,
            "esito": esito,
            "scostamenti": deviations,
        })
    return results


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3, 4):
        sys.exit(__doc__)
    register = load_register(sys.argv[2]) if len(sys.argv) >= 3 else ()
    permissions = load_permissions(sys.argv[3]) if len(sys.argv) == 4 else ()
    model = os.environ.get("CLASSIFIER_LLM_MODEL")
    llm = OllamaClient(os.environ.get("CLASSIFIER_LLM_URL", "http://localhost:11434"), model) if model else None
    print(json.dumps(classify(sys.argv[1], register, permissions, llm), ensure_ascii=False, indent=1))
