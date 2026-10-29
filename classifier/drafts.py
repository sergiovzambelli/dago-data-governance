"""Bozze di nuove schede del registro per i documenti SCHEDA_MANCANTE, da approvare dall'RPD.

Una bozza per tipo di documento (nome del file senza date, numeri e cognomi), anche se sparso in più cartelle.
Il sistema compila ciò che sa (cartella, gruppo di accesso, categorie rilevate); il modello locale, se c'è,
propone i campi descrittivi. Riferimenti normativi e conservazione restano sempre all'RPD.

Uso: python -m classifier.drafts <predizioni.json> <cartella> [permessi_cartelle.csv] > bozze.json
Modello locale facoltativo: CLASSIFIER_LLM_MODEL=qwen3:8b [CLASSIFIER_LLM_URL=http://localhost:11434]
"""
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

from classifier.compliance import _groups, load_permissions
from classifier.entities import find_entities
from classifier.extract import extract_text
from classifier.llm import OllamaClient

REGISTER_COLUMNS = (
    "Codice", "Origine", "Denominazione", "Struttura responsabile", "Ufficio", "Finalità", "Base giuridica",
    "Fonti normative", "Categorie di dati", "Categorie particolari dichiarate", "Interessati", "Comunicazione",
    "Diffusione", "Responsabili esterni", "Archivi", "Percorsi dichiarati", "Gruppo di accesso", "Conservazione",
    "Conservazione in anni", "Software", "Consenso", "Tipologie documentali tipiche", "Parole chiave")
# campi che il modello propone: chiave della risposta JSON → colonna del registro
MODEL_FIELDS = {"denominazione": "Denominazione", "finalita": "Finalità", "interessati": "Interessati",
                "categorie_dati": "Categorie di dati", "tipologie": "Tipologie documentali tipiche"}
# elenco chiuso: un modello piccolo inventa articoli di legge, qui può solo scegliere
LEGAL_BASES = {"a": "Art. 6, par. 1, lett. a) GDPR (consenso)", "b": "Art. 6, par. 1, lett. b) GDPR (contratto)",
               "c": "Art. 6, par. 1, lett. c) GDPR (obbligo di legge)",
               "e": "Art. 6, par. 1, lett. e) GDPR (compito di interesse pubblico)"}
# mai compilati dal sistema; la base giuridica va sempre rivista (art. 9 e 10 GDPR non sono nell'elenco)
ALWAYS_CHECK = ["Base giuridica", "Fonti normative", "Struttura responsabile", "Ufficio", "Comunicazione",
                "Responsabili esterni", "Archivi", "Conservazione", "Conservazione in anni", "Software", "Consenso"]
MAX_FIELD = 500
MAX_KEYWORDS = 10


def group_key(path):
    """Tipo di documento dal nome del file: SCIA_vicinato_20260124_202.pdf → scia_vicinato."""
    stem = Path(path).stem
    # shortcut: un cognome si riconosce solo dalla maiuscola iniziale; con nomi file tutti minuscoli resta nella
    # chiave (e nella tipologia proposta), da rivedere quando ci sarà il riconoscimento dei nomi (feat/names)
    parts = [p for p in re.split(r"[_\-\s]+", stem) if p and not re.search(r"\d", p) and not re.fullmatch(r"[A-Z][a-z]+", p)]
    return "_".join(parts).lower() or "documento"


def _clean(value, corpus):
    """Testo del modello: una riga, lunghezza massima, scartato se contiene dati personali riconoscibili."""
    if not isinstance(value, str):
        return ""
    value = " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", value).split())[:MAX_FIELD]
    # shortcut: un nome è "Nome Cognome" copiato dai documenti; nomi in maiuscolo o da soli passano,
    # da sostituire con il riconoscimento dei nomi (feat/names)
    names = re.findall(r"\b[A-ZÀ-Ý][a-zà-ÿ']+\s+[A-ZÀ-Ý][a-zà-ÿ']+", value)
    return "" if find_entities(value) or any(n in corpus for n in names) else value


