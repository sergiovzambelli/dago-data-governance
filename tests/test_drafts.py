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
    def __init__(self, answer, same=None):
        self.answer, self.calls, self._same, self.compared = answer, [], same, []

    def same_procedure(self, a, b):
        self.compared.append((a, b))
        return self._same

    def draft(self, texts, similar=()):
        self.calls.append(texts)
        self.similar = [r["Codice"] for r in similar]
        return self.answer


class FakeEmbedder:
    """Vettori fissi: il testo di ogni documento inizia con il nome del suo vettore."""

    def __init__(self, vectors):
        self.vectors = vectors

    def embed(self, texts):
        return [self.vectors[t.split()[0].strip(".")] for t in texts]


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


SEM_PREDS = [
    pred("fileserver/ServiziCimiteriali/Concessioni/concessione_loculo_20250622_965.pdf"),
    pred("fileserver/ServiziCimiteriali/Concessioni/domanda_loculo_20250914_584.pdf"),
    pred("fileserver/Sociale/Casa/domanda_ERP_Rinaldi.docx"),
    pred("fileserver/Sociale/Casa/domanda_ERP_Bianchi.docx"),
    pred("fileserver/Sociale/Casa/domanda_fondo_affitti_2025.docx"),
    pred("fileserver/Condivisa/scansioni/scan_20260302_0115.pdf"),
]
SEM_TEXTS = dict(zip([p["file"] for p in SEM_PREDS],
                     ["loculo concessione trentennale", "loculo2 domanda di loculo", "erp alloggio popolare",
                      "erp alloggio popolare", "affitti contributo", ""]))  # scansione senza testo: resta il nome
# loculo/loculo2 vicinissimi (unione automatica); erp/affitti solo candidati (decide il modello)
VECTORS = {"loculo": [1, 0, 0], "loculo2": [0.95, 0.1, 0], "erp": [0, 1, 0], "affitti": [0, 0.8, 0.5],
           "Concessione": [0.9, 0, 0.1], "Account": [0, 0.1, 1], "Contributi": [0, 0.7, 0.3]}
REGISTER = [
    dict.fromkeys(REGISTER_COLUMNS, "") | {"Codice": "T-CIM-01", "Denominazione": "Concessione cimiteriale",
                                           "Struttura responsabile": "Settore Servizi cimiteriali",
                                           "Ufficio": "Ufficio Polizia mortuaria", "Software": "Gestionale cimiteriale"},
    dict.fromkeys(REGISTER_COLUMNS, "") | {"Codice": "T-SIS-02", "Denominazione": "Account e log"},
    dict.fromkeys(REGISTER_COLUMNS, "") | {"Codice": "T-SOC-01", "Denominazione": "Contributi"},
]


def docs_by_draft(drafts):
    return sorted(sorted(f.rsplit("/", 1)[1] for f in d["documenti"]) for d in drafts)


def test_groups_with_very_similar_content_are_merged_even_with_different_names():
    drafts = build_drafts(SEM_PREDS, SEM_TEXTS, embedder=FakeEmbedder(VECTORS))
    assert docs_by_draft(drafts) == [
        ["concessione_loculo_20250622_965.pdf", "domanda_loculo_20250914_584.pdf"],
        ["domanda_ERP_Bianchi.docx", "domanda_ERP_Rinaldi.docx"], ["domanda_fondo_affitti_2025.docx"],
        ["scan_20260302_0115.pdf"]]


def test_the_model_decides_merges_of_groups_that_are_only_close():
    yes = build_drafts(SEM_PREDS, SEM_TEXTS, llm=FakeLLM(None, same=True), embedder=FakeEmbedder(VECTORS))
    assert ["domanda_ERP_Bianchi.docx", "domanda_ERP_Rinaldi.docx", "domanda_fondo_affitti_2025.docx"] in docs_by_draft(yes)
    # il gruppo più numeroso dà il nome alla bozza
    assert "NUOVA-DOMANDA-ERP" in [d["codice"] for d in yes]
    llm = FakeLLM(None, same=False)
    no = build_drafts(SEM_PREDS, SEM_TEXTS, llm=llm, embedder=FakeEmbedder(VECTORS))
    assert len(no) == 4 and len(llm.compared) == 1


def test_without_embedder_grouping_is_by_file_name():
    assert len(build_drafts(SEM_PREDS, SEM_TEXTS, llm=FakeLLM(None, same=True))) == 5


def test_similar_records_are_retrieved_and_copied_only_if_chosen():
    llm = FakeLLM({"denominazione": "Concessione di loculo", "scheda_simile": "T-CIM-01"})
    (draft,) = build_drafts(SEM_PREDS[:2], SEM_TEXTS, llm=llm, embedder=FakeEmbedder(VECTORS), register=REGISTER)
    # le schede più vicine per contenuto, la più simile per prima
    assert llm.similar[0] == "T-CIM-01" and len(llm.similar) <= 3
    f = draft["campi"]
    assert f["Ufficio"] == "Ufficio Polizia mortuaria" and f["Software"] == "Gestionale cimiteriale"
    assert f["Struttura responsabile"] == "Settore Servizi cimiteriali"
    assert "T-CIM-01" in f["Origine"]
    # copiati da un'altra scheda: restano da verificare
    assert {"Ufficio", "Software", "Struttura responsabile"} <= set(draft["da_verificare"])


def test_similar_record_outside_the_retrieved_ones_is_ignored():
    llm = FakeLLM({"denominazione": "Concessione di loculo", "scheda_simile": "T-XXX-99"})
    (draft,) = build_drafts(SEM_PREDS[:2], SEM_TEXTS, llm=llm, embedder=FakeEmbedder(VECTORS), register=REGISTER)
    assert draft["campi"]["Ufficio"] == "" and draft["campi"]["Origine"] == "Bozza del classificatore"
