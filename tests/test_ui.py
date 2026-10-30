"""Test della UI: richiedono requirements-ui.txt (fastapi, httpx). Senza, vengono saltati."""
import base64
import json
import re
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from ui.app import create_app  # noqa: E402
from ui.config import Settings  # noqa: E402
from ui.security import hash_password  # noqa: E402

PREDS = [
    {"file": "fileserver/Personale/Varie/scansione_0412.pdf", "sha256": "a" * 64, "dati_personali": True,
     "entita": [{"tipo": "CODICE_FISCALE", "valore_mascherato": "BLL***********Q", "inizio": 112, "fine": 128,
                 "confidenza": 0.99}],
     "categorie_particolari": ["SALUTE"], "livello": None,
     "proposte": [{"scheda": "T-PER-07", "punteggio": 5.04, "motivazione": "parole chiave: permesso"}],
     "scheda": "T-PER-07", "esito": "NON_CONFORME", "scostamenti": ["CONSERVAZIONE_SCADUTA", "ACCESSO_ECCESSIVO"]},
    {"file": "fileserver/Personale/Permessi/congedo_Lenzi.docx", "sha256": "b" * 64, "dati_personali": True,
     "entita": [], "categorie_particolari": [], "livello": None,
     "proposte": [{"scheda": "T-PER-07", "punteggio": 8.09, "motivazione": "cartella dichiarata"}],
     "scheda": "T-PER-07", "esito": "CONFORME", "scostamenti": []},
    {"file": "fileserver/URP/Reclami/reclamo_117.eml", "sha256": "c" * 64, "dati_personali": True,
     "entita": [], "categorie_particolari": [], "livello": None,
     "proposte": [{"scheda": "T-POL-02", "punteggio": 3.04, "motivazione": "parole chiave: pronto soccorso"}],
     "scheda": None, "esito": "SCHEDA_MANCANTE", "scostamenti": []},
    {"file": "fileserver/Comunicazione/comunicato.txt", "sha256": "d" * 64, "dati_personali": False,
     "entita": [], "categorie_particolari": [], "livello": None, "proposte": [], "scheda": None,
     "esito": "NESSUN_DATO_PERSONALE", "scostamenti": []},
]
REGISTER = (
    "Codice;Denominazione;Finalità;Categorie particolari dichiarate;Percorsi dichiarati;Conservazione in anni;Diffusione\n"
    "T-PER-07;Permessi, congedi e assenze;Gestione delle richieste di permesso;SALUTE;fileserver/Personale/Permessi;10;NO\n"
    "T-POL-02;Incidenti stradali;Rilevazione degli incidenti;SALUTE, GIUDIZIARI;fileserver/PoliziaLocale/Infortunistica;Illimitata / non calcolabile;NO\n"
)


DRAFT_FIELDS = {"Codice": "NUOVA-RECLAMO", "Origine": "Bozza del classificatore", "Denominazione": "Reclami per cadute",
                "Finalità": "Gestione dei reclami dei cittadini", "Base giuridica": "", "Interessati": "Cittadini",
                "Percorsi dichiarati": "fileserver/URP/Reclami", "Gruppo di accesso": "GG_URP",
                "Categorie particolari dichiarate": "SALUTE", "Diffusione": "NO",
                "Tipologie documentali tipiche": "reclamo", "Parole chiave": "caduta, marciapiede"}
DRAFTS = [{"id": "0123456789abcdef", "codice": "NUOVA-RECLAMO", "documenti": ["fileserver/URP/Reclami/reclamo_117.eml"],
           "campi": DRAFT_FIELDS, "da_verificare": ["Base giuridica", "Fonti normative"], "modello": True}]


@pytest.fixture
def settings(tmp_path):
    preds = tmp_path / "pred.json"
    preds.write_text(json.dumps(PREDS), encoding="utf-8")
    reg = tmp_path / "registro.csv"
    reg.write_text(REGISTER, encoding="utf-8")
    drafts = tmp_path / "bozze.json"
    drafts.write_text(json.dumps(DRAFTS), encoding="utf-8")
    return Settings(predictions=preds, register=reg, db=tmp_path / "decisioni.sqlite3", ente="Comune di Prova",
                    secret=b"segreto-di-test", drafts=drafts)


class Client(TestClient):
    """Toglie i punti di a capo <wbr> dei percorsi: i test confrontano il testo, non l'impaginazione."""

    def request(self, *args, **kwargs):
        r = super().request(*args, **kwargs)
        r._content = r.content.replace(b"<wbr>", b"")
        return r


@pytest.fixture
def client(settings):
    return Client(create_app(settings))


def doc_url(client, name, headers=None):
    html = client.get("/documenti", headers=headers).text
    return re.search(r'href="(/documenti/[0-9a-f]+)"[^>]*>(?:(?!</a>).)*?' + re.escape(name), html, re.S).group(1)


def token(html):
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def test_dashboard_is_italian_and_accessible(client):
    r = client.get("/")
    assert r.status_code == 200
    assert '<html lang="it"' in r.text
    assert "Vai al contenuto principale" in r.text and 'id="main-content"' in r.text
    assert "Comune di Prova" in r.text
    # conteggi per esito, con testo e non solo colore
    assert re.search(r"Non conforme\s*</[^>]+>\s*<[^>]+>\s*1\b", r.text)


def test_security_headers(client):
    h = client.get("/").headers
    assert "default-src 'self'" in h["content-security-policy"]
    assert h["x-frame-options"] == "DENY" and h["x-content-type-options"] == "nosniff"


def test_static_assets_are_local(client):
    html = client.get("/").text
    assert "bootstrap-italia-2.18.3/css/bootstrap-italia.min.css" in html
    assert "http://" not in html.split("<body")[0] and "https://" not in html.split("<body")[0]
    assert client.get("/static/vendor/bootstrap-italia-2.18.3/svg/sprites.svg").status_code == 200


