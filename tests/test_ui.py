"""Test della UI: richiedono requirements-ui.txt (fastapi, httpx). Senza, vengono saltati."""
import base64
import json
import re

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
     "scheda": "T-PER-07", "esito": "NON_CONFORME", "scostamenti": ["LUOGO_NON_DICHIARATO", "ACCESSO_ECCESSIVO"]},
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


@pytest.fixture
def settings(tmp_path):
    preds = tmp_path / "pred.json"
    preds.write_text(json.dumps(PREDS), encoding="utf-8")
    reg = tmp_path / "registro.csv"
    reg.write_text(REGISTER, encoding="utf-8")
    return Settings(predictions=preds, register=reg, db=tmp_path / "decisioni.sqlite3", ente="Comune di Prova",
                    secret=b"segreto-di-test")


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


def test_document_detail_shows_evidence_and_rules(client):
    html = client.get(doc_url(client, "scansione_0412.pdf")).text
    assert "BLL***********Q" in html and "Codice fiscale" in html
    assert "Luogo non dichiarato" in html and "fileserver/Personale/Permessi" in html  # cartella dichiarata
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


def test_local_mode_notice_only_on_dashboard(client):
    assert "Modalità locale" in client.get("/").text
    assert "Modalità locale" not in client.get("/documenti").text


def test_active_filters_can_be_removed_one_by_one(client):
    html = client.get("/documenti", params={"esito": "CONFORME", "scheda": "T-PER-07"}).text
    assert "Filtri attivi" in html
    assert 'href="/documenti?scheda=T-PER-07"' in html  # togli l'esito, tieni la scheda


def test_file_names_with_html_stay_text(settings):
    evil = [{**PREDS[1], "file": 'fileserver/<img src=x onerror=alert(1)>/a_<b>.txt'}]
    settings.predictions.write_text(json.dumps(evil), encoding="utf-8")
    html = TestClient(create_app(settings)).get("/documenti").text
    assert "<img src=x" not in html and "<b>" not in html and "&lt;img" in html


def test_dashboard_puts_urgent_documents_first(client):
    html = client.get("/").text
    assert "Da guardare subito" in html
    urgent = html[html.index("Da guardare subito"):html.index("Documenti per esito")]
    assert urgent.index("scansione_0412.pdf") < urgent.index("reclamo_117.eml")
    assert re.search(r">\s*1\s*</span>\s*con categorie particolari", html)


def test_document_verdict_says_what_matters(client):
    html = client.get(doc_url(client, "scansione_0412.pdf")).text
    assert "2 problemi da risolvere" in html
    assert "1 dato personale" in html
    assert html.index("2 problemi da risolvere") < html.index("La tua decisione")
