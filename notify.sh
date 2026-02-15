#!/bin/sh
set -e

RESULTS_DIR="/app/results"
DISCORD_WEBHOOK="https://discord.com/api/webhooks/1472487929862684703/a4vMYqiwQO6c1VLRXNpv4w09kC2yTq-Rtdm4VkEBjsca6hfKZ6ARalPq4dvpTYoYHniu"

# Vérifier s'il y a des résultats
if [ ! -d "$RESULTS_DIR" ] || [ -z "$(find $RESULTS_DIR -type f -size +0 2>/dev/null | head -1)" ]; then
    echo "ℹ️ No results to notify"
    exit 0
fi

# Extraire tous les domaines
DOMAINS=$(find "$RESULTS_DIR" -type f -exec cat {} \; 2>/dev/null | sort -u | head -100)

if [ -z "$DOMAINS" ]; then
    echo "ℹ️ No domains found"
    exit 0
fi

# Compter les domaines
COUNT=$(echo "$DOMAINS" | wc -l)

# Compter les dangling
DANGLING=$(echo "$DOMAINS" | grep -c "DANGLING" || echo "0")

# Compter les actifs (HTTP 200)
ACTIVE=$(echo "$DOMAINS" | grep -E "\|20[0-9]\|" | wc -l || echo "0")

# Formater la liste
DOMAIN_LIST=$(echo "$DOMAINS" | cut -d'|' -f1 | tr '\n' ',' | sed 's/,/, /g' | sed 's/, $//')

# Limiter à 2000 chars pour Discord
DOMAIN_LIST=$(echo "$DOMAIN_LIST" | cut -c1-2000)

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Créer le payload JSON
cat > /tmp/payload.json <<EOF
{
  "embeds": [{
    "title": "🎯 New Subdomains Found ($COUNT)",
    "description": "$DOMAIN_LIST",
    "fields": [
      {"name": "💾 Total", "value": "$COUNT", "inline": true},
      {"name": "⚠️ Dangling DNS", "value": "$DANGLING", "inline": true},
      {"name": "✅ Active (HTTP 200)", "value": "$ACTIVE", "inline": true}
    ],
    "color": 65280,
    "footer": {"text": "Gungnir CT Monitor"},
    "timestamp": "$TIMESTAMP"
  }]
}
EOF

# Envoyer à Discord
HTTP_CODE=$(curl -s -o /tmp/response.txt -w "%{http_code}" \
    -X POST "$DISCORD_WEBHOOK" \
    -H "Content-Type: application/json" \
    -d @/tmp/payload.json 2>/dev/null || echo "0")

if [ "$HTTP_CODE" = "204" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Discord notification sent ($COUNT domains, $DANGLING dangling)"
else
    echo "❌ Discord error (HTTP $HTTP_CODE)"
fi

# Cleanup results
find "$RESULTS_DIR" -type f ! -name ".gitkeep" -exec sh -c '> "$1"' _ {} \;

# Cleanup temp
rm -f /tmp/payload.json /tmp/response.txt
