"""Data del documento, per la regola CONSERVAZIONE_SCADUTA.

Ordine (scelto su sviluppo: 134/155 date esatte; solo testo 127, solo nome file 132):
1. data scritta dopo il luogo o un'etichetta ("Livorno, 12 marzo 2026", "Data: …");
2. data nel nome del file (AAAAMMGG);
3. data più recente nel testo, escluse le date di nascita e quelle future.
"""
import re
from datetime import date

REFERENCE = date(2026, 10, 28)  # data di riferimento della specifica
MONTHS = "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre".split()
DATE_RE = re.compile(r"\b(\d{1,2})(?:[/.-](\d{1,2})[/.-]|\s+(" + "|".join(MONTHS) + r")\s+)(\d{4})\b", re.I)
PLACED_RE = re.compile(r"(?:Livorno|lì|data)\s*[,:]?\s*$", re.I)
# "nato a … il 16/06/1979" oppure "Laura Bianchi (23/02/1991)"
BIRTH_RE = re.compile(r"(?:\bnat[oaie]\b[^\n]{0,60}|\()\s*$", re.I)
FILE_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(\d{2})(\d{2})(?!\d)")


def _date(y, m, d):
    try:
        return date(int(y), int(m), int(d))
    except ValueError:  # 31/02, mese 13…
        return None


def document_date(file_path, text):
    placed, others = [], []
    for m in DATE_RE.finditer(text):
        d = _date(m[4], m[2] or MONTHS.index(m[3].lower()) + 1, m[1])
        before = text[max(0, m.start() - 70):m.start()]
        # shortcut: una data futura è una scadenza, non la data del documento; vale per il 28/10/2026
        if not d or d > REFERENCE or BIRTH_RE.search(before):
            continue
        (placed if PLACED_RE.search(before) else others).append(d)
    if placed:
        return placed[0]
    f = FILE_RE.search(file_path.rsplit("/", 1)[-1])
    from_name = _date(*f.groups()) if f else None
    if from_name and from_name <= REFERENCE:
        return from_name
    return max(others, default=None)