def test_inventory_filters_by_outcome(client):
    html = client.get("/documenti", params={"esito": "SCHEDA_MANCANTE"}).text
    assert "reclamo_117.eml" in html and "congedo_Lenzi.docx" not in html


def test_inventory_rejects_unknown_filter_values(client):
    assert client.get("/documenti", params={"esito": "<script>"}).status_code == 400
    assert client.get("/documenti", params={"settore": "Inesistente"}).status_code == 400


def test_sector_is_the_folder_under_the_server():
    from ui.data import sector
    assert sector("fileserver/Sociale/Casa/domanda.docx") == "Sociale"
    assert sector("srv-archivi/Gare/offerta.pdf") == "Gare"
    assert sector("fileserver/leggimi.txt") == "" and sector("caricato.pdf") == ""


def test_dashboard_counts_documents_by_sector(client):
    html = client.get("/").text
    # Personale: 2 file, 1 conforme, 1 non conforme, 0 senza scheda
    row = re.search(r'<tr>\s*<th[^>]*><a href="/documenti\?settore=Personale">Personale</a></th>(.*?)</tr>', html, re.S)
    assert re.findall(r"<td[^>]*>\s*(\d+)\s*</td>", row.group(1)) == ["2", "1", "1", "0"]


def test_inventory_filters_by_sector(client):
    html = client.get("/documenti", params={"settore": "Personale"}).text
    assert "congedo_Lenzi.docx" in html and "scansione_0412.pdf" in html and "reclamo_117.eml" not in html
    assert "Settore: Personale" in html


def test_document_detail_shows_evidence_and_rules(client):
    html = client.get(doc_url(client, "scansione_0412.pdf")).text
    assert "BLL***********Q" in html and "Codice fiscale" in html
    assert "Accesso eccessivo" in html and "Luogo non dichiarato" not in html  # controllo del luogo tolto
    assert "T-PER-07" in html and "parole chiave: permesso" in html


def test_unknown_document_is_404(client):
    r = client.get("/documenti/0123456789ab")
    assert r.status_code == 404 and "Documento non trovato" in r.text


def test_queue_orders_by_risk_and_skips_no_personal_data(client):
    html = client.get("/coda").text
    assert html.index("scansione_0412.pdf") < html.index("reclamo_117.eml") < html.index("congedo_Lenzi.docx")
    assert "comunicato.txt" not in html


def test_decision_requires_csrf_token(client):
    url = doc_url(client, "reclamo_117.eml")
    r = client.post(url + "/decisione", data={"azione": "CONFERMA"})
    assert r.status_code == 403


def test_decision_from_other_origin_is_refused(client):
    url = doc_url(client, "reclamo_117.eml")
    data = {"csrf": token(client.get(url).text), "azione": "CONFERMA"}
    assert client.post(url + "/decisione", data=data, headers={"Origin": "https://attacco.example"}).status_code == 403
    assert client.post(url + "/decisione", data=data, headers={"Origin": "null"}).status_code == 403
    ok = client.post(url + "/decisione", data=data, headers={"Origin": "http://testserver"}, follow_redirects=False)
    assert ok.status_code == 303


def test_correction_is_logged_and_updates_dashboard(client):
    url = doc_url(client, "reclamo_117.eml")
    page = client.get(url).text
    r = client.post(url + "/decisione", follow_redirects=False,
                    data={"csrf": token(page), "azione": "CORREZIONE", "esito": "CONFORME", "scheda": "T-POL-02",
                          "nota": "Reclamo su incidente: rientra nella scheda"})
    assert r.status_code == 303
    assert "Reclamo su incidente" in client.get(url).text
    log = client.get("/decisioni").text
    assert "reclamo_117.eml" in log and "Correzione" in log and "T-POL-02" in log
    # il documento esce dalla coda e il cruscotto conta l'esito corretto
    assert "reclamo_117.eml" not in client.get("/coda").text
    assert re.search(r"Scheda mancante\s*</[^>]+>\s*<[^>]+>\s*0\b", client.get("/").text)


def test_decision_values_are_validated(client):
    url = doc_url(client, "reclamo_117.eml")
    t = token(client.get(url).text)
    assert client.post(url + "/decisione", data={"csrf": t, "azione": "CORREZIONE", "esito": "FORSE"}).status_code == 400
    assert client.post(url + "/decisione", data={"csrf": t, "azione": "CORREZIONE", "esito": "CONFORME",
                                                  "scheda": "T-INESISTENTE"}).status_code == 400
    # una scheda conforme senza scheda non ha senso
    assert client.post(url + "/decisione", data={"csrf": t, "azione": "CORREZIONE", "esito": "CONFORME",
                                                  "scheda": ""}).status_code == 400


def test_search_by_record_and_path(client):
    assert "congedo_Lenzi.docx" in client.get("/ricerca", params={"q": "T-PER-07"}).text
    html = client.get("/ricerca", params={"q": "reclami"}).text
    assert "reclamo_117.eml" in html and "congedo_Lenzi.docx" not in html


def test_export_applies_decisions_and_blocks_formula_injection(client, settings):
    url = doc_url(client, "reclamo_117.eml")
    client.post(url + "/decisione", data={"csrf": token(client.get(url).text), "azione": "CORREZIONE",
                                          "esito": "CONFORME", "scheda": "T-POL-02", "nota": "=HYPERLINK(\"x\")"})
    data = client.get("/esporta.json").json()
    rec = next(d for d in data if d["file"].endswith("reclamo_117.eml"))
    assert rec["esito"] == "CONFORME" and rec["validato"] is True
    csv_text = client.get("/esporta.csv").text
    assert "'=HYPERLINK" in csv_text and "\n=HYPERLINK" not in csv_text and ";=HYPERLINK" not in csv_text


def _users_file(tmp_path):
    f = tmp_path / "utenti.json"
    f.write_text(json.dumps({"utenti": [{"nome": "rpd", "ruolo": "rpd", **hash_password("pw-rpd-123")},
                                        {"nome": "ufficio", "ruolo": "operatore", **hash_password("pw-op-123")}]}))
    return f


