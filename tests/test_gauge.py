import re

from ui.gauge import compliance_score, gauge_svg, level


def doc(esito, scostamenti=()):
    return {"esito": esito, "scostamenti": list(scostamenti)}


def test_score_follows_outcome_and_severity():
    assert compliance_score(doc("CONFORME")) == 100
    assert compliance_score(doc("SCHEDA_MANCANTE")) == 30
    assert compliance_score(doc("NESSUN_DATO_PERSONALE")) is None
    one = compliance_score(doc("NON_CONFORME", ["ACCESSO_ECCESSIVO"]))
    two = compliance_score(doc("NON_CONFORME", ["ACCESSO_ECCESSIVO", "DIFFUSIONE_NON_PREVISTA"]))
    assert 30 < one < 70 and 0 <= two < one


def test_score_never_below_zero():
    worst = ["CATEGORIA_NON_DICHIARATA", "ACCESSO_ECCESSIVO", "CONSERVAZIONE_SCADUTA", "DIFFUSIONE_NON_PREVISTA"]
    assert compliance_score(doc("NON_CONFORME", worst)) == 0


def test_levels_are_words_not_only_colours():
    assert level(100)[0] == "alta" and level(55)[0] == "media" and level(10)[0] == "bassa"


def _needle_x(svg):
    return float(re.search(r'class="needle"[^>]*x2="([\d.]+)"', svg).group(1))


def test_needle_points_to_green_when_compliant_and_red_when_not():
    # come nella foto: verde a sinistra, rosso a destra
    assert _needle_x(gauge_svg(100, "Documento")) < 60
    assert _needle_x(gauge_svg(0, "Documento")) > 140
    assert 90 < _needle_x(gauge_svg(50, "Documento")) < 110


def test_gauge_is_an_image_with_its_text_and_escapes_the_label():
    svg = gauge_svg(78, '<b>Archivio</b>')
    assert 'role="img"' in svg and "Grado di conformità 78 su 100, alta" in svg
    assert "<b>" not in svg and "&lt;b&gt;" in svg
