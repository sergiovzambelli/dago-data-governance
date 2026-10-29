"""Analizza una cartella (in sola lettura) e produce una predizione per file nel formato della specifica.

Uso: python -m classifier.pipeline <cartella> > predizioni.json
"""
import hashlib
import json
import sys
from pathlib import Path

from classifier.entities import find_entities
from classifier.extract import extract_text


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def classify(root):
    root = Path(root)
    results = []
    for path in sorted(root.rglob("*")):
        # niente link simbolici: potrebbero portare fuori dalla cartella analizzata
        if path.is_symlink() or not path.is_file():
            continue
        text = extract_text(path)
        entities = find_entities(text)
        # senza testo (scansione, file illeggibile) non si può escludere la presenza di dati personali
        personal = bool(entities) or not text.strip()
        # shortcut: con dati personali l'esito è sempre CONFORME; i passi successivi lo sostituiscono
        results.append({
            "file": path.relative_to(root).as_posix(),
            "sha256": _sha256(path),
            "dati_personali": personal,
            "entita": entities,
            "categorie_particolari": [],
            "livello": None,
            "proposte": [],
            "scheda": None,
            "esito": "CONFORME" if personal else "NESSUN_DATO_PERSONALE",
            "scostamenti": [],
        })
    return results


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(json.dumps(classify(sys.argv[1]), ensure_ascii=False, indent=1))
