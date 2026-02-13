#!/bin/sh
echo "================================================"
echo "🚀 Starting crt.sh CT Monitor with SSL Validation"
echo "================================================"

# Créer les dossiers nécessaires
mkdir -p /app/results

echo ""
echo "📡 Starting HTTP server on port 8080..."
python3 /app/server.py &
SERVER_PID=$!

# Attendre que le serveur démarre
sleep 3
echo "✅ HTTP server started (PID: $SERVER_PID)"

echo ""
echo "🎯 Starting crt.sh monitor with SSL validation..."
python3 /app/certstream_monitor.py

# Note: Le script python gère maintenant les notifications en interne
# et tourne en boucle infinie, donc on n'arrive jamais ici sauf si erreur

echo "❌ Monitor stopped unexpectedly"
