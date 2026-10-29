"""Predizioni della pipeline, registro dei trattamenti e testi in italiano per la UI."""
import csv
import hashlib
import json

OUTCOMES = {
    "NON_CONFORME": ("Non conforme", "danger"),
    "SCHEDA_MANCANTE": ("Scheda mancante", "warning"),
    "CONFORME": ("Conforme", "success"),
    "NESSUN_DATO_PERSONALE": ("Nessun dato personale", "secondary"),
}
# titolo, cosa significa, cosa può fare l'RPD (specifica, "Controllo di conformità")
DEVIATIONS = {
    "CATEGORIA_NON_DICHIARATA": (
        "Categoria non dichiarata",
        "Il documento contiene una categoria particolare o giudiziaria che la scheda non dichiara.",
        "Aggiornare le categorie della scheda oppure spostare il documento nel trattamento corretto."),
    "LUOGO_NON_DICHIARATO": (
        "Luogo non dichiarato",
        "Il file non si trova in nessuna delle cartelle dichiarate nella scheda.",
        "Spostare il documento in una cartella dichiarata oppure aggiungere la cartella alla scheda."),
    "ACCESSO_ECCESSIVO": (
        "Accesso eccessivo",
        "Il documento contiene dati personali e la cartella è accessibile a tutti i dipendenti.",
        "Ridurre i permessi della cartella oppure spostare il documento."),
    "CONSERVAZIONE_SCADUTA": (
        "Conservazione scaduta",
        "La data del documento più gli anni di conservazione della scheda è anteriore alla data di riferimento.",
        "Avviare lo scarto oppure verificare il periodo di conservazione della scheda."),
    "DIFFUSIONE_NON_PREVISTA": (
        "Diffusione non prevista",
        "Il documento è destinato alla pubblicazione, ma la scheda non prevede diffusione oppure contiene "
        "categorie particolari.",
        "Ritirare o oscurare la pubblicazione oppure aggiornare la scheda."),
}
ENTITY_TYPES = {
    "CODICE_FISCALE": "Codice fiscale", "IBAN": "IBAN", "EMAIL": "Email", "TELEFONO": "Telefono",
    "DATA_NASCITA": "Data di nascita", "NOME": "Nome", "INDIRIZZO_IP": "Indirizzo IP", "MATRICOLA": "Matricola",
    "INDIRIZZO": "Indirizzo", "TARGA": "Targa",
}
CATEGORIES = {
    "SALUTE": "Salute", "GIUDIZIARI": "Giudiziari", "RELIGIOSE": "Convinzioni religiose", "SINDACALE": "Adesione sindacale",
    "ORIENTAMENTO_SESSUALE": "Orientamento sessuale", "ORIGINE_ETNICA": "Origine etnica", "POLITICHE": "Opinioni politiche",
    "BIOMETRICI": "Dati biometrici", "GENETICI": "Dati genetici", "FILOSOFICHE": "Convinzioni filosofiche",
}
MAX_TEXT = 500  # campi di testo dalla pipeline mostrati nella UI


def doc_id(path):
    # identificativo stabile e opaco: l'URL non contiene il percorso del file
    return hashlib.sha256(path.encode("utf-8")).hexdigest()[:16]


def _str(value, field, file):
    if not isinstance(value, str):
        raise ValueError(f"predizioni: campo {field!r} non valido per {file!r}")
    return value[:MAX_TEXT]


def _list(value, field, file):
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"predizioni: campo {field!r} non valido per {file!r}")
    return value


