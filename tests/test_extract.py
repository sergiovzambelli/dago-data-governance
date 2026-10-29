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


def _eml(tmp_path, body, attachment=None):
    from email.message import EmailMessage
    msg = EmailMessage()
    msg["From"] = "mario.rossi@example.it"
    msg["Subject"] = "Reclamo"
    msg.set_content(body, cte="quoted-printable")
    if attachment:
        name, data = attachment
        msg.add_attachment(data, maintype="text", subtype="plain", filename=name)
    p = tmp_path / "m.eml"
    p.write_bytes(bytes(msg))
    return p


def test_eml_body_is_decoded_and_headers_kept(tmp_path):
    # riga lunga: in quoted-printable va a capo con "=" a metà parola
    text = extract_text(_eml(tmp_path, "x" * 70 + " con 15 giorni di prognosi è un caso"))
    assert "15 giorni di prognosi è un caso" in text
    assert "mario.rossi@example.it" in text


def test_eml_attachments_are_extracted(tmp_path):
    text = extract_text(_eml(tmp_path, "vedi allegato", ("verbale.txt", b"C.F. BLDSLV66A68E625M")))
    assert "BLDSLV66A68E625M" in text


def test_kit_pec_with_pdf_attachment():
    pec = KIT / "Segreteria/Protocollo/PEC_accesso_atti_2026_3321.eml"
    # il CF è solo nel PDF allegato, codificato in base64
    assert "CCCSMN94B01E625Q" not in pec.read_text()
    assert "CCCSMN94B01E625Q" in extract_text(pec)
