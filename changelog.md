# Changelog

Alle wichtigen Änderungen an **AlertGateAI** werden in dieser Datei dokumentiert.

## [0.2.0] - 2026-02-25

### ✨ Neue Features

#### EPIC 1 – Alert Ingestion Engine
- **REST `/ingest` Endpoint**: Standardisierter Alert-Import via HTTP POST mit Pydantic-Validierung (`source`, `message`, `service_name`, `tags`, `severity_hint`). Antwortet mit 202 Accepted, Verarbeitung ist asynchron.
- **Rate Limiting**: `slowapi` Integration — 100 Requests/Minute pro IP auf `/ingest`.
- **Hash-basierte Deduplizierung**: SHA256-Fingerprint (source|message) mit 60s In-Memory-TTL-Cache. Duplikate werden mit `status: duplicate` zurückgewiesen.
- **Erweitertes Schema**: `LogEntry` um `service_name`, `tags`, `fingerprint` ergänzt.

#### EPIC 2 – KI-Analyse Core
- **Confidence Score**: KI-Prompt um Feld `confidence` (Float 0.0–1.0) erweitert. Wird in der DB persistiert und als farbiger Progress-Bar im Dashboard angezeigt (grün ≥80%, gelb ≥50%, rot <50%).
- **Fallback-Modus**: Vollständige Mock-Analyse ohne API-Key für alle bekannten Fehlermuster.

#### EPIC 3 – Dashboard (Basis)
- **Status-Workflow**: `status`-Feld (new/acknowledged/resolved) pro Event. Klickbarer Badge im Dashboard wechselt den Status zyklisch. Backend-Endpoint `PATCH /logs/{id}/status`.
- **KPI Critical%**: Prozentualer Anteil der Critical-Events der letzten 24h unter dem Zählwert angezeigt.

#### EPIC 4 – Smart Triage Engine
- **Alert-Clustering**: `cluster_id` (SHA256[:16] aus normalisierter Severity+Nachricht) gruppiert inhaltlich ähnliche Events. Volatile Tokens (IPs, Timestamps, Zahlen, UUIDs) werden vor dem Hashing entfernt.
- **Correlation Engine**: `correlation_id` (UUID4) verknüpft Events von derselben Source+Service innerhalb eines 15-Minuten-Fensters zu einem Incident.
- **Alert-Story**: `GET /logs/correlation/{id}` liefert alle korrelierten Events chronologisch. Im Dashboard öffnet ein Klick auf das 🔗-Icon ein `TriageModal` mit der Timeline.
- **Root Cause Analysis**: `POST /logs/correlation/{id}/rca` ruft den neuen `RCAService` (`diagnosis/rca.py`) auf. Dieser analysiert alle korrelierten Events mit der KI und generiert eine Root-Cause-Hypothese mit Kaskaden-Erklärung. Hypothesis wird in `rca_hypothesis` persistiert. Mock-Fallback für OOM, Netzwerk/Timeout, Disk, Crash und generische Muster.
- **On-Call Feedback**: `feedback`-Feld (valid/false_positive) per `PATCH /logs/{id}/feedback`. ThumbsUp/Down-Buttons im Dashboard mit optimistischem State-Update.
- **Cluster-Filter**: Klick auf Cluster-Badge in der Tabelle filtert alle gleichartigen Events.

### 🛠️ Infrastruktur & Architektur
- **SQLite Live-Migration**: `_run_migrations()` fügt fehlende Spalten via `PRAGMA table_info` + `ALTER TABLE` bei jedem Start hinzu — kein Datenverlust beim Upgrade.
- **`app.state` Service Registry**: `alerter`, `pipeline` und `rca_service` werden im Lifespan-Kontext initialisiert und sind in allen Endpoints erreichbar.
- **GitHub Actions**: Build-Check CI-Pipeline für Backend und Frontend.

### 🐛 Fixes
- SQLAlchemy `create_all` ergänzt keine neuen Spalten in bestehenden Tabellen — behoben durch `_run_migrations()`.

---

## [0.1.0] - 2026-02-22

### ✨ Neue Features
*   **Ingestion (Modul A)**:
    *   Syslog UDP-Receiver (Port 5140) für Echtzeit-Log-Ingest.
    *   IMAP Polling Service für den Empfang von Alarm-E-Mails.
    *   Asynchrone Event-Pipeline mit Keyword-Filterung.
*   **KI-Diagnose (Modul B)**:
    *   Integration von Google Gemini 1.5 Pro/Flash.
    *   Support für lokale LLMs via OpenAI-kompatible API (LM Studio, Ollama).
    *   Smart Prompting für präzise Ursachenanalyse und Handlungsempfehlungen.
*   **Alerting & Eskalation (Modul C)**:
    *   Deduplizierung von Alert-Storms (Aggregation über 3 Minuten).
    *   Automatisierte KI-Zusammenfassung von aggregierten Vorfällen.
    *   Scharfschaltung von SMTP (E-Mail) und Twilio (SMS) Integration.
*   **Frontend**:
    *   Modernes Command-Center Dashboard (React + Tailwind CSS).
    *   Live-Polling des Backends zur Anzeige von Events und Diagnosen.
    *   Responsive Design und intuitive Status-Karten.

### 🛠️ Infrastruktur & Deployment
*   **Vollständige Docker-Integration**: 
    *   Dockerfile für Backend (Python) und Frontend (Nginx).
    *   `docker-compose.yml` zur Orchestrierung beider Services inklusive persistenter SQLite-Datenbank.
*   **Skalierbare API**: FastAPI-basiertes Backend mit asynchronen Hintergrundprozessen.
*   **Konfiguration**: Zentrales Environment-Management via `.env`.

### 🚀 Initialer Release
*   Projektinitialisierung unter dem Namen **AlertGateAI**.
*   Vollständige Git-Historie auf GitHub.
