"""mitmproxy addon: dump only MyGate API calls (req + JSON resp) to disk.

Usage:
    mitmweb -s scripts/mygate_capture.py
Then proxy your iPhone through this Mac (see notes at bottom).
Captured flows land in scratchpad/mygate_flows/ as one JSON file per call.

ponytail: host match is a broad substring; tighten HOSTS once you see the real API domain.
"""
import json
import os
import time

OUT = os.path.join(os.path.dirname(__file__), "..", "captures", "mygate_flows")
os.makedirs(OUT, exist_ok=True)

# Any host containing one of these substrings is captured. Widen/narrow after first look.
HOSTS = ("mygate",)

_n = 0


def _match(host: str) -> bool:
    return any(h in host.lower() for h in HOSTS)


def response(flow):
    global _n
    if not _match(flow.request.pretty_host):
        return
    _n += 1
    body = flow.response.get_text() or ""
    try:
        parsed = json.loads(body)
    except Exception:
        parsed = None  # non-JSON (html, binary) — keep raw text
    rec = {
        "ts": time.time(),
        "method": flow.request.method,
        "url": flow.request.pretty_url,
        "req_headers": dict(flow.request.headers),
        "req_body": flow.request.get_text() if flow.request.content else None,
        "status": flow.response.status_code,
        "resp_json": parsed,
        "resp_raw": None if parsed is not None else body[:5000],
    }
    safe = flow.request.path.strip("/").replace("/", "_")[:60] or "root"
    fn = os.path.join(OUT, f"{_n:04d}_{flow.request.method}_{safe}.json")
    with open(fn, "w") as f:
        json.dump(rec, f, indent=2)
    print(f"[mygate] {flow.request.method} {flow.request.pretty_url} -> {flow.response.status_code}  saved {os.path.basename(fn)}")
