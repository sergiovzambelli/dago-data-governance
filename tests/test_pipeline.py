import hashlib
import json
import os
import subprocess
import sys

from classifier.compliance import load_permissions
from classifier.matching import load_register
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


def test_proposals_from_register(tmp_path):
    reg = tmp_path / "registro.csv"
    reg.write_text("Codice;Percorsi dichiarati;Parole chiave;Tipologie documentali tipiche\n"
                   "T-PER-07;Personale/Permessi;congedo;Istanza\n", encoding="utf-8")
    root = tmp_path / "share"
    (root / "Personale" / "Permessi").mkdir(parents=True)
    (root / "Personale" / "Permessi" / "a.txt").write_text("C.F. BLDSLV66A68E625M chiede congedo")
    (r,) = classify(root, load_register(reg))
    assert r["scheda"] == "T-PER-07"
    assert [p["scheda"] for p in r["proposte"]] == ["T-PER-07"]


def test_proposals_also_without_personal_data_but_no_record(tmp_path):
    # se il "senza dati personali" è un errore (es. soli nomi), le proposte restano utili all'RPD
    reg = tmp_path / "registro.csv"
    reg.write_text("Codice;Percorsi dichiarati;Parole chiave;Tipologie documentali tipiche\n"
                   "T-PER-02;Personale/Concorsi;graduatoria;Graduatoria\n", encoding="utf-8")
    root = tmp_path / "share"
    (root / "Personale" / "Concorsi").mkdir(parents=True)
    (root / "Personale" / "Concorsi" / "g.txt").write_text("Graduatoria: Rossi Mario 28/30")
    (r,) = classify(root, load_register(reg))
    assert r["esito"] == "NESSUN_DATO_PERSONALE" and r["scheda"] is None
    assert [p["scheda"] for p in r["proposte"]] == ["T-PER-02"]


def test_personal_document_without_matching_record_is_missing_record(tmp_path):
    reg = tmp_path / "registro.csv"
    reg.write_text("Codice;Percorsi dichiarati;Parole chiave;Tipologie documentali tipiche\n"
                   "T-PER-07;Personale/Permessi;congedo, legge 104;Istanza\n", encoding="utf-8")
    root = tmp_path / "share"
    (root / "Ambiente").mkdir(parents=True)
    (root / "Ambiente" / "esposto.txt").write_text("Esposto per rumori, C.F. BLDSLV66A68E625M, in congedo")
    (r,) = classify(root, load_register(reg))
    assert r["esito"] == "SCHEDA_MANCANTE" and r["scheda"] is None
    # la scheda più vicina resta tra le proposte, per il controllo dell'RPD
    assert [p["scheda"] for p in r["proposte"]] == ["T-PER-07"]


def test_document_outside_declared_folder_is_not_compliant(tmp_path):
    reg = tmp_path / "registro.csv"
    reg.write_text("Codice;Percorsi dichiarati;Parole chiave;Tipologie documentali tipiche;"
                   "Categorie particolari dichiarate\n"
                   "T-PER-07;Personale/Permessi;congedo, legge 104;Istanza;SALUTE\n", encoding="utf-8")
    perm = tmp_path / "permessi.csv"
    perm.write_text("cartella;gruppi_con_accesso\nVarie;GG_TUTTI_DIPENDENTI\n", encoding="utf-8")
    root = tmp_path / "share"
    (root / "Varie").mkdir(parents=True)
    (root / "Varie" / "scan.txt").write_text("C.F. BLDSLV66A68E625M chiede congedo, legge 104")
    (r,) = classify(root, load_register(reg), load_permissions(perm))
    assert r["scheda"] == "T-PER-07" and r["esito"] == "NON_CONFORME"
    assert r["scostamenti"] == ["LUOGO_NON_DICHIARATO", "ACCESSO_ECCESSIVO"]


def test_document_older_than_retention_is_not_compliant(tmp_path):
    reg = tmp_path / "registro.csv"
    reg.write_text("Codice;Percorsi dichiarati;Parole chiave;Tipologie documentali tipiche;Conservazione in anni\n"
                   "T-POL-01;Verbali;verbale, targa;Verbale;5\n", encoding="utf-8")
    root = tmp_path / "share"
    (root / "Verbali").mkdir(parents=True)
    (root / "Verbali" / "verbale_ZTL_20170316_840.txt").write_text("Verbale, targa AB123CD, C.F. BLDSLV66A68E625M")
    (r,) = classify(root, load_register(reg))
    assert r["esito"] == "NON_CONFORME" and r["scostamenti"] == ["CONSERVAZIONE_SCADUTA"]
