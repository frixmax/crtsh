#!/bin/sh

echo "================================================"
echo "🚀 Starting Gungnir CT Monitor"
echo "================================================"

# Créer les dossiers nécessaires
mkdir -p /app/results
touch /app/seen_domains.txt
touch /app/new_domains.txt

echo ""
echo "📡 Starting HTTP server on port 8080..."
python3 /app/server.py &
SERVER_PID=$!

# Attendre que le serveur démarre
sleep 3

echo "✅ HTTP server started (PID: $SERVER_PID)"
echo ""
echo "🎯 Starting Gungnir CT scanner..."
/go/bin/gungnir -r /app/domains.txt -o /app/results/ -v -j -f 2>&1 &
GUNGNIR_PID=$!

echo "✅ Gungnir started (PID: $GUNGNIR_PID)"
echo ""
echo "🔔 Starting notification loop (check every 5 minutes)..."
echo "================================================"
echo ""

# Première vérification après 30 secondes
sleep 30
/app/notify.sh

# Boucle de notification toutes les 5 minutes
while true; do
    sleep 300
    echo ""
    echo "🔍 Checking for new domains... ($(date))"
    /app/notify.sh
done