def _auth(user, pw):
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()}


def test_users_file_enforces_login(settings, tmp_path):
    c = Client(create_app(Settings(**{**settings.__dict__, "users_file": _users_file(tmp_path)})))
    assert c.get("/").status_code == 401
    assert c.get("/", headers=_auth("rpd", "sbagliata")).status_code == 401
    assert c.get("/", headers=_auth("rpd", "pw-rpd-123")).status_code == 200


def test_operator_cannot_record_decisions(settings, tmp_path):
    c = Client(create_app(Settings(**{**settings.__dict__, "users_file": _users_file(tmp_path)})))
    url = doc_url(c, "reclamo_117.eml", headers=_auth("ufficio", "pw-op-123"))
    page = c.get(url, headers=_auth("ufficio", "pw-op-123")).text
    assert 'name="azione"' not in page
    r = c.post(url + "/decisione", headers=_auth("ufficio", "pw-op-123"),
               data={"csrf": "x", "azione": "CONFERMA"})
    assert r.status_code == 403


def test_remote_bind_without_users_is_refused(settings):
    with pytest.raises(ValueError, match="utenti"):
        create_app(Settings(**{**settings.__dict__, "host": "0.0.0.0"}))


def test_malformed_predictions_are_rejected(settings):
    settings.predictions.write_text(json.dumps([{"file": 3}]), encoding="utf-8")
    with pytest.raises(ValueError, match="predizioni"):
        create_app(settings)


# --- leggibilità e flusso di validazione ---

def test_tables_separate_file_name_folder_and_record_name(client):
    html = client.get("/documenti").text
    assert '<span class="doc-name">reclamo_117.eml</span>' in html
    assert '<span class="doc-folder">fileserver/URP/Reclami</span>' in html
    assert "Permessi, congedi e assenze" in html  # nome della scheda, non solo il codice


def test_tables_have_labels_for_small_screens(client):
    html = client.get("/documenti").text
    for label in ("Documento", "Esito", "Scheda", "Problemi", "Stato"):
        assert f'data-label="{label}"' in html


def test_queue_explains_priority(client):
    html = client.get("/coda").text
    row = html[html.index("scansione_0412.pdf"):html.index("reclamo_117.eml")]
    assert "Alta" in row and "2 scostamenti" in row and "Salute" in row


def test_document_shows_queue_position_and_next(client):
    html = client.get(doc_url(client, "scansione_0412.pdf")).text
    assert "1 di 3 da validare" in html
    assert re.search(r'href="/documenti/[0-9a-f]+"[^>]*>\s*Prossimo da validare', html)


def test_confirm_and_next_opens_next_document_in_queue(client):
    first = doc_url(client, "scansione_0412.pdf")
    r = client.post(first + "/decisione", follow_redirects=False,
                    data={"csrf": token(client.get(first).text), "azione": "CONFERMA", "poi": "prossimo"})
    assert r.status_code == 303
    assert r.headers["location"].startswith(doc_url(client, "reclamo_117.eml"))
    assert "registrata=1" in r.headers["location"]


def test_correction_lives_in_a_collapsible_panel(client):
    html = client.get(doc_url(client, "reclamo_117.eml")).text
    assert "<details" in html and "Correggi esito o scheda" in html
    assert "Conferma la proposta" in html


def test_decision_log_is_readable(client):
    url = doc_url(client, "reclamo_117.eml")
    client.post(url + "/decisione", data={"csrf": token(client.get(url).text), "azione": "CONFERMA"})
    html = client.get("/decisioni").text
    assert re.search(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}", html)
    assert "Conferma" in html and ">CONFERMA<" not in html


def test_local_mode_has_no_banner(client):
    assert "Modalità locale" not in client.get("/").text


def test_sidebar_can_be_collapsed(client):
    html = client.get("/documenti").text
    assert re.search(r'<button class="side-collapse" type="button" aria-expanded="true" aria-controls="menu-principale" hidden>', html)
    assert "Comprimi il menu" in html
    js = (Path(__file__).parents[1] / "ui/static/ui.js").read_text(encoding="utf-8")
    assert "side-collapsed" in js


def test_active_filters_can_be_removed_one_by_one(client):
    html = client.get("/documenti", params={"esito": "CONFORME", "scheda": "T-PER-07"}).text
    assert "Filtri attivi" in html
    assert 'href="/documenti?scheda=T-PER-07"' in html  # togli l'esito, tieni la scheda


def test_file_names_with_html_stay_text(settings):
    evil = [{**PREDS[1], "file": 'fileserver/<img src=x onerror=alert(1)>/a_<b>.txt'}]
    settings.predictions.write_text(json.dumps(evil), encoding="utf-8")
    html = TestClient(create_app(settings)).get("/documenti").text
    assert "<img src=x" not in html and "<b>" not in html and "&lt;img" in html


DRAFT_URL = "/bozze/0123456789abcdef"


def draft_form(client, **fields):
    data = {"csrf": token(client.get("/bozze").text), "azione": "APPROVA", "denominazione": "Reclami per cadute",
            "finalita": "Gestione dei reclami", "base_giuridica": "Art. 6, par. 1, lett. e) GDPR"}
    return {**data, **fields}


def test_drafts_page_shows_proposal_and_fields_to_check(client):
    html = client.get("/bozze").text
    assert "NUOVA-RECLAMO" in html and "Reclami per cadute" in html and "GG_URP" in html
    assert "Da verificare" in html
    # i documenti che hanno originato la bozza sono collegati
    assert doc_url(client, "reclamo_117.eml") in html
    # ogni campo del modulo ha la sua etichetta
    for name in re.findall(r'<(?:input|textarea)[^>]*\bid="([^"]+)"', html):
        assert f'<label for="{name}"' in html


