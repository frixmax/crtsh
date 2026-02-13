#!/usr/bin/env python3
import requests
import time
import os
from datetime import datetime

DOMAINS_FILE = 'domains.txt'
OUTPUT_DIR = 'results'
FIRST_RUN_FILE = '/app/.first_run_complete'
CHECK_INTERVAL = 300  # Vérifier toutes les 5 minutes

# Charger les domaines à surveiller
with open(DOMAINS_FILE, 'r') as f:
    target_domains = [line.strip().lower() for line in f if line.strip()]

os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"🎯 Monitoring: {', '.join(target_domains)}")

# Vérifier si c'est la première exécution
is_first_run = not os.path.exists(FIRST_RUN_FILE)

if is_first_run:
    print("\n" + "="*80)
    print("🔧 PREMIÈRE EXÉCUTION - MODE INITIALISATION")
    print("📝 Remplissage de la base de domaines existants...")
    print("⚠️  AUCUNE notification ne sera envoyée pendant cette phase")
    print("="*80 + "\n")
else:
    print("\n✅ Mode monitoring normal - Notifications activées\n")

# Pour éviter de retraiter les mêmes certificats
processed_certs = set()

def get_certificates_from_crtsh(domain):
    """Récupère tous les certificats d'un domaine depuis crt.sh"""
    try:
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"❌ Error fetching crt.sh for {domain}: {e}")
        return []

def process_certificate(cert_data, target_domain):
    """Traite un certificat trouvé"""
    domain = cert_data['name_value']
    cert_id = cert_data['id']
    
    # Identifier unique pour ce certificat
    cert_key = f"{domain}_{cert_id}"
    
    if cert_key in processed_certs:
        return
    
    processed_certs.add(cert_key)
    
    timestamp = datetime.now().isoformat()
    
    if is_first_run:
        # Mode silencieux - juste afficher un point de progression
        print(".", end="", flush=True)
    else:
        # Mode normal - afficher les nouveaux domaines
        print(f"[{timestamp}] 🆕 {domain}")
    
    # Enregistrer dans le fichier
    output_file = os.path.join(OUTPUT_DIR, target_domain)
    with open(output_file, 'a') as f:
        f.write(f"{domain}\n")

def monitor_loop():
    """Boucle principale de surveillance"""
    global is_first_run
    
    print("🚀 Starting Certificate Transparency monitor with crt.sh...")
    print(f"⏱️  Checking every {CHECK_INTERVAL} seconds\n")
    
    while True:
        try:
            for target in target_domains:
                if is_first_run:
                    print(f"\n📡 Initializing {target}...", end=" ", flush=True)
                else:
                    print(f"\n📡 Checking certificates for {target}...")
                
                certificates = get_certificates_from_crtsh(target)
                
                if certificates:
                    if not is_first_run:
                        print(f"Found {len(certificates)} certificates")
                    
                    # Trier par date (plus récents d'abord)
                    certificates.sort(key=lambda x: x.get('entry_timestamp', ''), reverse=True)
                    
                    # Traiter seulement les 10 plus récents
                    for cert in certificates[:10]:
                        domain_lower = cert['name_value'].lower().lstrip('*.')
                        
                        if domain_lower.endswith(target) or domain_lower == target:
                            process_certificate(cert, target)
                
                if is_first_run:
                    print(" ✓")
                
                # Pause entre chaque domaine
                time.sleep(2)
            
            # Après le premier cycle complet
            if is_first_run:
                print("\n" + "="*80)
                print("✅ INITIALISATION TERMINÉE")
                print("📊 Base de domaines existants remplie")
                print("🔔 Les notifications Discord seront maintenant envoyées")
                print("="*80 + "\n")
                
                # Marquer la première exécution comme terminée
                with open(FIRST_RUN_FILE, 'w') as f:
                    f.write(datetime.now().isoformat())
                
                is_first_run = False
                
                # Appeler notify.sh pour initialiser seen_domains.txt
                if os.path.exists('./notify.sh'):
                    print("📝 Initializing seen_domains.txt...")
                    os.system('./notify.sh')
            
            print(f"\n⏳ Waiting {CHECK_INTERVAL} seconds before next check...")
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n🛑 Monitor stopped")
            break
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            print("🔄 Retrying in 30 seconds...")
            time.sleep(30)

if __name__ == "__main__":
    monitor_loop()
```

## **Comment ça fonctionne :**

### **1ère exécution (initialisation) :**
```
🔧 PREMIÈRE EXÉCUTION - MODE INITIALISATION
📝 Remplissage de la base de domaines existants...
⚠️  AUCUNE notification ne sera envoyée

📡 Initializing aswatson.com... ............ ✓
📡 Initializing iciparisxl.be... .......... ✓

✅ INITIALISATION TERMINÉE
📊 Base de domaines existants remplie
🔔 Les notifications Discord seront maintenant envoyées
```

### **2ème exécution et suivantes :**
```
✅ Mode monitoring normal - Notifications activées

📡 Checking certificates for aswatson.com...
[2026-02-13T10:30:00] 🆕 new-api.aswatson.com
[2026-02-13T10:30:01] 🆕 test.aswatson.com
