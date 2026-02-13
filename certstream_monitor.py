#!/usr/bin/env python3
import requests
import time
import os
from datetime import datetime

DOMAINS_FILE = 'domains.txt'
OUTPUT_DIR = 'results'
FIRST_RUN_FILE = '/app/.first_run_complete'
CHECK_INTERVAL = 300  # Attendre 5 minutes APRÈS la fin du cycle

# Charger les domaines à surveiller
with open(DOMAINS_FILE, 'r') as f:
    target_domains = [line.strip().lower() for line in f if line.strip()]

os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"Monitoring: {', '.join(target_domains)}")

# Vérifier si c'est la première exécution
is_first_run = not os.path.exists(FIRST_RUN_FILE)

if is_first_run:
    print("\n" + "="*80)
    print("PREMIERE EXECUTION - MODE INITIALISATION")
    print("Remplissage de la base de domaines existants...")
    print("AUCUNE notification ne sera envoyee pendant cette phase")
    print("="*80 + "\n")
else:
    print("\nMode monitoring normal - Notifications activees\n")

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
        print(f"\nError fetching crt.sh for {domain}: {e}")
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
        print(f"[{timestamp}] NEW: {domain}")
    
    # Enregistrer dans le fichier
    output_file = os.path.join(OUTPUT_DIR, target_domain)
    with open(output_file, 'a') as f:
        f.write(f"{domain}\n")

def monitor_loop():
    """Boucle principale de surveillance"""
    global is_first_run
    
    print("Starting Certificate Transparency monitor with crt.sh...")
    print(f"Waiting {CHECK_INTERVAL} seconds after each complete cycle\n")
    
    cycle_number = 0
    
    while True:
        try:
            cycle_number += 1
            cycle_start = time.time()
            
            # VÉRIFIER le statut d'initialisation au début de chaque cycle
            is_first_run = not os.path.exists(FIRST_RUN_FILE)
            
            print(f"\n{'='*80}")
            print(f"CYCLE #{cycle_number} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*80}")
            
            for idx, target in enumerate(target_domains, 1):
                if is_first_run:
                    print(f"\n[{idx}/{len(target_domains)}] Initializing {target}...", end=" ", flush=True)
                else:
                    print(f"\n[{idx}/{len(target_domains)}] Checking {target}...", end=" ", flush=True)
                
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
                    print(" OK")
                
                # Pause entre chaque domaine
                time.sleep(2)
            
            # Calculer la durée du cycle
            cycle_duration = int(time.time() - cycle_start)
            
            print(f"\n{'='*80}")
            print(f"CYCLE #{cycle_number} COMPLETE - Duration: {cycle_duration}s ({cycle_duration//60}m {cycle_duration%60}s)")
            print(f"{'='*80}")
            
            # Marquer la première exécution comme terminée AVANT d'appeler notify.sh
            if is_first_run:
                print("\n" + "="*80)
                print("INITIALISATION TERMINEE")
                print("Base de domaines existants remplie")
                print("Les notifications Discord seront maintenant envoyees")
                print("="*80 + "\n")
                
                with open(FIRST_RUN_FILE, 'w') as f:
                    f.write(datetime.now().isoformat())
            
            # Appeler notify.sh APRÈS CHAQUE cycle (init ou normal)
            if os.path.exists('./notify.sh'):
                if is_first_run:
                    print("Initializing seen_domains.txt (no notifications)...")
                else:
                    print("\nChecking for new domains and notifying...")
                os.system('./notify.sh')
            
            print(f"\nWaiting {CHECK_INTERVAL} seconds before next cycle...")
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\nMonitor stopped")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            print("Retrying in 30 seconds...")
            time.sleep(30)

if __name__ == "__main__":
    monitor_loop()

