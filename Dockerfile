FROM python:3.11-alpine

RUN apk add --no-cache curl

WORKDIR /app

# Installer certstream-python
RUN pip install --no-cache-dir certstream

COPY domains.txt .
COPY start.sh .
COPY notify.sh .
COPY server.py .
COPY certstream_monitor.py .

RUN chmod +x start.sh notify.sh

EXPOSE 8080

CMD ["./start.sh"]
