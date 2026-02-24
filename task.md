# AIOps Infrastruktur System - Taskliste

✅ **Erledigt:**
*   [x] Projekt-Basis: FastAPI Backend & SQLite Datenbankstruktur
*   [x] Modul A: Syslog UDP-Receiver Grundgerüst
*   [x] Modul A: E-Mail Ingestion `imap_receiver.py` Modul anlegen
*   [x] Modul A: IMAP Polling asynchron in FastAPI (`main.py`) integrieren
*   [x] Modul A: Testlauf: Echte E-Mail empfangen und simulierte Diagnose triggern
*   [x] Gemini API Integration (google-generativeai) implementieren.
*   [x] System-Prompt für präzise IT-Infrastruktur-Diagnosen erstellen.
*   [x] Fehler-Handling für API-Timeouts oder ungültige Antworten.
*   [x] Modul C: Alerting Logik mit Deduplizierung und KI-Zusammenfassungen.
*   [x] Modul C: SMTP und Twilio Integration (bereit für Credentials).
*   [x] Frontend: Modernes Dashboard (React/Vite/Tailwind) zur Visualisierung der Logs.

🧑‍💻 **Aktueller Fokus – Deployment:**
*   [x] Deployment: Docker/Docker Compose Setup aufbauen (Backend + Frontend + DB-Volume).
*   [x] CI/CD: Einfache GitHub Actions (Build-Check).

🚀 **Zukünftige Baustellen:**
*   [ ] **Zentrales Notification-Management**:
    *   Entwicklung eines dedizierten Moduls zur Verwaltung von Alert-Zielen.
    *   Konfigurations-Interface für Kanäle: Mail, Teams, SMS, Voice.
*   [ ] **MS Teams Integration**:
    *   Anbindung via Incoming Webhooks für Echtzeit-Alerts.
    *   Adaptive Cards für KI-Diagnosen und "Acknowledge"-Buttons.
*   [x] **Advanced Dashboard Features**:
    *   [x] Filterung & Suche: Filtern nach Zeiträumen, IP-Adressen oder Severity.
    *   [x] Gruppierung: Logik zum Zusammenfassen ähnlicher Fehlerbilder in der View.
    *   [x] Visualisierung: Implementierung von Charts (z.B. Alert-Frequenz über 24h) mit Recharts/Chart.js.
