"""Predizioni della pipeline, registro dei trattamenti e testi in italiano per la UI."""
import csv
import hashlib
import json
import re
from datetime import datetime

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
    return parse_predictions(json.loads(path.read_text(encoding="utf-8")))


def parse_predictions(raw):
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
    """Righe del registro per codice, con tutte le colonne (quelle assenti dal CSV restano vuote)."""
    if path is None or not path.exists():
        return {}
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        if "Codice" not in (reader.fieldnames or []):
            raise ValueError("registro: colonna 'Codice' mancante")
        rows = [{c: (r.get(c) or "").strip()[:MAX_TEXT * 2] for c in REGISTER_COLUMNS} for r in reader]
    return {r["Codice"]: r for r in rows if r["Codice"]}


def record_view(r):
    """Campi della scheda mostrati nelle pagine dei documenti."""
    return {
        "codice": r["Codice"], "denominazione": r["Denominazione"], "finalita": r["Finalità"],
        "struttura": r["Struttura responsabile"], "categorie": r["Categorie particolari dichiarate"] or "Nessuna",
        "percorsi": [p.strip() for p in r["Percorsi dichiarati"].split(";") if p.strip()],
        "conservazione": r["Conservazione"] or r["Conservazione in anni"], "diffusione": r["Diffusione"] or "NO",
    }


RECORD_ACTIONS = {"CREA": "Creazione", "MODIFICA": "Modifica", "ARCHIVIA": "Archiviazione", "RIPRISTINA": "Ripristino"}
RECORD_CODE = re.compile(r"[A-Z][A-Z0-9]{0,5}(-[A-Z0-9]{1,6}){1,3}")  # es. T-PER-07
RECORD_REQUIRED = ("Codice", "Denominazione", "Finalità", "Base giuridica")
NO_LIMIT = "Illimitata / non calcolabile"
# colonne del registro raggruppate nel modulo della scheda
RECORD_SECTIONS = (
    ("Trattamento", ("Codice", "Denominazione", "Origine", "Struttura responsabile", "Ufficio")),
    ("Finalità e base giuridica", ("Finalità", "Base giuridica", "Fonti normative", "Consenso")),
    ("Dati e interessati", ("Categorie di dati", "Categorie particolari dichiarate", "Interessati", "Comunicazione",
                            "Diffusione", "Responsabili esterni")),
    ("Dove stanno i documenti", ("Percorsi dichiarati", "Gruppo di accesso", "Archivi", "Software")),
    ("Conservazione", ("Conservazione", "Conservazione in anni")),
    ("Abbinamento automatico dei documenti", ("Tipologie documentali tipiche", "Parole chiave")),
)
RECORD_LONG = {"Finalità", "Base giuridica", "Fonti normative", "Categorie di dati", "Interessati", "Comunicazione",
               "Responsabili esterni", "Archivi", "Tipologie documentali tipiche", "Parole chiave"}
RECORD_HINTS = {
    "Codice": "Lettere maiuscole, cifre e trattini, es. T-URP-01. Non si cambia dopo la creazione.",
    "Categorie particolari dichiarate": "Codici in maiuscolo separati da virgola (es. SALUTE, GIUDIZIARI) oppure «Nessuna».",
    "Percorsi dichiarati": "Cartelle separate da punto e virgola, es. fileserver/URP/Reclami.",
    "Conservazione in anni": f"Un numero di anni oppure «{NO_LIMIT}»: serve al controllo della conservazione.",
    "Tipologie documentali tipiche": "Servono all'abbinamento automatico dei documenti alla scheda.",
    "Parole chiave": "Separate da virgola: servono all'abbinamento automatico dei documenti alla scheda.",
}


def clean_record(form):
    """Valori di una scheda dal modulo: testo senza caratteri di controllo, campi a scelta chiusa verificati."""
    out = {}
    for c in REGISTER_COLUMNS:
        value = form.get(c, "")
        if not isinstance(value, str):
            raise ValueError("Campo non valido.")
        out[c] = re.sub(r"[\x00-\x1f\x7f]", " ", value).strip()[:MAX_TEXT * 2]
    missing = [c for c in RECORD_REQUIRED if not out[c]]
    if missing:
        raise ValueError(f"Campi obbligatori: {', '.join(missing).lower()}.")
    if not RECORD_CODE.fullmatch(out["Codice"]):
        raise ValueError("Codice non valido: lettere maiuscole, cifre e trattini, es. T-URP-01.")
    for c in ("Diffusione", "Consenso"):
        if out[c] not in ("SI", "NO"):
            raise ValueError(f"{c}: scegli SI o NO.")
    years = out["Conservazione in anni"]
    if years and years != NO_LIMIT and not re.fullmatch(r"\d{1,3}", years):
        raise ValueError(f"Conservazione in anni: un numero oppure «{NO_LIMIT}».")
    cats = out["Categorie particolari dichiarate"]
    if cats and cats != "Nessuna" and not re.fullmatch(r"[A-Z_]+(, ?[A-Z_]+)*", cats):
        raise ValueError("Categorie particolari: codici in maiuscolo separati da virgola, oppure «Nessuna».")
    return out


def apply_records(base, versions):
    """Schede in uso: il registro CSV con sopra le versioni salvate dall'RPD, nell'ordine in cui sono state salvate."""
    records = {code: {"campi": row, "archiviata": False, "nuova": False, "versioni": []} for code, row in base.items()}
    for v in versions:
        r = records.setdefault(v["codice"], {"campi": v["campi"], "archiviata": False, "nuova": True, "versioni": []})
        if v["azione"] in ("CREA", "MODIFICA"):
            r["campi"] = v["campi"]
        r["archiviata"] = v["azione"] == "ARCHIVIA" or (r["archiviata"] and v["azione"] == "MODIFICA")
        r["versioni"].append(v)
    return records


