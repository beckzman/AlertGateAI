import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Optional

import httpx
import aiosmtplib
from twilio.rest import Client
from email.message import EmailMessage

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
        self.pending_alerts: List[Dict] = []
        self.aggregation_lock = asyncio.Lock()
        self.aggregation_task = None
        self.buffer_time = 60  # Sekunden (180 für Produktion)

        self.analyzer = None

    def set_analyzer(self, analyzer):
        self.analyzer = analyzer

    def reload_from_settings(self):
        """Liest alle Verbindungsparameter aus dem settings-Singleton neu ein (nach Web-UI-Update)."""
        self.smtp_server   = settings.SMTP_SERVER
        self.smtp_port     = settings.SMTP_PORT
        self.smtp_user     = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_from     = settings.SMTP_FROM_EMAIL
        self.twilio_sid    = settings.TWILIO_ACCOUNT_SID
        self.twilio_token  = settings.TWILIO_AUTH_TOKEN
        self.twilio_from   = settings.TWILIO_FROM_NUMBER
        self.on_call_email = settings.ON_CALL_EMAIL
        self.on_call_phone = settings.ON_CALL_PHONE
        logger.info("AlertingService: Konfiguration neu geladen.")

    # ------------------------------------------------------------------ #
    # Öffentliche Hilfsmethoden für Kanalstatus (für /notify/channels)    #
    # ------------------------------------------------------------------ #

    def email_status(self) -> str:
        """'configured' wenn echter SMTP-Server gesetzt, sonst 'mock'."""
        if self.smtp_server and not (self.smtp_server == "localhost" and not self.smtp_user):
            return "configured"
        return "mock"

    def sms_status(self) -> str:
        """'configured' wenn Twilio-Credentials vorhanden, sonst 'mock'."""
        if self.twilio_sid and self.twilio_token:
            return "configured"
        return "mock"

    # ------------------------------------------------------------------ #
    # Trigger & Aggregation                                               #
    # ------------------------------------------------------------------ #

    async def trigger_escalation(self, log_message: str, source_ip: str, diagnosis: dict):
        async with self.aggregation_lock:
            alert_item = {
                "log": log_message,
                "source": source_ip,
                "diagnosis": diagnosis,
                "timestamp": datetime.now(),
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
            sources.add(a["source"])
            sev = a["diagnosis"].get("severity", "INFO")
            if sev == "CRITICAL":
                highest_severity = "CRITICAL"
            elif sev == "HIGH" and highest_severity != "CRITICAL":
                highest_severity = "HIGH"

        summary = await self._generate_summary(alerts)

        # Eskalationsregel aus DB lesen
        from core.database import SessionLocal
        from models.log_model import EscalationRule

        db = SessionLocal()
        try:
            rule = db.query(EscalationRule).filter(EscalationRule.severity == highest_severity).first()
        finally:
            db.close()

        if rule:
            if rule.email_enabled:
                recipients = rule.email_recipients or self.on_call_email
                await self._send_email_alert(summary, list(sources), highest_severity, recipients)
            if rule.sms_enabled:
                phones = rule.sms_recipients or self.on_call_phone
                await self._send_sms_alert(summary, list(sources), phones)
            if rule.webhook_enabled and rule.webhook_url:
                await self._send_webhook_alert(rule.webhook_url, summary, highest_severity, list(sources))
        else:
            # Fallback: altes Verhalten ohne DB-Regel
            if highest_severity in ["HIGH", "CRITICAL"]:
                await self._send_email_alert(summary, list(sources), highest_severity, self.on_call_email)
            if highest_severity == "CRITICAL":
                await self._send_sms_alert(summary, list(sources), self.on_call_phone)

    # ------------------------------------------------------------------ #
    # Zusammenfassung                                                     #
    # ------------------------------------------------------------------ #

    async def _generate_summary(self, alerts: List[Dict]) -> str:
        if len(alerts) == 1:
            a = alerts[0]
            return (
                f"Einzel-Alarm von {a['source']}: {a['diagnosis'].get('diagnosis')}\n"
                f"Empfehlung: {a['diagnosis'].get('recommendation')}"
            )

        if self.analyzer:
            raw_data = "\n".join([f"- {a['source']}: {a['log']}" for a in alerts])
            prompt = (
                f"Fasse diese {len(alerts)} Infrastruktur-Fehlermeldungen zu einer kurzen, prägnanten Warnung "
                f"für eine Rufbereitschaft zusammen. Welche Systeme sind betroffen? Was ist das Hauptproblem?\n\n{raw_data}"
            )
            try:
                result = await self.analyzer.analyze_log(f"ZUSAMMENFASSUNG ANFORDERN: {prompt}")
                return result.get("diagnosis", "Event-Sturm erkannt.")
            except Exception:
                pass
        return f"Event-Sturm erkannt! {len(alerts)} Alarme von {len({a['source'] for a in alerts})} Quellen."

    # ------------------------------------------------------------------ #
    # Kanal-Implementierungen                                             #
    # ------------------------------------------------------------------ #

    async def _smtp_send(self, msg: EmailMessage):
        kwargs: dict = dict(
            hostname=self.smtp_server,
            port=self.smtp_port,
            use_tls=(self.smtp_port == 465),
            start_tls=(self.smtp_port == 587),
        )
        if self.smtp_user:
            kwargs["username"] = self.smtp_user
            kwargs["password"] = self.smtp_password
        await aiosmtplib.send(msg, **kwargs)

    async def _send_email_alert(
        self, summary_text: str, sources: List[str], severity: str, recipients: str
    ):
        if not self.smtp_server or (self.smtp_server == "localhost" and not self.smtp_user):
            logger.info(f"✉️ MOCK-Email ({severity}): {summary_text[:80]}…")
            return

        try:
            msg = EmailMessage()
            msg["Subject"] = f"[{severity}] AlertGateAI Alert: {len(sources)} betroffene Systeme"
            msg["From"] = self.smtp_from
            msg["To"] = recipients
            msg.set_content(summary_text)
            await self._smtp_send(msg)
            logger.info(f"✉️ E-Mail erfolgreich an {recipients} versendet.")
        except Exception as e:
            logger.error(f"❌ Fehler beim E-Mail Versand: {e}")

    async def _send_sms_alert(self, summary_text: str, sources: List[str], phones: str):
        if not self.twilio_sid or not self.twilio_token:
            logger.info(f"📱 MOCK-SMS für {sources}")
            return

        to_number = phones.split(",")[0].strip() if phones else self.on_call_phone
        try:
            def send_sms():
                client = Client(self.twilio_sid, self.twilio_token)
                short_text = (summary_text[:150] + "..") if len(summary_text) > 150 else summary_text
                client.messages.create(
                    body=f"🚨 CRITICAL AlertGateAI: {short_text}",
                    from_=self.twilio_from,
                    to=to_number,
                )

            await asyncio.to_thread(send_sms)
            logger.info(f"📱 Twilio SMS erfolgreich nach {to_number} versendet.")
        except Exception as e:
            logger.error(f"❌ Fehler bei Twilio: {e}")

    async def _send_webhook_alert(
        self, url: str, text: str, severity: str, sources: List[str]
    ):
        """HTTP POST an einen Webhook (MS Teams Incoming Webhook / Slack / Generic).

        Verwendet das MS Teams MessageCard-Format — ist auch mit generischen Webhooks
        kompatibel. Für Slack-kompatible Endpunkte wird zusätzlich ein 'text'-Feld gesetzt.
        """
        if not url:
            return

        color = {"CRITICAL": "FF0000", "HIGH": "FFA500"}.get(severity, "0078D4")
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": color,
            "summary": f"[{severity}] AlertGateAI Alert",
            "text": text,  # Slack-kompatibel
            "sections": [
                {
                    "activityTitle": f"🚨 [{severity}] AlertGateAI Alert",
                    "activityText": text,
                    "facts": [
                        {"name": "Schweregrad", "value": severity},
                        {"name": "Betroffene Quellen", "value": ", ".join(sources)},
                    ],
                }
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                logger.info(f"🔔 Webhook erfolgreich versendet → {url[:60]}…")
        except Exception as e:
            logger.error(f"❌ Webhook-Fehler ({url[:40]}…): {e}")

    # ------------------------------------------------------------------ #
    # Manueller Versand (für /notify/send und /notify/test)              #
    # ------------------------------------------------------------------ #

    async def send_manual_email(
        self, recipient: str, subject: str, message: str, severity: str
    ) -> dict:
        if not self.smtp_server or (self.smtp_server == "localhost" and not self.smtp_user):
            logger.info(f"✉️ MOCK-Email an {recipient}: {subject}")
            return {"status": "mock", "message": "E-Mail (Mock) simuliert – kein SMTP konfiguriert"}

        try:
            msg = EmailMessage()
            msg["Subject"] = f"[{severity}] AlertGateAI: {subject}"
            msg["From"] = self.smtp_from
            msg["To"] = recipient
            msg.set_content(message)
            await self._smtp_send(msg)
            logger.info(f"✉️ Manuelle E-Mail an {recipient} versendet.")
            return {"status": "sent", "message": f"E-Mail erfolgreich an {recipient} versendet"}
        except Exception as e:
            logger.error(f"❌ Fehler beim manuellen E-Mail Versand: {e}")
            return {"status": "failed", "message": str(e)}

    async def send_test_webhook(self, url: str) -> dict:
        """Sendet eine Test-Nachricht an einen Webhook-URL."""
        try:
            await self._send_webhook_alert(
                url,
                "Dies ist eine Test-Benachrichtigung von AlertGateAI. Konfiguration erfolgreich!",
                "INFO",
                ["test"],
            )
            return {"status": "sent", "message": f"Webhook-Test erfolgreich an {url[:60]}…"}
        except Exception as e:
            return {"status": "failed", "message": str(e)}

    async def send_test_sms(self, phone: Optional[str] = None) -> dict:
        """Sendet eine Test-SMS über Twilio."""
        to = phone or self.on_call_phone
        if not self.twilio_sid or not self.twilio_token:
            return {"status": "mock", "message": f"SMS-Test (Mock) an {to} – kein Twilio konfiguriert"}
        try:
            await self._send_sms_alert(
                "AlertGateAI Test-SMS: Konfiguration erfolgreich!",
                ["test"],
                to,
            )
            return {"status": "sent", "message": f"Test-SMS erfolgreich an {to} versendet"}
        except Exception as e:
            return {"status": "failed", "message": str(e)}
