# AlertGateAI 🛡️🤖

AlertGateAI ist ein intelligentes AIOps-Zentrum zur Überwachung deiner IT-Infrastruktur. Es empfängt Alarme aus verschiedenen Quellen, analysiert diese in Echtzeit mit modernster KI (Gemini oder lokale LLMs), korreliert verwandte Vorfälle automatisch und eskaliert kritische Events an das On-Call Team.

## 🚀 Kern-Features

### Alert Ingestion
- **Multi-Source**: Syslog (UDP, Port 5140), E-Mail (IMAP Polling), REST API (`POST /ingest`)
- **Deduplizierung**: SHA256-Fingerprint + 60s In-Memory-Cache verhindert Alert-Storms
- **Rate Limiting**: 100 Requests/Minute pro IP auf dem `/ingest` Endpoint
- **Schema-Validierung**: Pydantic-Modell mit `source`, `message`, `service_name`, `tags`, `severity_hint`

### KI-Diagnose
- **Automatische Analyse**: Erkennt Fehlerursachen und gibt konkrete Handlungsempfehlungen
- **Confidence Score**: KI-Konfidenz (0–100%) wird als farbiger Progress-Bar im Dashboard angezeigt
- **Fallback-Modus**: Regelbasierte Mock-Diagnose wenn kein API-Key konfiguriert
- **Flexible Backends**: Google Gemini API oder lokale, OpenAI-kompatible KI-Server (LM Studio, Ollama)

### Smart Triage Engine
- **Clustering**: Ähnliche Events werden anhand normalisierter Nachrichten geclustert (`cluster_id`). Clickbarer Badge im Dashboard filtert nach Cluster.
- **Correlation Engine**: Events von derselben Source/Service innerhalb von 15 Minuten erhalten dieselbe `correlation_id`
- **Alert-Story**: Klick auf das 🔗-Icon öffnet ein Modal mit der chronologischen Event-Timeline eines Incidents
- **Root Cause Analysis**: KI-gestützte Hypothesen-Generierung für korrelierte Incidents via `POST /logs/correlation/{id}/rca`
- **On-Call Feedback**: ThumbsUp/Down-Buttons markieren Events als korrekt diagnostiziert oder als False Positive

### Alerting & Eskalation
- **Smart Alerting**: Aggregation über 60s-Zeitfenster mit KI-Zusammenfassung
- **Eskalationsmatrix**: Konfigurierbare Regeln pro Severity (INFO/HIGH/CRITICAL) mit E-Mail, SMS und Webhook
- **DB-gesteuerte Dispatch**: Empfänger und Webhook-URLs kommen aus den DB-Eskalationsregeln, nicht aus `.env`-Hardcodes
- **Multi-Channel Versand**: SMTP (E-Mail), Twilio (SMS), Webhook/MS Teams — Mock-Modus wenn nicht konfiguriert

### Notification Management
- **Kanalstatus**: `GET /notify/channels` liefert Live-Status (configured/mock/disabled) für alle Kanäle
- **Test-Funnel**: `POST /notify/test` sendet eine Test-Nachricht pro Kanal und protokolliert das Ergebnis im Verlauf
- **MS Teams / Webhook**: HTTP POST mit Teams MessageCard-Format — kompatibel mit Slack und generischen Webhooks
- **Versandverlauf**: Alle Benachrichtigungen mit Kanal-Spalte (email/sms/webhook)

### Web-Konfiguration (Settings)
- **Settings-Seite**: Alle Parameter (KI, IMAP, SMTP, On-Call, Twilio) im Browser konfigurierbar — kein `.env`-Edit nötig
- **Live-Reload ohne Restart**: SMTP/Twilio sofort wirksam, LLM via Client-Re-Init, IMAP via asyncio Task-Neustart
- **Sichere Passwortverwaltung**: Secrets werden in SQLite gespeichert, niemals im Klartext zurückgegeben (`***`)
- **DB-Persistenz**: Gespeicherte Werte überschreiben `.env`-Defaults bei jedem Start automatisch

