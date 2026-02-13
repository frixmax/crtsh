from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
from datetime import datetime

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # Page d'accueil
            results = 0
            if os.path.exists('/app/results'):
                results = len([f for f in os.listdir('/app/results') if os.path.isfile(f'/app/results/{f}')])
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = f"""
            <html>
            <head>
                <title>Gungnir Monitor</title>
                <meta http-equiv="refresh" content="30">
                <style>
                    body {{ font-family: Arial; padding: 40px; background: #1a1a1a; color: #fff; }}
                    h1 {{ color: #00ff88; }}
                    .status {{ color: #00ff88; font-weight: bold; }}
                    a {{ color: #00aaff; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                    .box {{ background: #2a2a2a; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <h1>🎯 Gungnir CT Monitor</h1>
                <div class="box">
                    <p><strong>Status:</strong> <span class="status">✅ Running</span></p>
                    <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                    <p><strong>Domains found:</strong> {results}</p>
                </div>
                <div class="box">
                    <p>📋 <a href="/new">View new domains (JSON)</a></p>
                    <p>📊 <a href="/all">View all domains (JSON)</a></p>
                </div>
                <p style="color: #666; font-size: 12px;">Auto-refresh every 30 seconds</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
            
        elif self.path == '/new':
            # Nouveaux domaines
            new_domains = []
            if os.path.exists('/app/new_domains.txt'):
                with open('/app/new_domains.txt', 'r') as f:
                    new_domains = [line.strip() for line in f if line.strip()]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "new_domains": new_domains,
                "count": len(new_domains),
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            
        elif self.path == '/all':
            # Tous les domaines
            all_domains = set()
            if os.path.exists('/app/results'):
                for file in os.listdir('/app/results'):
                    filepath = f'/app/results/{file}'
                    if os.path.isfile(filepath):
                        try:
                            with open(filepath, 'r') as f:
                                for line in f:
                                    line = line.strip()
                                    if line and '.' in line:
                                        all_domains.add(line)
                        except:
                            pass
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "domains": sorted(list(all_domains)),
                "count": len(all_domains),
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Gungnir Monitor - OK')

    def log_message(self, format, *args):
        # Silence les logs HTTP
        pass

httpd = HTTPServer(('', 8080), Handler)
print("🚀 HTTP Server started on port 8080")
httpd.serve_forever()
