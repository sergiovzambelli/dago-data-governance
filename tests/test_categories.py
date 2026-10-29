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
])
def test_no_false_alarms_on_ordinary_text(text):
    assert cats(text) == set()


def test_reports_evidence_with_position():
    text = "Nota: invalidità civile riconosciuta"
    (c,) = find_categories(text)
    assert c["categoria"] == "SALUTE"
    assert text[c["inizio"]:c["fine"]] == c["evidenza"] == "invalidità"