### Dashboard
- **Echtzeit-Visualisierung**: Alert-Tabelle mit Live-Polling (10s Intervall)
- **Filterung**: API-seitige Filter (Severity, IP) + client-seitige Spalten-Filter (Datum, Source, Status, Cluster, Diagnose)
- **Status-Workflow**: Klickbarer Badge pro Event: NEU → ACK → GELÖST
- **KPI-Karten**: Total Events, Critical (inkl. %-Anteil), High, Info
- **Alert-Frequenz-Chart**: Stacked Bar Chart nach Severity, letzte 24h
- **TriageModal**: Alert-Story + RCA-Analyse direkt im Dashboard

---

## 🏗️ Architektur & Datenfluss

```
Syslog / E-Mail / REST API
         │
         ▼
  [ EventPipeline ]
  ├── Dedup (SHA256 Fingerprint, 60s TTL)
  ├── Keyword-Vorfilter (error/fail/timeout/oom/...)
  ├── Cluster-ID berechnen (SHA256 normalisierter Nachricht)
  └── Correlation-ID vergeben (15-Min-Fenster, selbe Source+Service)
         │
         ▼
  [ AIDiagnosticService ]    ←── Gemini / LM Studio / Mock
  └── {severity, diagnosis, recommendation, confidence}
         │
         ▼
  [ SQLite DB ] ← log_entries, escalation_rules, notification_history, app_settings
         │
         ├──► [ AlertingService ] → E-Mail (SMTP) / SMS (Twilio) / Webhook (MS Teams)
         └──► [ RCAService ]       → Root Cause Hypothesen (on-demand)
         │
         ▼
  [ React Dashboard ] ← pollt Backend alle 10s
  ├── Dashboard      (Alerts, Triage, RCA, Feedback)
  ├── Alarmierung    (Eskalationsregeln pro Severity)
  ├── Benachrichtigungen (Kanalstatus, Test, Verlauf)
  └── Einstellungen  (Web-Konfiguration, Live-Reload)
```

---

## 🐳 Deployment mit Docker (Empfohlen)

### 1. Repository klonen
```bash
git clone https://github.com/beckzman/AlertGateAI.git
cd AlertGateAI
```

### 2. Konfiguration
```bash
cp backend/.env.example backend/.env
# .env editieren: mindestens DATABASE_URL setzen
```

**Wichtig für Docker**: Datenbankpfad auf persistentes Volume setzen:
```
DATABASE_URL=sqlite:////app/data/aiops.db
```

Alle weiteren Parameter (API-Keys, SMTP, Twilio, On-Call) können nach dem ersten Start bequem über **Dashboard → Einstellungen** im Browser gesetzt werden. Kein Neustart erforderlich.

### 3. System starten
```bash
docker-compose up -d --build
```

### Ports & Zugriff
| Dienst | URL |
| :--- | :--- |
| Dashboard | `http://<ip>` (Port 80) |
| Backend API | `http://<ip>:8000` |
| API Docs | `http://<ip>:8000/docs` |
| Syslog Receiver | `udp://<ip>:5140` |
| Mailpit (Test-SMTP) | `http://<ip>:8025` |

### Container-Verwaltung
```bash
# Backend neu starten (nach .env-Änderungen)
docker compose restart backend

# Backend neu bauen (nach Code-Änderungen)
docker compose up -d --build backend

# Logs überwachen
docker compose logs -f backend
```

---

## 💻 Lokale Entwicklung

### Backend (Python/FastAPI)
```bash
python -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cd backend && uvicorn app.main:app --reload --port 8000
```

### Frontend (React/Vite)
```bash
cd frontend && npm install && npm run dev
```

---

## 🧪 System testen

### Syslog (UDP)
```bash
echo "ERROR: Data integrity check failed on DB-01" | nc -u -w0 localhost 5140
```

