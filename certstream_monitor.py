#!/usr/bin/env python3
import requests
import time
import os
import ssl
import socket
from datetime import datetime

DOMAINS_FILE = 'domains.txt'
OUTPUT_DIR = 'results'
CHECK_INTERVAL = 300  # Vérifier toutes les 5 minutes

# Charger les domaines à surveiller
with open(DOMAINS_FILE, 'r') as f:
    target_domains = [line.strip().lower() for line in f if line.strip()]

os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"🎯 Monitoring: {', '.join(target_domains)}")

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

def check_ssl_issues(domain):
    """Vérifie les problèmes SSL d'un domaine en temps réel"""
    issues = []
    cert_info = {}
    
    # Nettoyer le domaine (enlever les wildcards)
    clean_domain = domain.lstrip('*.')
    
    try:
        context = ssl.create_default_context()
        
        with socket.create_connection((clean_domain, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=clean_domain) as ssock:
                cert = ssock.getpeercert()
                cert_info = {
                    'issuer': dict(x[0] for x in cert['issuer']),
                    'subject': dict(x[0] for x in cert['subject']),
                    'notAfter': cert['notAfter'],
                    'notBefore': cert['notBefore'],
                    'subjectAltName': cert.get('subjectAltName', [])
                }
                
                # Vérifier expiration
                not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
                if not_after < datetime.now():
                    issues.append("EXPIRED")
                
                # Vérifier self-signed
                if cert_info['issuer'] == cert_info['subject']:
                    issues.append("SELF-SIGNED")
                
                # Vérifier correspondance du nom
                sans = [x[1] for x in cert.get('subjectAltName', [])]
                if clean_domain not in sans and f"*.{'.'.join(clean_domain.split('.')[1:])}" not in sans:
                    issues.append("NAME_MISMATCH")
                
    except ssl.SSLError as e:
        issues.append(f"SSL_ERROR: {str(e)}")
    except socket.timeout:
        issues.append("TIMEOUT")
    except socket.gaierror:
        issues.append("DNS_ERROR")
    except ConnectionRefusedError:
        issues.append("CONNECTION_REFUSED")
    except Exception as e:
        issues.append(f"ERROR: {str(e)}")
    
    return issues, cert_info

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
    print(f"[{timestamp}] 🔍 Found: {domain}")
    
    # Vérifier les problèmes SSL
    issues, cert_info = check_ssl_issues(domain)
    
    # Enregistrer TOUT dans le même fichier
    output_file = os.path.join(OUTPUT_DIR, target_domain)
    with open(output_file, 'a') as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"[{timestamp}] {domain}\n")
        f.write(f"Certificate ID: {cert_id}\n")
        
        if issues:
            f.write(f"⚠️  Issues: {', '.join(issues)}\n")
            print(f"⚠️  Issues detected: {', '.join(issues)}")
        else:
            f.write(f"✅ Status: OK\n")
            print(f"✅ No issues")
        
        if cert_info:
            f.write(f"Issuer: {cert_info.get('issuer', {}).get('organizationName', 'N/A')}\n")
            f.write(f"Valid until: {cert_info.get('notAfter', 'N/A')}\n")
        
        f.write(f"{'='*80}\n")
    
    # Notifier seulement si problème
    if issues and os.path.exists('./notify.sh'):
        os.system(f'./notify.sh "{domain}" "{", ".join(issues)}"')

def monitor_loop():
    """Boucle principale de surveillance"""
    print("🚀 Starting Certificate Transparency monitor with crt.sh...")
    print(f"⏱️  Checking every {CHECK_INTERVAL} seconds")
    
    while True:
        try:
            for target in target_domains:
                print(f"\n📡 Checking certificates for {target}...")
                
                certificates = get_certificates_from_crtsh(target)
                
                if certificates:
                    print(f"Found {len(certificates)} certificates for {target}")
                    
                    # Trier par date (plus récents d'abord)
                    certificates.sort(key=lambda x: x.get('entry_timestamp', ''), reverse=True)
                    
                    # Traiter seulement les 10 plus récents pour éviter la surcharge
                    for cert in certificates[:10]:
                        domain_lower = cert['name_value'].lower().lstrip('*.')
                        
                        if domain_lower.endswith(target) or domain_lower == target:
                            process_certificate(cert, target)
                
                # Pause entre chaque domaine pour éviter de surcharger crt.sh
                time.sleep(2)
            
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
