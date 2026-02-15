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

# Message 2+: Domaines par chunks (max 25 domaines par message)
CHUNK_SIZE=25
LINE_NUM=0
CHUNK_NUM=1
CHUNK_CONTENT=""

while IFS= read -r domain; do
    if [ -z "$domain" ]; then
        continue
    fi
    
    # Ajouter le domaine avec backticks et newline
    if [ -z "$CHUNK_CONTENT" ]; then
        CHUNK_CONTENT="\`$domain\`"
    else
        CHUNK_CONTENT="$CHUNK_CONTENT\n\`$domain\`"
    fi
    
    LINE_NUM=$((LINE_NUM + 1))
    
    # Si on atteint la limite du chunk, envoyer
    if [ $((LINE_NUM % CHUNK_SIZE)) -eq 0 ]; then
        # Envoyer le chunk
        cat > /tmp/payload_chunk.json <<PAYLOAD
{
  "embeds": [{
    "description": "$CHUNK_CONTENT",
    "color": 65280,
    "footer": {"text": "Gungnir CT Monitor - Part $CHUNK_NUM"}
  }]
}
PAYLOAD
        
        HTTP_CODE=$(curl -s -o /tmp/response.txt -w "%{http_code}" \
            -X POST "$DISCORD_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d @/tmp/payload_chunk.json 2>/dev/null || echo "0")
        
        if [ "$HTTP_CODE" = "204" ] || [ "$HTTP_CODE" = "200" ]; then
            echo "✅ Sent chunk $CHUNK_NUM ($LINE_NUM domains)"
        else
            echo "⚠️ Error chunk $CHUNK_NUM (HTTP $HTTP_CODE)"
        fi
        
        # Reset pour prochain chunk
        CHUNK_NUM=$((CHUNK_NUM + 1))
        CHUNK_CONTENT=""
        sleep 1  # Rate limit Discord
    fi
done < /tmp/domains_list.txt

# Envoyer le dernier chunk s'il reste des domaines
if [ -n "$CHUNK_CONTENT" ]; then
    cat > /tmp/payload_chunk.json <<PAYLOAD
{
  "embeds": [{
    "description": "$CHUNK_CONTENT",
    "color": 65280,
    "footer": {"text": "Gungnir CT Monitor - Part $CHUNK_NUM"}
  }]
}
PAYLOAD
    
    HTTP_CODE=$(curl -s -o /tmp/response.txt -w "%{http_code}" \
        -X POST "$DISCORD_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d @/tmp/payload_chunk.json 2>/dev/null || echo "0")
    
    if [ "$HTTP_CODE" = "204" ] || [ "$HTTP_CODE" = "200" ]; then
        echo "✅ Sent chunk $CHUNK_NUM (final)"
    else
        echo "⚠️ Error chunk $CHUNK_NUM (HTTP $HTTP_CODE)"
    fi
fi

echo "✅ Discord notification sent ($COUNT domains, $DANGLING dangling, $ACTIVE active)"

# Cleanup results
find "$RESULTS_DIR" -type f ! -name ".gitkeep" -exec sh -c '> "$1"' _ {} \;

# Cleanup temp
rm -f /tmp/payload*.json /tmp/response.txt /tmp/domains_list.txt
