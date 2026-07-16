"""content_scout — daily SEO worker on the ₹0 stack (ROADMAP §17 item 1).

Per run:
1. Pick the data-richest building with no draft yet → write one grounded SEO
   blog draft (Gemini free tier, qwen3 fallback) → seo_content_drafts (review-gated).
2. Search Reddit (public JSON, no auth, tagged UA) for Goregaon/Andheri/building
   threads → answer_opportunities.
3. Draft answers for up to 3 fresh finds → status 'drafted'.

NEVER posts anywhere, NEVER writes canonical tables. Operator approves in
/cockpit/seo and posts answers by hand (Lane A discipline).
Run: python3 workers/content_scout.py
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import log_run, one, q  # noqa: E402
from _llm_tiers import draft  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _db import jsonb_lit, sql_literal  # noqa: E402

WORKER = "content_scout"
SITE = "https://www.realdealhousing.com"
UA = "RealDealHousing content research (contact: hbanthiya@gmail.com)"
# site pages a draft may link to (only real URLs — never invent one)
PROJECT_PAGES = {
    "Imperial Heights": f"{SITE}/projects/imperial-heights",
    "Kalpataru Radiance": f"{SITE}/projects/kalpataru-radiance",
    "Ekta Tripolis": f"{SITE}/projects/ekta-tripolis",
    "DLF The Westpark": f"{SITE}/dlf-westpark",
}
REDDIT_QUERIES = [
    "Goregaon West flat buy",
    "Andheri West apartment advice",
    "Mumbai western suburbs real estate",
    "Imperial Heights Goregaon",
    "Kalpataru Radiance",
    "Ekta Tripolis",
]


# ── facts: everything comes from local Postgres, cited in sources ──────────
def building_facts(bid: str) -> tuple[dict, list[dict]]:
    sources: list[dict] = []
    b = q(f"""select name, coalesce(developer,''), coalesce(area,''),
                     coalesce(locality,''), city
              from buildings where id = '{bid}'""")[0]
    facts = {"name": b[0], "developer": b[1], "area": b[2] or b[3], "city": b[4]}
    sources.append({"table": "buildings", "id": bid})

    rera = q(f"""select rera_registration_number, coalesce(official_project_name,''),
                        coalesce(project_status,''), coalesce(promoter_name,'')
                 from rera_project_profiles where building_id = '{bid}'""")
    if rera and rera[0][0]:
        facts["rera"] = [{"number": r[0], "official_name": r[1],
                          "status": r[2], "promoter": r[3]} for r in rera]
        sources.append({"table": "rera_project_profiles", "building_id": bid})

    units = one(f"select count(*) from building_units where building_id = '{bid}'")
    if int(units or 0) > 0:
        facts["units_tracked"] = int(units)
        sources.append({"table": "building_units", "building_id": bid})

    towers = q(f"""select coalesce(tower_label,''), coalesce(floors_above_ground::text,'')
                   from building_tower_structure where building_id = '{bid}'
                   order by tower_label""")
    if towers and towers[0] and towers[0][0]:
        facts["towers"] = [{"tower": t[0], "floors": t[1]} for t in towers]
        sources.append({"table": "building_tower_structure", "building_id": bid})

    configs = q(f"""select distinct configuration_type from media_assets
                    where building_id = '{bid}' and configuration_type is not null
                    and configuration_type <> '' limit 10""")
    cfg = [c[0] for c in configs if c and c[0]]
    if cfg:
        facts["configurations_seen"] = cfg  # from our own floorplan/media archive
        sources.append({"table": "media_assets", "building_id": bid})
    return facts, sources


def pick_building() -> tuple[str, str] | None:
    rows = q("""
        select b.id, b.name from buildings b
        where not exists (select 1 from seo_content_drafts d
                          where d.building_id = b.id and d.status <> 'rejected')
        order by (select count(*) from building_units u where u.building_id = b.id) desc
        limit 1""")
    return (rows[0][0], rows[0][1]) if rows and rows[0] and rows[0][0] else None


def parse_llm_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("no JSON object in LLM output")
    return json.loads(m.group(0))


def draft_blog() -> int:
    target = pick_building()
    if not target:
        return 0
    bid, name = target
    facts, sources = building_facts(bid)
    link = PROJECT_PAGES.get(name)
    prompt = f"""You are the in-house content writer for Real Deal Housing, a
long-standing real-estate brokerage in Mumbai's western suburbs (Goregaon West,
Andheri West). Write an engaging, genuinely useful SEO blog post about the
building below for people researching a flat purchase or rent there.

HARD RULES:
- Use ONLY the verified facts given. NEVER invent prices, sizes, amenities,
  dates or availability. If a detail is not in the facts, do not mention it.
