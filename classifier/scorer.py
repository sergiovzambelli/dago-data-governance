"""Calcola le 6 metriche della giuria confrontando le predizioni con un CSV di etichette.
LUOGO_NON_DICHIARATO non si misura (vedi IGNORED): su questo il punteggio differisce da quello delle etichette originali.

Uso: python -m classifier.scorer <etichette.csv> <predizioni.json>
"""
import csv
import json
import sys
from pathlib import Path

WEIGHTS = {
    "esito": 20,
    "richiamo_categorie": 20,
    "scheda_top3": 20,
    "f1_scheda_mancante": 15,
    "f1_scostamenti": 15,
    "precisione_entita": 10,
}
# scostamenti che non si misurano, né nelle etichette né nelle predizioni (decisione dell'utente: niente controllo del
# luogo). Un documento non conforme solo per questi è atteso conforme
IGNORED = {"LUOGO_NON_DICHIARATO"}


def _split(value):
    return {v.strip() for v in value.split(",") if v.strip()}


def load_labels(path):
    labels = {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            deviations = _split(r["Scostamenti attesi"])
            esito = r["Esito atteso"]
            if esito == "NON_CONFORME" and deviations and deviations <= IGNORED:
                esito = "CONFORME"
            labels[r["Percorso"]] = {
                "esito": esito,
                "schede_ok": _split(r["Scheda attesa"]) | _split(r["Alternative accettabili"]),
                "dati_personali": r["Dati personali"] == "SI",
                "categorie": _split(r["Categorie particolari"]),
                "scostamenti": deviations - IGNORED,
            }
    return labels


def _f1(tp, fp, fn):
    return 1.0 if tp + fp + fn == 0 else 2 * tp / (2 * tp + fp + fn)


def score(labels, predictions):
    # i file senza etichetta (es. LEGGIMI.txt) non entrano in nessuna metrica
    preds = {p.get("file"): p for p in predictions}
    unlabelled = preds.keys() - labels.keys()
    if unlabelled:
        print(f"attenzione: {len(unlabelled)} file senza etichetta ignorati", file=sys.stderr)

    esito_ok = cat_found = cat_total = top3_ok = top3_total = 0
    sm = [0, 0, 0]  # tp, fp, fn
    sc = [0, 0, 0]
    ent_pos = ent_true = 0
    for file, lab in labels.items():
        p = preds.get(file, {})  # file non predetto: tutto sbagliato
        esito = p.get("esito")
        esito_ok += esito == lab["esito"]

        cats = set(p.get("categorie_particolari") or [])
        cat_found += len(lab["categorie"] & cats)
        cat_total += len(lab["categorie"])

        if lab["schede_ok"]:
            top3 = {x.get("scheda") for x in (p.get("proposte") or [])[:3]}
            top3_ok += bool(lab["schede_ok"] & top3)
            top3_total += 1

        exp_sm, got_sm = lab["esito"] == "SCHEDA_MANCANTE", esito == "SCHEDA_MANCANTE"
        sm[0] += exp_sm and got_sm
        sm[1] += got_sm and not exp_sm
        sm[2] += exp_sm and not got_sm

        got_sc = set(p.get("scostamenti") or []) - IGNORED
        sc[0] += len(got_sc & lab["scostamenti"])
        sc[1] += len(got_sc - lab["scostamenti"])
        sc[2] += len(lab["scostamenti"] - got_sc)

        # shortcut: le etichette non hanno le posizioni delle entità, quindi la precisione è
        # per file (file con entità che hanno davvero dati personali); da rifare se arrivano posizioni
        if p.get("entita"):
            ent_pos += 1
            ent_true += lab["dati_personali"]

    metrics = {
        "esito": esito_ok / len(labels),
        "richiamo_categorie": cat_found / cat_total if cat_total else 1.0,
        "scheda_top3": top3_ok / top3_total if top3_total else 1.0,
        "f1_scheda_mancante": _f1(*sm),
        "f1_scostamenti": _f1(*sc),
        "precisione_entita": ent_true / ent_pos if ent_pos else 0.0,  # nessuna entità: nessun punto gratis
    }
    return {"totale": sum(WEIGHTS[k] * v for k, v in metrics.items()), "metriche": metrics}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    result = score(load_labels(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")))
    print(json.dumps(result, indent=2))