def _keywords(answer, corpus):
    words = answer if isinstance(answer, list) else []
    lower = corpus.lower()
    out = []
    for w in (_clean(w, corpus).lower() for w in words):
        # solo parole presenti nei documenti: servono all'abbinamento delle analisi successive
        if len(w) > 2 and w in lower and w not in out:
            out.append(w)
    return out[:MAX_KEYWORDS]


def _draft(key, preds, texts, permissions, llm):
    folders = Counter(p["file"].rpartition("/")[0] for p in preds)
    top = max(folders.values())
    # la cartella prevalente: un documento finito in una cartella condivisa non diventa un percorso dichiarato
    paths = sorted(f for f, n in folders.items() if n == top)
    # _groups vuole un file: un nome fittizio dentro la cartella
    groups = sorted(set().union(*(_groups(permissions, p + "/x") for p in paths)))
    categories = sorted({c for p in preds for c in p["categorie_particolari"]})
    fallback = key.replace("_", " ")
    fields = dict.fromkeys(REGISTER_COLUMNS, "")
    code = "NUOVA-" + key.upper().replace("_", "-")[:40]
    fields.update({"Codice": code, "Origine": "Bozza del classificatore", "Diffusione": "NO",
                   "Percorsi dichiarati": "; ".join(paths), "Gruppo di accesso": ", ".join(groups),
                   "Categorie particolari dichiarate": ", ".join(categories) or "Nessuna",
                   "Tipologie documentali tipiche": fallback, "Parole chiave": fallback})
    doc_texts = [t for t in (texts.get(p["file"]) or "" for p in preds) if t.strip()]
    corpus = "\n".join(doc_texts)
    # scansioni senza OCR: nulla da far leggere al modello
    answer = llm.draft(doc_texts) if llm and doc_texts else None
    check = list(ALWAYS_CHECK)
    if isinstance(answer, dict):
        for k, col in MODEL_FIELDS.items():
            fields[col] = _clean(answer.get(k), corpus) or (fallback if col == "Tipologie documentali tipiche" else "")
        fields["Parole chiave"] = ", ".join(_keywords(answer.get("parole_chiave"), corpus)) or fallback
        fields["Base giuridica"] = LEGAL_BASES.get(str(answer.get("base_giuridica", "")).strip().lower()[:1], "")
    check += [col for col in MODEL_FIELDS.values() if not fields[col]]
    return {"id": hashlib.sha256(key.encode()).hexdigest()[:16], "codice": code,
            "documenti": sorted(p["file"] for p in preds), "campi": fields,
            "da_verificare": [c for c in REGISTER_COLUMNS if c in check], "modello": isinstance(answer, dict)}


def build_drafts(predictions, texts, permissions=(), llm=None):
    """Bozze per i documenti SCHEDA_MANCANTE. texts: testo per file."""
    groups = {}
    for p in predictions:
        if p["esito"] == "SCHEDA_MANCANTE":
            groups.setdefault(group_key(p["file"]), []).append(p)
    drafts = [_draft(k, ps, texts, permissions, llm) for k, ps in groups.items()]
    return sorted(drafts, key=lambda d: d["codice"])


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    preds = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    root = Path(sys.argv[2]).resolve()
    texts = {}
    for p in preds:
        path = (root / p["file"]).resolve()
        # il file deve stare dentro la cartella analizzata: le predizioni sono un input da validare
        if p["esito"] == "SCHEDA_MANCANTE" and path.is_relative_to(root) and path.is_file() and not path.is_symlink():
            texts[p["file"]] = extract_text(path)
    permissions = load_permissions(sys.argv[3]) if len(sys.argv) == 4 else ()
    model = os.environ.get("CLASSIFIER_LLM_MODEL")
    llm = OllamaClient(os.environ.get("CLASSIFIER_LLM_URL", "http://localhost:11434"), model) if model else None
    print(json.dumps(build_drafts(preds, texts, permissions, llm), ensure_ascii=False, indent=1))
