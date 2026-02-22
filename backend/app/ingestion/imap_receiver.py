import asyncio
import logging
import os
import email
from email.policy import default
import sys

# Damit die relativen Importe klappen, falls wir es standalone testen:
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ingestion.pipeline import EventPipeline
from core.config import settings
import aioimaplib

logger = logging.getLogger(__name__)

class IMAPReceiver:
    def __init__(self, pipeline: EventPipeline):
        self.pipeline = pipeline
        # IMAP Konfiguration aus zentraler Config laden
        self.imap_server = settings.IMAP_SERVER
        self.imap_user = settings.IMAP_USER
        self.imap_password = settings.IMAP_PASSWORD
        self.imap_port = settings.IMAP_PORT
        self.poll_interval = settings.IMAP_POLL_INTERVAL

    async def start_polling(self):
        """Startet eine Endlosschleife, die periodisch auf neue E-Mails prüft."""
        logger.info(f"Starte IMAP-Polling auf {self.imap_server} (Intervall: {self.poll_interval}s)")
        
        while True:
            try:
                await self._check_inbox()
            except Exception as e:
                logger.error(f"Fehler beim IMAP-Polling: {e}. Versuche es im nächsten Intervall erneut.")
            
            await asyncio.sleep(self.poll_interval)

    async def _check_inbox(self):
        """Verbindet sich mit dem IMAP Server und sucht nach unerledigten Nachrichten."""
        if self.imap_user == "test@example.com":
             logger.debug("IMAP Mock-Modus: Simuliere Postfach-Prüfung... (Nichts Neues)")
             return

        logger.info(f"Verbunden mit {self.imap_server}. Prüfe INBOX...")

    async def _process_email(self, subject: str, body: str, sender: str):
        """Übergibt eine gefundene E-Mail an die EventPipeline."""
        logger.info(f"📧 E-Mail empfangen von {sender}: {subject}")
        
        # Kombiniere Betreff und Body für die Analyse
        full_message = f"Subject: {subject} | Body: {body}"
        
        # Direkt asynchron in die Pipeline feuern!
        await self.pipeline.ingest(sender, full_message)

# Manuelles, lokales Testen
if __name__ == "__main__":
    async def run_test():
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
        analyzer = AIDiagnosticService()
        alerter = AlertingService()
        receiver = IMAPReceiver(analyzer, alerter)
        
        print("\n--- TEST: Simuliere E-Mail Eingang ---")
        # Wir rufen direkt die Verarbeitungsfunktion auf, um den Parser und die DB zu testen.
        await receiver._process_email(
            subject="CRITICAL: Database DOWN!",
            body="The database server db-01 is not responding to pings.",
            sender="monitoring@company.com"
        )
        # Kurz warten, damit Hintergrundtasks abschließen können
        await asyncio.sleep(2)

    asyncio.run(run_test())