def test_rpd_approves_draft_with_edits_and_exports_register_row(client):
    r = client.post(DRAFT_URL, data=draft_form(client, denominazione="Reclami per cadute su marciapiedi",
                                                conservazione_anni="5"), follow_redirects=False)
    assert r.status_code == 303
    assert "Approvata" in client.get("/bozze").text
    csv_text = client.get("/bozze/approvate.csv").text
    header, row = csv_text.lstrip("\ufeff").splitlines()[:2]
    assert header.startswith("Codice;Origine;Denominazione;") and header.endswith("Parole chiave")
    assert "NUOVA-RECLAMO;" in row and "Reclami per cadute su marciapiedi" in row and "fileserver/URP/Reclami" in row
    assert ";5;" in row


def test_discarded_draft_is_not_exported(client):
    assert client.post(DRAFT_URL, data=draft_form(client, azione="SCARTA"), follow_redirects=False).status_code == 303
    assert "Scartata" in client.get("/bozze").text
    assert "NUOVA-RECLAMO" not in client.get("/bozze/approvate.csv").text


def test_draft_decision_is_validated(client):
    assert client.post(DRAFT_URL, data={"azione": "APPROVA"}).status_code == 403
    assert client.post(DRAFT_URL, data=draft_form(client), headers={"Origin": "https://attacco.example"}).status_code == 403
    assert client.post("/bozze/ffffffffffffffff", data=draft_form(client)).status_code == 404
    assert client.post(DRAFT_URL, data=draft_form(client, azione="FORSE")).status_code == 400
    # la base giuridica la sceglie l'RPD: senza non si approva
    assert client.post(DRAFT_URL, data=draft_form(client, base_giuridica="")).status_code == 400
    assert client.post(DRAFT_URL, data=draft_form(client, conservazione_anni="dieci")).status_code == 400


def test_draft_export_blocks_formula_injection(client):
    client.post(DRAFT_URL, data=draft_form(client, denominazione="=HYPERLINK(\"x\")"))
    csv_text = client.get("/bozze/approvate.csv").text
    assert "'=HYPERLINK" in csv_text and ";=HYPERLINK" not in csv_text


def test_operator_cannot_decide_drafts(settings, tmp_path):
    c = Client(create_app(Settings(**{**settings.__dict__, "users_file": _users_file(tmp_path)})))
    auth = _auth("ufficio", "pw-op-123")
    assert 'name="azione"' not in c.get("/bozze", headers=auth).text
    assert c.post(DRAFT_URL, headers=auth, data={"csrf": "x", "azione": "SCARTA"}).status_code == 403


def test_without_drafts_file_page_explains_how_to_create_them(settings, tmp_path):
    c = Client(create_app(Settings(**{**settings.__dict__, "drafts": tmp_path / "manca.json"})))
    assert "make drafts" in c.get("/bozze").text


def test_dashboard_puts_urgent_documents_first(client):
    html = client.get("/").text
    assert "I più urgenti" in html
    urgent = html[html.index("I più urgenti"):html.index("Documenti per esito")]
    assert urgent.index("scansione_0412.pdf") < urgent.index("reclamo_117.eml")
    assert re.search(r"Con categorie particolari\s*</span>\s*<[^>]+>\s*1\b", html)


def test_document_verdict_says_what_matters(client):
    html = client.get(doc_url(client, "scansione_0412.pdf")).text
    assert "2 problemi da risolvere" in html
    assert "1 dato personale" in html
    assert html.index("2 problemi da risolvere") < html.index("La tua decisione")


# --- gestione delle schede del registro ---

def new_record(client, **fields):
    data = {"csrf": token(client.get("/schede/nuova").text), "Codice": "T-URP-01", "Denominazione": "Reclami e segnalazioni",
            "Finalità": "Gestione dei reclami dei cittadini", "Base giuridica": "Art. 6, par. 1, lett. e) GDPR",
            "Percorsi dichiarati": "fileserver/URP/Reclami", "Diffusione": "NO", "Consenso": "NO",
            "Conservazione in anni": "5", "Categorie particolari dichiarate": "Nessuna"}
    data.update(fields)
    return client.post("/schede/nuova", data=data, follow_redirects=False)


def test_records_page_lists_current_register(client):
    html = client.get("/schede").text
    assert "T-PER-07" in html and "Permessi, congedi e assenze" in html and "T-POL-02" in html


def test_create_record_appears_everywhere(client):
    r = new_record(client)
    assert r.status_code == 303 and r.headers["location"].startswith("/schede/T-URP-01?")
    assert "Reclami e segnalazioni" in client.get("/schede").text
    assert "Gestione dei reclami dei cittadini" in client.get("/schede/T-URP-01").text
    # subito utilizzabile nelle correzioni e nei filtri
    assert 'value="T-URP-01"' in client.get(doc_url(client, "reclamo_117.eml")).text
    assert client.get("/documenti", params={"scheda": "T-URP-01"}).status_code == 200


def test_edit_record_keeps_history(client, settings):
    page = client.get("/schede/T-PER-07").text
    r = client.post("/schede/T-PER-07", follow_redirects=False,
                    data={"csrf": token(page), "azione": "MODIFICA", "Denominazione": "Permessi e congedi",
                          "Finalità": "Gestione delle richieste di permesso", "Base giuridica": "Art. 6 lett. b",
                          "Percorsi dichiarati": "fileserver/Personale/Permessi", "Diffusione": "NO", "Consenso": "NO",
                          "Conservazione in anni": "10", "Categorie particolari dichiarate": "SALUTE"})
    assert r.status_code == 303
    html = client.get("/schede/T-PER-07").text
    assert "Permessi e congedi" in html and "Modifica" in html and "operatore locale" in html
    assert "Permessi e congedi" in client.get(doc_url(client, "congedo_Lenzi.docx")).text
    assert settings.register.read_text(encoding="utf-8") == REGISTER  # il CSV di partenza non si tocca


