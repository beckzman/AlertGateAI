# AlertGateAI

## Projekt-Kontext
AlertGateAI ist ein intelligentes AIOps-System, das Infrastruktur-Alarme (Syslogs, E-Mails) empfängt, mit KI eine Erstdiagnose erstellt und die Rufbereitschaft über ein Eskalationsmodell (E-Mail → Twilio) alarmiert. Das System besteht aus einem React-Frontend (Dashboard) und einem Python/FastAPI-Backend, bereitgestellt via Docker.

## Entwicklungs-Richtlinien (Antigravity-Regeln)

*   **Schritt für Schritt:** Wir schreiben nicht das ganze System auf einmal. Code wird immer in kleinen, testbaren Modulen präsentiert.
*   **Best Practices:** Wir achten auf sauberes Error-Handling, asynchrone Verarbeitung (wo nötig, z.B. bei Syslogs) und sicheres Verwalten von API-Keys (Umgebungsvariablen).
*   **Erklärungen:** Zu jedem Code-Snippet wird eine kurze, prägnante Erklärung geliefert, wie es zu testen ist.

## Modul-Übersicht
Das System besteht aus den folgenden Kernmodulen:
*   **A) Log/E-Mail-Ingestion (Fertig):** Empfang via Syslog (UDP) und E-Mail (IMAP). Inklusive Normalisierung, Filterung und asynchroner Warteschlange.
*   **B) Diagnose-Modul (Fertig):** Echtzeit-KI-Analyse via Google Gemini oder lokalem LLM (LM Studio/Ollama).
*   **C) Alarmierungs-Modul (In Arbeit):** Eskalationslogik für E-Mail, Twilio und Messenger.

## Aktueller Projektstand
*   **Backend:** FastAPI Kern mit asynchroner Event-Pipeline.
*   **KI-Integration:** Multi-Provider Support (Gemini & OpenAI-kompatible lokale LLMs).
*   **Konfiguration:** Zentrales Environment-Management via `.env`.
*   **Datenbank:** SQLite mit SQLAlchemy für Log-Historie und Diagnosen.

## Konfiguration & Lokale KI
Das System wird über eine `.env` Datei im `backend/` Ordner konfiguriert.
*   `AI_PROVIDER`: "gemini" oder "local"
*   `GOOGLE_API_KEY`: API Key für Gemini
*   `LOCAL_LLM_URL`: URL für lokale KI (z.B. http://localhost:1234/v1)

## Quick Start mit Docker
Das System ist für den Betrieb mit Docker und Docker Compose vorkonfiguriert.

### 1. Konfiguration
Kopiere `backend/.env.example` nach `backend/.env` und trage deine API-Keys (Gemini, Twilio, SMTP) ein.
*   **Wichtig**: Setze `DATABASE_URL=sqlite:////app/data/aiops.db` für Docker-Persistenz.

### 2. Starten
```bash
docker-compose up -d --build
```

### Ports
*   **Frontend**: Port `80` (HTTP)
*   **Backend API**: Port `8000`
*   **Syslog Receiver**: Port `5140/udp`

---

## Modul-Status & Fortschritt
Detaillierte Aufgaben findest du in der [task.md](./task.md).

*   ✅ **Modul A (Ingestion)**: Syslog, IMAP, Normalisierung & Filterung erledigt.
*   ✅ **Modul B (KI-Analyse)**: Google Gemini & Lokale LLM Integration erledigt.
*   ✅ **Modul C (Alerting)**: Deduplizierung, SMTP & Twilio Integration erledigt.
*   ✅ **Frontend**: React Dashboard (Vite/Tailwind) erledigt.
*   🚀 **Deployment**: Docker & Compose Setup einsatzbereit.
