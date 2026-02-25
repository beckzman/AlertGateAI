import asyncio
import hashlib
import logging
import re
import uuid
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

# Zeitfenster für Korrelation gleichartiger Events (EPIC 4)
CORRELATION_WINDOW_MINUTES = 15

# Normalisierungs-Regex für Cluster-IDs: entfernt volatile Tokens (IPs, Timestamps, Zahlen, UUIDs)
_NORMALIZE_TOKENS = re.compile(
    r"\b(?:\d{1,3}(?:\.\d{1,3}){3}"                              # IPv4
    r"|(?:\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})"              # ISO-Timestamps
    r"|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"  # UUIDs
    r"|\d+)\b",
    re.IGNORECASE,
)


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

    def _compute_cluster_id(self, severity: str, message: str) -> str:
        """Stabiler Cluster-Key: normalisiert volatile Tokens, hasht severity|nachricht (EPIC 4)."""
        normalized = _NORMALIZE_TOKENS.sub("X", message.lower().strip())[:120]
        content = f"{severity}|{normalized}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _find_or_create_correlation_id(self, db, source_ip: str, service_name: Optional[str]) -> str:
        """Gibt eine bestehende correlation_id zurück wenn ein verwandtes Event im 15-Min-Fenster
        existiert (selbe Source-IP + Service), sonst eine neue UUID4 (EPIC 4)."""
        window_start = datetime.now(timezone.utc) - timedelta(minutes=CORRELATION_WINDOW_MINUTES)
        query = (
            db.query(LogEntry.correlation_id)
            .filter(
                LogEntry.source_ip == source_ip,
                LogEntry.timestamp >= window_start,
                LogEntry.correlation_id.isnot(None),
            )
        )
        if service_name:
            query = query.filter(LogEntry.service_name == service_name)
        existing = query.order_by(LogEntry.timestamp.asc()).first()
        if existing and existing.correlation_id:
            return existing.correlation_id
        return str(uuid.uuid4())

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
            raw_confidence = diagnosis_result.get("confidence")
            confidence = float(raw_confidence) if raw_confidence is not None else None
            if confidence is not None:
                confidence = max(0.0, min(1.0, confidence))  # Clampen auf [0.0, 1.0]

            # EPIC 4: Cluster- und Korrelations-IDs berechnen
            severity = diagnosis_result.get("severity", event.severity or "INFO")
            cluster_id = self._compute_cluster_id(severity, event.raw_message)
            correlation_id = self._find_or_create_correlation_id(db, event.source, event.service_name)

            log_entry = LogEntry(
                source_ip=event.source,
                message=event.raw_message,
                severity=severity,
                diagnosis=diagnosis_result.get("diagnosis", ""),
                recommendation=diagnosis_result.get("recommendation", ""),
                confidence=confidence,
                service_name=event.service_name,
                tags=",".join(event.tags) if event.tags else None,
                fingerprint=event.fingerprint,
                cluster_id=cluster_id,
                correlation_id=correlation_id,
            )
            db.add(log_entry)
            db.commit()
            logger.debug(f"💾 Log von {event.source} in SQLite gespeichert. cluster={cluster_id[:8]} corr={correlation_id[:8]}")
        except Exception as e:
            logger.error(f"Fehler beim Speichern in der Datenbank: {e}")
        finally:
            db.close()
