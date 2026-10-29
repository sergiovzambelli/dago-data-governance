from classifier.drafts import REGISTER_COLUMNS, build_drafts, group_key


def pred(file, esito="SCHEDA_MANCANTE", categorie=(), proposte=("T-APP-01",)):
    return {"file": file, "esito": esito, "categorie_particolari": list(categorie),
            "proposte": [{"scheda": s} for s in proposte]}


PREDS = [
    pred("fileserver/SUAP/Pratiche/SCIA_vicinato_20260124_202.pdf", categorie=["GIUDIZIARI"]),
    pred("fileserver/SUAP/Pratiche/SCIA_vicinato_20260304_236.docx"),
    pred("fileserver/Condivisa/SCIA_vicinato_20260701_354.docx"),
    pred("fileserver/Sociale/Casa/domanda_ERP_Rinaldi.docx", categorie=["SALUTE"], proposte=()),
    pred("fileserver/SUAP/Pratiche/altro.pdf", esito="CONFORME"),
]
TEXTS = {p["file"]: "Segnalazione certificata di inizio attività per esercizio di vicinato. Il sottoscritto Mario "
                    "Rossi dichiara di non avere condanne penali." for p in PREDS}
PERMISSIONS = [("fileserver/SUAP", {"GG_SUAP"}), ("fileserver/Condivisa", {"GG_TUTTI_DIPENDENTI"})]


class FakeLLM:
    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def draft(self, texts):
        self.calls.append(texts)
        return self.answer


def test_group_key_drops_dates_numbers_and_names():
    assert group_key("fileserver/SUAP/Pratiche/SCIA_vicinato_20260124_202.pdf") == "scia_vicinato"
    # i cognomi non devono finire nella bozza
    assert group_key("fileserver/Sociale/Casa/domanda_ERP_Rinaldi.docx") == "domanda_erp"
    assert group_key("fileserver/Ambiente/Segnalazioni/esposto_rumori_Via_Grande.eml") == "esposto_rumori"
    assert group_key("fileserver/Condivisa/scansioni/scan_20260302_0113.pdf") == "scan"


def test_one_draft_per_kind_of_document_across_folders():
    drafts = build_drafts(PREDS, TEXTS, PERMISSIONS)
    assert [d["codice"] for d in drafts] == ["NUOVA-DOMANDA-ERP", "NUOVA-SCIA-VICINATO"]
    scia = drafts[1]
    assert len(scia["documenti"]) == 3
    f = scia["campi"]
    assert set(f) == set(REGISTER_COLUMNS)
    # la cartella prevalente, non quella dove il documento è finito per errore
    assert f["Percorsi dichiarati"] == "fileserver/SUAP/Pratiche"
    assert f["Gruppo di accesso"] == "GG_SUAP"
    assert f["Categorie particolari dichiarate"] == "GIUDIZIARI"
    assert f["Diffusione"] == "NO"
    assert drafts[0]["campi"]["Categorie particolari dichiarate"] == "SALUTE"


def test_without_model_descriptive_fields_are_left_to_the_rpd():
    (draft,) = build_drafts(PREDS[:1], TEXTS, PERMISSIONS)
    assert draft["modello"] is False
    assert draft["campi"]["Denominazione"] == "" and draft["campi"]["Finalità"] == ""
    assert draft["campi"]["Tipologie documentali tipiche"] == "scia vicinato"
    assert {"Denominazione", "Finalità", "Base giuridica", "Fonti normative"} <= set(draft["da_verificare"])


def test_model_answer_is_validated():
    llm = FakeLLM({"denominazione": "SCIA per esercizi di vicinato", "finalita": "Controllo delle SCIA",
                   "interessati": "Titolari di esercizi commerciali", "categorie_dati": "Anagrafici, giudiziari",
                   "tipologie": "SCIA, dichiarazione sostitutiva",
                   # una parola chiave inventata (non compare nei documenti) va scartata
                   "parole_chiave": ["vicinato", "condanne penali", "astronave"],
                   "base_giuridica": "z"})
    (draft,) = build_drafts(PREDS[:1], TEXTS, PERMISSIONS, llm)
    f = draft["campi"]
    assert draft["modello"] is True
    assert f["Denominazione"] == "SCIA per esercizi di vicinato"
    assert f["Parole chiave"] == "vicinato, condanne penali"
    # base giuridica fuori dall'elenco chiuso: resta da scegliere all'RPD
    assert f["Base giuridica"] == "" and "Base giuridica" in draft["da_verificare"]
    assert "Denominazione" not in draft["da_verificare"]
    assert llm.calls == [[TEXTS[PREDS[0]["file"]]]]


def test_model_fields_with_personal_data_are_dropped():
    llm = FakeLLM({"denominazione": "Pratica di CSMPRZ97B66G702K", "finalita": "x" * 2000,
                   "parole_chiave": "non è un elenco", "base_giuridica": "e"})
    (draft,) = build_drafts(PREDS[:1], TEXTS, PERMISSIONS, llm)
    f = draft["campi"]
    assert f["Denominazione"] == "" and "Denominazione" in draft["da_verificare"]
    assert len(f["Finalità"]) <= 500
    assert f["Parole chiave"] == "scia vicinato"
    assert f["Base giuridica"].startswith("Art. 6, par. 1, lett. e)")
    assert "Base giuridica" in draft["da_verificare"]


def test_names_from_the_documents_are_dropped():
    # find_entities non riconosce i nomi senza "Sig.": il modello li copia volentieri negli interessati
    llm = FakeLLM({"denominazione": "SCIA del Comune di Livorno", "interessati": "Mario Rossi, titolare",
                   "base_giuridica": "e"})
    (draft,) = build_drafts(PREDS[:1], TEXTS, PERMISSIONS, llm)
    assert draft["campi"]["Interessati"] == "" and "Interessati" in draft["da_verificare"]
    assert draft["campi"]["Denominazione"] == "SCIA del Comune di Livorno"


def test_unavailable_model_gives_skeleton():
    (draft,) = build_drafts(PREDS[:1], TEXTS, PERMISSIONS, FakeLLM(None))
    assert draft["modello"] is False and draft["campi"]["Denominazione"] == ""


def test_columns_match_the_register_and_the_ui():
    # le schede approvate si incollano nel registro: stesse colonne, stesso ordine
    import ui.data
    header = open("data/Kit_team_hackathon_sfida_5/Registro_trattamenti.csv", encoding="utf-8-sig").readline()
    assert tuple(header.strip().split(";")) == REGISTER_COLUMNS == ui.data.REGISTER_COLUMNS
