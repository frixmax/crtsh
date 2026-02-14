import requests
import time
import os
import sys
from datetime import datetime, timedelta
import json

DOMAINS_FILE = 'domains.txt'
OUTPUT_DIR = 'results'
FIRST_RUN_FILE = '/app/.first_run_complete'
CHECK_INTERVAL = 300  # 5 min
SEEN_FILE = '/app/seen_domains.txt'

# Vérifications au démarrage
if not os.path.exists(DOMAINS_FILE):
    print(f"❌ ERREUR: {DOMAINS_FILE} n'existe pas!", file=sys.stderr)
    sys.exit(1)

# Charger domaines avec validation
try:
    with open(DOMAINS_FILE, 'r') as f:
        target_domains = [line.strip().lower() for line in f if line.strip() and not line.startswith('#')]
    
    if not target_domains:
        print(f"❌ ERREUR: {DOMAINS_FILE} est vide!", file=sys.stderr)
        sys.exit(1)
        
except Exception as e:
    print(f"❌ ERREUR lecture {DOMAINS_FILE}: {e}", file=sys.stderr)
    sys.exit(1)

os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"Monitoring: {', '.join(target_domains)}", flush=True)

# ============================================================================
# CORRECTION #1: Gérer correctement le flag first_run
# ============================================================================
is_first_run = not os.path.exists(FIRST_RUN_FILE)

# Déduplication globale
processed_certs = set()

# Charger les domaines déjà vus
def load_seen_domains():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, 'r') as f:
                return set(line.strip().lower() for line in f if line.strip())
        except Exception as e:
            print(f"⚠️ Erreur lecture {SEEN_FILE}: {e}", file=sys.stderr)
            return set()
    return set()

def save_seen_domain(domain):
    try:
        with open(SEEN_FILE, 'a') as f:
            f.write(f"{domain}\n")
    except Exception as e:
        print(f"⚠️ Erreur écriture {SEEN_FILE}: {e}", file=sys.stderr)

seen_domains = load_seen_domains()
print(f"📊 {len(seen_domains)} domaines déjà vus", flush=True)

def get_certificates_from_crtsh(domain):
    # CORRECTION #2: Réduire à 2 jours au lieu de 7
    min_date = (datetime.utcnow() - timedelta(days=2)).strftime('%Y-%m-%d')
    try:
        url = f"https://crt.sh/?q=%.{domain}&output=json&minNotBefore={min_date}"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data if isinstance(data, list) else []
        return []
    except Exception as e:
        print(f"⚠️ Erreur crt.sh {domain}: {e}", file=sys.stderr, flush=True)
        return []

def is_subdomain_of_target(domain, target):
    """Vérifie si domain est un sous-domaine de target"""
    domain_lower = domain.lower().lstrip('*.')
    return domain_lower.endswith(target) or domain_lower == target

def process_certificate(cert_data, target_domain):
    try:
        cert_id = str(cert_data.get('id', ''))
        if not cert_id or cert_id in processed_certs:
            return
        processed_certs.add(cert_id)
        
        domain = cert_data.get('name_value', '').strip().lower()
        if not domain:
            return
        
        # CORRECTION #3: Valider le domaine AVANT de vérifier seen_domains
        if not is_subdomain_of_target(domain, target_domain):
            return
        
        domain_clean = domain.lstrip('*.')
        
        # Vérifier si déjà vu
        if domain_clean in seen_domains:
            return
        
        # CORRECTION #4: Enregistrer AVANT de filtrer sur first_run
        seen_domains.add(domain_clean)
        save_seen_domain(domain_clean)
        
        timestamp = datetime.now().isoformat()
        
        # Au 1er run: enregistrer mais pas d'output file
        if is_first_run:
            print(".", end="", flush=True)
            return
        
        # Nouveau domaine détecté (après le 1er run)
        print(f"[{timestamp}] NEW: {domain_clean}", flush=True)
        output_file = os.path.join(OUTPUT_DIR, target_domain.replace('.', '_'))
        try:
            with open(output_file, 'a') as f:
                f.write(f"{domain_clean}\n")
        except Exception as e:
            print(f"⚠️ Erreur écriture {output_file}: {e}", file=sys.stderr, flush=True)
            
    except Exception as e:
        print(f"⚠️ Erreur traitement certificat: {e}", file=sys.stderr, flush=True)

def monitor_loop():
    global is_first_run
    cycle_number = 0
    
    while True:
        try:
            cycle_number += 1
            cycle_start = time.time()
            
            # CORRECTION #5: Vérifier le flag à chaque cycle
            is_first_run = not os.path.exists(FIRST_RUN_FILE)
            
            print(f"\n=== CYCLE #{cycle_number} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===", flush=True)
            
            for idx, target in enumerate(target_domains, 1):
                print(f"[{idx}/{len(target_domains)}] Checking {target}...", end=" ", flush=True)
                certificates = get_certificates_from_crtsh(target)
                
                if certificates:
                    certificates.sort(key=lambda x: x.get('entry_timestamp', ''), reverse=True)
                    for cert in certificates[:15]:
                        process_certificate(cert, target)
                
                print("OK", flush=True)
                time.sleep(2)
            
            cycle_duration = int(time.time() - cycle_start)
            print(f"\nCycle terminé en {cycle_duration}s", flush=True)
            
            # CORRECTION #6: Gérer le 1er run correctement
            if is_first_run:
                print("✅ Initialisation terminée → notifications activées au prochain cycle", flush=True)
                with open(FIRST_RUN_FILE, 'w') as f:
                    f.write(datetime.now().isoformat())
                # Vider results/ pour ne pas déclencher de fausses alertes
                for target in target_domains:
                    output_file = os.path.join(OUTPUT_DIR, target.replace('.', '_'))
                    if os.path.exists(output_file):
                        try:
                            os.remove(output_file)
                        except Exception as e:
                            print(f"⚠️ Erreur suppression {output_file}: {e}", file=sys.stderr, flush=True)
            else:
                # CORRECTION #7: Appel notify.sh SEULEMENT après le 1er run
                print("📢 Lancement notification...", flush=True)
                ret = os.system('./notify.sh')
                if ret != 0:
                    print(f"⚠️ notify.sh returned {ret}", file=sys.stderr, flush=True)
            
            print(f"💤 Attente {CHECK_INTERVAL}s avant prochain cycle...", flush=True)
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n⚠️ Arrêt demandé par l'utilisateur", flush=True)
            break
        except Exception as e:
            print(f"\n❌ ERREUR dans monitor_loop: {e}", file=sys.stderr, flush=True)
            import traceback
            traceback.print_exc()
            print("Attente 60s avant retry...", flush=True)
            time.sleep(60)

if __name__ == "__main__":
    try:
        monitor_loop()
    except Exception as e:
        print(f"❌ ERREUR FATALE: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
