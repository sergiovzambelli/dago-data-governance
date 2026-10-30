"""Grado di conformità (0-100) e indicatore a lancetta in SVG: verde a sinistra (conforme), rosso a destra."""
import math

from markupsafe import Markup, escape

# quanto pesa ogni problema: la diffusione espone i dati a chiunque, la conservazione scaduta è meno urgente
PENALTY = {"DIFFUSIONE_NON_PREVISTA": 35, "CATEGORIA_NON_DICHIARATA": 25, "ACCESSO_ECCESSIVO": 25,
           "CONSERVAZIONE_SCADUTA": 20, "LUOGO_NON_DICHIARATO": 15}
NON_COMPLIANT_START = 70  # un documento non conforme parte sotto la soglia "alta"
MISSING_RECORD = 30       # senza scheda la conformità non si può verificare: grado basso
# sei settori come nella foto, dal verde scuro al rosso (decorativi: il valore è sempre scritto a parole)
SEGMENTS = ("#1e7b34", "#4caf2a", "#e2b007", "#f08c00", "#e8590c", "#c92a2a")
START, SWEEP = 210, 240   # gradi: l'arco va da in basso a sinistra a in basso a destra
CX, CY, R, WIDTH = 100, 100, 78, 26


def compliance_score(doc):
    """0-100, oppure None per i documenti senza dati personali (niente da verificare)."""
    if doc["esito"] == "NESSUN_DATO_PERSONALE":
        return None
    if doc["esito"] == "CONFORME":
        return 100
    if doc["esito"] == "SCHEDA_MANCANTE":
        return MISSING_RECORD
    # shortcut: pesi scelti a mano per ordinare la gravità; da tarare con l'RPD
    return max(0, NON_COMPLIANT_START - sum(PENALTY.get(s, 20) for s in doc["scostamenti"]))


def average(docs):
    scores = [s for s in (compliance_score(d) for d in docs) if s is not None]
    return round(sum(scores) / len(scores)) if scores else None


def level(score):
    """(parola, classe CSS): il livello si legge, non si deduce dal colore."""
    if score >= 75:
        return "alta", "ok"
    if score >= 40:
        return "media", "mid"
    return "bassa", "low"


def _point(angle, radius):
    a = math.radians(angle)
    return round(CX + radius * math.cos(a), 2), round(CY - radius * math.sin(a), 2)


def gauge_svg(score, label, size="md"):
    """Indicatore accessibile: immagine con testo alternativo, valore e livello scritti sotto."""
    word, cls = level(score)
    alt = f"Grado di conformità {score} su 100, {word} — {label}"
    step, gap = SWEEP / len(SEGMENTS), 1.5
    arcs = []
    for i, colour in enumerate(SEGMENTS):
        a1, a2 = START - i * step - (gap if i else 0), START - (i + 1) * step + (gap if i < len(SEGMENTS) - 1 else 0)
        (x1, y1), (x2, y2) = _point(a1, R), _point(a2, R)
        arcs.append(f'<path d="M {x1} {y1} A {R} {R} 0 0 1 {x2} {y2}" stroke="{colour}" stroke-width="{WIDTH}" fill="none"/>')
    # 100 = tutto a sinistra (verde), 0 = tutto a destra (rosso)
    nx, ny = _point(START - SWEEP * (100 - score) / 100, R - 8)
    return Markup(
        f'<figure class="gauge gauge-{size} gauge-{cls}" role="img" aria-label="{escape(alt)}">'
        f'<svg viewBox="0 0 200 150" aria-hidden="true" focusable="false">{"".join(arcs)}'
        f'<line class="needle" x1="{CX}" y1="{CY}" x2="{nx}" y2="{ny}" stroke="#2b2f3a" stroke-width="6" stroke-linecap="round"/>'
        f'<circle cx="{CX}" cy="{CY}" r="11" fill="#2b2f3a"/></svg>'
        f'<figcaption aria-hidden="true"><span class="gauge-value">{score}</span>'
        f'<span class="gauge-word">conformità {word}</span></figcaption></figure>')
