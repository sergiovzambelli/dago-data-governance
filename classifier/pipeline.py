"""Analizza una cartella (in sola lettura) e produce una predizione per file nel formato della specifica.

Uso: python -m classifier.pipeline <cartella> > predizioni.json
"""
import hashlib
import json
import sys
from pathlib import Path


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
        # shortcut: baseline costante (classe più frequente in sviluppo); i passi successivi la sostituiscono
        results.append({
            "file": path.relative_to(root).as_posix(),
            "sha256": _sha256(path),
            "dati_personali": True,
            "entita": [],
            "categorie_particolari": [],
            "livello": None,
            "proposte": [],
            "scheda": None,
            "esito": "CONFORME",
            "scostamenti": [],
        })
    return results


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(json.dumps(classify(sys.argv[1]), ensure_ascii=False, indent=1))
