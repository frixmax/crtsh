FROM golang:1.21-alpine

RUN apk add --no-cache git python3 curl

# Installer Gungnir
RUN go install github.com/opencyber-fr/gungnir@latest

WORKDIR /app

COPY domains.txt .
COPY start.sh .
COPY notify.sh .
COPY server.py .

RUN chmod +x start.sh notify.sh

EXPOSE 8080

CMD ["./start.sh"]
