from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uvicorn
import asyncio
from typing import List

# Eigene Importe
from core.database import engine, get_db
from models.log_model import Base, LogEntry, NotificationHistory
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
    
    # 2. Timeline (Alerts pro Stunde, letzte 24h)
    # Hinweis: strftime ist SQLite spezifisch. Für PostgreSQL wäre es date_trunc.
    hourly_counts = db.query(
        func.strftime('%Y-%m-%dT%H:00:00', LogEntry.timestamp).label('hour'),
        func.count(LogEntry.id)
    ).filter(LogEntry.timestamp >= since).group_by('hour').order_by('hour').all()
    
    return {
        "severity": {s: c for s, c in severity_counts},
        "timeline": [{"hour": h, "count": c} for h, c in hourly_counts]
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


# Einstiegspunkt für lokales Testen
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
