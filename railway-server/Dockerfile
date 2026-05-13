FROM python:3.11-slim

WORKDIR /app

COPY railway-server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY railway-server/server.py .

CMD gunicorn --workers 1 --threads 4 --worker-class gthread --timeout 120 --bind 0.0.0.0:${PORT:-8080} server:app
