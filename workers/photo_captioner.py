"""photo_captioner — SEO alt-text/titles/tags for the photo archive (₹0 stack).

3,677 photos have no alt text. Per run this captions PHOTOS_PER_RUN of them
via Gemini free-tier vision, preferring photos attached to a building.
Writes alt_text/seo_title/tags ONLY where empty, stamps
metadata.ai_captioned=true, and never touches the reviewed flag — operator
reviews in /cockpit/media as usual. At 15/run the archive is done in ~8 months
of daily runs, or run it in a loop overnight to finish in days:
  while python3 workers/photo_captioner.py; do sleep 60; done
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import log_run, q  # noqa: E402
from _llm_tiers import gemini_vision  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _db import jsonb_lit, sql_literal  # noqa: E402

WORKER = "photo_captioner"
PHOTOS_PER_RUN = 15  # gentle on the shared Gemini free-tier daily quota
DAILY_CAP = 200      # hard stop so the 30-min launchd loop can't exhaust the
                     # free tier that content_scout/video_scout also depend on


def parse_llm_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("no JSON in output")
    return json.loads(m.group(0))


def run() -> tuple[str, int, dict]:
    today = q("""select count(*) from llm_runs
                 where worker='photo_captioner' and status='ok'
                   and created_at >= date_trunc('day', now())""")[0][0]
    if int(today) >= DAILY_CAP:
        return (f"daily cap reached ({today}/{DAILY_CAP}) — resumes tomorrow",
                0, {"capped": True})
    rows = q(f"""
        select m.id, m.file_path, replace(coalesce(b.name,''),'|','-'),
               replace(coalesce(m.configuration_type,''),'|','-'),
               replace(coalesce(m.asset_type,''),'|','-')
        from media_assets m left join buildings b on b.id = m.building_id
        where m.media_type = 'photo' and coalesce(m.alt_text,'') = ''
          and coalesce(m.metadata->>'ai_caption_failed','') = ''
        order by m.building_id is not null desc, m.created_at desc
        limit {PHOTOS_PER_RUN}""")
    captioned = skipped = 0
    for mid, path, bname, config, atype in [r for r in rows if r and r[0]]:
        if not path or not Path(path).exists():
            q(f"""update media_assets set metadata = coalesce(metadata,'{{}}'::jsonb)
                  || '{{"ai_caption_failed":"file_missing"}}'::jsonb where id='{mid}'""")
            skipped += 1
            continue
        ctx = ", ".join(x for x in [bname, config, atype] if x)
        prompt = f"""This is a real-estate photo{' related to: ' + ctx if ctx else ''}
(Mumbai western suburbs — Goregaon West / Andheri West). Write SEO metadata.
RULES: describe only what is visible; no invented amenities or prices; natural
Indian-English; alt_text ≤ 125 chars; seo_title ≤ 60 chars.
Return ONLY JSON: {{"alt_text": "...", "seo_title": "...",
"tags": ["...", 4-8 lowercase items like 'living room','sea view','drone']}}"""
        text, run_id = gemini_vision(WORKER, "photo_caption", prompt, path)
        if not text:
            skipped += 1
            time.sleep(45)  # free tier throttles per-minute — back off, item retries next cycle
            continue
        try:
            p = parse_llm_json(text)
        except Exception:
            skipped += 1
            continue
        tags = ",".join(sql_literal(t) for t in p.get("tags", [])[:8])
        q(f"""update media_assets set
                alt_text = {sql_literal(p['alt_text'][:200])},
                seo_title = coalesce(nullif(seo_title,''), {sql_literal(p.get('seo_title','')[:100])}),
                tags = case when tags is null or tags = '{{}}' then
                       ARRAY[{tags}]::text[] else tags end,
                metadata = coalesce(metadata,'{{}}'::jsonb) ||
                           {jsonb_lit({'ai_captioned': True, 'ai_caption_run': run_id})},
                updated_at = now()
              where id = '{mid}' and coalesce(alt_text,'') = ''""")
        captioned += 1
        time.sleep(8)  # ~7 RPM keeps us under the free-tier per-minute limit
    remaining = q("""select count(*) from media_assets
                     where media_type='photo' and coalesce(alt_text,'')=''""")[0][0]
    return (f"{captioned} captioned, {skipped} skipped, {remaining} remaining",
            captioned, {"captioned": captioned, "skipped": skipped,
                        "remaining": int(remaining)})


if __name__ == "__main__":
    ok = log_run(WORKER, run)
    sys.exit(0 if ok else 1)