def test_archive_and_restore_record(client):
    page = client.get("/schede/T-POL-02").text
    assert client.post("/schede/T-POL-02", data={"csrf": token(page), "azione": "ARCHIVIA"},
                       follow_redirects=False).status_code == 303
    active = client.get("/schede").text
    assert "Archiviate" in active
    url = doc_url(client, "reclamo_117.eml")
    t = token(client.get(url).text)
    assert client.post(url + "/decisione", data={"csrf": t, "azione": "CORREZIONE", "esito": "CONFORME",
                                                 "scheda": "T-POL-02"}).status_code == 400
    page = client.get("/schede/T-POL-02").text
    assert client.post("/schede/T-POL-02", data={"csrf": token(page), "azione": "RIPRISTINA"},
                       follow_redirects=False).status_code == 303
    assert client.post(url + "/decisione", data={"csrf": t, "azione": "CORREZIONE", "esito": "CONFORME",
                                                 "scheda": "T-POL-02"}, follow_redirects=False).status_code == 303


def test_record_values_are_validated(client):
    assert new_record(client, Codice="T-PER-07").status_code == 400          # già esistente
    assert new_record(client, Codice="../x").status_code == 400              # formato
    assert new_record(client, Denominazione="").status_code == 400           # obbligatorio
    assert new_record(client, Diffusione="FORSE").status_code == 400
    assert new_record(client, **{"Conservazione in anni": "dieci"}).status_code == 400
    assert new_record(client, **{"Categorie particolari dichiarate": "<b>"}).status_code == 400
    assert client.get("/schede/..%2Fetc").status_code == 404


def test_records_require_rpd_and_csrf(client, settings, tmp_path):
    assert new_record(client, csrf="sbagliato").status_code == 403
    c = Client(create_app(Settings(**{**settings.__dict__, "users_file": _users_file(tmp_path)})))
    h = _auth("ufficio", "pw-op-123")
    page = c.get("/schede", headers=h).text
    assert "T-PER-07" in page and 'href="/schede/nuova"' not in page
    assert 'name="azione"' not in c.get("/schede/T-PER-07", headers=h).text
    assert c.post("/schede/nuova", headers=h, data={"csrf": "x", "Codice": "T-X-01"}).status_code == 403


def test_register_export_has_all_columns_and_no_formulas(client):
    new_record(client, Codice="T-URP-02", Denominazione="=HYPERLINK(\"x\")")
    text = client.get("/schede/registro.csv").text.lstrip("﻿")
    header, *rows = text.splitlines()
    assert header.startswith("Codice;Origine;Denominazione;") and header.endswith("Parole chiave")
    assert any(r.startswith("T-URP-02;") and "'=HYPERLINK" in r for r in rows)


def test_try_file_shows_each_step_without_saving(client, settings):
    pytest.importorskip("markitdown")
    page = client.get("/prova").text
    assert 'type="file"' in page and "<label" in page
    before = settings.predictions.read_text(encoding="utf-8")
    r = client.post("/prova", data={"csrf": token(page), "cartella": "fileserver/Personale/Permessi"},
                    files={"file": ("congedo.txt", "Richiesta di permesso. C.F. CSMPRZ97B66G702K".encode())})
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert "Richiesta di permesso" in r.text  # testo estratto
    assert "Codice fiscale" in r.text and "CSM************K" in r.text  # entità mascherate
    assert "T-PER-07" in r.text and "Conforme" in r.text  # scheda ed esito
    assert "100% degli indizi" in r.text and "punteggio" not in r.text  # quota leggibile, non il punteggio grezzo
    assert settings.predictions.read_text(encoding="utf-8") == before  # niente salvato


def test_try_file_requires_rpd_csrf_and_a_small_file(client, monkeypatch):
    t = token(client.get("/prova").text)
    assert client.post("/prova", data={"csrf": "x"}, files={"file": ("a.txt", b"x")}).status_code == 403
    assert client.post("/prova", data={"csrf": t}, files={"file": ("", b"")}).status_code == 400
    monkeypatch.setattr("ui.app.MAX_UPLOAD", 10)
    assert client.post("/prova", data={"csrf": t}, files={"file": ("a.txt", b"x" * 11)}).status_code == 400
    r = client.post("/prova", data={"csrf": t, "cartella": "../etc"}, files={"file": ("a.txt", b"x")})
    assert r.status_code == 400


def test_proposals_show_share_of_evidence(client, settings):
    preds = json.loads(settings.predictions.read_text(encoding="utf-8"))
    preds[0]["proposte"] = [{"scheda": "T-PER-07", "punteggio": 3.0, "motivazione": "a"},
                            {"scheda": "T-POL-02", "punteggio": 1.0, "motivazione": "b"}]
    settings.predictions.write_text(json.dumps(preds), encoding="utf-8")
    html = client.get(doc_url(client, "scansione_0412.pdf")).text
    assert "75% degli indizi" in html and "25% degli indizi" in html


@pytest.fixture
def try_client(settings):
    """Registro con parole chiave: servono a evidenziarle e all'abbinamento."""
    pytest.importorskip("markitdown")
    settings.register.write_text(
        "Codice;Denominazione;Finalità;Percorsi dichiarati;Parole chiave;Tipologie documentali tipiche;Diffusione\n"
        "T-PER-07;Permessi;Permessi;fileserver/Personale/Permessi;permesso, congedo;richiesta;NO\n", encoding="utf-8")
    settings.permissions = None
    return Client(create_app(settings))


def upload(client, text, folder):
    page = client.get("/prova").text
    return client.post("/prova", data={"csrf": token(page), "cartella": folder},
                       files={"file": ("richiesta.txt", text.encode())})


def test_try_file_highlights_what_was_found(try_client):
    html = upload(try_client, "Richiesta di permesso per malattia. C.F. CSMPRZ97B66G702K",
                  "fileserver/Personale/Permessi").text
    assert re.search(r'<mark class="hl hl-entita"[^>]*>CSMPRZ97B66G702K</mark>', html)
    assert re.search(r'<mark class="hl hl-chiave"[^>]*>permesso</mark>', html)
    assert re.search(r'<mark class="hl hl-categoria"[^>]*>malattia</mark>', html)
    assert "Usa questa scheda" not in html  # la scheda c'è: niente scelta


