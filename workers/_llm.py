"""Optional LLM step for workers. Skips gracefully when no API key.

Uses the Anthropic API directly (billed separately from Claude Code session
limits) so LLM-assisted workers keep running when interactive usage is down.
Key resolution: ANTHROPIC_API_KEY env var, else secrets/anthropic_api_key.
"""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path

_KEY_FILE = Path(__file__).resolve().parents[1] / "secrets" / "anthropic_api_key"


def api_key() -> str | None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key and _KEY_FILE.exists():
        key = _KEY_FILE.read_text(encoding="utf-8").strip()
    return key or None


def complete(prompt: str, system: str = "", max_tokens: int = 1024,
             model: str = "claude-haiku-4-5-20251001") -> str | None:
    """One-shot completion. Returns None (worker should skip) if no key/error."""
    key = api_key()
    if not key:
        return None
    body = {"model": model, "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]}
    if system:
        body["system"] = system
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.load(resp)
        return "".join(b.get("text", "") for b in data.get("content", []))
    except Exception:
        return None
