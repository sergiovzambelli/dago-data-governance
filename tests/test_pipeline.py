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
    # baseline: classe più frequente nel dataset di sviluppo, nessuna evidenza
    assert a["esito"] == "CONFORME"
    assert a["entita"] == [] and a["proposte"] == [] and a["scostamenti"] == []


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
