#!/bin/sh
# start.sh - Démarrage Gungnir avec auto-cleanup + server web + monitor CT

set -e

APP_DIR="/app"
RESET_MARKER="${APP_DIR}/.cleanup_done"
DOMAINS_FILE="${APP_DIR}/domains.txt"

echo "================================================"
echo "🚀 GUNGNIR MONITOR - Démarrage"
echo "================================================"
echo ""

# ============================================================================
# ÉTAPE 1: VÉRIFICATIONS
# ============================================================================

echo "1️⃣ Vérifications préalables..."

if [ ! -f "$DOMAINS_FILE" ]; then
    echo "   ❌ ERREUR: $DOMAINS_FILE n'existe pas!"
    exit 1
fi

DOMAIN_COUNT=$(grep -v '^#' "$DOMAINS_FILE" 2>/dev/null | grep -v '^$' | wc -l)
if [ "$DOMAIN_COUNT" -eq 0 ]; then
    echo "   ❌ ERREUR: $DOMAINS_FILE est vide!"
    exit 1
fi

echo "   ✅ $DOMAIN_COUNT domaines à monitorer"

# ============================================================================
# ÉTAPE 2: PREMIER DÉMARRAGE - CLEANUP AUTOMATIQUE
# ============================================================================

if [ ! -f "$RESET_MARKER" ]; then
    echo ""
    echo "2️⃣🟢 PREMIER DÉMARRAGE - Initialisation..."
    
    echo "   ▫️ Suppression /app/.first_run_complete..."
    > "${APP_DIR}/.first_run_complete"
    
    echo "   ▫️ Suppression /app/seen_domains.txt..."
    > "${APP_DIR}/seen_domains.txt"
    
    echo "   ▫️ Suppression /app/new_domains.txt..."
    > "${APP_DIR}/new_domains.txt"
    
    echo "   ▫️ Nettoyage /app/results..."
    mkdir -p "${APP_DIR}/results"
    find "${APP_DIR}/results" -type f ! -name ".gitkeep" -delete 2>/dev/null || true
    
    echo "   ▫️ Nettoyage /tmp..."
    rm -f /tmp/all_domains.txt /tmp/seen_sorted.txt /tmp/all_sorted.txt
    rm -f /tmp/payload.json /tmp/discord_response.txt /tmp/seen_updated.txt
    
    echo "   ✅ Initialisation terminée"
    touch "$RESET_MARKER"
    
    echo "   ℹ️ Prochain redémarrage: démarrage normal"
else
    echo ""
    echo "2️⃣ Démarrage normal (cleanup précédent OK)"
fi

echo ""

# ============================================================================
# ÉTAPE 3: AFFICHER L'ÉTAT
# ============================================================================

echo "3️⃣ État du système:"
echo "   📋 Domaines: $DOMAIN_COUNT"

SEEN_COUNT=$(wc -l < "${APP_DIR}/seen_domains.txt" 2>/dev/null || echo "0")
echo "   🔍 Domaines vus: $SEEN_COUNT"

mkdir -p "${APP_DIR}/results"
RESULTS_COUNT=$(find "${APP_DIR}/results" -type f ! -name ".gitkeep" 2>/dev/null | wc -l)
echo "   📁 Résultats: $RESULTS_COUNT fichiers"

echo ""

# ============================================================================
# ÉTAPE 4: DÉMARRER LES SERVICES
# ============================================================================

echo "4️⃣ Démarrage des services..."
echo ""

# Créer le dossier results
mkdir -p /app/results

# Démarrer le serveur web en arrière-plan
echo "   ▶️  HTTP server (port 8080)..."
python3 /app/server.py &
SERVER_PID=$!
echo "      ✅ PID: $SERVER_PID"

# Attendre que le serveur démarre
sleep 3

echo ""
echo "   ▶️  CT Monitor (crt.sh polling)..."
echo "      Domaines: $(echo $DOMAIN_COUNT)"

echo ""
echo "================================================"
echo "✅ Services lancés"
echo "================================================"
echo ""

# Démarrer le monitor (bloquant - se lance en avant-plan)
# C'est lui qui gère les notifications via notify.sh
python3 /app/certstream_monitor.py

# Si on arrive ici, le monitor s'est arrêté (erreur ou arrêt utilisateur)
echo ""
echo "❌ Monitor arrêté de manière inattendue"
echo "   Tentative de cleanup..."

# Tuer le serveur web
if [ -n "$SERVER_PID" ]; then
    kill $SERVER_PID 2>/dev/null || true
    echo "   ✅ Serveur web arrêté"
fi

exit 1
