#!/usr/bin/env python3
import certstream
import os
from datetime import datetime

DOMAINS_FILE = '/app/domains.txt'
OUTPUT_DIR = '/app/results'

# Charger les domaines à surveiller
with open(DOMAINS_FILE, 'r') as f:
    target_domains = [line.strip().lower() for line in f if line.strip()]

os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"🎯 Monitoring: {', '.join(target_domains)}")

def callback(message, context):
    if message['message_type'] == "certificate_update":
        all_domains = message['data']['leaf_cert']['all_domains']
        
        for domain in all_domains:
            domain_lower = domain.lower().lstrip('*.')
            
            # Vérifier si le domaine correspond à nos cibles
            for target in target_domains:
                if domain_lower.endswith(target) or domain_lower == target:
                    timestamp = datetime.now().isoformat()
                    print(f"[{timestamp}] Found: {domain}")
                    
                    # Enregistrer dans le fichier de résultats
                    output_file = os.path.join(OUTPUT_DIR, target)
                    with open(output_file, 'a') as f:
                        f.write(f"{domain}\n")

print("🚀 Starting Certificate Transparency monitor...")
print("⏳ Connecting to certstream...")

try:
    certstream.listen_for_events(callback, url='wss://certstream.calidog.io/')
except KeyboardInterrupt:
    print("\n🛑 Monitor stopped")
except Exception as e:
    print(f"❌ Error: {e}")
    print("🔄 Retrying in 10 seconds...")
    import time
    time.sleep(10)
    # Relancer
    os.execv(__file__, ['python3'] + [__file__])
