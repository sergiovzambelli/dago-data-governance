"""Registro delle decisioni dell'RPD (SQLite): solo aggiunte, nessuna modifica o cancellazione."""
import json
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisioni (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quando TEXT NOT NULL,
    utente TEXT NOT NULL,
    documento TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    azione TEXT NOT NULL CHECK (azione IN ('CONFERMA', 'CORREZIONE')),
    esito TEXT NOT NULL,
    scheda TEXT NOT NULL,
    nota TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS decisioni_no_update BEFORE UPDATE ON decisioni
BEGIN SELECT RAISE(ABORT, 'registro in sola aggiunta'); END;
CREATE TRIGGER IF NOT EXISTS decisioni_no_delete BEFORE DELETE ON decisioni
BEGIN SELECT RAISE(ABORT, 'registro in sola aggiunta'); END;
CREATE TABLE IF NOT EXISTS bozze (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quando TEXT NOT NULL,
    utente TEXT NOT NULL,
    bozza TEXT NOT NULL,
    azione TEXT NOT NULL CHECK (azione IN ('APPROVA', 'SCARTA')),
    campi TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS bozze_no_update BEFORE UPDATE ON bozze
BEGIN SELECT RAISE(ABORT, 'registro in sola aggiunta'); END;
CREATE TRIGGER IF NOT EXISTS bozze_no_delete BEFORE DELETE ON bozze
BEGIN SELECT RAISE(ABORT, 'registro in sola aggiunta'); END;
"""
FIELDS = ("id", "quando", "utente", "documento", "sha256", "azione", "esito", "scheda", "nota")


class DecisionLog:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with self._db() as db:
            db.executescript(SCHEMA)

    def _db(self):
        return sqlite3.connect(self.path)

    def add(self, user, doc, action, esito, scheda, note):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._db() as db:
            db.execute("INSERT INTO decisioni (quando, utente, documento, sha256, azione, esito, scheda, nota) "
                       "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (now, user, doc["file"], doc["sha256"], action, esito, scheda, note))

    def add_draft(self, user, draft_id, action, fields):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._db() as db:
            db.execute("INSERT INTO bozze (quando, utente, bozza, azione, campi) VALUES (?, ?, ?, ?, ?)",
                       (now, user, draft_id, action, json.dumps(fields, ensure_ascii=False)))

    def drafts(self):
        """Ultima decisione per bozza: una nuova decisione prevale sulla precedente."""
        with self._db() as db:
            rows = db.execute("SELECT quando, utente, bozza, azione, campi FROM bozze ORDER BY id").fetchall()
        return {b: {"quando": q, "utente": u, "azione": a, "campi": json.loads(c)} for q, u, b, a, c in rows}

    def all(self):
        with self._db() as db:
            rows = db.execute(f"SELECT {', '.join(FIELDS)} FROM decisioni ORDER BY id DESC").fetchall()
        return [dict(zip(FIELDS, r)) for r in rows]

    def latest(self):
        """Ultima decisione per documento. Vale solo se il file non è cambiato (stessa impronta SHA-256)."""
        out = {}
        for d in reversed(self.all()):
            out[(d["documento"], d["sha256"])] = d
        return out
