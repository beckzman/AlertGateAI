from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uvicorn
import asyncio
from typing import List

# Eigene Importe
from core.config import settings
from core.database import engine, get_db
from models.log_model import Base, LogEntry, NotificationHistory, EscalationRule
from ingestion.syslog_receiver import start_syslog_server
from ingestion.imap_receiver import IMAPReceiver
from diagnosis.analyzer import AIDiagnosticService
from alerting.service import AlertingService
from ingestion.pipeline import EventPipeline

from contextlib import asynccontextmanager

# Globale Variable um Referenzen auf ewige Tasks zu halten
background_tasks = set()

class SendNotificationRequest(BaseModel):
    recipient: str
    subject: str
    message: str
    severity: str = "INFO"


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

    # Alerter in app.state speichern für Endpoint-Zugriff
    app.state.alerter = alerter
    
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
    
    print("AIOps Backend gestartet! EventPipeline, Syslog (Port 5140) & IMAP laufen.")
    yield
    print("AIOps Backend wird heruntergefahren.")

# FastAPI App initialisieren
app = FastAPI(title="AlertGateAI Backend", lifespan=lifespan)

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
        "recommendation": log.recommendation
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


# Einstiegspunkt für lokales Testen
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
