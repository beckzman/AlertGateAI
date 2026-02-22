# AIOps Infrastructure System - Projektplan

## Projekt-Kontext
Wir bauen einen Bot, der Infrastruktur-Alarme (Syslogs, E-Mails von Servern) empfängt. Er nutzt KI, um eine Erstdiagnose zu erstellen. Anschließend alarmiert er eine Rufbereitschaft über ein Eskalationsmodell (E-Mail -> Messenger -> Twilio Sprachanruf) und gibt konkrete Tipps zur Fehlerbehebung. Das System besteht aus einem Frontend (Dashboard) und einem Backend, bereitgestellt via Docker auf einem Linux-System.

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

## Tech-Stack (Festgelegt)

| Komponente | Technologie-Vorschlag | Begründung |
| :--- | :--- | :--- |
| **Backend & Ingestion** | Python (FastAPI) | Ideal für schnelle APIs, asynchrone Tasks (Logs empfangen) und KI-Integration. |
| **Log-Verarbeitung** | logging / socket / imaplib | Direkter Empfang von Syslogs über UDP/TCP und Lesen von IMAP-Postfächern. |
| **KI / Diagnose** | LLM-API (z.B. Gemini) oder lokal (Ollama) | Extrahiert Fehler aus unstrukturiertem Text und generiert Diagnose-Tipps. |
| **Alarmierung** | Twilio API, SMTP, Messenger Webhooks | Twilio für Voice, Standard-Bibliotheken für Mail, Webhooks für z.B. Telegram/Slack. |
| **Frontend** | React, Vue.js oder Streamlit | Streamlit für einen rasend schnellen Prototyp, React für ein vollwertiges Dashboard. |
| **Deployment** | Docker & Docker Compose | Sorgt für ein reibungsloses und isoliertes Deployment auf deinem Linux-System. |

## Taskliste (Auszug)
*   [x] Modul A: Ingestion (Syslog, Email, Queue, Filter)
*   [x] Modul B: KI-Diagnose (Gemini & Lokale LLM Integration)
*   **[ ] Modul C: Alerting / Eskalation**
    *   [ ] Echte SMTP/Twilio Integration
    *   [ ] Deduplizierungs-Mechanismus (Alert-Storm Protection)
*   [ ] Frontend: Dashboard (React oder Streamlit)
*   [ ] Deployment: Docker Compose Setup
