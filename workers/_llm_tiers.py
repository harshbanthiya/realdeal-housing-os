"""₹0 LLM tiers for daily workers (ROADMAP §17 item 1).

Two tiers, both free:
- ollama: local qwen3:4b via the OpenAI-compatible endpoint. Unlimited volume,
  data never leaves the machine — the ONLY tier allowed to see contact PII.
- gemini: Gemini free API tier for long-form drafting (blog posts, answers).
  Key: GEMINI_API_KEY env var, else secrets/gemini_api_key. Public content
  only — free tier may use inputs for training, so PII never goes here.

Every call is logged to llm_runs. Drafting falls back gemini → ollama so the
pipeline still completes end-to-end with no API key at all.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

from _lib import q
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _db import sql_literal  # noqa: E402

OLLAMA_URL = "http://localhost:11434/v1/chat/completions"
OLLAMA_MODEL = "qwen3:4b"
GEMINI_MODEL = "gemini-flash-latest"  # new free-tier keys can't call pinned 2.5 names
_GEMINI_KEY_FILE = Path(__file__).resolve().parents[1] / "secrets" / "gemini_api_key"


def gemini_key() -> str | None:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key and _GEMINI_KEY_FILE.exists():
        key = _GEMINI_KEY_FILE.read_text(encoding="utf-8").strip()
    return key or None


def _log(worker: str, tier: str, model: str, purpose: str, prompt: str,
         output: str | None, ms: int, status: str, error: str = "") -> str:
    rows = q(f"""
        INSERT INTO llm_runs (worker, tier, model, purpose, prompt_chars,
                              output_chars, duration_ms, status, error,
                              prompt_head, output_head)
        VALUES ({sql_literal(worker)}, {sql_literal(tier)}, {sql_literal(model)},
                {sql_literal(purpose)}, {len(prompt)},
                {len(output) if output else 'NULL'}, {ms}, {sql_literal(status)},
                {sql_literal(error[:500]) if error else 'NULL'},
                {sql_literal(prompt[:400])},
                {sql_literal(output[:400]) if output else 'NULL'})
        RETURNING id""")
    return rows[0][0]


def _post_json(url: str, body: dict, headers: dict, timeout: int = 300) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def ollama(worker: str, purpose: str, prompt: str, system: str = "",
           schema: dict | None = None, max_tokens: int = 4096) -> tuple[str | None, str | None]:
    """Local call. Returns (text, llm_run_id). schema forces JSON output."""
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": prompt}]
    body: dict = {"model": OLLAMA_MODEL, "messages": msgs, "max_tokens": max_tokens,
                  "temperature": 0.4}
    if schema:
        body["response_format"] = {"type": "json_schema",
                                   "json_schema": {"name": "out", "schema": schema}}
    t0 = time.time()
    try:
        data = _post_json(OLLAMA_URL, body, {})
        text = data["choices"][0]["message"]["content"]
        run_id = _log(worker, "ollama", OLLAMA_MODEL, purpose, prompt, text,
                      int((time.time() - t0) * 1000), "ok")
        return text, run_id
    except Exception as e:  # worker skips gracefully; run still traced
        run_id = _log(worker, "ollama", OLLAMA_MODEL, purpose, prompt, None,
                      int((time.time() - t0) * 1000), "error", str(e))
        return None, run_id


def gemini(worker: str, purpose: str, prompt: str, system: str = "") -> tuple[str | None, str | None]:
    """Free-tier Gemini call. Returns (text, llm_run_id); (None, id) on skip/error."""
    key = gemini_key()
    if not key:
        run_id = _log(worker, "gemini", GEMINI_MODEL, purpose, prompt, None, 0,
                      "skipped", "no GEMINI_API_KEY")
        return None, run_id
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{GEMINI_MODEL}:generateContent")
    body: dict = {"contents": [{"parts": [{"text": prompt}]}]}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    t0 = time.time()
    try:
        data = _post_json(url, body, {"x-goog-api-key": key})
        text = "".join(p.get("text", "")
                       for p in data["candidates"][0]["content"]["parts"])
        run_id = _log(worker, "gemini", GEMINI_MODEL, purpose, prompt, text,
                      int((time.time() - t0) * 1000), "ok")
        return text, run_id
    except Exception as e:
        run_id = _log(worker, "gemini", GEMINI_MODEL, purpose, prompt, None,
                      int((time.time() - t0) * 1000), "error", str(e))
        return None, run_id


def openai_compat(worker: str, purpose: str, prompt: str, system: str = "") -> tuple[str | None, str | None]:
    """Generic free fallback: any OpenAI-compatible provider (Groq, Cerebras,
    OpenRouter, Mistral…). Configure via env or secrets/ files:
    OPENAI_COMPAT_URL (e.g. https://api.groq.com/openai/v1/chat/completions),
    OPENAI_COMPAT_KEY, OPENAI_COMPAT_MODEL. Skips when unconfigured."""
    def _cfg(name: str) -> str | None:
        v = os.environ.get(name.upper(), "").strip()
        f = Path(__file__).resolve().parents[1] / "secrets" / name.lower()
        if not v and f.exists():
            v = f.read_text(encoding="utf-8").strip()
        return v or None
    url, key, model = _cfg("openai_compat_url"), _cfg("openai_compat_key"), _cfg("openai_compat_model")
    if not (url and key and model):
        return None, None  # unconfigured — silent skip, no llm_runs noise
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": prompt}]
    t0 = time.time()
    try:
        data = _post_json(url, {"model": model, "messages": msgs},
                          {"authorization": f"Bearer {key}"})
        text = data["choices"][0]["message"]["content"]
        run_id = _log(worker, "openai_compat", model, purpose, prompt, text,
                      int((time.time() - t0) * 1000), "ok")
        return text, run_id
    except Exception as e:
        run_id = _log(worker, "openai_compat", model, purpose, prompt, None,
                      int((time.time() - t0) * 1000), "error", str(e))
        return None, run_id


def draft(worker: str, purpose: str, prompt: str, system: str = "") -> tuple[str | None, str | None]:
    """Best free drafting tier: gemini → any OpenAI-compatible free API → local ollama."""
    text, run_id = gemini(worker, purpose, prompt, system)
    if text:
        return text, run_id
    text, run_id2 = openai_compat(worker, purpose, prompt, system)
    if text:
        return text, run_id2
    return ollama(worker, purpose, prompt, system)
