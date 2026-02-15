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
DOMAINS=$(find "$RESULTS_DIR" -type f -exec cat {} \; 2>/dev/null | cut -d'|' -f1 | sort -u)

if [ -z "$DOMAINS" ]; then
    echo "ℹ️ No domains found"
    exit 0
fi

# Compter les domaines
COUNT=$(echo "$DOMAINS" | wc -l)

# Compter les dangling
DANGLING=$(find "$RESULTS_DIR" -type f -exec cat {} \; 2>/dev/null | grep -c "DANGLING" || echo "0")

# Compter les actifs (HTTP 200)
ACTIVE=$(find "$RESULTS_DIR" -type f -exec cat {} \; 2>/dev/null | grep -E "\|20[0-9]\|" | wc -l || echo "0")

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Sauvegarder les domaines dans un fichier temporaire
echo "$DOMAINS" > /tmp/domains_list.txt

# Message 1: Header avec stats
cat > /tmp/payload1.json <<EOF
{
  "embeds": [{
    "title": "🎯 New Subdomains Found",
    "description": "**Total:** $COUNT\n**Dangling DNS:** $DANGLING\n**Active (HTTP 200):** $ACTIVE",
    "color": 65280,
    "footer": {"text": "Gungnir CT Monitor"},
    "timestamp": "$TIMESTAMP"
  }]
}
EOF

# Envoyer message 1
HTTP_CODE=$(curl -s -o /tmp/response.txt -w "%{http_code}" \
    -X POST "$DISCORD_WEBHOOK" \
    -H "Content-Type: application/json" \
    -d @/tmp/payload1.json 2>/dev/null || echo "0")

if [ "$HTTP_CODE" != "204" ] && [ "$HTTP_CODE" != "200" ]; then
    echo "❌ Discord error on header (HTTP $HTTP_CODE)"
    exit 1
fi

# Message 2+: Domaines par chunks (max 25 domaines par message pour éviter la limite Discord)
CHUNK_SIZE=25
LINE_NUM=0
CHUNK_NUM=1

cat > /tmp/chunk_$CHUNK_NUM.txt << 'CHUNK'
CHUNK

while IFS= read -r domain; do
    LINE_NUM=$((LINE_NUM + 1))
    echo "\`$domain\`" >> /tmp/chunk_$CHUNK_NUM.txt
    
    if [ $((LINE_NUM % CHUNK_SIZE)) -eq 0 ]; then
        CHUNK_NUM=$((CHUNK_NUM + 1))
        cat > /tmp/chunk_$CHUNK_NUM.txt << 'CHUNK'
CHUNK
    fi
done < /tmp/domains_list.txt

# Envoyer les chunks
CHUNK_NUM=1
while [ -f /tmp/chunk_$CHUNK_NUM.txt ] && [ -s /tmp/chunk_$CHUNK_NUM.txt ]; do
    CHUNK_CONTENT=$(cat /tmp/chunk_$CHUNK_NUM.txt)
    
    cat > /tmp/payload_chunk.json <<EOF
{
  "embeds": [{
    "description": "$CHUNK_CONTENT",
    "color": 65280,
    "footer": {"text": "Gungnir CT Monitor - Part $CHUNK_NUM"}
  }]
}
EOF
    
    HTTP_CODE=$(curl -s -o /tmp/response.txt -w "%{http_code}" \
        -X POST "$DISCORD_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d @/tmp/payload_chunk.json 2>/dev/null || echo "0")
    
    if [ "$HTTP_CODE" = "204" ] || [ "$HTTP_CODE" = "200" ]; then
        echo "✅ Sent chunk $CHUNK_NUM (domains)"
    else
        echo "⚠️  Error chunk $CHUNK_NUM (HTTP $HTTP_CODE)"
    fi
    
    CHUNK_NUM=$((CHUNK_NUM + 1))
    sleep 1  # Rate limit Discord
done

echo "✅ Discord notification sent ($COUNT domains, $DANGLING dangling, $ACTIVE active)"

# Cleanup results
find "$RESULTS_DIR" -type f ! -name ".gitkeep" -exec sh -c '> "$1"' _ {} \;

# Cleanup temp
rm -f /tmp/payload*.json /tmp/response.txt /tmp/domains_list.txt /tmp/chunk_*.txt
