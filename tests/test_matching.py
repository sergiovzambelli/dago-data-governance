import pytest

from classifier.matching import is_missing_record, load_register, match

HEADER = "Codice;Percorsi dichiarati;Parole chiave;Tipologie documentali tipiche"
ROWS = [
    "T-EDU-01;fileserver/Educazione;nido, mensa, dieta speciale, iscrizione;Domanda di iscrizione",
    "T-APP-01;srv-archivi/Gare;gara, CIG, operatore economico, iscrizione;Verbale di gara",
    "T-PER-07;fileserver/Personale/Permessi;legge 104, congedo, permesso;Istanza di permessi",
]


@pytest.fixture
def register(tmp_path):
    p = tmp_path / "registro.csv"
    p.write_text("﻿" + "\n".join([HEADER, *ROWS]) + "\n", encoding="utf-8")
    return load_register(p)


def codes(proposals):
    return [p["scheda"] for p in proposals]


def test_declared_folder_counts(register):
    assert codes(match(register, "fileserver/Educazione/x.pdf", "testo qualunque")) == ["T-EDU-01"]


def test_folder_must_match_whole_segments(register):
    assert match(register, "fileserver/EducazioneFisica/x.pdf", "testo qualunque") == []


def test_text_beats_wrong_folder(register):
    # istanza 104 salvata nella cartella dell'Educazione (LUOGO_NON_DICHIARATO)
    text = "Istanza di permessi ai sensi della legge 104 e congedo straordinario"
    assert codes(match(register, "fileserver/Educazione/scan.pdf", text))[0] == "T-PER-07"


def test_shared_keyword_weighs_less_than_specific_one(register):
    # "iscrizione" è in due schede, "CIG" in una sola
    assert codes(match(register, "x/y.pdf", "iscrizione, CIG 12345"))[0] == "T-APP-01"


def test_whole_words_only(register):
    assert match(register, "x/y.pdf", "il garage e la cigolante porta") == []


def test_at_most_three_with_score_and_reason(register):
    props = match(register, "fileserver/Educazione/a.pdf", "nido, gara, congedo")
    assert len(props) == 3
    assert props[0]["scheda"] == "T-EDU-01"
    assert props[0]["punteggio"] >= props[1]["punteggio"] >= props[2]["punteggio"] > 0
    assert "cartella dichiarata" in props[0]["motivazione"]
    assert "nido" in props[0]["motivazione"]


def test_register_without_required_columns_is_rejected(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text("Codice;Altro\nT-1;x\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Percorsi dichiarati"):
        load_register(p)


def test_no_proposal_means_missing_record(register):
    assert is_missing_record(register, "fileserver/Ambiente/esposto.eml", "rumori notturni in via Grande")


def test_single_keyword_outside_declared_folders_is_missing_record(register):
    # domanda di un servizio non censito che cita per caso "congedo"
    assert is_missing_record(register, "fileserver/Condivisa/domanda.pdf", "chiedo il servizio, sono in congedo")


def test_declared_folder_is_never_missing_record(register):
    assert not is_missing_record(register, "fileserver/Educazione/x.pdf", "testo qualunque")


def test_two_keywords_in_wrong_folder_keep_their_record(register):
    # documento fuori posto (LUOGO_NON_DICHIARATO): il testo basta per riconoscere la scheda
    assert not is_missing_record(register, "fileserver/Condivisa/x.pdf", "istanza legge 104 e congedo")


def test_register_reads_declared_categories_and_diffusion(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text("Codice;Percorsi dichiarati;Parole chiave;Tipologie documentali tipiche;"
                 "Categorie particolari dichiarate;Diffusione\n"
                 "T-1;a/b;x;y;ETNICA, SALUTE;SI\nT-2;c;x;y;Nessuna;NO\nT-3;d;x;y;SESSUALE;\n", encoding="utf-8")
    recs = {r["codice"]: r for r in load_register(p)}
    # i nomi del registro diventano quelli usati dal classificatore
    assert recs["T-1"]["categorie_dichiarate"] == {"ORIGINE_ETNICA", "SALUTE"} and recs["T-1"]["diffusione"]
    assert recs["T-2"]["categorie_dichiarate"] == set() and not recs["T-2"]["diffusione"]
    assert recs["T-3"]["categorie_dichiarate"] == {"ORIENTAMENTO_SESSUALE"} and not recs["T-3"]["diffusione"]


def test_register_reads_retention_years(tmp_path):
    p = tmp_path / "r.csv"
    p.write_text("Codice;Percorsi dichiarati;Parole chiave;Tipologie documentali tipiche;Conservazione in anni\n"
                 "T-1;a;x;y;10\nT-2;b;x;y;Illimitata / non calcolabile\nT-3;c;x;y;\n", encoding="utf-8")
    recs = {r["codice"]: r["conservazione_anni"] for r in load_register(p)}
    assert recs == {"T-1": 10, "T-2": None, "T-3": None}


def test_doubtful_match(register):
    from classifier.matching import is_doubtful
    assert is_doubtful(register, "fileserver/Condivisa/x.pdf", "nessun indizio")
    # due parole chiave fuori cartella: la scheda c'è, ma va verificata
    assert is_doubtful(register, "fileserver/Condivisa/x.pdf", "istanza legge 104 e congedo")
    assert not is_doubtful(register, "fileserver/Condivisa/x.pdf", "legge 104, congedo, permesso")
    assert not is_doubtful(register, "fileserver/Personale/Permessi/x.pdf", "congedo")