ACTIONS = {"CONFERMA": "Conferma", "CORREZIONE": "Correzione"}
# stesse colonne di classifier/drafts.py: la UI non importa il classificatore
REGISTER_COLUMNS = (
    "Codice", "Origine", "Denominazione", "Struttura responsabile", "Ufficio", "Finalità", "Base giuridica",
    "Fonti normative", "Categorie di dati", "Categorie particolari dichiarate", "Interessati", "Comunicazione",
    "Diffusione", "Responsabili esterni", "Archivi", "Percorsi dichiarati", "Gruppo di accesso", "Conservazione",
    "Conservazione in anni", "Software", "Consenso", "Tipologie documentali tipiche", "Parole chiave")
# campi di una bozza che l'RPD può correggere: nome nel modulo → colonna del registro. Gli altri (cartelle, gruppo,
# categorie rilevate, diffusione) vengono dall'analisi e si cambiano nel registro dopo l'approvazione
DRAFT_EDITABLE = {
    "denominazione": "Denominazione", "finalita": "Finalità", "base_giuridica": "Base giuridica",
    "fonti": "Fonti normative", "interessati": "Interessati", "categorie_dati": "Categorie di dati",
    "struttura": "Struttura responsabile", "ufficio": "Ufficio", "tipologie": "Tipologie documentali tipiche",
    "parole_chiave": "Parole chiave", "conservazione": "Conservazione", "conservazione_anni": "Conservazione in anni",
}
DRAFT_REQUIRED = ("Denominazione", "Finalità", "Base giuridica")
DRAFT_ACTIONS = {"APPROVA": "Approvata", "SCARTA": "Scartata"}


def load_drafts(path):
    """Bozze di schede (classifier/drafts.py), validate come le predizioni; senza file nessuna bozza."""
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("bozze: atteso un elenco")
    drafts = []
    for item in raw:
        if not isinstance(item, dict) or not re.fullmatch(r"[0-9a-f]{16}", str(item.get("id", ""))) \
                or not isinstance(item.get("campi"), dict):
            raise ValueError("bozze: ogni bozza deve avere 'id' e 'campi'")
        fields = {c: str(item["campi"].get(c) or "")[:MAX_TEXT] for c in REGISTER_COLUMNS}
        drafts.append({"id": item["id"], "codice": fields["Codice"], "campi": fields, "modello": bool(item.get("modello")),
                       "documenti": [d[:MAX_TEXT] for d in _list(item.get("documenti"), "documenti", item["id"])
                                     if isinstance(d, str)],
                       "da_verificare": [c for c in _list(item.get("da_verificare"), "da_verificare", item["id"])
                                         if c in REGISTER_COLUMNS]})
    return drafts


def risk(doc):
    """Priorità nella coda di validazione: più alta prima."""
    score = {"NON_CONFORME": 30, "SCHEDA_MANCANTE": 20, "CONFORME": 0, "NESSUN_DATO_PERSONALE": 0}[doc["esito"]]
    score += 10 * len(doc["scostamenti"]) + 8 * len(doc["categorie_particolari"])
    score += 5 if "ACCESSO_ECCESSIVO" in doc["scostamenti"] or "DIFFUSIONE_NON_PREVISTA" in doc["scostamenti"] else 0
    return score + min(len(doc["entita"]), 5)


def priority(doc):
    """Priorità a parole, con i motivi: è ciò che l'RPD legge nella coda al posto del punteggio."""
    score = risk(doc)
    level = ("Alta", "danger") if score >= 40 else ("Media", "warning") if score >= 20 else ("Bassa", "neutral")
    reasons = []
    if doc["esito"] == "SCHEDA_MANCANTE":
        reasons.append("nessuna scheda")
    n = len(doc["scostamenti"])
    if n:
        reasons.append(f"{n} scostament{'o' if n == 1 else 'i'}")
    reasons += [CATEGORIES.get(c, c) for c in doc["categorie_particolari"]]
    if "ACCESSO_ECCESSIVO" in doc["scostamenti"]:
        reasons.append("aperto a tutti i dipendenti")
    if "DIFFUSIONE_NON_PREVISTA" in doc["scostamenti"]:
        reasons.append("pubblicato")
    return {"livello": level[0], "colore": level[1], "motivi": reasons}


def highlight(text, spans):
    """Testo a pezzi [(testo, tipo o None, etichetta)]. spans: (inizio, fine, tipo, etichetta), a parità di
    inizio vince il primo dell'elenco; quelli sovrapposti a uno già preso si scartano."""
    order = sorted(enumerate(spans), key=lambda x: (x[1][0], x[0]))
    out, pos = [], 0
    for _, (start, end, kind, label) in order:
        if start < pos or end > len(text) or start >= end:
            continue
        out += [(text[pos:start], None, "")] if start > pos else []
        out.append((text[start:end], kind, label))
        pos = end
    return out + ([(text[pos:], None, "")] if pos < len(text) else [])


def split_path(path):
    """(cartella, nome del file) per mostrarli separati."""
    folder, _, name = path.rpartition("/")
    return folder, name


def when(iso):
    """2026-10-29T14:01:05+00:00 → 29/10/2026 14:01 UTC."""
    try:
        d = datetime.fromisoformat(iso)
    except ValueError:
        return iso
    return d.strftime("%d/%m/%Y %H:%M") + (" UTC" if d.utcoffset() is not None and not d.utcoffset() else "")


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
