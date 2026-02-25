import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel, Field

from diagnosis.analyzer import AIDiagnosticService
from alerting.service import AlertingService
from core.database import SessionLocal
from models.log_model import LogEntry

logger = logging.getLogger(__name__)

# Zeitfenster für Hash-basierte Deduplizierung (Sekunden)
DEDUP_WINDOW_SECONDS = 60


# [Aufgabe 1] Erweitertes NormalizedEvent-Schema (EPIC 1)
class NormalizedEvent(BaseModel):
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str
    severity: str = "UNKNOWN"
    raw_message: str
    service_name: Optional[str] = None
    tags: Optional[list[str]] = None
    fingerprint: Optional[str] = None  # SHA256(source|message) für Deduplizierung


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

        # In-Memory Dedup-Cache: fingerprint -> timestamp des letzten Eingangs
        self._dedup_cache: dict[str, datetime] = {}

    def _compute_fingerprint(self, source: str, message: str) -> str:
        """SHA256-Fingerprint aus Quelle + normalisierter Nachricht."""
        content = f"{source}|{message.strip()}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def _is_duplicate(self, fingerprint: str) -> bool:
        """Prüft den In-Memory-Cache auf Duplikate innerhalb des Zeitfensters."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=DEDUP_WINDOW_SECONDS)

        # Abgelaufene Einträge bereinigen
        expired = [fp for fp, ts in self._dedup_cache.items() if ts < cutoff]
        for fp in expired:
            del self._dedup_cache[fp]

        if fingerprint in self._dedup_cache:
            return True

        self._dedup_cache[fingerprint] = now
        return False

    async def ingest(
        self,
        source: str,
        raw_message: str,
        service_name: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> dict:
        """1. Mündung der Pipeline: Nimmt rohe Daten an, normalisiert sie und steckt sie in die Warteschlange.

        Gibt ein dict zurück: {"status": "queued"|"duplicate", "fingerprint": str}
        """
        fingerprint = self._compute_fingerprint(source, raw_message)

        if self._is_duplicate(fingerprint):
            logger.info(
                f"[DEDUP] Duplikat erkannt ({fingerprint[:8]}…) von {source}. "
                f"Zeitfenster: {DEDUP_WINDOW_SECONDS}s."
            )
            return {"status": "duplicate", "fingerprint": fingerprint}

        event = NormalizedEvent(
            source=source,
            raw_message=raw_message,
            service_name=service_name,
            tags=tags,
            fingerprint=fingerprint,
        )
        await self.queue.put(event)
        logger.debug(
            f"Event von {source} in Warteschlange gelegt. (Elemente in Queue: {self.queue.qsize()})"
        )
        return {"status": "queued", "fingerprint": fingerprint}

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
                recommendation=diagnosis_result.get("recommendation", ""),
                service_name=event.service_name,
                tags=",".join(event.tags) if event.tags else None,
                fingerprint=event.fingerprint,
            )
            db.add(log_entry)
            db.commit()
            logger.debug(f"💾 Log von {event.source} in SQLite gespeichert.")
        except Exception as e:
            logger.error(f"Fehler beim Speichern in der Datenbank: {e}")
        finally:
            db.close()
