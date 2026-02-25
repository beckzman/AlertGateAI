from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class LogEntry(Base):
    __tablename__ = "log_entries"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    source_ip = Column(String, index=True)
    message = Column(String)

    # Erweiterte Metadaten (EPIC 1)
    service_name = Column(String, nullable=True, index=True)
    tags = Column(String, nullable=True)          # kommagetrennte Tags
    fingerprint = Column(String, nullable=True, index=True)  # SHA256 für Dedup

    # Diagnose Ergebnisse (B)
    severity = Column(String, index=True, default="INFO")
    diagnosis = Column(String, nullable=True)
    recommendation = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)  # KI-Konfidenz 0.0–1.0 (EPIC 2)

    # Lifecycle-Status (EPIC 3): "new" | "acknowledged" | "resolved"
    status = Column(String, index=True, default="new")


class EscalationRule(Base):
    __tablename__ = "escalation_rules"

    id = Column(Integer, primary_key=True, index=True)
    severity = Column(String, unique=True, index=True)  # INFO, HIGH, CRITICAL

    email_enabled = Column(Boolean, default=False)
    email_recipients = Column(String, default="")  # kommagetrennte Adressen

    sms_enabled = Column(Boolean, default=False)
    sms_recipients = Column(String, default="")   # kommagetrennte Nummern

    webhook_enabled = Column(Boolean, default=False)
    webhook_url = Column(String, default="")


class NotificationHistory(Base):
    __tablename__ = "notification_history"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    recipient = Column(String)
    subject = Column(String)
    message = Column(String)
    severity = Column(String, default="INFO")
    channel = Column(String, default="email")
    status = Column(String)  # "sent", "mock", "failed"
    error = Column(String, nullable=True)
