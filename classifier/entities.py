"""Trova i dati personali con regole: codice fiscale e IBAN (con verifica del controllo), email, telefono,
nascita, nome dopo Sig./Sig.ra, indirizzo IP, matricola."""
import re

# omocodia: le cifre possono essere sostituite da lettere LMNPQRSTUV
_D = "[0-9LMNPQRSTUV]"
CF_RE = re.compile(rf"\b[A-Z]{{6}}{_D}{{2}}[A-EHLMPRST]{_D}{{2}}[A-Z]{_D}{{3}}[A-Z]\b")
IBAN_RE = re.compile(r"\bIT\d{2}(?: ?[A-Z0-9]){23}\b")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
BIRTH_RE = re.compile(r"\bnat[oaie]\b[^\n]{0,60}?\b(?:il|in data)\s*\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}", re.I)
# shortcut: solo i nomi preceduti da Sig./Sig.ra; gli altri nomi richiedono un modello (spaCy)
NAME_RE = re.compile(r"\b(?:Sig\.(?:ra)?|[Ss]ignor[a]?)\s+[A-Z][a-zàèéìòù']+(?: [A-Z][a-zàèéìòù']+)?")
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
MATRICOLA_RE = re.compile(r"\bmatricola\W{0,5}(?:n\.\s*)?\d+", re.I)
PHONE_RE = re.compile(r"(?<![\w/])(?:\+39[ .]?)?[03]\d{1,3}(?:[ .-]?\d{2,4}){1,3}(?![\w/])")

_CF_ODD = dict(zip("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                   [1, 0, 5, 7, 9, 13, 15, 17, 19, 21, 1, 0, 5, 7, 9, 13, 15, 17, 19, 21,
                    2, 4, 18, 20, 11, 3, 6, 8, 12, 14, 16, 10, 22, 25, 24, 23]))


def _cf_ok(cf):
    total = sum(_CF_ODD[c] if i % 2 == 0 else (int(c) if c.isdigit() else ord(c) - 65)
                for i, c in enumerate(cf[:15]))
    return chr(65 + total % 26) == cf[15]


def _iban_ok(iban):
    iban = iban.replace(" ", "")
    return int("".join(str(int(c, 36)) for c in iban[4:] + iban[:4])) % 97 == 1


def _phone_ok(phone):
    digits = re.sub(r"\D", "", phone.removeprefix("+39"))
    return (digits[0] == "3" and len(digits) == 10) or (digits[0] == "0" and 6 <= len(digits) <= 11)


def _ip_ok(ip):
    return all(int(part) <= 255 for part in ip.split("."))


def _mask(value):
    return value[:3] + "*" * (len(value) - 4) + value[-1]


# ordine: prima i tipi con controllo, così le loro cifre non diventano telefoni
RULES = [
    ("CODICE_FISCALE", CF_RE, _cf_ok, 0.99),
    ("IBAN", IBAN_RE, _iban_ok, 0.99),
    ("EMAIL", EMAIL_RE, lambda _: True, 0.95),
    ("INDIRIZZO_IP", IP_RE, _ip_ok, 0.9),
    ("DATA_NASCITA", BIRTH_RE, lambda _: True, 0.9),
    ("NOME", NAME_RE, lambda _: True, 0.85),
    ("MATRICOLA", MATRICOLA_RE, lambda _: True, 0.9),
    ("TELEFONO", PHONE_RE, _phone_ok, 0.8),
]


def find_entities(text):
    found = []
    for tipo, regex, valid, conf in RULES:
        for m in regex.finditer(text):
            overlaps = any(m.start() < e["fine"] and e["inizio"] < m.end() for e in found)
            if valid(m.group()) and not overlaps:
                found.append({"tipo": tipo, "valore_mascherato": _mask(m.group()),
                              "inizio": m.start(), "fine": m.end(), "confidenza": conf})
    return sorted(found, key=lambda e: e["inizio"])
