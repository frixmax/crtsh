FROM golang:1.21-alpine

RUN apk add --no-cache git python3 curl ca-certificates build-base

WORKDIR /tmp

# Cloner et compiler Gungnir depuis le bon repo
RUN git clone https://github.com/d-Rickyy-b/gungnir.git && \
    cd gungnir && \
    go build -o /usr/local/bin/gungnir . && \
    cd / && \
    rm -rf /tmp/gungnir

WORKDIR /app

COPY domains.txt .
COPY start.sh .
COPY notify.sh .
COPY server.py .

RUN chmod +x start.sh notify.sh

EXPOSE 8080

CMD ["./start.sh"]
