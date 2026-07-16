"""video_scout — learn from top real-estate videos, queue our own posts (₹0 stack).

Per run:
1. DISCOVER: yt-dlp search for high-view Mumbai/Goregaon/Andheri real-estate
   videos → video_research (view counts, duration).
2. LEARN: pull auto-transcripts for the top unanalyzed videos, LLM-analyze
   hook/structure/why-it-works → analysis jsonb.
3. DRAFT: combine what performs with OUR reviewed video assets → review-gated
   social_post_drafts (title/description/tags/edit_spec). NOTHING auto-posts:
   operator approves, scripts/prep_short.sh renders, YouTube upload is a
   separate explicit step; Instagram is always manual (Lane A).

Run: python3 workers/video_scout.py
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import finding, log_run, one, q  # noqa: E402
from _llm_tiers import draft  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _db import jsonb_lit, sql_literal  # noqa: E402

WORKER = "video_scout"
SEARCHES = [
    "mumbai real estate market",
    "goregaon west apartment tour",
    "andheri west flat tour",
    "mumbai flat buying guide",
    "mumbai apartment walkthrough 2026",
]
ANALYZE_PER_RUN = 2   # transcripts + LLM per run — stays polite with YouTube
DRAFTS_PER_RUN = 2


def ytdlp(*args: str, timeout: int = 120) -> str:
    exe = shutil.which("yt-dlp")
    if not exe:
        raise RuntimeError("yt-dlp not installed (pip3 install yt-dlp)")
    res = subprocess.run([exe, *args], capture_output=True, text=True, timeout=timeout)
    return res.stdout


def discover() -> int:
    found = 0
    for query in SEARCHES:
        out = ytdlp("--flat-playlist",
                    "--print", "%(id)s\t%(title)s\t%(channel)s\t%(view_count)s\t%(duration)s",
                    f"ytsearch10:{query}", timeout=180)
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) != 5 or not parts[0]:
                continue
            vid, title, channel, views, duration = parts
            views_i = int(views) if views.isdigit() else 0
            if views_i < 10000:      # only learn from proven videos
                continue
            inserted = one(f"""
                INSERT INTO video_research (video_id, url, title, channel, views,
                                            duration_s, search_query)
                VALUES ({sql_literal(vid)},
                        {sql_literal('https://www.youtube.com/watch?v=' + vid)},
                        {sql_literal(title)}, {sql_literal(channel)}, {views_i},
                        {int(float(duration)) if duration.replace('.','',1).isdigit() else 'NULL'},
                        {sql_literal(query)})
                ON CONFLICT (video_id) DO UPDATE SET views = EXCLUDED.views,
                  updated_at = now()
                RETURNING (xmax = 0)::int""")
            found += int(inserted or 0)
        time.sleep(3)
    return found


def fetch_transcript(video_id: str, workdir: Path) -> str | None:
    ytdlp("-q", "--write-auto-sub", "--sub-lang", "en", "--skip-download",
          "--sub-format", "vtt", "-o", str(workdir / video_id),
          f"https://youtube.com/watch?v={video_id}", timeout=180)
    vtt = workdir / f"{video_id}.en.vtt"
    if not vtt.exists():
        return None
    seen, out = set(), []
    for line in vtt.read_text(encoding="utf-8").splitlines():
        line = re.sub(r"<[^>]+>", "", line).strip()
        if not line or "-->" in line or line.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        if line not in seen:
            seen.add(line)
            out.append(line)
    return " ".join(out)[:15000]


def parse_llm_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("no JSON in LLM output")
    return json.loads(m.group(0))


def analyze() -> int:
    # _lib.q splits psql output on '|' — strip pipes from free-text columns
    rows = q(f"""select video_id, replace(title,'|','-'), replace(coalesce(channel,''),'|','-'),
                        views from video_research
                 where status = 'found' order by views desc limit {ANALYZE_PER_RUN}""")
    workdir = Path("/tmp/video_scout")
    workdir.mkdir(exist_ok=True)
    done = 0
    for vid, title, channel, views in [r for r in rows if r and r[0]]:
        transcript = fetch_transcript(vid, workdir)
        if not transcript:
            q(f"UPDATE video_research SET status='ignored', updated_at=now() "
              f"WHERE video_id={sql_literal(vid)}")
            continue
        prompt = f"""Analyze why this real-estate YouTube video performs
