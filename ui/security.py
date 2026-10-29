"""Accesso: utenti con password (PBKDF2), ruoli, token anti-CSRF e intestazioni di sicurezza."""
import base64
import hashlib
import hmac
import json
import os
import secrets

ROLES = {"rpd": "RPD", "operatore": "Operatore"}
ITERATIONS = 310_000  # PBKDF2-SHA256, raccomandazione OWASP
LOCAL_USER = {"nome": "operatore locale", "ruolo": "rpd"}
HEADERS = {
    # tutto servito dall'applicazione: niente CDN, niente script inline. Gli stili inline servono al JavaScript di
    # Bootstrap Italia (menu, collassabili) e il suo CSS incorpora un font come data: URI
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; font-src 'self' data:; "
                               "style-src 'self' 'unsafe-inline'; script-src 'self'; "
                               "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    # same-origin e non no-referrer: con no-referrer i browser inviano "Origin: null" nei moduli
    "Referrer-Policy": "same-origin",
    "Cache-Control": "no-store",
}


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return {"salt": salt.hex(), "hash": digest.hex()}


def load_users(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    users = {}
    for u in data.get("utenti", []):
        if u.get("ruolo") not in ROLES or not u.get("nome") or not u.get("salt") or not u.get("hash"):
            raise ValueError(f"utenti: voce non valida ({u.get('nome')!r})")
        users[u["nome"]] = u
    if not users:
        raise ValueError("utenti: nessun utente nel file")
    return users


def check_basic_auth(header, users):
    """Utente dall'intestazione Authorization: Basic, oppure None."""
    if not header or not header.startswith("Basic "):
        return None
    try:
        name, _, password = base64.b64decode(header[6:], validate=True).decode("utf-8").partition(":")
    except (ValueError, UnicodeDecodeError):
        return None
    user = users.get(name)
    # stesso tempo di calcolo anche per utenti inesistenti
    salt = bytes.fromhex(user["salt"]) if user else b"\0" * 16
    expected = user["hash"] if user else "0" * 64
    ok = hmac.compare_digest(hash_password(password, salt)["hash"], expected)
    return {"nome": name, "ruolo": user["ruolo"]} if user and ok else None


class Csrf:
    def __init__(self, secret=None):
        self.secret = secret or os.urandom(32)

    def token(self, user):
        return hmac.new(self.secret, user["nome"].encode("utf-8"), hashlib.sha256).hexdigest()

    def valid(self, user, token):
        return bool(token) and hmac.compare_digest(self.token(user), token)

    def _mac(self, user, payload):
        return hmac.new(self.secret, b"analisi:" + user["nome"].encode("utf-8") + b":" + payload,
                        hashlib.sha256).hexdigest()

    def sign(self, user, data):
        """Dati che tornano dal browser senza poter essere cambiati (es. l'analisi di un file caricato)."""
        payload = base64.urlsafe_b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        return payload.decode() + "." + self._mac(user, payload)

    def unsign(self, user, signed):
        """I dati firmati, oppure None se manomessi, di un altro utente o firmati prima di un riavvio."""
        payload, _, mac = (signed if isinstance(signed, str) else "").encode().rpartition(b".")
        if not payload or not hmac.compare_digest(self._mac(user, payload).encode(), mac):
            return None
        return json.loads(base64.urlsafe_b64decode(payload))
