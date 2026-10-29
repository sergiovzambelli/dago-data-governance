"""Estrae il testo da un file. Formati: PDF con testo, DOCX, XLSX, CSV, TXT (markitdown), ODT ed EML con allegati.

Uso: python -m classifier.extract <file>
"""
import email
import email.policy
import sys
import tempfile
import zipfile
from pathlib import Path

from defusedxml import ElementTree as ET
from markitdown import MarkItDown

MAX_ODT_XML = 50 * 1024 * 1024  # contro gli zip bomb
MAX_EML_DEPTH = 3  # email allegate dentro email

_md = MarkItDown()


def _odt_text(path):
    with zipfile.ZipFile(path) as z:
        if z.getinfo("content.xml").file_size > MAX_ODT_XML:
            return ""
        return " ".join(ET.fromstring(z.read("content.xml")).itertext())


def _eml_text(path, depth):
    msg = email.message_from_bytes(path.read_bytes(), policy=email.policy.default)
    parts = [f"{h}: {msg[h]}" for h in ("From", "To", "Cc", "Subject", "Date") if msg[h]]
    body = msg.get_body(preferencelist=("plain", "html"))
    if body:
        parts.append(body.get_content())
    if depth < MAX_EML_DEPTH:
        for att in msg.iter_attachments():
            # dal nome dell'allegato si usa solo l'estensione: il nome non decide il percorso
            suffix = Path(att.get_filename() or "").suffix[:10]
            with tempfile.TemporaryDirectory() as tmp:
                f = Path(tmp) / f"allegato{suffix}"
                f.write_bytes(att.get_payload(decode=True) or b"")
                parts.append(extract_text(f, depth + 1))
    return "\n".join(parts)


def extract_text(path, depth=0):
    path = Path(path)
    try:
        if path.suffix.lower() == ".odt":
            return _odt_text(path)
        if path.suffix.lower() == ".eml":
            return _eml_text(path, depth)
        return _md.convert(str(path)).text_content
    # shortcut: un file illeggibile diventa testo vuoto senza dire perché; aggiungere lo stato di estrazione quando serve in UI
    except Exception:
        return ""


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(extract_text(sys.argv[1]))
