from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn
import asyncio
from typing import List, Optional

# Eigene Importe
from core.config import settings
from core.database import engine, get_db
from models.log_model import Base, LogEntry, NotificationHistory, EscalationRule, AppSetting
from ingestion.syslog_receiver import start_syslog_server
from ingestion.imap_receiver import IMAPReceiver
from diagnosis.analyzer import AIDiagnosticService
from diagnosis.rca import RCAService
from alerting.service import AlertingService
from ingestion.pipeline import EventPipeline

from contextlib import asynccontextmanager

# Rate Limiter (identifiziert Clients per Remote-IP)
limiter = Limiter(key_func=get_remote_address)

# Globale Variable um Referenzen auf ewige Tasks zu halten
background_tasks = set()


# ---------------------------------------------------------------------------
# Metadaten aller konfigurierbaren Parameter (Reihenfolge = Darstellung in UI)
# ---------------------------------------------------------------------------
SETTINGS_META = [
    {
        "group": "llm",
        "label": "KI / LLM",
        "restart_required": False,
        "fields": [
            {"key": "AI_PROVIDER",     "label": "Provider",         "type": "select",   "options": ["gemini", "local"], "is_secret": False},
            {"key": "GOOGLE_API_KEY",  "label": "Google API Key",   "type": "password", "is_secret": True},
            {"key": "LOCAL_LLM_URL",   "label": "Local LLM URL",    "type": "text",     "is_secret": False},
            {"key": "LOCAL_LLM_MODEL", "label": "Local LLM Model",  "type": "text",     "is_secret": False},
        ],
    },
    {
        "group": "imap",
        "label": "IMAP (E-Mail Eingang)",
        "restart_required": False,
        "fields": [
            {"key": "IMAP_SERVER",        "label": "Server",              "type": "text",     "is_secret": False},
            {"key": "IMAP_PORT",          "label": "Port",                "type": "number",   "is_secret": False},
            {"key": "IMAP_USER",          "label": "Benutzer",            "type": "text",     "is_secret": False},
            {"key": "IMAP_PASSWORD",      "label": "Passwort",            "type": "password", "is_secret": True},
            {"key": "IMAP_POLL_INTERVAL", "label": "Poll-Intervall (s)", "type": "number",   "is_secret": False},
        ],
    },
    {
        "group": "smtp",
        "label": "SMTP (E-Mail Versand)",
        "restart_required": False,
        "fields": [
            {"key": "SMTP_SERVER",     "label": "Server",          "type": "text",     "is_secret": False},
            {"key": "SMTP_PORT",       "label": "Port",            "type": "number",   "is_secret": False},
            {"key": "SMTP_USER",       "label": "Benutzer",        "type": "text",     "is_secret": False},
            {"key": "SMTP_PASSWORD",   "label": "Passwort",        "type": "password", "is_secret": True},
            {"key": "SMTP_FROM_EMAIL", "label": "Absender-E-Mail", "type": "text",     "is_secret": False},
        ],
    },
    {
        "group": "oncall",
        "label": "On-Call",
        "restart_required": False,
        "fields": [
            {"key": "ON_CALL_EMAIL", "label": "On-Call E-Mail",  "type": "text", "is_secret": False},
            {"key": "ON_CALL_PHONE", "label": "On-Call Telefon", "type": "text", "is_secret": False},
        ],
    },
    {
        "group": "twilio",
        "label": "SMS / Twilio",
        "restart_required": False,
        "fields": [
            {"key": "TWILIO_ACCOUNT_SID",  "label": "Account SID",  "type": "text",     "is_secret": False},
            {"key": "TWILIO_AUTH_TOKEN",   "label": "Auth Token",    "type": "password", "is_secret": True},
            {"key": "TWILIO_FROM_NUMBER",  "label": "Von-Nummer (+E164)", "type": "text", "is_secret": False},
        ],
    },
]

# Schneller Lookup: key → is_secret
_SECRET_KEYS = {f["key"] for g in SETTINGS_META for f in g["fields"] if f["is_secret"]}


