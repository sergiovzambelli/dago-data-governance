from classifier.entities import find_entities


def kinds(text):
    return [(e["tipo"], text[e["inizio"]:e["fine"]]) for e in find_entities(text)]


def test_codice_fiscale_valid_checksum_only():
    assert kinds("C.F. CSMPRZ97B66G702K.") == [("CODICE_FISCALE", "CSMPRZ97B66G702K")]
    # ultimo carattere sbagliato
    assert kinds("C.F. CSMPRZ97B66G702A") == []


def test_codice_fiscale_is_masked():
    (e,) = find_entities("BLDSLV66A68E625M")
    assert e["valore_mascherato"] == "BLD************M"
    assert e["confidenza"] >= 0.99


def test_iban_with_spaces_and_checksum():
    text = "IBAN IT49 X076 0113 9000 0104 5677 821 intestato"
    assert kinds(text) == [("IBAN", "IT49 X076 0113 9000 0104 5677 821")]
    assert kinds("IT49X0760113900001045677822") == []


def test_iban_digits_are_not_also_phones():
    assert [k for k, _ in kinds("IT21 X020 0854 0790 2025 6215 815")] == ["IBAN"]


def test_phone_mobile_and_landline():
    assert kinds("tel. 326 552 5231, ufficio 0586 402118") == [
        ("TELEFONO", "326 552 5231"), ("TELEFONO", "0586 402118")]


def test_numbers_that_are_not_phones():
    # partita IVA (11 cifre), data, numero di pratica
    assert kinds("P.IVA 38528312087 del 11/07/1938, pratica CILA/2025/355") == []


def test_email():
    assert kinds("scrivere a mario.rossi@example.it.") == [("EMAIL", "mario.rossi@example.it")]


def test_entities_sorted_by_position():
    starts = [e["inizio"] for e in find_entities("a@b.it 333 401 7762 BLDSLV66A68E625M")]
    assert starts == sorted(starts)


def test_birth_date():
    text = "Bruno Baldini, nato a Livorno il 11/07/1938, deceduto"
    assert kinds(text) == [("DATA_NASCITA", "nato a Livorno il 11/07/1938")]


def test_name_after_courtesy_title():
    assert kinds("la Sig.ra Elena Gori chiede") == [("NOME", "Sig.ra Elena Gori")]


def test_ip_address_valid_octets_only():
    assert kinds("login da 93.41.12.7 ok") == [("INDIRIZZO_IP", "93.41.12.7")]
    assert kinds("versione 1.300.2.4") == []


def test_matricola():
    assert kinds("dipendente matricola n. 40213") == [("MATRICOLA", "matricola n. 40213")]


def test_ordinary_dates_and_names_are_not_entities():
    assert kinds("Delibera del 11/07/2026, Giunta Comunale di Livorno") == []
