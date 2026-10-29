"""Controllo di conformità: confronta il documento con la scheda del registro a cui è abbinato.

Le 5 regole della specifica, deterministiche.
"""
import csv

from classifier.dates import REFERENCE

ALL_EMPLOYEES = "GG_TUTTI_DIPENDENTI"
# shortcut: cartelle di pubblicazione scritte qui, come nel kit; da spostare in configurazione per un altro ente
PUBLISHED = ("Pubblicazioni", "OpenData")


def _under(path, folder):
    return path.startswith(folder.rstrip("/") + "/")


def load_permissions(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        missing = [c for c in ("cartella", "gruppi_con_accesso") if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"colonne mancanti nei permessi: {', '.join(missing)}")
        return [(r["cartella"].strip().rstrip("/"), {g.strip() for g in r["gruppi_con_accesso"].split(",") if g.strip()})
                for r in reader]


def _groups(permissions, file_path):
    # vale la cartella più specifica che contiene il file
    folders = [(len(f), groups) for f, groups in permissions if _under(file_path, f)]
    return max(folders, key=lambda x: x[0])[1] if folders else set()


def _expired(doc_date, years):
    if doc_date is None or years is None:
        return False
    try:
        end = doc_date.replace(year=doc_date.year + years)
    except ValueError:  # 29 febbraio in un anno non bisestile
        end = doc_date.replace(year=doc_date.year + years, day=28)
    return end < REFERENCE


def check(record, file_path, categories, permissions, doc_date=None):
    found = []
    if set(categories) - record["categorie_dichiarate"]:
        found.append("CATEGORIA_NON_DICHIARATA")
    # niente LUOGO_NON_DICHIARATO: controllo tolto su decisione dell'utente; le cartelle dichiarate restano per
    # l'abbinamento della scheda
    # shortcut: il livello di riservatezza non c'è ancora, ogni documento con dati personali vale come livello ≥ 2
    # (sviluppo: nessun falso positivo); da sostituire con il livello calcolato in feat/level
    if ALL_EMPLOYEES in _groups(permissions, file_path):
        found.append("ACCESSO_ECCESSIVO")
    if _expired(doc_date, record.get("conservazione_anni")):
        found.append("CONSERVAZIONE_SCADUTA")
    # shortcut: "destinato alla pubblicazione" solo dalla cartella; le determine da pubblicare all'albo
    # si riconoscono dal testo (PR successiva)
    published = any(seg in PUBLISHED for seg in file_path.split("/")[:-1])
    if published and (not record["diffusione"] or categories):
        found.append("DIFFUSIONE_NON_PREVISTA")
    return found