def _current_value(key: str) -> str:
    """Gibt den aktuellen Wert eines Settings-Keys aus dem settings-Singleton zurück."""
    return str(getattr(settings, key, "") or "")


class AlertIngestRequest(BaseModel):
    """Schema für den REST Alert-Import Endpoint (EPIC 1)."""
    source: str = Field(..., min_length=1, max_length=255, description="IP-Adresse oder Hostname der Quelle")
    message: str = Field(..., min_length=1, max_length=10_000, description="Rohe Log-/Alert-Nachricht")
    service_name: Optional[str] = Field(None, max_length=128, description="Optionaler Service-Name (z.B. 'nginx', 'postgres')")
    tags: Optional[List[str]] = Field(None, description="Optionale Tags (z.B. ['prod', 'k8s'])")
    severity_hint: Optional[str] = Field(None, description="Optionaler Severity-Hinweis vom Sender (INFO/HIGH/CRITICAL)")


class SendNotificationRequest(BaseModel):
    recipient: str
    subject: str
    message: str
    severity: str = "INFO"


class TestNotificationRequest(BaseModel):
    channel: str  # "email" | "sms" | "webhook"
    target: Optional[str] = None  # Empfänger-Override (E-Mail, Telefon oder Webhook-URL)


class EscalationRuleRequest(BaseModel):
    email_enabled: bool = False
    email_recipients: str = ""
    sms_enabled: bool = False
    sms_recipients: str = ""
    webhook_enabled: bool = False
    webhook_url: str = ""


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Wenn FastAPI startet, werfen wir unsere Receiver im Hintergrund an!
    loop = asyncio.get_running_loop()

    # Zentrale Event-Pipeline initialisieren
    analyzer = AIDiagnosticService()
    alerter = AlertingService()
    alerter.set_analyzer(analyzer)  # Verknüpfung für KI-Zusammenfassungen
    pipeline = EventPipeline(analyzer, alerter)

    # RCA-Service initialisieren (EPIC 4)
    rca_service = RCAService(analyzer)

    # Services in app.state speichern für Endpoint-Zugriff
    app.state.alerter = alerter
    app.state.pipeline = pipeline
    app.state.rca_service = rca_service
    
    # 0. Pipeline Worker starten (arbeitet die Warteschlange ab)
    task1 = loop.create_task(pipeline.start_worker())
    background_tasks.add(task1)
    
    # 1. Syslog UDP Server
    task2 = loop.create_task(start_syslog_server(pipeline))
    background_tasks.add(task2)
    
    # 2. IMAP Polling Receiver
    imap_receiver = IMAPReceiver(pipeline)
    task3 = loop.create_task(imap_receiver.start_polling())
    background_tasks.add(task3)
    # In app.state ablegen, damit PUT /settings ihn hot-reloaden kann
    app.state.imap_task = task3
    app.state.imap_receiver = imap_receiver

    print("AIOps Backend gestartet! EventPipeline, Syslog (Port 5140) & IMAP laufen.")
    yield
    print("AIOps Backend wird heruntergefahren.")

# FastAPI App initialisieren
app = FastAPI(title="AlertGateAI Backend", lifespan=lifespan)

