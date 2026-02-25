import asyncio
import logging
from typing import List

logger = logging.getLogger(__name__)


class RCAService:
    """Generiert Root-Cause-Hypothesen aus korrelierten Log-Events (EPIC 4)."""

    def __init__(self, analyzer):
        # Dependency Injection: nutzt die bestehende AIDiagnosticService-Instanz
        self.analyzer = analyzer

    async def generate_hypothesis(self, events: List[dict]) -> dict:
        """Nimmt eine Liste korrelierter Events und erzeugt eine Root-Cause-Hypothese.

        Gibt zurück: {hypothesis, confidence, affected_services, recommendation}
        """
        if not events:
            return {
                "hypothesis": "Keine Events für RCA vorhanden.",
                "confidence": 0.0,
                "affected_services": [],
                "recommendation": "",
            }

        if self.analyzer.use_mock:
            await asyncio.sleep(0.5)
            return self._mock_rca(events)

        ctx = self._build_context(events)
        prompt = self._build_prompt(ctx)

        try:
            # analyze_log liefert {severity, diagnosis, recommendation, confidence}
            # Wir übergeben den RCA-Kontext als strukturierten Prompt
            result = await self.analyzer.analyze_log(prompt)
            return {
                "hypothesis": result.get("diagnosis", "Keine Hypothese generiert."),
                "confidence": result.get("confidence", 0.5),
                "affected_services": ctx["services"],
                "recommendation": result.get("recommendation", ""),
            }
        except Exception as e:
            logger.error(f"RCA-Analyse fehlgeschlagen: {e}")
            return self._mock_rca(events)

    def _build_context(self, events: List[dict]) -> dict:
        services = list({e.get("service_name") or "unknown" for e in events})
        hosts = list({e.get("source_ip", "?") for e in events})
        severities = [e.get("severity", "INFO") for e in events]
        highest = "CRITICAL" if "CRITICAL" in severities else ("HIGH" if "HIGH" in severities else "INFO")

        timeline_lines = []
        for e in sorted(events, key=lambda x: x.get("timestamp", "")):
            ts = str(e.get("timestamp", "?"))[:19]
            svc = e.get("service_name") or e.get("source_ip", "?")
            msg = (e.get("message") or "")[:200]
            diag = (e.get("diagnosis") or "")
            line = f"  [{ts}] {svc}: {msg}"
            if diag:
                line += f" → {diag}"
            timeline_lines.append(line)

        return {
            "services": services,
            "hosts": hosts,
            "highest_severity": highest,
            "event_count": len(events),
            "timeline": "\n".join(timeline_lines),
        }

    def _build_prompt(self, ctx: dict) -> str:
        return (
            f"Du bist ein Senior Site Reliability Engineer. Analysiere diesen Incident "
            f"aus {ctx['event_count']} korrelierten Events.\n\n"
            f"Betroffene Services: {', '.join(ctx['services'])}\n"
            f"Betroffene Hosts: {', '.join(ctx['hosts'])}\n"
            f"Höchster Schweregrad: {ctx['highest_severity']}\n\n"
            f"Chronologische Event-Timeline:\n{ctx['timeline']}\n\n"
            f"Aufgabe: Identifiziere die wahrscheinlichste Root Cause und erkläre den Kaskadeneffekt.\n"
            f"Antworte ausschließlich als JSON mit den Feldern: "
            f'"diagnosis" (Root-Cause-Hypothese, 2–3 Sätze, Deutsch), '
            f'"recommendation" (nummerierte Sofortmaßnahmen, Deutsch), '
            f'"severity" (INFO/HIGH/CRITICAL), '
            f'"confidence" (Float 0.0–1.0).'
        )

    def _mock_rca(self, events: List[dict]) -> dict:
        """Regelbasierter RCA-Fallback – funktioniert ohne API-Key."""
        combined = " ".join((e.get("message") or "") for e in events).lower()
        services = list({e.get("service_name") or e.get("source_ip", "?") for e in events})
        count = len(events)

        if "memory" in combined or "oom" in combined:
            return {
                "hypothesis": (
                    f"Speichermangel-Kaskade auf {count} System(en). Ein Memory-Leak in einem der "
                    "betroffenen Prozesse hat den OOM-Killer ausgelöst und verdrängt andere Dienste."
                ),
                "confidence": 0.82,
                "affected_services": services,
                "recommendation": (
                    "1. OOM-Killer Logs prüfen: dmesg | grep -i oom\n"
                    "2. Top-Speicherverbraucher identifizieren: top -o %MEM\n"
                    "3. Betroffene Prozesse neu starten und Memory-Limits setzen."
                ),
            }
        elif "timeout" in combined or "refused" in combined or "connection" in combined:
            return {
                "hypothesis": (
                    f"Netzwerk-Konnektivitätsproblem zwischen {count} Komponenten. "
                    "Ein zentraler Dienst (z.B. Datenbank oder Load Balancer) reagiert nicht, "
                    "was einen Domino-Effekt in abhängigen Services ausgelöst hat."
                ),
                "confidence": 0.75,
                "affected_services": services,
                "recommendation": (
                    "1. Abhängigkeitsgraph der Services prüfen.\n"
                    "2. Datenbankverbindungspool und Health Checks kontrollieren.\n"
                    "3. Load Balancer Logs analysieren."
                ),
            }
        elif "disk" in combined or "storage" in combined or "no space" in combined:
            return {
                "hypothesis": (
                    f"Speicherplatz-Erschöpfung auf {count} System(en). "
                    "Voll gelaufene Partitionen verhindern Schreiboperationen und können Service-Abstürze auslösen."
                ),
                "confidence": 0.88,
                "affected_services": services,
                "recommendation": (
                    "1. Freien Speicher prüfen: df -h\n"
                    "2. Größte Verzeichnisse finden: du -sh /*\n"
                    "3. Alte Logs rotieren oder archivieren."
                ),
            }
        elif "crash" in combined or "segfault" in combined:
            return {
                "hypothesis": (
                    f"Prozessabsturz auf {count} System(en). Mögliche Ursache: Segmentation Fault "
                    "durch einen Speicherzugriffsfehler oder einen unbehandelten Ausnahmezustand."
                ),
                "confidence": 0.70,
                "affected_services": services,
                "recommendation": (
                    "1. Core Dumps analysieren: coredumpctl list\n"
                    "2. Letzte Code-Deployments prüfen.\n"
                    "3. Prozess neu starten und Monitoring schärfen."
                ),
            }
        else:
            return {
                "hypothesis": (
                    f"Mehrere ({count}) korrelierte Events von {len(services)} Service(s). "
                    "Kein dominantes Fehlermuster erkennbar – manuelle Analyse empfohlen."
                ),
                "confidence": 0.35,
                "affected_services": services,
                "recommendation": (
                    "1. Logs jedes betroffenen Services einzeln prüfen.\n"
                    "2. Zeitlichen Verlauf analysieren: Welches Event trat zuerst auf?\n"
                    "3. Change-Log der letzten 24h prüfen."
                ),
            }
