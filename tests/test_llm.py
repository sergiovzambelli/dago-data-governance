import pytest

from classifier.llm import OllamaClient, decide

RECORDS = {
    "T-SIS-02": {"codice": "T-SIS-02", "denominazione": "Account e log", "finalita": "Log di sicurezza", "tipologie": "estratto dei log"},
    "T-PER-07": {"codice": "T-PER-07", "denominazione": "Permessi", "finalita": "Permessi del personale", "tipologie": "istanza"},
}


class FakeClient:
    """Risposte fisse al posto del modello: verify per codice, pick unico."""

    def __init__(self, verified=None, pick=None):
        self.verified, self._pick, self.calls = verified or {}, pick, []

    def verify(self, record, text):
        self.calls.append(record["codice"])
        return self.verified.get(record["codice"])

    def pick(self, records, text):
        return self._pick


def test_top_proposal_confirmed_by_model():
    client = FakeClient(verified={"T-PER-07": (True, "istanza di permesso")})
    assert decide(client, RECORDS, [{"scheda": "T-PER-07"}], "testo") == ("T-PER-07", "istanza di permesso")


def test_model_choice_when_top_proposal_rejected():
    client = FakeClient(verified={"T-PER-07": (False, "no"), "T-SIS-02": (True, "log VPN")}, pick="T-SIS-02")
    assert decide(client, RECORDS, [{"scheda": "T-PER-07"}], "testo") == ("T-SIS-02", "log VPN")


def test_missing_record_when_model_confirms_nothing():
    client = FakeClient(verified={"T-PER-07": (False, "altro servizio")}, pick="NESSUNA")
    assert decide(client, RECORDS, [{"scheda": "T-PER-07"}], "testo") == (None, "altro servizio")


def test_model_choice_outside_register_is_ignored():
    client = FakeClient(verified={"T-PER-07": (False, "no")}, pick="T-INVENTATA")
    assert decide(client, RECORDS, [{"scheda": "T-PER-07"}], "testo") == (None, "no")
    assert client.calls == ["T-PER-07"]


def test_unavailable_model_leaves_decision_to_rules():
    # verify restituisce None: server spento o risposta illeggibile
    assert decide(FakeClient(), RECORDS, [{"scheda": "T-PER-07"}], "testo") is None


def test_client_refuses_remote_hosts():
    # nessun contenuto deve uscire dall'ente
    with pytest.raises(ValueError, match="locale"):
        OllamaClient("http://llm.example.com:11434", "qwen3:8b")
    with pytest.raises(ValueError):
        OllamaClient("file:///etc/passwd", "qwen3:8b")


def test_client_without_server_answers_none():
    client = OllamaClient("http://127.0.0.1:9", "qwen3:8b", timeout=2)
    assert client.verify(RECORDS["T-PER-07"], "testo") is None
    assert client.pick(RECORDS, "testo") is None


def test_draft_without_server_answers_none():
    client = OllamaClient("http://127.0.0.1:9", "qwen3:8b", timeout=2)
    assert client.draft(["testo"]) is None