# Rate Limiter registrieren
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware hinzufügen (erlaubt Anfragen vom Frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In Produktion einschränken auf z.B. http://localhost:5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tabellen in der Datenbank erstellen (falls sie noch nicht existieren)
Base.metadata.create_all(bind=engine)


def _run_migrations():
    """Fügt fehlende Spalten zu bestehenden SQLite-Tabellen hinzu.
    SQLAlchemy create_all erstellt keine neuen Spalten in bereits vorhandenen Tabellen.
    """
    from sqlalchemy import text
    with engine.connect() as conn:
        existing_cols = {
            row[1] for row in conn.execute(text("PRAGMA table_info(log_entries)")).fetchall()
        }
        new_columns = [
            ("service_name",    "VARCHAR"),
            ("tags",            "VARCHAR"),
            ("fingerprint",     "VARCHAR"),
            ("confidence",      "REAL"),
            ("status",          "VARCHAR DEFAULT 'new'"),
            # EPIC 4 – Smart Triage
            ("cluster_id",      "VARCHAR"),
            ("correlation_id",  "VARCHAR"),
            ("rca_hypothesis",  "TEXT"),
            ("feedback",        "VARCHAR"),
        ]
        for col_name, col_type in new_columns:
            if col_name not in existing_cols:
                conn.execute(text(f"ALTER TABLE log_entries ADD COLUMN {col_name} {col_type}"))
                print(f"Migration: Spalte '{col_name}' zu log_entries hinzugefügt.")
        conn.commit()


_run_migrations()

# Standard-Eskalationsregeln anlegen wenn noch nicht vorhanden
def _seed_escalation_rules():
    from sqlalchemy.orm import Session
    with Session(engine) as db:
        for sev in ["INFO", "HIGH", "CRITICAL"]:
            if not db.query(EscalationRule).filter(EscalationRule.severity == sev).first():
                rule = EscalationRule(severity=sev)
                if sev in ["HIGH", "CRITICAL"]:
                    rule.email_enabled = True
                    rule.email_recipients = settings.ON_CALL_EMAIL
                if sev == "CRITICAL":
                    rule.sms_enabled = True
                    rule.sms_recipients = settings.ON_CALL_PHONE
                db.add(rule)
        db.commit()

_seed_escalation_rules()


def _load_settings_from_db():
    """Überschreibt den settings-Singleton mit in der DB gespeicherten Werten (aus dem Web-UI)."""
    from sqlalchemy.orm import Session as _Session
    with _Session(engine) as db:
        rows = db.query(AppSetting).all()
        for row in rows:
            if row.value is not None:
                # Typen anpassen (PORT und INTERVAL sind int)
                if row.key in ("SMTP_PORT", "IMAP_PORT", "IMAP_POLL_INTERVAL"):
                    try:
                        setattr(settings, row.key, int(row.value))
                    except ValueError:
                        pass
                else:
                    setattr(settings, row.key, row.value)


_load_settings_from_db()


@app.get("/")
def read_root():
    return {"status": "AIOps Bot is running", "version": "0.1.0"}

@app.get("/logs")
def get_logs(
    skip: int = 0, 
    limit: int = 50, 
    severity: str = None,
    source_ip: str = None,
    db: Session = Depends(get_db)
):
    """API-Endpunkt für das Dashboard, um Logs mit Filtermöglichkeit abzurufen."""
    query = db.query(LogEntry)
    
    if severity:
        query = query.filter(LogEntry.severity == severity)
    if source_ip:
        query = query.filter(LogEntry.source_ip.contains(source_ip))
        
    logs = query.order_by(LogEntry.timestamp.desc()).offset(skip).limit(limit).all()
    
    return [{
        "id": log.id,
        "timestamp": log.timestamp,
        "source_ip": log.source_ip,
        "severity": log.severity,
        "message": log.message,
        "diagnosis": log.diagnosis,
        "recommendation": log.recommendation,
        "confidence": log.confidence,
        "status": log.status or "new",
        "service_name": log.service_name,
        "cluster_id": log.cluster_id,
        "correlation_id": log.correlation_id,
        "feedback": log.feedback,
    } for log in logs]

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Statistiken für die Dashboard-Charts."""
    from sqlalchemy import func
    from datetime import datetime, timedelta, timezone

    # 24h Zeitraum
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    # 1. Severity Verteilung (letzte 24h)
    severity_counts = db.query(
        LogEntry.severity,
        func.count(LogEntry.id)
    ).filter(LogEntry.timestamp >= since).group_by(LogEntry.severity).all()

    # 2. Timeline (Alerts pro Stunde UND Severity, letzte 24h)
    # strftime ist SQLite-spezifisch; für PostgreSQL wäre es date_trunc.
    hourly_severity = db.query(
        func.strftime('%Y-%m-%dT%H:00:00', LogEntry.timestamp).label('hour'),
        LogEntry.severity,
        func.count(LogEntry.id)
    ).filter(LogEntry.timestamp >= since).group_by('hour', LogEntry.severity).order_by('hour').all()

    # Rohdaten in ein dict überführen: { "2024-01-01T14:00:00": {"CRITICAL": 2, "HIGH": 1, ...} }
    data_map: dict = {}
    for h, sev, cnt in hourly_severity:
        if h not in data_map:
            data_map[h] = {"CRITICAL": 0, "HIGH": 0, "INFO": 0}
        data_map[h][sev] = cnt

    # Alle 24 Stunden-Slots generieren (auch leere), neueste zuletzt
    now = datetime.now(timezone.utc)
    timeline = []
    for i in range(23, -1, -1):
        slot = (now - timedelta(hours=i)).replace(minute=0, second=0, microsecond=0)
        slot_str = slot.strftime('%Y-%m-%dT%H:00:00')
        entry = data_map.get(slot_str, {"CRITICAL": 0, "HIGH": 0, "INFO": 0})
        timeline.append({
            "hour": slot_str,
            "CRITICAL": entry.get("CRITICAL", 0),
            "HIGH": entry.get("HIGH", 0),
            "INFO": entry.get("INFO", 0),
        })

    return {
        "severity": {s: c for s, c in severity_counts},
        "timeline": timeline,
    }

@app.post("/notify/send")
async def send_notification(req: SendNotificationRequest, request: Request, db: Session = Depends(get_db)):
    """Manuell eine E-Mail-Benachrichtigung versenden und im Verlauf speichern."""
    alerter: AlertingService = request.app.state.alerter
    result = await alerter.send_manual_email(req.recipient, req.subject, req.message, req.severity)

    entry = NotificationHistory(
        recipient=req.recipient,
        subject=req.subject,
        message=req.message,
        severity=req.severity,
        channel="email",
        status=result["status"],
        error=result["message"] if result["status"] == "failed" else None,
    )
    db.add(entry)
    db.commit()

    if result["status"] == "failed":
        raise HTTPException(status_code=500, detail=result["message"])

    return result


@app.get("/notify/history")
def get_notification_history(db: Session = Depends(get_db)):
    """Verlauf der manuell versendeten Benachrichtigungen."""
    entries = db.query(NotificationHistory).order_by(NotificationHistory.timestamp.desc()).limit(50).all()
    return [{
        "id": e.id,
        "timestamp": e.timestamp,
        "recipient": e.recipient,
        "subject": e.subject,
        "message": e.message,
        "severity": e.severity,
        "channel": e.channel,
        "status": e.status,
        "error": e.error,
    } for e in entries]


@app.get("/notify/channels")
def get_notification_channels(request: Request, db: Session = Depends(get_db)):
    """Gibt den konfigurierten Status aller Benachrichtigungskanäle zurück."""
    alerter: AlertingService = request.app.state.alerter

    # Webhook-Konfiguration aus Eskalationsregeln ermitteln
    rules = db.query(EscalationRule).all()
    webhook_rules = [r for r in rules if r.webhook_enabled and r.webhook_url]
    webhook_urls = list({r.webhook_url for r in webhook_rules})

    channels = [
        {
            "id": "email",
            "name": "E-Mail (SMTP)",
            "status": alerter.email_status(),
            "detail": (
                f"{alerter.smtp_server} → {alerter.on_call_email}"
                if alerter.email_status() == "configured"
                else "Kein SMTP-Server konfiguriert – Mock-Modus aktiv"
            ),
        },
        {
            "id": "sms",
            "name": "SMS (Twilio)",
            "status": alerter.sms_status(),
            "detail": (
                f"Twilio → {alerter.on_call_phone}"
                if alerter.sms_status() == "configured"
                else "Kein Twilio-Konto konfiguriert – Mock-Modus aktiv"
            ),
        },
        {
            "id": "webhook",
            "name": "Webhook / MS Teams",
            "status": "configured" if webhook_urls else "disabled",
            "detail": (
                f"{len(webhook_urls)} Webhook-URL(s) konfiguriert"
                if webhook_urls
                else "Kein Webhook in den Eskalationsregeln aktiviert"
            ),
            "webhook_urls": webhook_urls,
        },
    ]
    return {"channels": channels}


@app.post("/notify/test")
async def test_notification(req: TestNotificationRequest, request: Request, db: Session = Depends(get_db)):
    """Sendet eine Test-Benachrichtigung über den angegebenen Kanal."""
    alerter: AlertingService = request.app.state.alerter
    channel = req.channel.lower()

    if channel == "email":
        recipient = req.target or alerter.on_call_email
        result = await alerter.send_manual_email(
            recipient,
            "AlertGateAI Test-Benachrichtigung",
            "Dies ist eine Test-Benachrichtigung von AlertGateAI. Konfiguration erfolgreich!",
            "INFO",
        )
        entry = NotificationHistory(
            recipient=recipient,
            subject="AlertGateAI Test-Benachrichtigung",
            message="Test-Benachrichtigung",
            severity="INFO",
            channel="email",
            status=result["status"],
            error=result["message"] if result["status"] == "failed" else None,
        )
        db.add(entry)
        db.commit()
        return result

    elif channel == "sms":
        result = await alerter.send_test_sms(req.target)
        entry = NotificationHistory(
            recipient=req.target or alerter.on_call_phone,
            subject="AlertGateAI Test-SMS",
            message="Test-SMS",
            severity="INFO",
            channel="sms",
            status=result["status"],
            error=result["message"] if result["status"] == "failed" else None,
        )
        db.add(entry)
        db.commit()
        return result

    elif channel == "webhook":
        if not req.target:
            # Ersten konfigurierten Webhook aus den Regeln verwenden
            rule = db.query(EscalationRule).filter(
                EscalationRule.webhook_enabled == True,
                EscalationRule.webhook_url != "",
                EscalationRule.webhook_url.isnot(None),
            ).first()
            url = rule.webhook_url if rule else None
        else:
            url = req.target

        if not url:
            raise HTTPException(status_code=400, detail="Kein Webhook-URL konfiguriert.")

        result = await alerter.send_test_webhook(url)
        entry = NotificationHistory(
            recipient=url[:255],
            subject="AlertGateAI Test-Webhook",
            message="Test-Webhook",
            severity="INFO",
            channel="webhook",
            status=result["status"],
            error=result["message"] if result["status"] == "failed" else None,
        )
        db.add(entry)
        db.commit()
        return result

    else:
        raise HTTPException(status_code=400, detail="channel muss 'email', 'sms' oder 'webhook' sein.")


@app.get("/escalation")
def get_escalation_rules(db: Session = Depends(get_db)):
    """Alle Eskalationsregeln abrufen."""
    rules = db.query(EscalationRule).order_by(EscalationRule.id).all()
    return [{
        "severity": r.severity,
        "email_enabled": r.email_enabled,
        "email_recipients": r.email_recipients,
        "sms_enabled": r.sms_enabled,
        "sms_recipients": r.sms_recipients,
        "webhook_enabled": r.webhook_enabled,
        "webhook_url": r.webhook_url,
    } for r in rules]


@app.put("/escalation/{severity}")
def update_escalation_rule(severity: str, req: EscalationRuleRequest, db: Session = Depends(get_db)):
    """Eine Eskalationsregel für einen Severity-Level aktualisieren."""
    severity = severity.upper()
    if severity not in ("INFO", "HIGH", "CRITICAL"):
        raise HTTPException(status_code=400, detail="Severity muss INFO, HIGH oder CRITICAL sein.")
    rule = db.query(EscalationRule).filter(EscalationRule.severity == severity).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Regel nicht gefunden.")
    rule.email_enabled = req.email_enabled
    rule.email_recipients = req.email_recipients
    rule.sms_enabled = req.sms_enabled
    rule.sms_recipients = req.sms_recipients
    rule.webhook_enabled = req.webhook_enabled
    rule.webhook_url = req.webhook_url
    db.commit()
    return {"status": "ok", "severity": severity}


@app.patch("/logs/{log_id}/status")
def update_log_status(log_id: int, status: str, db: Session = Depends(get_db)):
    """Status eines Log-Eintrags ändern (new → acknowledged → resolved)."""
    if status not in ("new", "acknowledged", "resolved"):
        raise HTTPException(status_code=422, detail="Status muss new, acknowledged oder resolved sein.")
    log = db.query(LogEntry).filter(LogEntry.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log-Eintrag nicht gefunden.")
    log.status = status
    db.commit()
    return {"id": log_id, "status": status}


class FeedbackRequest(BaseModel):
    feedback: str  # "valid" | "false_positive"


@app.get("/logs/correlation/{correlation_id}")
def get_correlated_events(correlation_id: str, db: Session = Depends(get_db)):
    """Alert-Story: alle Events einer Korrelationsgruppe, chronologisch sortiert (EPIC 4)."""
    logs = (
        db.query(LogEntry)
        .filter(LogEntry.correlation_id == correlation_id)
        .order_by(LogEntry.timestamp.asc())
        .all()
    )
    if not logs:
        raise HTTPException(status_code=404, detail="Korrelationsgruppe nicht gefunden.")
    return [{
        "id": log.id,
        "timestamp": log.timestamp,
        "source_ip": log.source_ip,
        "severity": log.severity,
        "message": log.message,
        "diagnosis": log.diagnosis,
        "recommendation": log.recommendation,
        "confidence": log.confidence,
        "service_name": log.service_name,
        "cluster_id": log.cluster_id,
        "rca_hypothesis": log.rca_hypothesis,
    } for log in logs]


@app.post("/logs/correlation/{correlation_id}/rca")
async def trigger_rca(correlation_id: str, request: Request, db: Session = Depends(get_db)):
    """Root-Cause-Hypothese für alle Events einer Korrelationsgruppe generieren (EPIC 4)."""
    logs = (
        db.query(LogEntry)
        .filter(LogEntry.correlation_id == correlation_id)
        .order_by(LogEntry.timestamp.asc())
        .all()
    )
    if not logs:
        raise HTTPException(status_code=404, detail="Korrelationsgruppe nicht gefunden.")

    rca_service: RCAService = request.app.state.rca_service
    events = [{
        "source_ip": log.source_ip,
        "service_name": log.service_name,
        "message": log.message,
        "diagnosis": log.diagnosis,
        "severity": log.severity,
        "timestamp": str(log.timestamp),
    } for log in logs]

    result = await rca_service.generate_hypothesis(events)

    # Hypothese auf dem schwerwiegendsten Event persistieren
    severity_rank = {"CRITICAL": 2, "HIGH": 1, "INFO": 0}
    target = sorted(logs, key=lambda l: severity_rank.get(l.severity or "INFO", 0), reverse=True)[0]
    target.rca_hypothesis = result.get("hypothesis", "")
    db.commit()

    return {"correlation_id": correlation_id, "event_count": len(logs), **result}


@app.patch("/logs/{log_id}/feedback")
def update_feedback(log_id: int, req: FeedbackRequest, db: Session = Depends(get_db)):
    """On-Call-Feedback für einen Log-Eintrag speichern (EPIC 4)."""
    if req.feedback not in ("valid", "false_positive"):
        raise HTTPException(status_code=422, detail="feedback muss 'valid' oder 'false_positive' sein.")
    log = db.query(LogEntry).filter(LogEntry.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log-Eintrag nicht gefunden.")
    log.feedback = req.feedback
    db.commit()
    return {"id": log_id, "feedback": req.feedback}


@app.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    """Gibt alle konfigurierbaren Parameter zurück.
    Geheimnisse (Passwörter, Tokens) werden als '***' maskiert, wenn sie gesetzt sind.
    """
    # DB-Werte in einen dict laden
    db_values = {row.key: row.value for row in db.query(AppSetting).all()}

    result = []
    for group in SETTINGS_META:
        fields_out = []
        for f in group["fields"]:
            key = f["key"]
            # Wert: zuerst DB, dann live settings-Singleton
            raw = db_values.get(key) or _current_value(key)
            if f["is_secret"]:
                display = "***" if raw else ""
            else:
                display = raw
            fields_out.append({**f, "value": display})
        result.append({
            "group": group["group"],
            "label": group["label"],
            "restart_required": group["restart_required"],
            "fields": fields_out,
        })
    return result


@app.put("/settings")
def update_settings(payload: dict, request: Request, db: Session = Depends(get_db)):
    """Speichert Konfigurationsparameter in der DB und aktualisiert die laufenden Services.

    Sicherheitsregeln:
    - Leerer String bei einem Secret-Feld → Feld wird NICHT überschrieben (keep existing).
    - '***' → ebenfalls ignoriert (unveränderter Platzhalterwert aus dem UI).
    """
    updated_keys = []
    needs_restart = set()

    for key, value in payload.items():
        # Unbekannte Keys ablehnen
        all_keys = {f["key"] for g in SETTINGS_META for f in g["fields"]}
        if key not in all_keys:
            continue

        is_secret = key in _SECRET_KEYS
        # Geheimnisse: leerer String oder "***" → überspringen
        if is_secret and (not value or value == "***"):
            continue

        # DB upsert
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        if row:
            row.value = str(value)
        else:
            db.add(AppSetting(key=key, value=str(value), is_secret=is_secret))

        # settings-Singleton aktualisieren
        if key in ("SMTP_PORT", "IMAP_PORT", "IMAP_POLL_INTERVAL"):
            try:
                setattr(settings, key, int(value))
            except ValueError:
                pass
        else:
            setattr(settings, key, value)

        updated_keys.append(key)

        # Prüfen ob Neustart nötig
        for group in SETTINGS_META:
            if any(f["key"] == key for f in group["fields"]) and group["restart_required"]:
                needs_restart.add(group["label"])

    db.commit()

    # Live-Reload: Alerting + LLM (immer, kostet nichts)
    alerter: AlertingService = request.app.state.alerter
    alerter.reload_from_settings()

    analyzer = request.app.state.pipeline.analyzer
    analyzer.reload_from_settings()

    # Hot-Reload: IMAP-Task neu starten wenn IMAP-Parameter geändert wurden
    _IMAP_KEYS = {"IMAP_SERVER", "IMAP_PORT", "IMAP_USER", "IMAP_PASSWORD", "IMAP_POLL_INTERVAL"}
    if _IMAP_KEYS & set(updated_keys):
        old_task = getattr(request.app.state, "imap_task", None)
        if old_task and not old_task.done():
            old_task.cancel()
        new_receiver = IMAPReceiver(request.app.state.pipeline)
        loop = asyncio.get_event_loop()
        new_task = loop.create_task(new_receiver.start_polling())
        request.app.state.imap_task = new_task
        request.app.state.imap_receiver = new_receiver

    return {
        "status": "ok",
        "updated": updated_keys,
        "restart_required": [],  # alles wird live neu geladen
    }


@app.post("/ingest", status_code=202)
@limiter.limit("100/minute")
async def ingest_alert(req: AlertIngestRequest, request: Request):
    """REST-Endpoint für Alert-Import (EPIC 1).

    Nimmt einen Alert entgegen, prüft auf Duplikate und leitet ihn an die Pipeline weiter.
    Rate Limit: 100 Requests/Minute pro IP.
    Antwort 202 Accepted — Verarbeitung erfolgt asynchron.
    """
    VALID_SEVERITIES = {"INFO", "HIGH", "CRITICAL"}
    if req.severity_hint and req.severity_hint.upper() not in VALID_SEVERITIES:
        raise HTTPException(
            status_code=422,
            detail=f"severity_hint muss INFO, HIGH oder CRITICAL sein (übergeben: '{req.severity_hint}')."
        )

    pipeline = request.app.state.pipeline
    result = await pipeline.ingest(
        source=req.source,
        raw_message=req.message,
        service_name=req.service_name,
        tags=req.tags,
    )

    return {
        "status": result["status"],
        "fingerprint": result["fingerprint"],
        "detail": "Duplikat ignoriert." if result["status"] == "duplicate" else "Alert wird verarbeitet.",
    }


# Einstiegspunkt für lokales Testen
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
