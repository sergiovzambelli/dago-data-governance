"""Bozze di nuove schede del registro per i documenti SCHEDA_MANCANTE, da approvare dall'RPD.

Una bozza per tipo di documento (nome del file senza date, numeri e cognomi), anche se sparso in più cartelle.
Con gli embedding locali due tipi diversi si uniscono se il contenuto è quasi uguale, o se è vicino e il modello
conferma che è lo stesso procedimento (es. concessione_loculo e domanda_loculo).
Il sistema compila ciò che sa (cartella, gruppo di accesso, categorie rilevate); il modello locale, se c'è,
propone i campi descrittivi e sceglie tra le schede esistenti più simili (recuperate per contenuto) quella da cui
copiare struttura, ufficio e software. Riferimenti normativi e conservazione restano sempre all'RPD.

Uso: python -m classifier.drafts <predizioni.json> <cartella> [permessi_cartelle.csv] [registro.csv] > bozze.json
Modelli locali facoltativi: CLASSIFIER_LLM_MODEL=qwen3:8b CLASSIFIER_EMBED_MODEL=bge-m3
[CLASSIFIER_LLM_URL=http://localhost:11434]
"""
import csv
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
from classifier.llm import MAX_CHARS, OllamaClient

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
# coseno tra i centri di due gruppi (bge-m3, sviluppo): stesso tipo ≥ 0,78, ma "loculo" vs "loculo" 0,76 e
# ERP vs fondo affitti 0,75. Nessuna soglia li separa: tra CANDIDATE e SIMILARITY decide il modello
CANDIDATE = 0.70
SIMILARITY = 0.85
SIMILAR_RECORDS = 3
# copiati dalla scheda simile scelta dal modello: stesso ufficio, stessi strumenti (restano da verificare)
COPIED_FIELDS = ("Struttura responsabile", "Ufficio", "Software")


def group_key(path):
    """Tipo di documento dal nome del file: SCIA_vicinato_20260124_202.pdf → scia_vicinato."""
    stem = Path(path).stem
    # shortcut: un cognome si riconosce solo dalla maiuscola iniziale; con nomi file tutti minuscoli resta nella
    # chiave (e nella tipologia proposta), da rivedere quando ci sarà il riconoscimento dei nomi (feat/names)
    parts = [p for p in re.split(r"[_\-\s]+", stem) if p and not re.search(r"\d", p) and not re.fullmatch(r"[A-Z][a-z]+", p)]
    return "_".join(parts).lower() or "documento"


def _cosine(a, b):
    na, nb = sum(x * x for x in a) ** 0.5, sum(x * x for x in b) ** 0.5
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


def _centroid(vectors):
    return [sum(xs) / len(vectors) for xs in zip(*vectors)]


def _cluster(preds, vectors, texts, llm):
    """Gruppi {chiave: predizioni}: per nome del file, poi uniti se il contenuto dice che è lo stesso procedimento."""
    groups = {}
    for p in sorted(preds, key=lambda p: p["file"]):
        groups.setdefault(group_key(p["file"]), []).append(p)

    def center(ps):
        vs = [vectors[p["file"]] for p in ps if p["file"] in vectors]
        return _centroid(vs) if vs else None

    rejected = set()
    while True:
        centers = {k: c for k, ps in groups.items() if (c := center(ps))}
        pairs = sorted(((_cosine(centers[a], centers[b]), a, b) for a in centers for b in centers
                        if a < b and (a, b) not in rejected), reverse=True)
        sim, a, b = pairs[0] if pairs else (0, None, None)
        if sim < CANDIDATE:
            return groups
        # sotto la soglia automatica decide il modello: stesso ufficio non vuol dire stesso trattamento
        if sim < SIMILARITY:
            sample_a, sample_b = ([texts[p["file"]] for p in groups[k] if p["file"] in vectors][:2] for k in (a, b))
            if not (llm and llm.same_procedure(sample_a, sample_b)):
                rejected.add((a, b))
                continue
        # il gruppo più numeroso dà il nome alla bozza
        keep, drop = sorted((a, b), key=lambda k: (-len(groups[k]), k))
        groups[keep] += groups.pop(drop)
        groups[keep].sort(key=lambda p: p["file"])
        rejected = {r for r in rejected if drop not in r}


