import asyncio
import logging
import sys
import os

# Damit Python das 'ingestion'-Modul findet, wenn wir das Skript direkt hier ausführen:
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ingestion.pipeline import EventPipeline

# Konfiguration des Loggers
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SyslogProtocol(asyncio.DatagramProtocol):
    def __init__(self, pipeline: EventPipeline):
        self.pipeline = pipeline
        # Halte starke Referenzen auf Background-Tasks!
        self.bg_tasks = set()

    def connection_made(self, transport):
        self.transport = transport
        logger.info("Syslog-Receiver gestartet. Warte auf Logs...")

    def datagram_received(self, data, addr):
        # 1. Log empfangen
        message = data.decode('utf-8', errors='ignore').strip()
        source_ip = addr[0]
        
        # 2. Direkt asynchron in die Pipeline-Warteschlange feuern
        task = asyncio.create_task(self.pipeline.ingest(source_ip, message))
        self.bg_tasks.add(task)
        task.add_done_callback(self.bg_tasks.discard)

async def start_syslog_server(pipeline: EventPipeline, host='0.0.0.0', port=5140):
    logger.info(f"Starte Syslog-Server auf {host}:{port}")
    loop = asyncio.get_running_loop()
    
    # Server initialisieren und die Pipeline an unser Protokoll übergeben
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: SyslogProtocol(pipeline),
        local_addr=(host, port)
    )
    
    try:
        await asyncio.Event().wait()
    finally:
        transport.close()

if __name__ == "__main__":
    try:
        logging.warning("Bitte nutze main.py um das Backend samt Datenbank zu starten. Syslog kann hier aber standalone getestet werden.")
        asyncio.run(start_syslog_server())
    except KeyboardInterrupt:
        logger.info("Server beendet.")
