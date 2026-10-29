"""Gestione degli utenti della UI.

Uso: python -m ui.users <file.json> <nome> <rpd|operatore>   (la password viene chiesta senza mostrarla)
"""
import getpass
import json
import sys
from pathlib import Path

from ui.security import ROLES, hash_password

MIN_PASSWORD = 12


def add_user(path, name, role, password):
    if role not in ROLES:
        raise ValueError(f"ruolo non valido: usa {', '.join(ROLES)}")
    if len(password) < MIN_PASSWORD:
        raise ValueError(f"password troppo corta: almeno {MIN_PASSWORD} caratteri")
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"utenti": []}
    data["utenti"] = [u for u in data["utenti"] if u["nome"] != name]
    data["utenti"].append({"nome": name, "ruolo": role, **hash_password(password)})
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    pw = getpass.getpass("Password: ")
    if pw != getpass.getpass("Ripeti la password: "):
        sys.exit("Le password non coincidono.")
    try:
        add_user(Path(sys.argv[1]), sys.argv[2], sys.argv[3], pw)
    except ValueError as e:
        sys.exit(str(e))
    print(f"Utente {sys.argv[2]} ({ROLES[sys.argv[3]]}) salvato in {sys.argv[1]}.")