def load_predictions(path):
    """Legge e valida il JSON della pipeline: i campi inattesi vengono scartati, quelli sbagliati bloccano l'avvio."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("predizioni: atteso un elenco di documenti")
    docs, seen = [], set()
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("file"), str):
            raise ValueError("predizioni: ogni documento deve avere il campo 'file'")
        f = item["file"][:MAX_TEXT]
        if f in seen:
            raise ValueError(f"predizioni: documento ripetuto {f!r}")
        seen.add(f)
        esito = item.get("esito")
        if esito not in OUTCOMES:
            raise ValueError(f"predizioni: esito {esito!r} non valido per {f!r}")
        deviations = [d for d in _list(item.get("scostamenti"), "scostamenti", f) if d in DEVIATIONS]
        entities = [{"tipo": _str(e.get("tipo", ""), "entita.tipo", f),
                     "valore_mascherato": _str(e.get("valore_mascherato", ""), "entita.valore_mascherato", f),
                     "inizio": e.get("inizio") if isinstance(e.get("inizio"), int) else None,
                     "confidenza": e.get("confidenza") if isinstance(e.get("confidenza"), (int, float)) else None}
                    for e in _list(item.get("entita"), "entita", f) if isinstance(e, dict)]
        proposals = [{"scheda": _str(p.get("scheda", ""), "proposte.scheda", f),
                      "punteggio": p.get("punteggio") if isinstance(p.get("punteggio"), (int, float)) else None,
                      "motivazione": _str(p.get("motivazione", ""), "proposte.motivazione", f)}
                     for p in _list(item.get("proposte"), "proposte", f)[:3] if isinstance(p, dict)]
        docs.append({
            "id": doc_id(f), "file": f, "sha256": _str(item.get("sha256", ""), "sha256", f),
            "dati_personali": bool(item.get("dati_personali")), "entita": entities,
            "categorie_particolari": [c for c in _list(item.get("categorie_particolari"), "categorie_particolari", f)
                                      if isinstance(c, str)],
            "livello": item.get("livello") if isinstance(item.get("livello"), int) else None,
            "proposte": proposals, "scheda": item.get("scheda") if isinstance(item.get("scheda"), str) else None,
            "esito": esito, "scostamenti": deviations,
        })
    return docs


def load_register(path):
    """Schede del registro per codice: solo i campi mostrati nella UI."""
    if path is None or not path.exists():
        return {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        if "Codice" not in (reader.fieldnames or []):
            raise ValueError("registro: colonna 'Codice' mancante")
        rows = list(reader)

    def col(r, name):
        return (r.get(name) or "").strip()[:MAX_TEXT * 2]
    return {col(r, "Codice"): {
        "codice": col(r, "Codice"), "denominazione": col(r, "Denominazione"), "finalita": col(r, "Finalità"),
        "struttura": col(r, "Struttura responsabile"),
        "categorie": col(r, "Categorie particolari dichiarate") or "Nessuna",
        "percorsi": [p.strip() for p in col(r, "Percorsi dichiarati").split(";") if p.strip()],
        "conservazione": col(r, "Conservazione") or col(r, "Conservazione in anni"),
        "diffusione": col(r, "Diffusione") or "NO",
    } for r in rows if col(r, "Codice")}


def risk(doc):
    """Priorità nella coda di validazione: più alta prima."""
    score = {"NON_CONFORME": 30, "SCHEDA_MANCANTE": 20, "CONFORME": 0, "NESSUN_DATO_PERSONALE": 0}[doc["esito"]]
    score += 10 * len(doc["scostamenti"]) + 8 * len(doc["categorie_particolari"])
    score += 5 if "ACCESSO_ECCESSIVO" in doc["scostamenti"] or "DIFFUSIONE_NON_PREVISTA" in doc["scostamenti"] else 0
    return score + min(len(doc["entita"]), 5)


def apply_decision(doc, decision):
    """Valori dopo la validazione dell'RPD; senza decisione restano quelli della pipeline."""
    if decision is None:
        return {**doc, "validato": False, "decisione": None}
    out = {**doc, "validato": True, "decisione": decision}
    if decision["azione"] == "CORREZIONE":
        out["esito"], out["scheda"] = decision["esito"], decision["scheda"] or None
        if out["esito"] != "NON_CONFORME":
            out["scostamenti"] = []
    return out
