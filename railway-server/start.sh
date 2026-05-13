#!/bin/bash
PORT=${PORT:-8080}
echo "=== START.SH === python: $(python3 --version 2>&1) port: $PORT"
gunicorn --workers 1 --threads 4 --worker-class gthread --timeout 30 --bind 0.0.0.0:$PORT server:app 2>&1
echo "=== GUNICORN SALIÓ CON CÓDIGO: $? ==="
echo "Iniciando servidor de diagnóstico en puerto $PORT..."
python3 -u -c "
import os, sys, http.server, socketserver, threading

PORT = int(os.environ.get('PORT', 8080))
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'GUNICORN FAILED - VER LOGS ARRIBA')
    def log_message(self, *a): pass

print(f'[diag] Servidor en {PORT}', flush=True)
with socketserver.TCPServer(('0.0.0.0', PORT), H) as srv:
    srv.serve_forever()
"
