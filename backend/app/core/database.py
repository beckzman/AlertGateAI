from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from .config import settings

# Wir nutzen vorerst SQLite, da es keine Installation erfordert und alles in einer lokalen .db Datei speichert
# In einer Prod-Umgebung würden wir hier z.B. PostgreSQL nutzen.
DATABASE_URL = settings.DATABASE_URL

# Engine erstellen (check_same_thread=False ist wichtig bei SQLite und asynchronem Zugriff / FastAPI)
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Sitzungsfabrik
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency-Funktion für FastAPI, um bei jedem Request eine saubere DB-Session zu bekommen
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
