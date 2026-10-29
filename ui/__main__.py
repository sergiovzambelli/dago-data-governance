"""Avvio: python -m ui  (impostazioni da variabili d'ambiente, vedi docs/ui.md)."""
import uvicorn

from ui.app import create_app
from ui.config import Settings

settings = Settings.from_env()
# access_log spento: gli URL della ricerca possono contenere termini sensibili
uvicorn.run(create_app(settings), host=settings.host, port=settings.port, access_log=False)
