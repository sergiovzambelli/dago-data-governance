"""Abbina un documento alle schede del registro dei trattamenti: le tre più probabili, con punteggio e motivazione.

Punteggio = somma dei pesi delle parole chiave e tipologie documentali della scheda trovate nel testo
(più una parola è rara tra le schede, più pesa) + un bonus se il file sta in una cartella dichiarata.
"""
import csv
import math
import re

REQUIRED = ("Codice", "Percorsi dichiarati", "Parole chiave", "Tipologie documentali tipiche")
TERM_FIELDS = ("Parole chiave", "Tipologie documentali tipiche")
# tarato su sviluppo: con pesi da 0,5 a 8 la top-3 non cambia; 2 lascia al testo la possibilità di vincere
PATH_BONUS = 2.0
# nomi del registro → nomi usati dal classificatore (categories.py)
CATEGORY_ALIASES = {"ETNICA": "ORIGINE_ETNICA", "SESSUALE": "ORIENTAMENTO_SESSUALE"}


def _split(value):
    return {t.strip().lower() for t in re.split(r"[,;]", value) if len(t.strip()) > 2}


def load_register(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"colonne mancanti nel registro: {', '.join(missing)}")
        rows = list(reader)
    terms = {r["Codice"]: set().union(*(_split(r[f]) for f in TERM_FIELDS)) for r in rows}
    df = {}
    for ts in terms.values():
        for t in ts:
            df[t] = df.get(t, 0) + 1
    return [{
        "codice": r["Codice"],
        "percorsi": [p.strip().rstrip("/") for p in r["Percorsi dichiarati"].split(";") if p.strip()],
        # colonne facoltative: se mancano nulla è dichiarato, quindi i controlli segnalano di più (default sicuro)
        "categorie_dichiarate": {CATEGORY_ALIASES.get(c, c) for c in (
            x.strip().upper() for x in (r.get("Categorie particolari dichiarate") or "").split(","))
            if c and c != "NESSUNA"},
        "diffusione": (r.get("Diffusione") or "").strip().upper() == "SI",
        # parole intere; lo spazio vale anche come a capo (PDF)
        "termini": [(t, re.compile(r"\b" + r"\s+".join(map(re.escape, t.split())) + r"\b", re.I),
                     math.log(1 + len(rows) / df[t])) for t in sorted(terms[r["Codice"]])],
    } for r in rows]


def _evidence(register, file_path, text):
    """Per ogni scheda con qualche indizio: (punteggio, codice, termini trovati, sta in una cartella dichiarata)."""
    out = []
    for rec in register:
        found = [(t, w) for t, regex, w in rec["termini"] if regex.search(text)]
        in_folder = any(file_path.startswith(p + "/") for p in rec["percorsi"])
        score = sum(w for _, w in found) + (PATH_BONUS if in_folder else 0)
        if score > 0:
            out.append((score, rec["codice"], found, in_folder))
    return sorted(out, key=lambda e: -e[0])


def match(register, file_path, text, k=3):
    proposals = []
    for score, code, found, in_folder in _evidence(register, file_path, text)[:k]:
        reasons = (["cartella dichiarata"] if in_folder else []) + \
                  ([f"parole chiave: {', '.join(t for t, _ in found)}"] if found else [])
        proposals.append({"scheda": code, "punteggio": round(score, 2), "motivazione": "; ".join(reasons)})
    return proposals


def is_missing_record(register, file_path, text):
    """Nessuna scheda copre il documento: la migliore ha al massimo una parola chiave e il file non è nella sua cartella.

    Si contano le parole e non il punteggio, che non è normalizzato e cambia con il registro.
    """
    # tarato su sviluppo: soglia 1 → F1 SCHEDA_MANCANTE 0,755; con 2 sale a 0,806 ma i falsi positivi in più sono
    # documenti fuori posto (LUOGO_NON_DICHIARATO) con testo chiaro, che perderebbero la scheda per i controlli
    # shortcut: una sola parola chiave non distingue un servizio non censito da un documento povero di testo;
    # da rivedere con l'LLM locale o con parole chiave più ricche nel registro
    ev = _evidence(register, file_path, text)
    return not ev or (len(ev[0][2]) <= 1 and not ev[0][3])
