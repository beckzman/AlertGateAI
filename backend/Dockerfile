# Basis-Image: Schlankes Python 3.11 (stabil)
FROM python:3.11-slim

# Arbeitsverzeichnis im Container
WORKDIR /app

# System-Abhängigkeiten (für einige Python-Libs nötig)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Abhängigkeiten kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Den gesamten Backend-Code kopieren
COPY . .

# Umgebungsvariablen setzen
ENV PYTHONPATH=/app/app
ENV PYTHONUNBUFFERED=1

# Port für FastAPI/Uvicorn
EXPOSE 8000

# Start-Befehl (aus /app/app heraus, damit Imports stimmen)
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
