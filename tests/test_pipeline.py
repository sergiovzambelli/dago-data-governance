import hashlib
import json
import os
import subprocess
import sys

from classifier.pipeline import classify


def test_classify_lists_every_file_with_relative_path_and_sha256(tmp_path):
    (tmp_path / "fileserver" / "Ufficio").mkdir(parents=True)
    (tmp_path / "fileserver" / "Ufficio" / "a.txt").write_bytes(b"ciao")
    (tmp_path / "b.csv").write_bytes(b"x;y")

    out = {r["file"]: r for r in classify(tmp_path)}

    assert set(out) == {"fileserver/Ufficio/a.txt", "b.csv"}
    a = out["fileserver/Ufficio/a.txt"]
    assert a["sha256"] == hashlib.sha256(b"ciao").hexdigest()
    assert a["proposte"] == [] and a["scostamenti"] == []


def test_text_without_entities_has_no_personal_data(tmp_path):
    (tmp_path / "avviso.txt").write_text("Chiusura uffici il 2 giugno.")
    (r,) = classify(tmp_path)
    assert r["esito"] == "NESSUN_DATO_PERSONALE"
    assert r["dati_personali"] is False and r["entita"] == []


def test_text_with_entities_is_personal(tmp_path):
    (tmp_path / "domanda.txt").write_text("Richiedente C.F. BLDSLV66A68E625M")
    (r,) = classify(tmp_path)
    assert r["dati_personali"] is True
    assert r["esito"] == "CONFORME"
    assert [e["tipo"] for e in r["entita"]] == ["CODICE_FISCALE"]


def test_unreadable_file_is_not_declared_free_of_personal_data(tmp_path):
    # senza testo (es. scansione senza OCR) non possiamo dire che non ci sono dati
    (tmp_path / "scan.odt").write_bytes(b"non leggibile")
    (r,) = classify(tmp_path)
    assert r["dati_personali"] is True and r["esito"] == "CONFORME"


def test_classify_skips_symlinks_outside_root(tmp_path):
    secret = tmp_path / "fuori.txt"
    secret.write_text("segreto")
    root = tmp_path / "root"
    root.mkdir()
    os.symlink(secret, root / "link.txt")

    assert classify(root) == []


def test_cli_writes_json(tmp_path):
    (tmp_path / "a.txt").write_text("x")
    out = subprocess.run(
        [sys.executable, "-m", "classifier.pipeline", str(tmp_path)],
        capture_output=True, text=True, check=True,
    ).stdout
    assert [r["file"] for r in json.loads(out)] == ["a.txt"]


def test_special_category_makes_document_personal(tmp_path):
    # nessun codice fiscale, ma descrive la salute di una persona
    (tmp_path / "relazione.txt").write_text("Il padre è affetto da distrofia muscolare.")
    (r,) = classify(tmp_path)
    assert r["dati_personali"] is True and r["esito"] == "CONFORME"
    assert r["categorie_particolari"] == ["SALUTE"]
