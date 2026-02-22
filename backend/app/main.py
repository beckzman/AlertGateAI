from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uvicorn
import asyncio
from typing import List

# Eigene Importe
from core.database import engine, get_db
from models.log_model import Base, LogEntry
from ingestion.syslog_receiver import start_syslog_server
from ingestion.imap_receiver import IMAPReceiver
from diagnosis.analyzer import AIDiagnosticService
from alerting.service import AlertingService
from ingestion.pipeline import EventPipeline

from contextlib import asynccontextmanager

# Globale Variable um Referenzen auf ewige Tasks zu halten
background_tasks = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Wenn FastAPI startet, werfen wir unsere Receiver im Hintergrund an!
    loop = asyncio.get_running_loop()
    
    # Zentrale Event-Pipeline initialisieren
    analyzer = AIDiagnosticService()
    alerter = AlertingService()
    alerter.set_analyzer(analyzer) # Verknüpfung für KI-Zusammenfassungen
    pipeline = EventPipeline(analyzer, alerter)
    
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
app = FastAPI(title="AIOps Bot Backend", lifespan=lifespan)

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
def get_logs(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """API-Endpunkt für das zukünftige Frontend, um die letzten System-Logs abzurufen."""
    # Rufe die neuesten Logs ab, sortiert nach Timestamp absteigend
    logs = db.query(LogEntry).order_by(LogEntry.timestamp.desc()).offset(skip).limit(limit).all()
    # Damit Pydantic es sauber ins JSON umwandelt (später bauen wir richtige Pydantic Models)
    return [{
        "id": log.id,
        "timestamp": log.timestamp,
        "source_ip": log.source_ip,
        "severity": log.severity,
        "message": log.message,
        "diagnosis": log.diagnosis,
        "recommendation": log.recommendation
    } for log in logs]

# Einstiegspunkt für lokales Testen
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
