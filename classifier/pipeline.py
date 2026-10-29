"""Analizza una cartella (in sola lettura) e produce una predizione per file nel formato della specifica.

Uso: python -m classifier.pipeline <cartella> [registro.csv] > predizioni.json
"""
import hashlib
import json
import sys
from pathlib import Path

from classifier.categories import find_categories
from classifier.entities import find_entities
from classifier.extract import extract_text
from classifier.matching import load_register, match


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(root, register=()):
    root = Path(root)
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
        # shortcut: con dati personali l'esito è sempre CONFORME; i passi successivi lo sostituiscono
        results.append({
            "file": rel,
            "sha256": _sha256(path),
            "dati_personali": personal,
            "entita": entities,
            "categorie_particolari": categories,
            "livello": None,
            "proposte": proposals,
            "scheda": proposals[0]["scheda"] if proposals and personal else None,
            "esito": "CONFORME" if personal else "NESSUN_DATO_PERSONALE",
            "scostamenti": [],
        })
    return results


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    register = load_register(sys.argv[2]) if len(sys.argv) == 3 else ()
    print(json.dumps(classify(sys.argv[1], register), ensure_ascii=False, indent=1))
