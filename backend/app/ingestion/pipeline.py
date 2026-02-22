import asyncio
import logging
import re
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from diagnosis.analyzer import AIDiagnosticService
from alerting.service import AlertingService
from core.database import SessionLocal
from models.log_model import LogEntry

logger = logging.getLogger(__name__)

# [Aufgabe 1] 1. Ingestion Events normalisieren
class NormalizedEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    severity: str = "UNKNOWN"
    raw_message: str

class EventPipeline:
    def __init__(self, analyzer: AIDiagnosticService, alerter: AlertingService):
        self.analyzer = analyzer
        self.alerter = alerter
        
        # [Aufgabe 3] 3. Warteschlange (asyncio.Queue) einbauen
        self.queue = asyncio.Queue()
        # Halte starke Referenzen auf Background-Tasks, damit sie nicht vom Garbage Collector zerstört werden
        self.bg_tasks = set()
        
        # [Aufgabe 2] 2. Vorfilter (RegEx / Keywords) implementieren
        # Diese Regex sucht nach bekannten Problem-Wörtern. Alles andere wird NICHT an die KI geschickt.
        self.trigger_keywords = re.compile(r"(error|critical|fail|timeout|oom|down|crash)", re.IGNORECASE)

    async def ingest(self, source: str, raw_message: str):
        """1. Mündung der Pipeline: Nimmt rohe Daten an, normalisiert sie und steckt sie in die Warteschlange."""
        event = NormalizedEvent(
            source=source,
            raw_message=raw_message
        )
        await self.queue.put(event)
        logger.debug(f"Event von {source} in Warteschlange gelegt. (Elemente in Queue: {self.queue.qsize()})")

    async def start_worker(self):
        """Der asynchrone Consumer, der die Events geduldig aus der Warteschlange abarbeitet."""
        logger.info("EventPipeline-Worker gestartet. Warte auf neue Logs/E-Mails...")
        while True:
            # Wartet asynchron, bis ein neues Event in die Queue gepusht wird
            event = await self.queue.get()
            try:
                await self._process_event(event)
            except Exception as e:
                logger.error(f"Fehler bei der Event-Verarbeitung: {e}")
            finally:
                self.queue.task_done()

    async def _process_event(self, event: NormalizedEvent):
        """Filterung, KI-Diagnose und Alerting für ein einzelnes Event"""
        
        # Filter: Prüfen ob das Event überhaupt relevant für eine teure Diagnose ist
        if not self.trigger_keywords.search(event.raw_message):
            logger.info(f"[FILTERED] Event von {event.source} wurde als ungefährlich eingestuft. Keine KI notwendig.")
            event.severity = "INFO"
            # Wir speichern es trotzdem asynchron als History in der Datenbank
            task = asyncio.create_task(asyncio.to_thread(self._save_to_db, event, diagnosis_result={}))
            self.bg_tasks.add(task)
            task.add_done_callback(self.bg_tasks.discard)
            return

        logger.info(f"🚨 [TRIGGER] Relevantes Event entdeckt! Starte KI-Analyse für: {event.source}")
        
        # KI-Diagnose aufrufen
        result = await self.analyzer.analyze_log(event.raw_message)
        event.severity = result.get("severity", "UNKNOWN")
        
        # In DB speichern (Fire & Forget Thread)
        task = asyncio.create_task(asyncio.to_thread(self._save_to_db, event, result))
        self.bg_tasks.add(task)
        task.add_done_callback(self.bg_tasks.discard)

        # Alerting triggern
        if event.severity in ["CRITICAL", "HIGH"]:
            logger.warning(f"Problem (Schweregrad {event.severity}) entdeckt! Übergebe an Alerting-Modul...")
            await self.alerter.trigger_escalation(event.raw_message, event.source, result)

    def _save_to_db(self, event: NormalizedEvent, diagnosis_result: dict):
        """Speichert den Log-Eintrag synchron in der Datenbank"""
        db = SessionLocal()
        try:
            log_entry = LogEntry(
                source_ip=event.source,
                message=event.raw_message,
                severity=event.severity,
                diagnosis=diagnosis_result.get("diagnosis", ""),
                recommendation=diagnosis_result.get("recommendation", "")
            )
            db.add(log_entry)
            db.commit()
            logger.debug(f"💾 Log von {event.source} in SQLite gespeichert.")
        except Exception as e:
            logger.error(f"Fehler beim Speichern in der Datenbank: {e}")
        finally:
            db.close()
