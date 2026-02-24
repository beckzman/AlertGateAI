import os
import logging
import asyncio
import json
import google.generativeai as genai
from openai import OpenAI
from core.config import settings

logger = logging.getLogger(__name__)

class AIDiagnosticService:
    def __init__(self):
        # AI Provider Auswahl: "gemini" oder "local"
        self.provider = settings.AI_PROVIDER
        self.use_mock = False
        
        if self.provider == "gemini":
            self.api_key = settings.GOOGLE_API_KEY
            if not self.api_key:
                logger.warning("Kein GOOGLE_API_KEY gefunden. Nutze Mock-Modus.")
                self.use_mock = True
            else:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        elif self.provider == "local":
            logger.info(f"Nutze lokales LLM via {settings.LOCAL_LLM_URL}")
            # Lokale LLMs (LM Studio/Ollama) nutzen meist das OpenAI-Schnittstellenformat
            self.client = OpenAI(base_url=settings.LOCAL_LLM_URL, api_key="not-needed")
            self.model_name = settings.LOCAL_LLM_MODEL
        else:
            logger.error(f"Unbekannter Provider '{self.provider}'. Nutze Mock-Modus.")
            self.use_mock = True

    async def analyze_log(self, log_message: str) -> dict:
        """
        Analysiert eine Log-Nachricht asynchron.
        Entscheidet basierend auf Config, ob Gemini oder ein lokaler Provider genutzt wird.
        """
        logger.info(f"Starte KI-Analyse ({self.provider}) für: '{log_message}'")
        
        if self.use_mock:
            await asyncio.sleep(1)
            return self._mock_analysis(log_message)
        
        # System-Prompt für die KI (einheitlich für beide Provider)
        prompt = f"""
        Du bist ein Senior IT System Engineer. Analysiere das folgende Log oder die folgende Fehlermeldung:
        ---
        {log_message}
        ---
        Gib dein Ergebnis IMMER im JSON-Format zurück mit den folgenden 3 Feldern:
        1. "severity": (Wähle aus: INFO, HIGH, CRITICAL)
        2. "diagnosis": (Was ist die Ursache des Problems auf Deutsch? Kurz und prägnant.)
        3. "recommendation": (Konkrete Schritte zur Fehlerbehebung auf Deutsch.)
        
        Wichtig: Gib NUR das JSON-Objekt ohne weiteren Text oder Markdown-Formatierung zurück.
        """

        try:
            loop = asyncio.get_running_loop()
            
            if self.provider == "gemini":
                response = await loop.run_in_executor(None, lambda: self.model.generate_content(prompt))
                content = response.text
            else:
                # Lokale LLM (OpenAI Format)
                response = await loop.run_in_executor(None, lambda: self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                ))
                content = response.choices[0].message.content

            # JSON-Extraktion und Parsing
            content = content.replace("```json", "").replace("```", "").strip()
            result = json.loads(content)
            
            logger.info(f"KI-Analyse erfolgreich abgeschlossen.")
            return result

        except Exception as e:
            logger.error(f"Fehler bei der KI-Analyse ({self.provider}): {e}")
            return {
                "severity": "ERROR",
                "diagnosis": f"KI-Analyse fehlgeschlagen: {str(e)}",
                "recommendation": "System-Logs manuell prüfen."
            }

    def _mock_analysis(self, log_message: str) -> dict:
        """Ein rudimentäres System, um die Integration zu testen, bevor wir Geld für Tokens ausgeben."""
        log_lower = log_message.lower()
        if "oom" in log_lower or "out of memory" in log_lower or "memory" in log_lower:
            return {
                "severity": "CRITICAL",
                "diagnosis": "Out-of-Memory-Fehler: Arbeitsspeicher erschöpft, Prozess wurde beendet.",
                "recommendation": "1. OOM-Killer-Logs prüfen: dmesg | grep -i oom. 2. Speicher-hungrige Prozesse identifizieren. 3. Swap erweitern oder RAM aufrüsten."
            }
        elif "disk space" in log_lower or "storage" in log_lower or "no space left" in log_lower:
            return {
                "severity": "CRITICAL",
                "diagnosis": "Speicherplatz auf einer Festplatte oder Partition erschöpft.",
                "recommendation": "1. Temporäre Dateien löschen. 2. Alte Logs komprimieren/löschen. 3. Mountpunkte prüfen: df -h"
            }
        elif "crash" in log_lower or "segfault" in log_lower or "core dump" in log_lower:
            return {
                "severity": "CRITICAL",
                "diagnosis": "Prozess-Absturz (Crash/Segfault) erkannt.",
                "recommendation": "1. Core-Dump analysieren. 2. Anwendungs-Log prüfen. 3. Service neustarten und überwachen."
            }
        elif "timeout" in log_lower or "connection" in log_lower or "refused" in log_lower:
            return {
                "severity": "HIGH",
                "diagnosis": "Netzwerk-Timeout oder Verbindung zu einem Dienst fehlgeschlagen.",
                "recommendation": "1. Ping-Test zum Zielhost. 2. Firewall-Regeln prüfen. 3. Zieldienst-Status prüfen."
            }
        elif "error" in log_lower or "fail" in log_lower:
            return {
                "severity": "HIGH",
                "diagnosis": "Allgemeiner Fehler oder Komponentenausfall erkannt.",
                "recommendation": "1. Vollständige Log-Ausgabe prüfen. 2. Service-Status kontrollieren. 3. Neustart erwägen."
            }
        elif "down" in log_lower or "unreachable" in log_lower:
            return {
                "severity": "CRITICAL",
                "diagnosis": "System oder Dienst nicht erreichbar.",
                "recommendation": "1. Ping und Traceroute zum Zielsystem. 2. Interface-Status prüfen. 3. NOC informieren."
            }
        else:
            return {
                "severity": "INFO",
                "diagnosis": "Die Log-Nachricht zeigt kein kritisches Muster (Mock-Modus).",
                "recommendation": "Weiterhin beobachten, keine akute Maßnahme erforderlich."
            }

# Für manuelles lokales Testen dieses Moduls
if __name__ == "__main__":
    async def run_test():
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        analyzer = AIDiagnosticService()
        
        # Test 1: Speicher-Fehler
        test_log = "Oct 11 22:14:15 myserver ERROR: Disk space is running low on /var/log"
        result = await analyzer.analyze_log(test_log)
        
        print("\n" + "="*40)
        print("KI DIAGNOSE ERGEBNIS")
        print("="*40)
        print(f"Schweregrad: {result['severity']}")
        print(f"Diagnose:    {result['diagnosis']}")
        print(f"Empfehlung:  {result['recommendation']}")
        print("="*40 + "\n")

    asyncio.run(run_test())
