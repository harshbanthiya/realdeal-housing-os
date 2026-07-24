"""shorts_scout — keep next week's Shorts drafted and waiting for approval.

Every 30 minutes this looks at what reviewed footage and imagery we hold per
building, and — if the shelf is thin — drafts one more Short: Remotion scenes
(edit_spec), SEO title/description/tags, and a matching blog draft. Everything
lands as status='draft' for the operator in /cockpit/seo. Nothing renders,
nothing uploads, nothing publishes.

It only ever draws on media_assets where reviewed = TRUE. That is deliberate:
un-reviewed footage has not been checked for anything embarrassing, and the
review queue at /cockpit/review is the gate. When a building has footage but
none of it reviewed, this records a finding instead of a draft — which is the
signal that the operator's media cohorts are what unblocks content.

Copy rules enforced here (docs/YOUTUBE-WORKFLOW.md):
  - building name leads the title; it IS the keyword
  - never a flat number — configuration only ("3.5 BHK")
  - description carries wa.me, the UTM'd site link, music credit, hashtags

Run: python3 workers/shorts_scout.py [--status] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import finding, log_run, one, q  # noqa: E402
from _llm_tiers import draft as llm_draft  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _db import jsonb_lit, sql_literal as lit  # noqa: E402

WORKER = "shorts_scout"

SHELF_TARGET = 3          # keep this many unapproved shorts waiting
SCENES_PER_SHORT = 5
PHONE = "+91 829 129 3889"
WA_LINK = "https://wa.me/918291293889"
SITE = "https://www.realdealhousing.com"

# A flat number in public copy is the one unrecoverable mistake here.
FLAT_NUMBER = re.compile(r"\b[A-D]\s?-\s?\d{3,4}\b|\bflat\s*(no\.?|number)?\s*\d+", re.I)

SCENE_ORDER = ["exterior", "amenity", "interior", "master_layout", "floor_plan"]


def pg_array(items: list[str]) -> str:
    """Python list → a Postgres text[] literal (lit() would emit Python repr)."""
    return "{" + ",".join('"' + str(i).replace("\\", "").replace('"', "") + '"' for i in items) + "}"


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def shelf_count() -> int:
    return int(one("""SELECT count(*) FROM social_post_drafts
                       WHERE status = 'draft' AND platform = 'youtube'""") or 0)


def building_readiness() -> list[dict]:
    """Per building: reviewed assets we could actually cut, and recent drafts."""
    rows = q("""
        SELECT b.id::text, b.name, coalesce(b.locality, b.city, ''),
               count(*) FILTER (WHERE m.reviewed AND m.asset_type IS NOT NULL
                                  AND m.asset_type <> 'brochure')::text,
               count(*) FILTER (WHERE NOT m.reviewed)::text,
               (SELECT count(*) FROM social_post_drafts s
                 WHERE s.building_id = b.id AND s.status IN ('draft','approved','rendered'))::text
          FROM buildings b
          LEFT JOIN media_assets m ON m.building_id = b.id
         GROUP BY b.id, b.name, b.locality, b.city
         ORDER BY 4::int DESC
    """)
    return [{"id": r[0], "name": r[1], "area": r[2],
             "reviewed": int(r[3]), "unreviewed": int(r[4]), "queued": int(r[5])}
            for r in rows]


def pick_scenes(building_id: str) -> list[dict]:
    """Reviewed assets, ordered so the cut opens wide and moves inward."""
    rows = q(f"""
        SELECT coalesce(m.asset_type,''), regexp_replace(m.file_path,'^.*/',''),
               coalesce(nullif(m.alt_text,''), nullif(m.caption,''), ''),
               coalesce(m.media_type,'')
          FROM media_assets m
         WHERE m.building_id = {lit(building_id)}::uuid
           AND m.reviewed IS TRUE
           AND coalesce(m.asset_type,'') <> 'brochure'
         ORDER BY array_position({lit('{' + ','.join(SCENE_ORDER) + '}')}::text[], m.asset_type),
                  m.created_at
         LIMIT {SCENES_PER_SHORT * 3}
    """)
    seen, scenes = set(), []
    for asset_type, filename, caption, media_type in rows:
        if filename in seen:
            continue
        seen.add(filename)
        scenes.append({"asset_type": asset_type, "file": filename,
                       "caption": caption, "media_type": media_type})
        if len(scenes) >= SCENES_PER_SHORT:
            break
    return scenes


def build_props(b: dict, scenes: list[dict], headlines: list[dict]) -> dict:
    """Remotion props — same shape as video/props/*.json."""
    out_scenes = []
    for i, sc in enumerate(scenes):
        h = headlines[i] if i < len(headlines) else {}
        out_scenes.append({
            "source": sc["file"],
            "sourceStart": 0,
            "duration": 4.6 if i == 0 else 5.0,
            "eyebrow": (h.get("eyebrow") or f"{b['name']} · {b['area']}").upper()[:60],
            "headline": h.get("headline") or [b["name"], b["area"]],
            "body": (h.get("body") or sc["caption"] or "")[:140],
            "layout": "full",
        })
    return {
        "building": b["name"],
        "config": "",              # operator fills the configuration if relevant
        "area": b["area"],
        "phone": PHONE,
        "music": "music-clouds.mp3",
        "musicVolume": 0.3,
        "scenes": out_scenes,
    }


def compose_copy(b: dict, scenes: list[dict]) -> tuple[dict | None, str | None]:
    """LLM writes the scene text + title/description. Falls back to templates."""
    scene_desc = "\n".join(
        f"{i+1}. {s['asset_type'] or 'scene'} — {s['caption'] or s['file']}"
        for i, s in enumerate(scenes))
    system = (
        "You write YouTube Shorts copy for a Mumbai real-estate brokerage. "
        "Voice: specific facts, real footage, no brochure language, no hype. "
        "NEVER mention a flat/unit number — configuration only (e.g. '3.5 BHK'). "
        "The building name is the SEO keyword and must lead the title."
    )
    prompt = f"""Building: {b['name']}, {b['area']}, Mumbai.
Scenes available, in order:
{scene_desc}

Return STRICT JSON, no markdown fence:
{{
  "title": "<=90 chars, building name first",
  "description_hook": "one line naming the building and area",
  "tags": ["6-10 lowercase tags"],
  "scenes": [
    {{"eyebrow": "<=40 chars", "headline": ["line 1", "line 2"], "body": "<=120 chars"}}
  ]
}}
Give exactly {len(scenes)} scene objects, matching the order above."""

    text, run_id = llm_draft(WORKER, "short_copy", prompt, system)
    if not text:
        return None, None
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(cleaned), run_id
    except json.JSONDecodeError:
        return None, run_id


def fallback_copy(b: dict, scenes: list[dict]) -> dict:
    return {
        "title": f"Inside {b['name']}, {b['area']} — a walkthrough",
        "description_hook": f"A look inside {b['name']} in {b['area']}, Mumbai.",
        "tags": [slugify(b["name"]), slugify(b["area"]), "mumbai real estate",
                 "property tour", "mumbai flats"],
        "scenes": [{"eyebrow": f"{b['name']} · {b['area']}",
                    "headline": [b["name"]], "body": s["caption"] or ""} for s in scenes],
    }


def description(b: dict, hook: str, tags: list[str]) -> str:
    utm = f"{SITE}/?utm_source=youtube&utm_medium=video&utm_campaign={slugify(b['name'])}"
    hashtags = " ".join("#" + re.sub(r"[^A-Za-z0-9]", "", t.title()) for t in tags[:5])
    return "\n".join([
        hook, "",
        f"Talk to Padmini on WhatsApp: {WA_LINK}",
        f"More listings: {utm}", "",
        "Music: No Copyright Music — credit per licence (Declan DP / Hotham).", "",
        hashtags,
    ])


def create_draft(b: dict, scenes: list[dict], dry_run: bool) -> str | None:
    copy, run_id = compose_copy(b, scenes)
    if not copy:
        copy = fallback_copy(b, scenes)

    title = str(copy.get("title") or "")[:200]
    hook = str(copy.get("description_hook") or "")
    tags = [str(t)[:40] for t in (copy.get("tags") or [])][:10]
    desc = description(b, hook, tags)

    # Hard guard: a flat number must never reach public copy.
    if FLAT_NUMBER.search(title) or FLAT_NUMBER.search(desc):
        finding(WORKER, "copy_rejected", f"shorts_scout:flatnum:{b['id']}",
                f"Generated copy for {b['name']} contained a flat number — draft skipped",
                {"title": title}, "warn")
        return None

    props = build_props(b, scenes, copy.get("scenes") or [])

    if dry_run:
        print(json.dumps({"building": b["name"], "title": title,
                          "scenes": len(props["scenes"])}, indent=2))
        return None

    return one(f"""
        INSERT INTO social_post_drafts
          (building_id, platform, title, description, tags, edit_spec, status,
           decision_notes, llm_run_id)
        VALUES ({lit(b['id'])}::uuid, 'youtube', {lit(title)}, {lit(desc)},
                {lit(pg_array(tags))}::text[], {jsonb_lit(props)}, 'draft',
                'Drafted by shorts_scout from reviewed media only.',
                {lit(run_id) + '::uuid' if run_id else 'NULL'})
        RETURNING id::text""")


def create_blog_companion(b: dict, short_title: str) -> None:
    """A Short and a blog post target the same query; draft both together."""
    slug = f"{slugify(b['name'])}-{slugify(b['area'])}" if b["area"] else slugify(b["name"])
    exists = one(f"SELECT id::text FROM seo_content_drafts WHERE slug = {lit(slug)}")
    if exists:
        return
    # Built outside the f-string: Python 3.10 rejects backslashes in f-string
    # expressions, and this body needs real newlines.
    body_md = (
        f"# {b['name']}, {b['area']}\n\n"
        f"_Draft companion to the Short '{short_title}'. Written from our own "
        f"footage and IGR records — fill in from the unit registry before publishing._\n"
    )
    keywords = "{" + ",".join([slugify(b["name"]), slugify(b["area"] or "mumbai")]) + "}"
    q(f"""INSERT INTO seo_content_drafts (kind, building_id, target_area, slug, title,
             excerpt, body_md, seo_title, seo_description, target_keywords, sources, status)
          VALUES ('blog_post', {lit(b['id'])}::uuid, {lit(b['area'])}, {lit(slug)},
                  {lit(f"{b['name']}, {b['area']}: what buyers actually ask")},
                  {lit(f"A working guide to {b['name']} in {b['area']}, Mumbai.")},
                  {lit(body_md)},
                  {lit(f"{b['name']} {b['area']} — price, layouts, what to check")},
                  {lit(f"Real footage and registry data for {b['name']}, {b['area']}, Mumbai.")},
                  {lit(keywords)}::text[],
                  {jsonb_lit({"origin": "shorts_scout", "short_title": short_title})},
                  'draft')
          ON CONFLICT DO NOTHING""")


def run() -> tuple[str, int, dict]:
    shelf = shelf_count()
    buildings = building_readiness()
    detail = {"shelf": shelf, "shelf_target": SHELF_TARGET,
              "buildings": {b["name"]: {"reviewed": b["reviewed"],
                                        "unreviewed": b["unreviewed"],
                                        "queued": b["queued"]} for b in buildings}}

    # Buildings with footage but nothing reviewed are blocked on the operator.
    blocked = [b for b in buildings if b["reviewed"] == 0 and b["unreviewed"] > 20]
    for b in blocked:
        finding(WORKER, "media_unreviewed", f"shorts_scout:blocked:{b['id']}",
                f"{b['name']}: {b['unreviewed']} media assets, none reviewed — "
                f"no Short can be drafted until some are approved",
                {"building": b["name"], "unreviewed": b["unreviewed"]}, "action")
    detail["blocked_on_media_review"] = [b["name"] for b in blocked]

    if shelf >= SHELF_TARGET:
        return (f"shelf full ({shelf}/{SHELF_TARGET}) — no new draft; "
                f"{len(blocked)} buildings blocked on media review"), 0, detail

    # Draft for the ready building with the least already queued.
    ready = sorted([b for b in buildings if b["reviewed"] >= 2], key=lambda x: x["queued"])
    if not ready:
        return (f"no building has reviewed media to cut — "
                f"{len(blocked)} blocked on review"), 0, detail

    target = ready[0]
    scenes = pick_scenes(target["id"])
    if len(scenes) < 2:
        return f"{target['name']}: not enough distinct reviewed scenes", 0, detail

    draft_id = create_draft(target, scenes, dry_run=False)
    if not draft_id:
        return f"{target['name']}: draft rejected by copy guard", 0, detail

    title = one(f"SELECT title FROM social_post_drafts WHERE id = {lit(draft_id)}::uuid")
    create_blog_companion(target, title or "")

    detail.update(drafted=target["name"], draft_id=draft_id, scenes=len(scenes))
    finding(WORKER, "short_drafted", f"shorts_scout:draft:{draft_id}",
            f"New Short draft ready for review — {target['name']} ({len(scenes)} scenes)",
            {"building": target["name"], "title": title}, "info")

    return (f"drafted 1 Short for {target['name']} ({len(scenes)} scenes), "
            f"shelf now {shelf + 1}/{SHELF_TARGET}"), 1, detail


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.status or a.dry_run:
        print(json.dumps({"shelf": shelf_count(), "buildings": building_readiness()}, indent=2))
        return 0
    return 0 if log_run(WORKER, run) else 1


if __name__ == "__main__":
    sys.exit(main())