def _describe(row):
    return f"{row['Denominazione']}. {row['Finalità']} Documenti tipici: {row['Tipologie documentali tipiche']}."


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


def _draft(key, preds, texts, permissions, llm, similar):
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
    answer = llm.draft(doc_texts, similar) if llm and doc_texts else None
    check = list(ALWAYS_CHECK)
    if isinstance(answer, dict):
        for k, col in MODEL_FIELDS.items():
            fields[col] = _clean(answer.get(k), corpus) or (fallback if col == "Tipologie documentali tipiche" else "")
        fields["Parole chiave"] = ", ".join(_keywords(answer.get("parole_chiave"), corpus)) or fallback
        fields["Base giuridica"] = LEGAL_BASES.get(str(answer.get("base_giuridica", "")).strip().lower()[:1], "")
        # elenco chiuso anche qui: solo una delle schede recuperate, mai un codice inventato
        ref = next((r for r in similar if r["Codice"] == str(answer.get("scheda_simile", "")).strip().upper()), None)
        if ref:
            fields.update({c: ref[c] for c in COPIED_FIELDS})
            fields["Origine"] += f" (struttura e ufficio da {ref['Codice']})"
    check += [col for col in MODEL_FIELDS.values() if not fields[col]]
    return {"id": hashlib.sha256(key.encode()).hexdigest()[:16], "codice": code,
            "documenti": sorted(p["file"] for p in preds), "campi": fields,
            "da_verificare": [c for c in REGISTER_COLUMNS if c in check], "modello": isinstance(answer, dict)}


def _embed(embedder, texts):
    vectors = embedder.embed(texts) if embedder and texts else None
    if embedder and texts and not (vectors and len(vectors) == len(texts)):
        print("embedding non disponibili: gruppi per nome del file", file=sys.stderr)
        return None
    return vectors


def build_drafts(predictions, texts, permissions=(), llm=None, embedder=None, register=()):
    """Bozze per i documenti SCHEDA_MANCANTE. texts: testo per file; register: righe del registro CSV."""
    preds = [p for p in predictions if p["esito"] == "SCHEDA_MANCANTE"]
    with_text = [p["file"] for p in preds if (texts.get(p["file"]) or "").strip()]
    # embedder spento o senza risposta: si torna al nome del file
    doc_vectors = _embed(embedder, [texts[f][:MAX_CHARS] for f in with_text]) or []
    vectors = dict(zip(with_text, doc_vectors))
    record_vectors = _embed(embedder, [_describe(r) for r in register]) if vectors else None
    drafts = []
    for key, ps in _cluster(preds, vectors, texts, llm).items():
        similar = []
        group = [vectors[p["file"]] for p in ps if p["file"] in vectors]
        if record_vectors and group:
            c = _centroid(group)
            ranked = sorted(zip(register, record_vectors), key=lambda rv: -_cosine(c, rv[1]))
            similar = [r for r, _ in ranked[:SIMILAR_RECORDS]]
        drafts.append(_draft(key, ps, texts, permissions, llm, similar))
    return sorted(drafts, key=lambda d: d["codice"])


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4, 5):
        sys.exit(__doc__)
    preds = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    root = Path(sys.argv[2]).resolve()
    texts = {}
    for p in preds:
        path = (root / p["file"]).resolve()
        # il file deve stare dentro la cartella analizzata: le predizioni sono un input da validare
        if p["esito"] == "SCHEDA_MANCANTE" and path.is_relative_to(root) and path.is_file() and not path.is_symlink():
            texts[p["file"]] = extract_text(path)
    permissions = load_permissions(sys.argv[3]) if len(sys.argv) >= 4 else ()
    register = ()
    if len(sys.argv) == 5:
        with open(sys.argv[4], encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            if tuple(reader.fieldnames or ()) != REGISTER_COLUMNS:
                sys.exit("registro: colonne diverse da quelle attese")
            register = list(reader)
    url = os.environ.get("CLASSIFIER_LLM_URL", "http://localhost:11434")
    model, embed_model = os.environ.get("CLASSIFIER_LLM_MODEL"), os.environ.get("CLASSIFIER_EMBED_MODEL")
    llm = OllamaClient(url, model) if model else None
    embedder = OllamaClient(url, embed_model) if embed_model else None
    print(json.dumps(build_drafts(preds, texts, permissions, llm, embedder, register), ensure_ascii=False, indent=1))
