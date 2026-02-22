# Changelog

Alle wichtigen Änderungen an **AlertGateAI** werden in dieser Datei dokumentiert.

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
