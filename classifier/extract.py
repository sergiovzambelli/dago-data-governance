"""Estrae il testo da un file. Formati: PDF con testo, DOCX, XLSX, CSV, TXT, EML (markitdown) e ODT.

Uso: python -m classifier.extract <file>
"""
import sys
import zipfile
from pathlib import Path

from defusedxml import ElementTree as ET
from markitdown import MarkItDown

MAX_ODT_XML = 50 * 1024 * 1024  # contro gli zip bomb

_md = MarkItDown()


def _odt_text(path):
    with zipfile.ZipFile(path) as z:
        if z.getinfo("content.xml").file_size > MAX_ODT_XML:
            return ""
        return " ".join(ET.fromstring(z.read("content.xml")).itertext())


def extract_text(path):
    path = Path(path)
    try:
        if path.suffix.lower() == ".odt":
            return _odt_text(path)
        return _md.convert(str(path)).text_content
    # shortcut: un file illeggibile diventa testo vuoto senza dire perché; aggiungere lo stato di estrazione quando serve in UI
    except Exception:
        return ""


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(extract_text(sys.argv[1]))
