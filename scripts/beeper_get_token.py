#!/usr/bin/env python3
"""One-time OAuth PKCE flow to mint a Beeper Desktop API token for the
ingest worker. Opens browser; approve in Beeper Desktop; token lands in
secrets/beeper_access_token. Re-run any time to rotate.
"""
import base64
import hashlib
import http.server
import json
import secrets as pysecrets
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:23373"
PORT = 8976
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "secrets" / "beeper_access_token"

# register a fresh public client each run (registration is open + local-only)
reg = json.loads(
    urllib.request.urlopen(
        urllib.request.Request(
            f"{BASE}/oauth/register",
            data=json.dumps(
                {
                    "client_name": "RDH ingest worker",
                    "redirect_uris": [f"http://127.0.0.1:{PORT}/cb"],
                    "grant_types": ["authorization_code"],
                    "response_types": ["code"],
                    "token_endpoint_auth_method": "none",
                }
            ).encode(),
            headers={"Content-Type": "application/json"},
        ),
        timeout=10,
    ).read()
)
client_id = reg["client_id"]

verifier = base64.urlsafe_b64encode(pysecrets.token_bytes(48)).rstrip(b"=").decode()
challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
state = pysecrets.token_urlsafe(16)

auth_url = f"{BASE}/oauth/authorize?" + urllib.parse.urlencode(
    {
        "client_id": client_id,
        "redirect_uri": f"http://127.0.0.1:{PORT}/cb",
        "response_type": "code",
        "scope": "read",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
)

code_holder = {}


class CB(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        code_holder.update({k: v[0] for k, v in q.items()})
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Token captured - close this tab.")

    def log_message(self, *a):
        pass


print(f"Opening approval page...\nIf no browser opens, visit:\n{auth_url}\n")
subprocess.run(["open", auth_url], check=False)
srv = http.server.HTTPServer(("127.0.0.1", PORT), CB)
srv.timeout = 180
while "code" not in code_holder and "error" not in code_holder:
    srv.handle_request()
srv.server_close()

if "error" in code_holder:
    raise SystemExit(f"Denied: {code_holder}")
assert code_holder.get("state") == state, "state mismatch"

tok = json.loads(
    urllib.request.urlopen(
        urllib.request.Request(
            f"{BASE}/oauth/token",
            data=urllib.parse.urlencode(
                {
                    "grant_type": "authorization_code",
                    "code": code_holder["code"],
                    "redirect_uri": f"http://127.0.0.1:{PORT}/cb",
                    "client_id": client_id,
                    "code_verifier": verifier,
                }
            ).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ),
        timeout=10,
    ).read()
)
OUT.write_text(tok["access_token"] + "\n")
OUT.chmod(0o600)
print(f"OK: token saved to {OUT}")
