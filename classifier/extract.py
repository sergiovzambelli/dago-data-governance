"""Estrae il testo da un file. Formati: PDF con testo, DOCX, XLSX, CSV, TXT (markitdown), ODT, EML con allegati;
OCR in italiano (tesseract, ocrmypdf) per PDF scansionati e immagini.

Uso: python -m classifier.extract <file>
"""
import email
import email.policy
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from defusedxml import ElementTree as ET
from markitdown import MarkItDown

MAX_ODT_XML = 50 * 1024 * 1024  # contro gli zip bomb
MAX_EML_DEPTH = 3  # email allegate dentro email
OCR_TIMEOUT = 300  # secondi per file
IMAGES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

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


def _ocr(path):
    # percorso assoluto: un nome che inizia con "-" non diventa un'opzione del comando
    src = str(path.resolve())
    run = dict(check=True, capture_output=True, text=True, timeout=OCR_TIMEOUT)
    if path.suffix.lower() in IMAGES:
        return subprocess.run(["tesseract", src, "stdout", "-l", "ita"], **run).stdout
    with tempfile.TemporaryDirectory() as tmp:
        side = Path(tmp) / "testo.txt"
        subprocess.run(["ocrmypdf", "-q", "-l", "ita", "--skip-text", "--sidecar", str(side),
                        src, str(Path(tmp) / "out.pdf")], **run)
        return side.read_text(encoding="utf-8")


def extract_text(path, depth=0):
    path = Path(path)
    try:
        if path.suffix.lower() == ".odt":
            return _odt_text(path)
        if path.suffix.lower() == ".eml":
            return _eml_text(path, depth)
        if path.suffix.lower() in IMAGES:
            return _ocr(path)
        text = _md.convert(str(path)).text_content
        # PDF scansionato: nessuno strato di testo
        if path.suffix.lower() == ".pdf" and not text.strip():
            return _ocr(path)
        return text
    # shortcut: un file illeggibile diventa testo vuoto senza dire perché; aggiungere lo stato di estrazione quando serve in UI
    except Exception:
        return ""


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(extract_text(sys.argv[1]))