### REST API
```bash
# Einzelnen Alert ingesten
curl -X POST localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"source":"10.0.0.1","message":"connection refused to postgres","service_name":"api"}'

# Korrelierten Alert (innerhalb 15 Min nach obigem Aufruf → selbe correlation_id)
curl -X POST localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"source":"10.0.0.1","message":"timeout waiting for postgres response","service_name":"api"}'

# Alert-Story abrufen
curl localhost:8000/logs | python3 -m json.tool | grep correlation_id

# RCA generieren (correlation_id aus vorherigem Aufruf einsetzen)
curl -X POST localhost:8000/logs/correlation/<correlation_id>/rca
```

---

## 📡 API Endpoints

| Method | Endpoint | Beschreibung |
| :--- | :--- | :--- |
| `GET` | `/logs` | Events abrufen (Filter: severity, source_ip, skip, limit) |
| `POST` | `/ingest` | Alert ingesten (Rate: 100/min/IP) |
| `PATCH` | `/logs/{id}/status` | Status ändern (new/acknowledged/resolved) |
| `PATCH` | `/logs/{id}/feedback` | Feedback setzen (valid/false_positive) |
| `GET` | `/logs/correlation/{id}` | Alert-Story Timeline |
| `POST` | `/logs/correlation/{id}/rca` | Root Cause Analyse triggern |
| `GET` | `/stats` | Severity-Verteilung + 24h Timeline |
| `GET` | `/escalation` | Eskalationsregeln abrufen |
| `PUT` | `/escalation/{severity}` | Eskalationsregel aktualisieren |
| `GET` | `/notify/channels` | Live-Status aller Kanäle (configured/mock/disabled) |
| `POST` | `/notify/test` | Test-Nachricht über einen Kanal senden |
| `POST` | `/notify/send` | Manuelle E-Mail senden |
| `GET` | `/notify/history` | Benachrichtigungs-Verlauf (inkl. Kanal-Spalte) |
| `GET` | `/settings` | Alle Konfigurationsparameter abrufen (Secrets maskiert) |
| `PUT` | `/settings` | Parameter speichern + sofort live aktivieren |

---

## 🛠️ Konfigurations-Parameter (`.env`)

> **Hinweis:** Alle Parameter können nach dem ersten Start auch bequem über **Dashboard → Einstellungen** konfiguriert werden — kein `.env`-Edit und kein Neustart nötig. DB-Werte überschreiben `.env`-Defaults automatisch.

| Variable | Beschreibung | Standard |
| :--- | :--- | :--- |
| `AI_PROVIDER` | `gemini` oder `local` | `gemini` |
| `GOOGLE_API_KEY` | Google Gemini API Key | — |
| `LOCAL_LLM_URL` | OpenAI-kompatibler Endpunkt | `http://localhost:1234/v1` |
| `LOCAL_LLM_MODEL` | Modellname für lokale KI | — |
| `DATABASE_URL` | SQLAlchemy DB-URL | `sqlite:///./aiops.db` |
| `IMAP_SERVER` | IMAP Server (E-Mail Eingang) | `imap.gmail.com` |
| `IMAP_PORT` | IMAP Port | `993` |
| `IMAP_USER` | IMAP Benutzername | — |
| `IMAP_PASSWORD` | IMAP Passwort / App-Token | — |
| `IMAP_POLL_INTERVAL` | Abfrageintervall in Sekunden | `10` |
| `SMTP_SERVER` | SMTP Server | — |
| `SMTP_PORT` | SMTP Port | `587` |
| `SMTP_USER` | SMTP Benutzername | — |
| `SMTP_PASSWORD` | SMTP Passwort | — |
| `SMTP_FROM_EMAIL` | Absender-Adresse | — |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | — |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | — |
| `TWILIO_FROM_NUMBER` | Twilio Absender-Nummer | — |
| `ON_CALL_EMAIL` | E-Mail des Bereitschaftsdienstes | — |
| `ON_CALL_PHONE` | Telefon des Bereitschaftsdienstes | — |

---

## 📝 Lizenz
Dieses Projekt wurde im Rahmen eines Antigravity KI-Coding-Workflows entwickelt. Frei zur Verwendung für Monitoring- und AIOps-Enthusiasten.
