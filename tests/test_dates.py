from datetime import date

from classifier.dates import document_date


def test_date_after_place_wins():
    text = "Scadenza 30/09/2026.\nLivorno, 12 marzo 2026\nIl dirigente"
    assert document_date("x/delibera.docx", text) == date(2026, 3, 12)


def test_file_name_date_when_text_has_no_placed_date():
    assert document_date("Verbali/verbale_ZTL_20170316_840.pdf", "riferimento 01/02/2017") == date(2017, 3, 16)


def test_latest_text_date_as_last_resort():
    assert document_date("x/a.eml", "inviata il 07/01/2025, sollecito del 20.02.2025") == date(2025, 2, 20)


def test_birth_dates_are_not_document_dates():
    text = "Mario Rossi, nato a Livorno il 16/06/1979, e la sig.ra Laura Bianchi (23/02/1991)"
    assert document_date("x/relazione.odt", text) is None


def test_future_dates_are_ignored():
    # una scadenza futura non è la data del documento
    assert document_date("x/a.txt", "valido fino al 31/12/2030") is None


def test_impossible_dates_are_ignored():
    assert document_date("x/scan_20261340_1.pdf", "il 31/02/2025") is None
