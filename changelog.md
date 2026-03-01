# Changelog

Alle wichtigen Änderungen an **AlertGateAI** werden in dieser Datei dokumentiert.

## [0.3.1] - 2026-03-01

### ✨ Neue Features

#### CSV-Export
- **`GET /export/logs`**: Neuer Endpoint der alle passenden Events ohne Row-Limit als CSV-Datei zurückgibt. Optionale Filter: `severity`, `source_ip` (analog zu `/logs`). UTF-8-BOM Encoding für korrekte Darstellung von Umlauten in Excel und LibreOffice.
- **12 Spalten**: Zeitstempel, Quelle, Service, Severity, Status, Nachricht, Diagnose, Empfehlung, Confidence, Cluster-ID, Correlation-ID, Feedback.
- **"Export CSV"-Button** im Dashboard-Header: Übergibt aktive Severity- und Source-Filter automatisch; Browser startet den Download mit vorausgefülltem Dateinamen `alertgate_export_YYYY-MM-DD.csv`.

---

## [0.3.0] - 2026-02-27

### ✨ Neue Features

#### Zentrales Notification-Management
- **Webhook / MS Teams**: Neuer Kanal neben E-Mail und SMS. HTTP POST im Teams MessageCard-Format (kompatibel mit Slack und generischen Webhooks). URL wird pro Eskalationsregel in der DB gespeichert.
- **DB-gesteuerte Dispatch**: `_process_aggregated_alerts()` liest Empfänger und Webhook-URLs aus den Eskalationsregeln in SQLite — kein Hardcode mehr in `.env`.
- **`GET /notify/channels`**: Liefert Live-Status (configured/mock/disabled) für alle drei Kanäle (email/sms/webhook).
- **`POST /notify/test`**: Sendet eine Test-Nachricht über den gewählten Kanal und protokolliert das Ergebnis im Versandverlauf.
- **Kanal-Spalte im Verlauf**: Benachrichtigungs-Historie zeigt jetzt den verwendeten Kanal (email/sms/webhook) je Eintrag.
- **Dynamische Notifications-Seite**: Kanalstatus-Karten mit farbigem Indikator und "Test senden"-Button pro Kanal.

#### Web-Konfigurationsseite (Settings)
- **`GET /settings`** und **`PUT /settings`**: Vollständige Konfiguration aller Parameter (KI, IMAP, SMTP, On-Call, Twilio) über die REST API. Secrets werden in SQLite gespeichert und niemals im Klartext zurückgegeben (`***`).
- **Settings-Seite im Dashboard**: Alle Parameter im Browser konfigurierbar — kein `.env`-Edit nötig. Erreichbar über den neuen "Einstellungen"-Button in der Navigation.
- **`AppSetting`-Tabelle**: Neues Key-Value-Modell in SQLite mit `is_secret`-Flag. DB-Werte überschreiben `.env`-Defaults bei jedem Start automatisch.
- **Sichere Passwortverwaltung**: Passwortfelder mit Eye/EyeOff-Toggle. Leere Felder beim Speichern = bestehenden Wert behalten. "gesetzt"-Badge wenn Secret bereits konfiguriert.
- **Live-Reload ohne Restart**: Alle Services werden nach dem Speichern sofort aktualisiert:
  - SMTP/Twilio: `reload_from_settings()` auf `AlertingService`
  - LLM: `reload_from_settings()` auf `AIDiagnosticService` (Client-Re-Initialisierung)
  - IMAP: `old_task.cancel()` + `asyncio.create_task(new_receiver.start_polling())` — neue Verbindung ohne Container-Neustart

### 🛠️ Infrastruktur & Architektur
- **`app.state`-Erweiterung**: `imap_task` und `imap_receiver` werden im Lifespan-Kontext registriert, damit `PUT /settings` den IMAP-Task gezielt ersetzen kann.
- **`httpx` Abhängigkeit**: Für asynchrone Webhook-Anfragen in `AlertingService`.

### 🐛 Fixes
- **`PUT /settings` Verbindungsfehler**: Sync-Endpoint rief `asyncio.get_event_loop()` auf, was in Python 3.10+ im Thread-Pool-Kontext fehlschlägt. Behoben durch `async def update_settings` + `asyncio.create_task()`.
- **Placeholder-Defaults entfernt**: `config.py` hatte hartkodierte Fallback-Werte (`+49123456789`, `oncall@mycompany.com`, `test@example.com`, `secret`). Alle Felder standardmäßig auf `""` gesetzt.

---

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