def save_choice(client, html, scheda):
    analysis = re.search(r'name="analisi" value="([^"]+)"', html).group(1)
    return client.post("/prova/salva", data={"csrf": token(html), "analisi": analysis, "scheda": scheda},
                       follow_redirects=False)


def test_missing_record_operator_picks_one_and_document_enters_inventory(try_client):
    html = upload(try_client, "Domanda di permesso. C.F. CSMPRZ97B66G702K", "fileserver/Altro").text
    assert "Scheda mancante" in html and "Usa questa scheda" in html and "Nuova scheda" in html
    r = save_choice(try_client, html, "T-PER-07")
    assert r.status_code == 303 and r.headers["location"].startswith("/documenti/")
    doc = try_client.get(r.headers["location"]).text
    assert "fileserver/Altro" in doc and "T-PER-07" in doc and "Conforme" in doc and "Validato" in doc
    assert "Luogo non dichiarato" not in doc
    assert "richiesta.txt" in try_client.get("/documenti").text


def test_missing_record_new_record_is_prefilled(try_client):
    html = upload(try_client, "Domanda di permesso. C.F. CSMPRZ97B66G702K", "fileserver/Altro").text
    r = save_choice(try_client, html, "NUOVA")
    assert r.status_code == 303 and r.headers["location"].startswith("/schede/")
    page = try_client.get(r.headers["location"]).text
    assert "fileserver/Altro" in page and "richiesta" in page  # cartella e tipologia già compilate
    assert "richiesta.txt" in try_client.get("/documenti", params={"esito": "CONFORME"}).text


def test_save_choice_rejects_tampered_analysis(try_client):
    html = upload(try_client, "Domanda di permesso. C.F. CSMPRZ97B66G702K", "fileserver/Altro").text
    html = re.sub(r'(name="analisi" value=")([^"]{5})', r"\1AAAAA", html)
    assert save_choice(try_client, html, "T-PER-07").status_code == 400


DOC_TEXT = "Reclamo: chiedo un permesso per la caduta, malattia. C.F. CSMPRZ97B66G702K"


