import json
import subprocess
import sys

import pytest

from classifier.scorer import load_labels, score

HEADER = "ID;Percorso;Esito atteso;Scheda attesa;Alternative accettabili;Dati personali;Categorie particolari;Scostamenti attesi"
ROWS = [
    "D01;a.pdf;NON_CONFORME;T-1;T-2;SI;SALUTE, GIUDIZIARI;LUOGO_NON_DICHIARATO, ACCESSO_ECCESSIVO",
    "D02;b.pdf;CONFORME;T-3;;SI;;",
    "D03;c.pdf;SCHEDA_MANCANTE;;;SI;SALUTE;",
    "D04;d.txt;NESSUN_DATO_PERSONALE;;;NO;;",
]


@pytest.fixture
def labels(tmp_path):
    p = tmp_path / "labels.csv"
    # BOM come nei CSV del kit
    p.write_text("﻿" + "\n".join([HEADER, *ROWS]) + "\n", encoding="utf-8")
    return load_labels(p)


def pred(file, esito, schede=(), cats=(), scost=(), entita=0):
    return {
        "file": file,
        "esito": esito,
        "proposte": [{"scheda": s} for s in schede],
        "categorie_particolari": list(cats),
        "scostamenti": list(scost),
        "dati_personali": entita > 0,
        "entita": [{"tipo": "NOME"}] * entita,
    }


def test_load_labels_splits_lists(labels):
    d01 = labels["a.pdf"]
    assert d01["categorie"] == {"SALUTE", "GIUDIZIARI"}
    assert d01["schede_ok"] == {"T-1", "T-2"}
    assert d01["scostamenti"] == {"ACCESSO_ECCESSIVO"} and d01["esito"] == "NON_CONFORME"
    assert labels["d.txt"]["dati_personali"] is False


def test_perfect_predictions_score_100(labels):
    preds = [
        pred("a.pdf", "NON_CONFORME", ["T-2"], ["SALUTE", "GIUDIZIARI"], ["LUOGO_NON_DICHIARATO", "ACCESSO_ECCESSIVO"], 1),
        pred("b.pdf", "CONFORME", ["T-9", "T-3"], entita=1),
        pred("c.pdf", "SCHEDA_MANCANTE", cats=["SALUTE"], entita=1),
        pred("d.txt", "NESSUN_DATO_PERSONALE"),
    ]
    s = score(labels, preds)
    assert s["totale"] == pytest.approx(100)
    assert all(v == pytest.approx(1) for k, v in s["metriche"].items())


def test_missing_and_wrong_predictions(labels):
    preds = [
        # top-3 sbagliato (T-1 al quarto posto), metà categorie, 1 scostamento giusto + 1 falso
        pred("a.pdf", "CONFORME", ["T-5", "T-6", "T-7", "T-1"], ["SALUTE"], ["ACCESSO_ECCESSIVO", "CONSERVAZIONE_SCADUTA"], 1),
        # falso allarme SCHEDA_MANCANTE
        pred("b.pdf", "SCHEDA_MANCANTE", entita=1),
        # c.pdf mancante: conta come errore
        # entità su documento senza dati personali
        pred("d.txt", "NESSUN_DATO_PERSONALE", entita=2),
    ]
    m = score(labels, preds)["metriche"]
    assert m["esito"] == pytest.approx(1 / 4)
    assert m["richiamo_categorie"] == pytest.approx(1 / 3)
    assert m["scheda_top3"] == pytest.approx(0 / 2)
    assert m["f1_scheda_mancante"] == pytest.approx(0)
    # tp=1 fp=1 fn=0 (il luogo atteso in a.pdf non si misura)
    assert m["f1_scostamenti"] == pytest.approx(2 / 3)
    # 3 file predetti con entità, 2 davvero con dati personali
    assert m["precisione_entita"] == pytest.approx(2 / 3)


def test_unlabelled_files_are_ignored_with_warning(labels, capsys):
    # es. sviluppo/LEGGIMI.txt: non ha etichetta, non deve cambiare il punteggio
    base = score(labels, [pred("d.txt", "NESSUN_DATO_PERSONALE")])
    assert score(labels, [pred("d.txt", "NESSUN_DATO_PERSONALE"), pred("z.pdf", "CONFORME", entita=1)]) == base
    assert "1 file senza etichetta" in capsys.readouterr().err


def test_cli_prints_json(labels, tmp_path):
    lab = tmp_path / "labels.csv"
    pr = tmp_path / "pred.json"
    pr.write_text(json.dumps([pred("d.txt", "NESSUN_DATO_PERSONALE")]))
    out = subprocess.run(
        [sys.executable, "-m", "classifier.scorer", str(lab), str(pr)],
        capture_output=True, text=True, check=True,
    ).stdout
    assert json.loads(out)["metriche"]["esito"] == pytest.approx(1 / 4)


def test_location_is_not_measured(tmp_path):
    # il luogo non si misura più (decisione dell'utente): via dalle etichette, e senza altri problemi è conforme
    p = tmp_path / "labels.csv"
    p.write_text("\n".join([HEADER, "D05;e.pdf;NON_CONFORME;T-1;;SI;;LUOGO_NON_DICHIARATO"]) + "\n", encoding="utf-8")
    assert load_labels(p)["e.pdf"]["scostamenti"] == set() and load_labels(p)["e.pdf"]["esito"] == "CONFORME"
