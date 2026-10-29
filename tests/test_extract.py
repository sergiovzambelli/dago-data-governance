from pathlib import Path

import pytest

from classifier.extract import extract_text

KIT = Path("data/Kit_team_hackathon_sfida_5/sviluppo/fileserver")


@pytest.mark.parametrize("rel, expected", [
    ("Comunicazione/comunicato_stampa_lungomare.txt", "Terrazza Mascagni"),
    ("Edilizia/Pratiche/CILA_20251012_115.docx", "CSMPRZ97B66G702K"),
    ("Edilizia/Pratiche/CILA_20250610_735.pdf", "FRDRNN90C44E625E"),
    ("OpenData/parcheggi_capienza_2026.csv", "Parcheggio Porta a Mare"),
    ("Sociale/Scambio/presenze_centri_diurni_20250207_459.xlsx", "|"),
    ("Condivisa/Cimiteri/domanda_loculo_Baldini.odt", "BLDSLV66A68E625M"),
    ("Ambiente/Segnalazioni/esposto_rumori_Via_Grande.eml", "Via Grande"),
])
def test_extracts_text_from_kit_formats(rel, expected):
    assert expected in extract_text(KIT / rel)


def test_scanned_pdf_has_no_text_layer_yet():
    # niente OCR in questa PR: la scansione resta vuota
    assert extract_text(KIT / "Condivisa/scansioni/scan_20260302_0113.pdf").strip() == ""


def test_corrupt_file_returns_empty_string(tmp_path):
    bad = tmp_path / "rotto.odt"
    bad.write_bytes(b"non sono uno zip")
    assert extract_text(bad) == ""