- Natural, specific, local voice — no marketing fluff, no "nestled in the heart of".
- 700-1000 words of markdown (## sections, short paragraphs).
- Weave in that we track this building registration-by-registration (that IS
  our edge and is true).
{('- Link naturally once to ' + link) if link else '- Do not include any links.'}

VERIFIED FACTS (from our Postgres registry + MahaRERA records):
{json.dumps(facts, indent=1)}

Return ONLY a JSON object:
{{"title": ..., "slug": "kebab-case-with-area", "excerpt": "1-2 sentences",
 "seo_title": "<60 chars", "seo_description": "<155 chars",
 "target_keywords": ["...", 4-6 items], "body_md": "the full markdown post"}}"""
    text, run_id = draft(WORKER, "blog_draft", prompt)
    if not text:
        return 0
    p = parse_llm_json(text)
    q(f"""INSERT INTO seo_content_drafts (kind, building_id, target_area, slug,
            title, excerpt, body_md, seo_title, seo_description, target_keywords,
            sources, llm_run_id)
          VALUES ('blog_post', '{bid}', {sql_literal(facts.get('area',''))},
            {sql_literal(p['slug'])}, {sql_literal(p['title'])},
            {sql_literal(p.get('excerpt',''))}, {sql_literal(p['body_md'])},
            {sql_literal(p.get('seo_title',''))}, {sql_literal(p.get('seo_description',''))},
            ARRAY[{','.join(sql_literal(k) for k in p.get('target_keywords', []))}]::text[],
            {jsonb_lit(sources)}, '{run_id}')
          ON CONFLICT (slug, kind) DO NOTHING""")
    return 1


# ── reddit discovery: official OAuth API (free script app, 100 QPM) ─────────
# Anonymous .json endpoints are 403-blocked since 2023. Operator creates a free
# "script" app at reddit.com/prefs/apps → drop id/secret into
# secrets/reddit_client_id + secrets/reddit_client_secret. Skips gracefully.
_SECRETS = Path(__file__).resolve().parents[1] / "secrets"
_reddit_token: str | None = None


def _secret(name: str) -> str | None:
    import os
    v = os.environ.get(name.upper(), "").strip()
    f = _SECRETS / name
    if not v and f.exists():
        v = f.read_text(encoding="utf-8").strip()
    return v or None


def reddit_token() -> str | None:
    global _reddit_token
    if _reddit_token:
        return _reddit_token
    cid, secret = _secret("reddit_client_id"), _secret("reddit_client_secret")
    if not cid or not secret:
        return None
    import base64
    req = urllib.request.Request(
        "https://www.reddit.com/api/v1/access_token",
        data=b"grant_type=client_credentials",
        headers={"User-Agent": UA,
                 "Authorization": "Basic " +
                 base64.b64encode(f"{cid}:{secret}".encode()).decode()})
    try:
        _reddit_token = json.load(urllib.request.urlopen(req, timeout=30))["access_token"]
    except Exception:
        return None
    return _reddit_token


def reddit_search(query: str) -> list[dict]:
    token = reddit_token()
    if not token:
        return []
    url = ("https://oauth.reddit.com/search?"
           + urllib.parse.urlencode({"q": query, "sort": "new", "t": "year", "limit": 10}))
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Authorization": f"Bearer {token}"})
    try:
        data = json.load(urllib.request.urlopen(req, timeout=30))
        return [c["data"] for c in data.get("data", {}).get("children", [])]
    except Exception:
        return []


def find_threads() -> int:
    if not reddit_token():
        from _lib import finding
        finding(WORKER, "setup_needed", "reddit_oauth_missing",
                "Reddit discovery skipped — create a free script app at "
                "reddit.com/prefs/apps and save secrets/reddit_client_id + "
                "secrets/reddit_client_secret")
        return 0
    found = 0
    for query in REDDIT_QUERIES:
        for post in reddit_search(query):
            url = "https://www.reddit.com" + post.get("permalink", "")
            title = post.get("title", "")
            if not title:
                continue
            inserted = one(f"""
                INSERT INTO answer_opportunities (platform, url, title, snippet,
                    community, thread_created, matched_area, relevance)
                VALUES ('reddit', {sql_literal(url)}, {sql_literal(title)},
                    {sql_literal(post.get('selftext', '')[:800])},
                    {sql_literal(post.get('subreddit', ''))},
                    to_timestamp({int(post.get('created_utc', 0))}),
                    {sql_literal(query)}, NULL)
                ON CONFLICT (url) DO NOTHING RETURNING id""")
            if inserted:
                found += 1
        time.sleep(2)  # ponytail: fixed pacing keeps us far under reddit's public limits
    return found


def draft_answers(limit: int = 3) -> int:
    rows = q(f"""select id, title, snippet, community, url from answer_opportunities
                 where status = 'found' order by thread_created desc nulls last
                 limit {limit}""")
    drafted = 0
    for rid, title, snippet, community, url in [r for r in rows if r and r[0]]:
        prompt = f"""You are a Mumbai western-suburbs real-estate expert answering on
r/{community}. Draft a reply to this thread.

THREAD TITLE: {title}
THREAD BODY: {snippet}

HARD RULES:
- Be genuinely helpful FIRST — answer their actual question from local knowledge
  of Goregaon West / Andheri West (registration process, RERA checks, carpet vs
  built-up, locality trade-offs). No sales pitch.
- Honest tone of a local broker who knows these buildings floor-by-floor.
- Disclose naturally: "I'm a broker in this area" — never hide it.
- Only if a Real Deal Housing page truly helps the asker, mention
  www.realdealhousing.com once. If not relevant, no link at all.
- 80-200 words, reddit-native tone, no markdown headers.

Return ONLY JSON: {{"answer_md": "...", "suggested_link": "url or empty",
"relevance": "one line: why this thread matters to us"}}"""
        text, run_id = draft(WORKER, "answer_draft", prompt)
        if not text:
            continue
        try:
            p = parse_llm_json(text)
        except Exception:
            continue
        q(f"""UPDATE answer_opportunities SET status = 'drafted',
                draft_answer_md = {sql_literal(p['answer_md'])},
                suggested_link = {sql_literal(p.get('suggested_link',''))},
                relevance = {sql_literal(p.get('relevance',''))},
                llm_run_id = '{run_id}', updated_at = now()
              WHERE id = '{rid}'""")
        drafted += 1
    return drafted


def run() -> tuple[str, int, dict]:
    blogs = draft_blog()
    threads = find_threads()
    answers = draft_answers()
    summary = f"{blogs} blog draft, {threads} new threads, {answers} answers drafted"
    return summary, blogs + threads + answers, {
        "blog_drafts": blogs, "threads_found": threads, "answers_drafted": answers}


if __name__ == "__main__":
    sys.exit(0 if log_run(WORKER, run) else 1)
