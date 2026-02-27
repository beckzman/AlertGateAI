import os
from pathlib import Path
from dotenv import load_dotenv

# Suche die .env Datei relativ zu dieser Datei (backend/app/core/ -> backend/)
# Das funktioniert unabhängig vom Startverzeichnis
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

class Config:
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./aiops.db")
    
    # KI
    AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini") # "gemini" oder "local"
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL", "http://localhost:1234/v1") # Default für LM Studio
    LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "local-model")
    
    # IMAP
    IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
    IMAP_PORT = int(os.getenv("IMAP_PORT", 993))
    IMAP_USER = os.getenv("IMAP_USER", "")
    IMAP_PASSWORD = os.getenv("IMAP_PASSWORD", "")
    IMAP_POLL_INTERVAL = int(os.getenv("IMAP_POLL_INTERVAL", 10))
    
    # Alerting
    SMTP_SERVER = os.getenv("SMTP_SERVER", "localhost")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "")

    ON_CALL_EMAIL = os.getenv("ON_CALL_EMAIL", "")
    ON_CALL_PHONE = os.getenv("ON_CALL_PHONE", "")

    # Twilio
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")

settings = Config()
