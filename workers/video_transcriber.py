"""video_transcriber — whisper.cpp transcripts for our own video archive (₹0, local).

Per run: transcribe VIDEOS_PER_RUN videos from media_assets that have audio and
no transcript yet. Transcript lands in metadata.transcript (searchable, feeds
content_scout blogs + YouTube descriptions). Silent/ambient clips are marked
metadata.transcript='' so they're not retried. 100% local (whisper.cpp base
model, multilingual — handles Hindi/English mixes). Batch the archive overnight:
  while python3 workers/video_transcriber.py; do :; done
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import finding, log_run, q  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from _db import jsonb_lit  # noqa: E402

WORKER = "video_transcriber"
VIDEOS_PER_RUN = 3           # ~1-3 min of CPU per minute of video on the M1
MODEL = Path.home() / ".whisper" / "ggml-base.bin"


def transcribe(path: str) -> str | None:
    """Extract mono 16k audio, run whisper-cli, return plain text ('' if silent)."""
    with tempfile.TemporaryDirectory() as tmp:
        wav = f"{tmp}/a.wav"
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
            capture_output=True, text=True)
        if "audio" not in probe.stdout:
            return ""  # no audio track — ambient/drone clip
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", path,
                        "-ar", "16000", "-ac", "1", wav],
                       check=True, timeout=600)
        res = subprocess.run(
            ["whisper-cli", "-m", str(MODEL), "-f", wav, "-nt"],
            capture_output=True, text=True, timeout=1800)
        if res.returncode != 0:
            return None
        return " ".join(res.stdout.split())[:20000]


def run() -> tuple[str, int, dict]:
    if not shutil.which("whisper-cli") or not MODEL.exists():
        finding(WORKER, "setup_needed", "whisper_missing",
                "brew install whisper-cpp + download ggml-base.bin to ~/.whisper/")
        return "whisper not installed — skipped", 0, {}
    rows = q(f"""
        select m.id, m.file_path from media_assets m
        where m.media_type = 'video'
          and m.metadata->>'transcript' is null
          and coalesce(m.metadata->>'transcribe_failed','') = ''
        order by m.building_id is not null desc, m.created_at desc
        limit {VIDEOS_PER_RUN}""")
    done = failed = 0
    for mid, path in [r for r in rows if r and r[0]]:
        if not path or not Path(path).exists():
            q(f"""update media_assets set metadata = coalesce(metadata,'{{}}'::jsonb)
                  || '{{"transcribe_failed":"file_missing"}}'::jsonb where id='{mid}'""")
            failed += 1
            continue
        try:
            text = transcribe(path)
        except Exception:
            text = None
        if text is None:
            q(f"""update media_assets set metadata = coalesce(metadata,'{{}}'::jsonb)
                  || '{{"transcribe_failed":"whisper_error"}}'::jsonb where id='{mid}'""")
            failed += 1
            continue
        q(f"""update media_assets set
                metadata = coalesce(metadata,'{{}}'::jsonb) ||
                           {jsonb_lit({'transcript': text})},
                updated_at = now()
              where id = '{mid}'""")
        done += 1
    remaining = q("""select count(*) from media_assets where media_type='video'
                     and metadata->>'transcript' is null
                     and coalesce(metadata->>'transcribe_failed','')=''""")[0][0]
    return (f"{done} transcribed, {failed} failed, {remaining} remaining",
            done, {"transcribed": done, "failed": failed, "remaining": int(remaining)})


if __name__ == "__main__":
    ok = log_run(WORKER, run)
    sys.exit(0 if ok else 1)
