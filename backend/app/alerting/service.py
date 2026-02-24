import os
import logging
import asyncio
from datetime import datetime
from typing import List, Dict
from email.message import EmailMessage

import aiosmtplib
from twilio.rest import Client

from core.config import settings

logger = logging.getLogger(__name__)

class AlertingService:
    def __init__(self):
        # Konfiguration
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_from = settings.SMTP_FROM_EMAIL
        
        self.twilio_sid = settings.TWILIO_ACCOUNT_SID
        self.twilio_token = settings.TWILIO_AUTH_TOKEN
        self.twilio_from = settings.TWILIO_FROM_NUMBER
        
        self.on_call_email = settings.ON_CALL_EMAIL
        self.on_call_phone = settings.ON_CALL_PHONE
        
        # Aggregations-Speicher
        self.pending_alerts = [] # Liste von Dicts: {log, source, diagnosis, timestamp}
        self.aggregation_lock = asyncio.Lock()
        self.aggregation_task = None
        self.buffer_time = 60 # Sekunden zum Testen (später 180 für 3 Min)
        
        # Referenz zum Analyzer für Zusammenfassungen
        self.analyzer = None

    def set_analyzer(self, analyzer):
        self.analyzer = analyzer

    async def trigger_escalation(self, log_message: str, source_ip: str, diagnosis: dict):
        async with self.aggregation_lock:
            alert_item = {
                "log": log_message,
                "source": source_ip,
                "diagnosis": diagnosis,
                "timestamp": datetime.now()
            }
            self.pending_alerts.append(alert_item)
            logger.info(f"Alarm von {source_ip} gepuffert. (Warteschlange: {len(self.pending_alerts)})")

            if self.aggregation_task is None or self.aggregation_task.done():
                self.aggregation_task = asyncio.create_task(self._wait_and_flush())

    async def _wait_and_flush(self):
        logger.info(f"⏱️ Aggregations-Timer gestartet ({self.buffer_time}s)...")
        await asyncio.sleep(self.buffer_time)
        
        async with self.aggregation_lock:
            if not self.pending_alerts:
                return
            alerts_to_send = self.pending_alerts.copy()
            self.pending_alerts = []
        
        await self._process_aggregated_alerts(alerts_to_send)

    async def _process_aggregated_alerts(self, alerts: List[Dict]):
        count = len(alerts)
        logger.warning(f"🚀 Verarbeite {count} gebündelte Alarme...")

        highest_severity = "INFO"
        sources = set()
        for a in alerts:
            sources.add(a['source'])
            sev = a['diagnosis'].get('severity', 'INFO')
            if sev == "CRITICAL": highest_severity = "CRITICAL"
            elif sev == "HIGH" and highest_severity != "CRITICAL": highest_severity = "HIGH"

        summary = await self._generate_summary(alerts)
        
        if highest_severity in ["HIGH", "CRITICAL"]:
            await self._send_email_alert(summary, list(sources), highest_severity)
        
        if highest_severity == "CRITICAL":
            await self._send_twilio_alert(summary, list(sources))

    async def _generate_summary(self, alerts: List[Dict]) -> str:
        if len(alerts) == 1:
            a = alerts[0]
            return f"Einzel-Alarm von {a['source']}: {a['diagnosis'].get('diagnosis')}\nEmpfehlung: {a['diagnosis'].get('recommendation')}"
        
        if self.analyzer:
            raw_data = "\n".join([f"- {a['source']}: {a['log']}" for a in alerts])
            prompt = f"Fasse diese {len(alerts)} Infrastruktur-Fehlermeldungen zu einer kurzen, prägnanten Warnung für eine Rufbereitschaft zusammen. Welche Systeme sind betroffen? Was ist das Hauptproblem?\n\n{raw_data}"
            try:
                result = await self.analyzer.analyze_log(f"ZUSAMMENFASSUNG ANFORDERN: {prompt}")
                return result.get("diagnosis", "Event-Sturm erkannt.")
            except:
                pass
        return f"Event-Sturm erkannt! {len(alerts)} Alarme von {len(set(a['source'] for a in alerts))} Quellen."

    async def _send_email_alert(self, summary_text: str, sources: List[str], severity: str):
        """Versand via SMTP (real)"""
        if not self.smtp_server or self.smtp_server == "localhost" and not self.smtp_user:
            logger.info("✉️ MOCK-Email: " + summary_text)
            return

        try:
            msg = EmailMessage()
            msg["Subject"] = f"[{severity}] AIOps Alert: {len(sources)} betroffene Systeme"
            msg["From"] = self.smtp_from
            msg["To"] = self.on_call_email
            msg.set_content(summary_text)

            await aiosmtplib.send(
                msg,
                hostname=self.smtp_server,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=(self.smtp_port == 465),
                start_tls=(self.smtp_port == 587)
            )
            logger.info(f"✉️ E-Mail erfolgreich an {self.on_call_email} versendet.")
        except Exception as e:
            logger.error(f"❌ Fehler beim E-Mail Versand: {e}")

    async def send_manual_email(self, recipient: str, subject: str, message: str, severity: str) -> dict:
        """Manuell eine E-Mail-Benachrichtigung versenden."""
        if not self.smtp_server or (self.smtp_server == "localhost" and not self.smtp_user):
            logger.info(f"✉️ MOCK-Email an {recipient}: {subject}")
            return {"status": "mock", "message": f"E-Mail (Mock) simuliert – kein SMTP konfiguriert"}

        try:
            msg = EmailMessage()
            msg["Subject"] = f"[{severity}] AlertGateAI: {subject}"
            msg["From"] = self.smtp_from
            msg["To"] = recipient
            msg.set_content(message)

            await aiosmtplib.send(
                msg,
                hostname=self.smtp_server,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=(self.smtp_port == 465),
                start_tls=(self.smtp_port == 587)
            )
            logger.info(f"✉️ Manuelle E-Mail an {recipient} versendet.")
            return {"status": "sent", "message": f"E-Mail erfolgreich an {recipient} versendet"}
        except Exception as e:
            logger.error(f"❌ Fehler beim manuellen E-Mail Versand: {e}")
            return {"status": "failed", "message": str(e)}

    async def _send_twilio_alert(self, summary_text: str, sources: List[str]):
        """Versand via Twilio (real)"""
        if not self.twilio_sid or not self.twilio_token:
            logger.info(f"📱 MOCK-SMS: CRITICAL Alert für {sources}")
            return

        try:
            # Twilio's Client ist synchron, daher in Thread auslagern
            def send_sms():
                client = Client(self.twilio_sid, self.twilio_token)
                # Nachricht auf 160 Zeichen begrenzen
                short_text = (summary_text[:150] + '..') if len(summary_text) > 150 else summary_text
                client.messages.create(
                    body=f"🚨 CRITICAL AIOps Alert: {short_text}",
                    from_=self.twilio_from,
                    to=self.on_call_phone
                )
            
            await asyncio.to_thread(send_sms)
            logger.info(f"📱 Twilio SMS erfolgreich nach {self.on_call_phone} versendet.")
        except Exception as e:
            logger.error(f"❌ Fehler bei Twilio: {e}")
