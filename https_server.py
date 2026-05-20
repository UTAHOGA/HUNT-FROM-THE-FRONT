import http.server
import ssl
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8443
CERT = ROOT / "certs" / "localhost.crt"
KEY = ROOT / "certs" / "localhost.key"

os.chdir(ROOT)
handler = http.server.SimpleHTTPRequestHandler
httpd = http.server.ThreadingHTTPServer((HOST, PORT), handler)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ctx.load_cert_chain(certfile=str(CERT), keyfile=str(KEY))
httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
print(f"HTTPS server running at https://{HOST}:{PORT}")
httpd.serve_forever()
