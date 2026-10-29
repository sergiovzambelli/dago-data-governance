import pytest

from classifier.categories import find_categories


def cats(text):
    return {c["categoria"] for c in find_categories(text)}


@pytest.mark.parametrize("text, expected", [
    ("presenza nel nucleo di un componente con invalidità al 100%", {"SALUTE"}),
    ("spese per un intervento di cardiochirurgia e il successivo periodo di malattia", {"SALUTE"}),
    ("Soffro di ipertensione e il mio medico mi ha raccomandato", {"SALUTE"}),
    ("procedimento penale per il reato di cui all'art. 640 c.p.", {"GIUDIZIARI"}),
    ("dal certificato del casellario giudiziale risulta", {"GIUDIZIARI"}),
    ("possesso dei requisiti morali e l'assenza di condanne ostative", {"GIUDIZIARI"}),
    ("sepoltura secondo il rito islamico", {"RELIGIOSE"}),
    ("menu senza carne per motivi religiosi (induismo)", {"RELIGIOSE"}),
    ("contributo associativo a favore dell'organizzazione sindacale FP CGIL", {"SINDACALE"}),
    ("Il defunto era iscritto all'associazione per la cremazione di Livorno", {"SINDACALE"}),
    ("seguito dal Servizio per le dipendenze per un percorso di disintossicazione", {"SALUTE"}),
    ("il figlio Gabriele, affetto da distrofia muscolare", {"SALUTE"}),
    ("tempi aggiuntivi in quanto affetta da disturbo specifico dell'apprendimento", {"SALUTE"}),
    ("padre dei minori, è detenuto presso la Casa circondariale", {"GIUDIZIARI"}),
    # dichiarazione sui requisiti penali di gara: dato giudiziario anche se negativa
    ("non sono state pronunciate condanne definitive per i reati di cui all'art. 94 D.Lgs. 36/2023", {"GIUDIZIARI"}),
    # la parola va a capo nel PDF
    ("era iscritto all'associazione per la\ncremazione", {"SINDACALE"}),
])
def test_detects_category_also_when_only_described(text, expected):
    assert cats(text) == expected


@pytest.mark.parametrize("text", [
    "certificato del medico necroscopo che esclude il sospetto di morte dovuta a reato",
    "rifacimento dei servizi igienico-sanitari al piano terra",
    "Delibera di variazione di bilancio approvata dalla Giunta",
    # negazioni
    "Nel nucleo non sono presenti persone con invalidità.",
    "dichiara di non aver riportato condanne penali e di non avere procedimenti penali in corso",
    # "sindacale" = del sindaco; diritto di farsi assistere non è iscrizione
    "In esecuzione dell'ordinanza sindacale n. 64",
    "con facoltà di farsi assistere da un rappresentante sindacale",
    "Parcheggio Ospedale, 120 posti; protocollo Azienda USL Toscana",
    "Richiesta di copia del rapporto all'ufficio Infortunistica",
    # casella non spuntata di un modulo: è un'opzione, non un fatto
    "☐ iscrizione ad associazione per la cremazione  ☐ dichiarazione dei familiari",
])
def test_no_false_alarms_on_ordinary_text(text):
    assert cats(text) == set()


def test_reports_evidence_with_position():
    text = "Nota: invalidità civile riconosciuta"
    (c,) = find_categories(text)
    assert c["categoria"] == "SALUTE"
    assert text[c["inizio"]:c["fine"]] == c["evidenza"] == "invalidità"


@pytest.mark.parametrize("text, expected", [
    # radici: non solo il sostantivo
    ("il figlio è invalido civile", {"SALUTE"}),
    ("assistenza al coniuge disabile", {"SALUTE"}),
    ("titolare di indennità di accompagnamento", {"SALUTE"}),
    ("in cura presso il reparto di oncologia", {"SALUTE"}),
    ("affetta da demenza di tipo Alzheimer", {"SALUTE"}),
    ("seguito dal Centro di salute mentale", {"SALUTE"}),
    ("ospite di una RSA dal 2024", {"SALUTE"}),
    ("chiede l'esenzione ticket per reddito", {"SALUTE"}),
    ("l'imputato è sottoposto a misura cautelare", {"GIUDIZIARI"}),
    ("ammesso alla messa alla prova", {"GIUDIZIARI"}),
    ("non si avvale dell'insegnamento della religione cattolica", {"RELIGIOSE"}),
    ("aderente ai testimoni di Geova, rifiuta trasfusioni", {"RELIGIOSE"}),
    ("chiede permessi sindacali per il 3 marzo", {"SINDACALE"}),
    # categorie art. 9 non presenti nelle etichette del kit
    ("costituzione di unione civile tra le parti", {"ORIENTAMENTO_SESSUALE"}),
    ("famiglia appartenente alla comunità rom", {"ORIGINE_ETNICA"}),
    ("iscritto al partito dal 2010", {"POLITICHE"}),
    ("acquisizione delle impronte digitali", {"BIOMETRICI"}),
    ("esito del test genetico", {"GENETICI"}),
])
def test_extended_dictionaries(text, expected):
    assert cats(text) == expected


@pytest.mark.parametrize("text", [
    "Modulo SI-07 Ticket n. 2026-1844",
    "id_parcheggio;posti_totali;posti_disabili",
    "Il treno è partito in ritardo; CD-ROM allegato; autista dello scuolabus",
])
def test_extended_dictionaries_no_false_alarms(text):
    assert cats(text) == set()


def _kit_documents_without_personal_data():
    import csv
    from pathlib import Path
    from classifier.extract import extract_text
    kit = Path("data/Kit_team_hackathon_sfida_5")
    with open(kit / "Etichette_sviluppo.csv", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f, delimiter=";") if r["Dati personali"] == "NO"]
    return [(r["Percorso"], extract_text(kit / "sviluppo" / r["Percorso"])) for r in rows]


@pytest.mark.parametrize("path, text", _kit_documents_without_personal_data())
def test_no_category_in_kit_documents_without_personal_data(path, text):
    assert cats(text) == set(), path