@pytest.fixture
def doc_settings(settings, tmp_path):
    """Cartella analizzata con il file del reclamo (scheda mancante), come la vede la pipeline."""
    import hashlib
    pytest.importorskip("markitdown")
    root = tmp_path / "analizzata"
    path = root / "fileserver/URP/Reclami/reclamo_117.txt"
    path.parent.mkdir(parents=True)
    path.write_text(DOC_TEXT, encoding="utf-8")
    preds = json.loads(settings.predictions.read_text(encoding="utf-8"))
    preds[2] |= {"file": "fileserver/URP/Reclami/reclamo_117.txt", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    settings.predictions.write_text(json.dumps(preds), encoding="utf-8")
    settings.register.write_text(
        "Codice;Denominazione;Finalità;Percorsi dichiarati;Parole chiave;Tipologie documentali tipiche;Diffusione\n"
        "T-PER-07;Permessi;Permessi;fileserver/Personale/Permessi;permesso, congedo;richiesta;NO\n", encoding="utf-8")
    settings.permissions = None
    settings.documents = root
    return settings


def test_document_page_shows_the_file_like_try_file(doc_settings):
    c = Client(create_app(doc_settings))
    r = c.get(doc_url(c, "reclamo_117.txt"))
    assert r.headers["cache-control"] == "no-store"  # la pagina contiene il testo del documento
    assert "Il file, con ciò che è stato trovato" in r.text
    assert re.search(r'<mark class="hl hl-entita"[^>]*>CSMPRZ97B66G702K</mark>', r.text)
    assert re.search(r'<mark class="hl hl-chiave"[^>]*>permesso</mark>', r.text)
    # scheda mancante: le stesse card di Prova un file
    assert "Usa questa scheda" in r.text and "Nuova scheda" in r.text


def test_document_page_choice_validates_the_document(doc_settings):
    c = Client(create_app(doc_settings))
    url = doc_url(c, "reclamo_117.txt")
    r = save_choice(c, c.get(url).text, "T-PER-07")
    assert r.status_code == 303 and r.headers["location"].startswith(url)
    page = c.get(url).text
    assert "Validato" in page and "T-PER-07" in page and "Conforme" in page
    assert len(re.findall(r"reclamo_117\.txt", c.get("/documenti").text)) >= 1
    assert c.get("/documenti", params={"esito": "SCHEDA_MANCANTE"}).text.count("reclamo_117.txt") == 0


def test_document_page_hides_the_text_from_operators(doc_settings, tmp_path):
    c = Client(create_app(Settings(**{**doc_settings.__dict__, "users_file": _users_file(tmp_path)})))
    auth = _auth("ufficio", "pw-op-123")
    page = c.get(doc_url(c, "reclamo_117.txt", headers=auth), headers=auth).text
    assert "CSMPRZ97B66G702K" not in page and "Usa questa scheda" not in page


def test_document_page_warns_if_the_file_changed_or_is_missing(doc_settings):
    c = Client(create_app(doc_settings))
    url = doc_url(c, "reclamo_117.txt")
    (doc_settings.documents / "fileserver/URP/Reclami/reclamo_117.txt").write_text("altro testo", encoding="utf-8")
    page = c.get(url).text
    assert "è cambiato dopo l'analisi" in page and "Usa questa scheda" not in page
    (doc_settings.documents / "fileserver/URP/Reclami/reclamo_117.txt").unlink()
    assert "File non disponibile" in c.get(url).text


def test_document_page_never_reads_outside_the_analysed_folder(doc_settings, tmp_path):
    (tmp_path / "segreto.txt").write_text("SEGRETO", encoding="utf-8")
    preds = json.loads(doc_settings.predictions.read_text(encoding="utf-8"))
    preds[3]["file"] = "../segreto.txt"
    doc_settings.predictions.write_text(json.dumps(preds), encoding="utf-8")
    c = Client(create_app(doc_settings))
    html = c.get("/documenti").text
    for url in set(re.findall(r'href="(/documenti/[0-9a-f]{16})"', html)):
        assert "SEGRETO" not in c.get(url).text


# --- area di lavoro: menu laterale, coda affiancata, scorciatoie, cruscotto a dati ---

def test_app_shell_has_sidebar_and_no_italia_header(client):
    html = client.get("/documenti").text
    assert '<nav class="sidebar-nav" aria-label="Navigazione principale">' in html
    assert re.search(r'href="/documenti"[^>]*aria-current="page"', html)
    assert "it-header-wrapper" not in html and "it-footer" not in html
    assert "bootstrap-italia.bundle.min.js" not in html  # menu e scorciatoie con ui.js


def test_queued_document_shows_the_queue_beside_it(client):
    html = client.get(doc_url(client, "reclamo_117.eml")).text
    pane = html[html.index('class="queue-pane"'):]
    assert "scansione_0412.pdf" in pane and "congedo_Lenzi.docx" in pane
    assert re.search(r'aria-current="true"[^>]*>(?:(?!</a>).)*reclamo_117\.eml', pane, re.S)


def test_validated_document_has_no_queue_pane(client):
    url = doc_url(client, "congedo_Lenzi.docx")
    client.post(url + "/decisione", data={"csrf": token(client.get(url).text), "azione": "CONFERMA"})
    assert 'class="queue-pane"' not in client.get(url).text


def test_keyboard_shortcuts_are_declared_and_can_be_turned_off(client):
    html = client.get(doc_url(client, "reclamo_117.eml")).text  # secondo della coda
    assert re.search(r'data-key="c"[^>]*>\s*Conferma la proposta e vai al prossimo', html)
    assert re.search(r'<details[^>]*data-key="e"', html)
    assert re.search(r'data-key="j"[^>]*href="/documenti/[0-9a-f]+"|href="/documenti/[0-9a-f]+"[^>]*data-key="j"', html)
    assert re.search(r'data-key="k"[^>]*href="/documenti/[0-9a-f]+"|href="/documenti/[0-9a-f]+"[^>]*data-key="k"', html)
    assert "Scorciatoie da tastiera" in html and "Disattiva le scorciatoie" in html


def test_operator_gets_no_decision_shortcuts(settings, tmp_path):
    c = Client(create_app(Settings(**{**settings.__dict__, "users_file": _users_file(tmp_path)})))
    url = doc_url(c, "reclamo_117.eml", headers=_auth("ufficio", "pw-op-123"))
    assert 'data-key="c"' not in c.get(url, headers=_auth("ufficio", "pw-op-123")).text


def test_dashboard_shows_metrics_and_validation_ring(client):
    html = client.get("/").text
    assert re.search(r'class="metric-label">\s*Da validare\s*</[^>]+>\s*<[^>]+>\s*3\b', html)
    assert re.search(r'role="img" aria-label="Validati 0 su 3"', html)


# --- indicatori a lancetta del grado di conformità ---

def test_document_shows_its_compliance_gauge(client):
    html = client.get(doc_url(client, "scansione_0412.pdf")).text
    assert re.search(r'role="img" aria-label="Grado di conformità \d+ su 100, (alta|media|bassa)', html)
    assert "Conformità" in html


def test_document_without_personal_data_has_no_gauge(client):
    html = client.get(doc_url(client, "comunicato.txt")).text
    assert "Grado di conformità" not in html


def test_dashboard_shows_archive_and_sector_gauges(client):
    html = client.get("/").text
    # archivio: media di 3 documenti con dati personali (non conforme, conforme, senza scheda)
    assert re.search(r'aria-label="Grado di conformità \d+ su 100, \w+ — archivio"', html)
    assert len(re.findall(r'aria-label="Grado di conformità \d+ su 100, \w+ — settore ', html)) >= 2


# --- Prova un file: analisi in background con barra di avanzamento ---

def start(client, text, folder, name="richiesta.txt"):
    page = client.get("/prova").text
    return client.post("/prova/avvia", data={"csrf": token(page), "cartella": folder},
                       files={"file": (name, text.encode())})


def wait_done(client, job, timeout=20):
    import time
    end = time.time() + timeout
    while time.time() < end:
        s = client.get(f"/prova/stato/{job}").json()
        if s["fatto"]:
            return s
        time.sleep(0.05)
    raise AssertionError("analisi non conclusa")


def test_try_file_page_has_an_accessible_progress_bar(try_client):
    html = try_client.get("/prova").text
    assert 'data-progress' in html and 'role="progressbar"' in html and 'aria-live="polite"' in html


def test_background_analysis_reports_phases_and_outcome(try_client):
    r = start(try_client, "Richiesta di permesso. C.F. CSMPRZ97B66G702K", "fileserver/Personale/Permessi")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    job = r.json()["lavoro"]
    s = wait_done(try_client, job)
    assert [f for f in s["fasi"]][0] == "Lettura del file" and len(s["fasi"]) == 5
    assert s["fase"] == len(s["fasi"]) and s["errore"] is None
    assert s["esito"] == "CONFORME" and s["etichetta"] == "Conforme" and s["grado"] == 100
    assert "C.F." not in json.dumps(s)  # lo stato non contiene il testo del documento


def test_background_result_is_shown_once(try_client):
    job = start(try_client, "Richiesta di permesso. C.F. CSMPRZ97B66G702K", "fileserver/Personale/Permessi").json()["lavoro"]
    wait_done(try_client, job)
    page = try_client.get(f"/prova/risultato/{job}")
    # "Richiesta" e "permesso" sono evidenziate come parole chiave (<mark>): si controllano testo e conteggio
    assert page.status_code == 200 and "CSMPRZ97B66G702K" in page.text and "44 caratteri estratti" in page.text
    assert "T-PER-07" in page.text
    assert page.headers["cache-control"] == "no-store"
    assert try_client.get(f"/prova/risultato/{job}").status_code == 404  # testo non conservato


def test_background_analysis_is_protected(try_client, settings, tmp_path):
    t = token(try_client.get("/prova").text)
    assert try_client.post("/prova/avvia", data={"csrf": "x"}, files={"file": ("a.txt", b"x")}).status_code == 403
    assert try_client.post("/prova/avvia", data={"csrf": t, "cartella": "../etc"},
                           files={"file": ("a.txt", b"x")}).status_code == 400
    assert try_client.get("/prova/stato/inesistente").status_code == 404
    # un altro utente non vede lo stato né il risultato
    other = Client(create_app(Settings(**{**settings.__dict__, "users_file": _users_file(tmp_path)})))
    job = start(try_client, "Richiesta di permesso.", "fileserver/Personale/Permessi").json()["lavoro"]
    assert other.get(f"/prova/stato/{job}", headers=_auth("rpd", "pw-rpd-123")).status_code == 404


# --- accessibilità: dichiarazione, link con contesto, riflusso, colori forzati ---

def test_accessibility_statement_page(client):
    html = client.get("/accessibilita").text
    assert "<h1>Dichiarazione di accessibilità</h1>" in html
    assert "WCAG 2.1" in html and "parzialmente conforme" in html and "Segnala un problema" in html
    assert 'href="/accessibilita"' in client.get("/").text  # raggiungibile da ogni pagina


def test_record_counts_say_what_they_count(client):
    html = client.get("/schede").text
    assert re.search(r'>\d+<span class="visually-hidden"> document[oi] con la scheda T-PER-07</span></a>', html)


def test_css_supports_reflow_and_forced_colors():
    css = (Path(__file__).parents[1] / "ui/static/ui.css").read_text(encoding="utf-8")
    assert "@media (forced-colors: active)" in css
    assert re.search(r"\.btn\s*\{[^}]*white-space:\s*normal", css)
    assert re.search(r"\.crumbs \.breadcrumb\s*\{[^}]*flex-wrap:\s*wrap", css)


def test_mobile_menu_makes_page_inert_and_skip_link_opens_it():
    js = (Path(__file__).parents[1] / "ui/static/ui.js").read_text(encoding="utf-8")
    assert ".inert = open" in js and 'a[href="#menu-principale"]' in js


# --- marchio DaGo (docs/brand) ---

def test_pages_carry_the_dago_name_logo_and_favicon(client):
    html = client.get("/").text
    assert "<title>Compliance · DaGo · Comune di Prova</title>" in html
    assert re.search(r'<link rel="icon" href="/static/brand/logo-vaglio.svg" type="image/svg\+xml">', html)
    assert re.search(r'<img class="brand-logo" src="/static/brand/logo-vaglio.svg" alt="" width="\d+" height="\d+">', html)
    assert '<span class="brand-name">DaGo</span>' in html and "Vaglio" not in html and "Cruscotto" not in html and "Patrimonio informativo" in html
    assert client.get("/static/brand/logo-vaglio.svg").status_code == 200


def test_brand_kit_is_kept_in_the_repository():
    brand = Path(__file__).parents[1] / "docs/brand"
    tokens = json.loads((brand / "tokens.json").read_text(encoding="utf-8"))
    assert tokens["name"] == "DaGo"
    css = (Path(__file__).parents[1] / "ui/static/ui.css").read_text(encoding="utf-8").lower()
    # i colori principali del marchio sono quelli usati dall'app
    for name in ("blue-700", "yellow", "side", "ink", "muted", "green", "amber", "red"):
        value = next(t["value"] for t in tokens["color"]["tokens"] if t["name"] == name).lower()
        assert value in css, name
    # palette in asset/palette.jpg: giallo e blu principali, rosso accento
    palette = {t["name"]: t["value"].lower() for t in tokens["color"]["tokens"]}
    assert (palette["blue-700"], palette["yellow"], palette["red"]) == ("#1c4b62", "#e8a519", "#cd3318")


# --- pannello Accessibilità (preferenze dell'utente) ---

OPTIONS = ("contrasto", "leggibile", "spaziatura", "link", "animazioni", "cursore", "guida", "grigi")


def test_accessibility_panel_has_labelled_controls(client):
    html = client.get("/").text
    assert re.search(r'<button[^>]*class="a11y-toggle"[^>]*aria-expanded="false"[^>]*aria-controls="a11y-panel"', html)
    assert 'aria-label="Impostazioni di accessibilità"' in html
    panel = html[html.index('id="a11y-panel"'):]
    assert "<legend" in panel and "Dimensione del testo" in panel
    for opt in OPTIONS:
        m = re.search(r'<input type="checkbox" id="a11y-' + opt + r'" data-a11y="' + opt + '"', panel)
        assert m and f'<label for="a11y-{opt}"' in panel, opt
    for size in ("100", "125", "150"):
        assert f'value="{size}"' in panel
    assert "Ripristina" in panel


def test_preferences_apply_before_the_page_is_drawn(client):
    head = client.get("/").text.split("</head>")[0]
    assert '<script src="/static/a11y-init.js"></script>' in head  # nel head: niente lampeggio


def test_css_defines_every_preference():
    css = (Path(__file__).parents[1] / "ui/static/ui.css").read_text(encoding="utf-8")
    for cls in ("a11y-contrasto", "a11y-leggibile", "a11y-spaziatura", "a11y-link", "a11y-animazioni",
                "a11y-cursore", "a11y-grigi", "a11y-testo-125", "a11y-testo-150"):
        assert "." + cls in css, cls


def test_preferences_are_stored_safely_in_the_browser():
    init = (Path(__file__).parents[1] / "ui/static/a11y-init.js").read_text(encoding="utf-8")
    assert "localStorage" in init and "try" in init and "catch" in init