({views} views). Title: {title} | Channel: {channel}

TRANSCRIPT (auto-captions):
{transcript[:12000]}

Return ONLY JSON:
{{"hook": "what the first 15s does", "structure": ["step1", ...],
 "topics": ["..."], "why_it_works": "2-3 sentences",
 "steal_ideas": ["concrete idea we can adapt for a Mumbai brokerage that owns
                  drone/interior footage of Goregaon & Andheri buildings", ...]}}"""
        text, run_id = draft(WORKER, "video_analysis", prompt)
        if not text:
            continue
        try:
            analysis = parse_llm_json(text)
        except Exception:
            continue
        q(f"""UPDATE video_research SET status='analyzed',
                transcript={sql_literal(transcript)},
                analysis={jsonb_lit(analysis)}, llm_run_id='{run_id}',
                updated_at=now()
              WHERE video_id={sql_literal(vid)}""")
        done += 1
        time.sleep(5)
    return done


def draft_posts() -> int:
    # our best raw material: video assets attached to a building
    assets = q("""select m.id, replace(coalesce(m.title,''),'|','-'),
                         replace(coalesce(m.caption,''),'|','-'),
                         b.id, replace(b.name,'|','-')
                  from media_assets m join buildings b on b.id = m.building_id
                  where m.media_type = 'video'
                    and not exists (select 1 from social_post_drafts d
                                    where d.media_asset_id = m.id
                                      and d.status <> 'rejected')
                  order by m.reviewed desc, m.created_at desc limit %d""" % DRAFTS_PER_RUN)
    lessons = q("""select analysis from video_research
                   where status='analyzed' order by views desc limit 5""")
    lessons_txt = "\n".join(r[0] for r in lessons if r and r[0])[:6000]
    if not lessons_txt:
        return 0
    made = 0
    for aid, title, caption, bid, bname in [r for r in assets if r and r[0]]:
        prompt = f"""You plan YouTube Shorts + long-form content for Real Deal
Housing, a Mumbai western-suburbs brokerage with its own drone/interior footage.

OUR ASSET: video "{title or 'untitled'}" ({caption or 'no caption'}) of
{bname}, our own footage.

WHAT PERFORMS (analyses of high-view real-estate videos):
{lessons_txt}

Draft ONE YouTube Shorts post using our asset. HARD RULES: no invented facts
about the building, no prices; hook in first line of the title; honest local
broker voice.

Return ONLY JSON:
{{"platform": "youtube_shorts", "title": "<70 chars, hook first",
 "description": "2-4 sentences + line: Full tours: www.realdealhousing.com",
 "tags": ["...", 5-8 items],
 "edit_spec": {{"crop": "9:16", "max_seconds": 45, "captions": true,
               "notes": "what to show first and why, based on the analyses"}}}}"""
        text, run_id = draft(WORKER, "post_draft", prompt)
        if not text:
            continue
        try:
            p = parse_llm_json(text)
        except Exception:
            continue
        q(f"""INSERT INTO social_post_drafts (media_asset_id, building_id, platform,
                title, description, tags, edit_spec, llm_run_id)
              VALUES ('{aid}', '{bid}', {sql_literal(p.get('platform','youtube_shorts'))},
                {sql_literal(p['title'])}, {sql_literal(p.get('description',''))},
                ARRAY[{','.join(sql_literal(t) for t in p.get('tags', []))}]::text[],
                {jsonb_lit(p.get('edit_spec', {}))}, '{run_id}')""")
        made += 1
    return made


def run() -> tuple[str, int, dict]:
    found = discover()
    analyzed = analyze()
    drafts = draft_posts()
    if drafts == 0 and analyzed == 0 and found == 0:
        finding(WORKER, "info", "video_scout_idle",
                "video_scout found nothing new — searches may be exhausted or YouTube throttled")
    summary = f"{found} videos found, {analyzed} analyzed, {drafts} post drafts"
    return summary, found + analyzed + drafts, {
        "found": found, "analyzed": analyzed, "post_drafts": drafts}


if __name__ == "__main__":
    sys.exit(0 if log_run(WORKER, run) else 1)
