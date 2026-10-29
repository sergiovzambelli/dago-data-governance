"""Riconosce le categorie particolari (art. 9 GDPR) e i dati giudiziari (art. 10) con dizionari di espressioni.

Le espressioni coprono anche i casi descritti senza nominare la categoria (es. "cardiochirurgia" → SALUTE).
"""
import re

# shortcut: dizionari ricavati dal dataset di sviluppo; i casi più impliciti richiedono il LLM locale
PATTERNS = {
    "SALUTE": [
        r"invalidit[àa]", r"disabilit[àa]", r"handicap", r"non autosufficien\w*", r"l(?:egge|\.)\s*104",
        r"diagnos\w*", r"patologi\w*", r"malatti\w*", r"infermit[àa]", r"ipertension\w*", r"diabet\w*",
        r"\w*chirurgi\w*", r"ricover\w*", r"pronto soccorso", r"prognosi", r"referto", r"affett[oa] da",
        r"trattamento sanitario obbligatorio", r"\bTSO\b", r"psichiatr\w*", r"terapi\w*",
        r"celiachi\w*", r"allergi\w*", r"intolleranz\w*", r"gravidanz\w*", r"infortuni[oa]\b", r"lesion[ei]",
        r"servizio per le dipendenze", r"disintossica\w*", r"tossicodipenden\w*", r"distrofi\w*",
        r"disturb\w* specific\w*", r"spese sanitarie",
        r"medico (?:competente|curante)", r"mio medico", r"certificat\w* medic\w*", r"inidone\w*",
        r"limitazioni", r"equo indennizzo",
    ],
    "GIUDIZIARI": [
        r"casellario", r"procedimento penale", r"notizia di reato", r"per il reato", r"reato di",
        r"condann\w*", r"carichi pendenti", r"indagat[oaie]\b", r"persona offesa", r"denuncia",
        r"querela", r"\bc\.\s?p\.", r"codice penale", r"autorit[àa] giudiziaria",
        r"detenut[oaie]", r"casa circondariale", r"carcer\w*",
        r"procura della repubblica", r"requisiti morali", r"antimafia", r"misure di prevenzione",
        r"sentenza", r"art\.\s?(?:80|94) d\.\s?lgs",
    ],
    "RELIGIOSE": [
        r"religios\w*", r"rito (?:islamico|ebraico|cattolico|ortodosso|evangelico|buddista|induista)",
        r"islam\w*", r"musulman\w*", r"ebrai\w*", r"induis\w*", r"buddis\w*", r"halal", r"kosher",
        r"ramadan", r"ministro di culto",
    ],
    "SINDACALE": [
        # "sindacale" da solo vuol dire anche "del sindaco"
        r"organizzazione sindacale", r"delega sindacale", r"iscrizione sindacale", r"sindacato",
        r"\b(?:CGIL|CISL|UIL)\b", r"associazione per la cremazione",
    ],
}
# gli spazi valgono anche come a capo (PDF)
_RE = {cat: re.compile("|".join(rf"(?:{p})".replace(" ", r"\s+") for p in pats), re.I)
       for cat, pats in PATTERNS.items()}
# "non" poco prima, nella stessa frase: "non sono presenti persone con invalidità"
_NEGATION = re.compile(r"\bnon\b[^.;\n]{0,40}$", re.I)


def find_categories(text):
    """Una evidenza (la prima) per ogni categoria trovata."""
    found = []
    for cat, regex in _RE.items():
        m = next((m for m in regex.finditer(text) if not _NEGATION.search(text, max(0, m.start() - 45), m.start())), None)
        if m:
            found.append({"categoria": cat, "evidenza": m.group(), "inizio": m.start(), "fine": m.end()})
    return found
