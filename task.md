# AlertGateAI – Roadmap & Taskliste

---

## ✅ Abgeschlossen

*   [x] Projekt-Basis: FastAPI Backend & SQLite Datenbankstruktur
*   [x] Modul A: Syslog UDP-Receiver Grundgerüst
*   [x] Modul A: E-Mail Ingestion `imap_receiver.py` Modul anlegen
*   [x] Modul A: IMAP Polling asynchron in FastAPI (`main.py`) integrieren
*   [x] Modul A: Testlauf: Echte E-Mail empfangen und simulierte Diagnose triggern
*   [x] Gemini API Integration (google-generativeai) implementieren
*   [x] System-Prompt für präzise IT-Infrastruktur-Diagnosen erstellen
*   [x] Fehler-Handling für API-Timeouts oder ungültige Antworten
*   [x] Modul C: Alerting Logik mit Deduplizierung und KI-Zusammenfassungen
*   [x] Modul C: SMTP und Twilio Integration (bereit für Credentials)
*   [x] Frontend: Modernes Dashboard (React/Vite/Tailwind) zur Visualisierung der Logs
*   [x] Deployment: Docker/Docker Compose Setup aufbauen (Backend + Frontend + DB-Volume)
*   [x] CI/CD: Einfache GitHub Actions (Build-Check)
*   [x] Dashboard: Filterung & Suche (Zeiträume, IP-Adressen, Severity)
*   [x] Dashboard: Gruppierung ähnlicher Fehlerbilder in der View
*   [x] Dashboard: Alert-Frequenz Chart (24h, Stacked Bar nach Severity)
*   [x] Dashboard: Notification-Seite (E-Mail manuell versenden + Verlauf)

---

## 🥇 Phase 1 – Stabile Basis (aktuell)

🎯 **Ziel:** Produktionsreifer Kern der Plattform

---

### EPIC 1 – Alert Ingestion Engine

🔧 **Tasks:**
*   [ ] REST API für Alert-Import stabilisieren (Validation + Error Handling) — _kein dedizierter REST-Endpoint für Alert-Import_
*   [~] JSON Schema Definition für Alerts erstellen — _`NormalizedEvent` Pydantic-Modell existiert, aber unvollständig (fehlen: tags, service_name, etc.)_
*   [ ] Rate Limiting einbauen — _nicht vorhanden_
*   [~] Deduplizierung (Hash + Zeitfenster) — _zeitbasiertes Alert-Buffering (60s) vorhanden, aber kein Hash-basiertes Dedup auf Ingestion-Ebene_
*   [~] Speicherung in DB (PostgreSQL oder MongoDB) — _SQLite läuft; PostgreSQL-Migration vorbereitet aber nicht umgesetzt (strftime statt date_trunc)_
*   [~] Logging & Monitoring für eigene Plattform — _Python-Logging vorhanden, kein zentrales System (kein Prometheus/ELK)_

---

### EPIC 2 – KI-Analyse Core

🔧 **Tasks:**
*   [x] Prompt-Template standardisieren — _einheitliches Template für Gemini + lokale LLMs_
*   [x] Severity-Mapping (INFO/HIGH/CRITICAL) — _vollständig implementiert inkl. Mock-Logik_
*   [x] Handlungsempfehlung generieren — _`recommendation`-Feld in DB + Dashboard angezeigt_
*   [ ] Confidence Score einführen — _nicht vorhanden; KI gibt nur severity/diagnosis/recommendation zurück_
*   [x] Fallback-Mechanismus bei LLM-Fehlern — _Mock-Modus bei fehlendem API-Key + Exception-Handling_

---

### EPIC 3 – Dashboard (Basis)

🔧 **Tasks:**
*   [x] Alert-Liste mit Filter (Severity, Service, Zeit) — _Spalten- und Seitenleisten-Filter implementiert_
*   [x] Detailansicht mit KI-Analyse — _Diagnose + Empfehlung direkt in der Tabellenzeile sichtbar_
*   [ ] Status-Workflow (New → Acknowledged → Resolved) — _kein Status-Feld in DB, kein Lifecycle-UI_
*   [~] KPI-Boxen (Anzahl Alerts, Critical, High, Info) — _Zählungen vorhanden; Critical% und MTTR fehlen_
*   [ ] Authentifizierung (JWT / OAuth) — _alle Endpoints öffentlich, kein Login_

---

## 🥈 Phase 2 – Intelligente Triage & Automatisierung (1–3 Monate)

🎯 **Ziel:** Reduktion von Alert-Noise + Automatische Eskalation

---

### EPIC 4 – Smart Triage Engine

🔧 **Tasks:**
*   [ ] Clustering ähnlicher Alerts — _nicht vorhanden; Frontend-Gruppierung (source+diagnosis) ist kein echtes Clustering_
*   [ ] Correlation Engine (Zeit + Service + Host) — _nicht vorhanden_
*   [~] Root Cause Hypothesen generieren — _KI-Diagnose liefert Ursachen-Text, aber kein dediziertes RCA-Modul_
*   [ ] Alert-Story (Timeline-Rekonstruktion) — _Frequenz-Chart vorhanden, aber kein Event-Zusammenhang_
*   [ ] Feedback-System für On-Call-Team — _nicht vorhanden_

---

### EPIC 5 – Incident Automation

🔧 **Tasks:**
*   [ ] Webhook-System — _nicht vorhanden_
*   [ ] Jira-Integration (Auto-Ticket bei Critical) — _nicht vorhanden_
*   [ ] Slack-Bot (Severity-abhängiges Channel-Routing) — _nicht vorhanden_
*   [x] E-Mail-Fallback — _vollständig: SMTP + Twilio SMS; Mock-Modus wenn nicht konfiguriert_
*   [x] Eskalationsmatrix (Level 1 → Level 2 → Manager) — _Konfigurationsseite mit DB-persistierten Regeln pro Severity (E-Mail/SMS/Webhook toggle + Empfänger)_

---

## 🥉 Phase 3 – ML-basierte Optimierung (3–6 Monate)

🎯 **Ziel:** Echte AIOps-Plattform

---

### EPIC 6 – Predictive Alerting

🔧 **Tasks:**
*   [ ] Historische Alert-Daten sammeln
*   [ ] Feature Engineering (Frequenz, Zeitmuster)
*   [ ] Anomalie-Detection Modell (IsolationForest / LSTM)
*   [ ] Forecasting (Trendanalyse)
*   [ ] UI-Vorhersage Dashboard

---

### EPIC 7 – Self-Learning Feedback Loop

🔧 **Tasks:**
*   [ ] Feedback speichern (False Positive / Valid)
*   [ ] Reinforcement-Ansatz für Severity-Anpassung
*   [ ] Alert-Confidence Recalculation
*   [ ] Modell-Re-Training Pipeline

---

## 🔮 Weitere Baustellen

*   [ ] **Zentrales Notification-Management**: Konfigurations-Interface für Kanäle (Mail, Teams, SMS, Voice)
*   [ ] **MS Teams Integration**: Incoming Webhooks + Adaptive Cards mit Acknowledge-Buttons

---

> **Legende:** `[x]` = Fertig · `[~]` = Teilweise umgesetzt · `[ ]` = Offen
