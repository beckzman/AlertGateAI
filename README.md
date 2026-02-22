# AlertGateAI 🛡️🤖

AlertGateAI ist ein intelligentes AIOps-Zentrum zur Überwachung deiner IT-Infrastruktur. Es empfängt Alarme aus verschiedenen Quellen, analysiert diese in Echtzeit mit modernster KI (Gemini oder lokale LLMs) und eskaliert kritische Vorfälle automatisch an das On-Call Team.

## 🚀 Kern-Features

*   **Multi-Source Ingestion**: Empfang von Alarmen via Syslog (UDP, Port 5140) und E-Mail (IMAP Polling).
*   **KI-powered Diagnose**: Automatische Analyse von Log-Nachrichten. Erkennt Fehlerursachen und gibt konkrete Handlungsempfehlungen.
*   **Smart Alerting**: 
    *   Deduplizierung von "Alert-Storms" (Aggregation über einen 3-Minuten-Zeitfenster).
    *   KI-Zusammenfassung von gebündelten Alarmen.
    *   Eskalation via E-Mail (SMTP) und optional Twilio (SMS/Voice).
*   **Modern Dashboard**: Echtzeit-Visualisierung der Events und Diagnosen in einem modernen React-Dashboard.
*   **Flexible KI-Backends**: Support für Google Gemini API oder lokale, OpenAI-kompatible KI-Server (LM Studio, Ollama).

---

## 🏗️ Architektur & Datenfluss

1.  **Ingestion**: Server senden Logs via Syslog oder E-Mail an AlertGateAI.
2.  **Pipeline**: Events werden normalisiert und nach relevanten Keywords gefiltert.
3.  **Diagnosis**: Relevante Events werden an die KI gesendet. Diese liefert `Severity`, `Diagnosis` und `Recommendation`.
4.  **Database**: Alle Events und Diagnosen werden in einer SQLite-Datenbank persistiert.
5.  **Alerter**: Bei `CRITICAL` oder `HIGH` Severity wird die Eskalationskette gestartet.
6.  **Frontend**: Das Dashboard pollt das Backend und zeigt den aktuellen Status live an.

---

## 🐳 Deployment mit Docker (Empfohlen)

Das System ist für den Betrieb mit Docker vorkonfiguriert und ideal für das Deployment auf einem Linux-Server.

### 1. Repository klonen
```bash
git clone https://github.com/beckzman/AlertGateAI.git
cd AlertGateAI/aiops-bot
```

### 2. Konfiguration
Kopiere die Beispiel-Konfiguration und trage deine API-Keys ein:
```bash
cp backend/.env.example backend/.env
```
**Wichtig für Docker**: In der `.env` muss der Datenbankpfad auf das persistente Volume zeigen:
`DATABASE_URL=sqlite:////app/data/aiops.db`

### 3. System starten
```bash
docker-compose up -d --build
```

### Ports & Zugriff
*   **Dashboard**: `http://<deine-ip>` (Port 80)
*   **Backend API**: `http://<deine-ip>:8000`
*   **Syslog Receiver**: `udp://<deine-ip>:5140`

---

## 💻 Lokale Entwicklung (Windows/Mac/Linux)

Falls du das System ohne Docker lokal starten möchtest:

### Backend (Python/FastAPI)
1.  Venv erstellen: `python -m venv venv`
2.  Aktivieren & Installieren: `pip install -r backend/requirements.txt`
3.  Starten (Windows):
    ```powershell
    cd backend
    .\start.ps1
    ```

### Frontend (React/Vite)
1.  Navigate: `cd frontend`
2.  Installieren: `npm install`
3.  Starten: `npm run dev`

---

## 🧪 System testen
Um einen Test-Alarm an das System zu senden, kannst du das mitgelieferte PowerShell-Skript nutzen (aus dem Root-Verzeichnis):

```powershell
.\send_test_syslog.ps1 -Message "CRITICAL: No space left on device /dev/sda1" -Source "192.168.1.50"
```

Oder via Bash (Linux/Mac):
```bash
echo "ERROR: Data integrity check failed on DB-01" | nc -u -w0 localhost 5140
```

---

## 🛠️ Konfigurations-Parameter (`.env`)

| Variable | Beschreibung |
| :--- | :--- |
| `AI_PROVIDER` | `gemini` oder `local` |
| `GOOGLE_API_KEY` | Dein Google Gemini API Key |
| `LOCAL_LLM_URL` | API-Endpunkt für lokale KI (z.B. LM Studio) |
| `SMTP_SERVER` | SMTP Server für E-Mail Alarme |
| `TWILIO_SID` | Twilio Account SID für SMS/Voice |
| `ON_CALL_EMAIL` | E-Mail Adresse des Bereitschaftsdienstes |

---

## 📝 Lizenz
Dieses Projekt wurde im Rahmen eines Antigravity KI-Coding-Workflows entwickelt. Frei zur Verwendung für Monitoring- und AIOps-Enthusiasten.
