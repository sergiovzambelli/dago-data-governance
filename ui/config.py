"""Impostazioni della UI, da variabili d'ambiente con valori predefiniti per il kit."""
import os
from dataclasses import dataclass
from pathlib import Path

KIT = Path("data/Kit_team_hackathon_sfida_5")
LOOPBACK = {"127.0.0.1", "localhost", "::1"}


@dataclass
class Settings:
    predictions: Path = Path("data/pred_sviluppo.json")
    register: Path | None = KIT / "Registro_trattamenti.csv"
    # bozze di nuove schede (make drafts); se il file manca la pagina spiega come crearlo
    drafts: Path = Path("data/bozze_sviluppo.json")
    db: Path = Path("ui/var/decisioni.sqlite3")
    ente: str = "Comune"
    host: str = "127.0.0.1"
    port: int = 8000
    # file JSON degli utenti (python -m ui.users); senza, la UI accetta solo connessioni dalla stessa macchina
    users_file: Path | None = None
    # chiave per i token anti-CSRF; senza, ne viene generata una a ogni avvio
    secret: bytes | None = None

    @classmethod
    def from_env(cls):
        env = os.environ.get
        register = env("UI_REGISTRO", str(cls.register))
        users = env("UI_UTENTI")
        secret = env("UI_SEGRETO")
        return cls(predictions=Path(env("UI_PREDIZIONI", str(cls.predictions))),
                   register=Path(register) if register else None,
                   drafts=Path(env("UI_BOZZE", str(cls.drafts))),
                   db=Path(env("UI_DB", str(cls.db))),
                   ente=env("UI_ENTE", cls.ente),
                   host=env("UI_HOST", cls.host),
                   port=int(env("UI_PORTA", str(cls.port))),
                   users_file=Path(users) if users else None,
                   secret=secret.encode() if secret else None)
