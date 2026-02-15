FROM python:3.11-alpine

# Dépendances minimales
RUN apk add --no-cache curl

WORKDIR /app

# Python deps
RUN pip install --no-cache-dir requests

# Copier fichiers
COPY domains.txt .
COPY certstream_monitor.py .
COPY notify.sh .

# Permissions
RUN chmod +x notify.sh certstream_monitor.py

# Créer dossiers
RUN mkdir -p results && \
    touch seen_domains.txt new_domains.txt

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/ 2>/dev/null || exit 0

CMD ["python3", "certstream_monitor.py"]
