#!/usr/bin/env bash
# Branded video render — Gallery White design system, ₹0 stack, M1-friendly.
#
# Pipeline: trim/crop → [optional AI upscale] → AI voice-over (edge-tts en-IN)
# + music with ducking → whisper captions (Manrope, teal outline) → RDH logo
# watermark + optional title lower-third.
#
# Usage:
#   scripts/brand_video.sh -i in.mp4 -o out.mp4 [-s start] [-d duration]
#     [--vo "voice-over text"] [--voice en-IN-PrabhatNeural]
#     [--music assets/music/track.mp3] [--title "Ekta Tripolis · Goregaon West"]
#     [--landscape] [--no-captions] [--upscale]
#
# Free tools: ffmpeg, edge-tts (pip3 install edge-tts), whisper-cpp (brew),
# realesrgan-ncnn-vulkan (optional, github release) for --upscale of ≤60s clips.
set -euo pipefail
cd "$(dirname "$0")/.."

# ponytail: neither local ffmpeg has libass, but miniforge's has drawtext —
# captions + titles are drawtext overlays, so any freetype-enabled ffmpeg works.
command -v ffmpeg >/dev/null || { echo "ffmpeg required"; exit 1; }
ffmpeg -hide_banner -h filter=drawtext 2>&1 | grep -q "Draw text" || {
  echo "this ffmpeg lacks drawtext (freetype) — use the miniforge/conda build"; exit 1; }

BRAND_DIR="assets/brand"
FONT="$BRAND_DIR/Manrope-Bold.ttf"
LOGO="$BRAND_DIR/rdh-mark.png"
TEAL="1f3d4d"; MIST="eef1ef"

in="" out="" start=0 dur=45 vo="" voice="en-IN-NeerjaNeural" music="" title=""
portrait=1 captions=1 upscale=0
while [ $# -gt 0 ]; do case "$1" in
  -i) in=$2; shift 2;; -o) out=$2; shift 2;; -s) start=$2; shift 2;;
  -d) dur=$2; shift 2;; --vo) vo=$2; shift 2;; --voice) voice=$2; shift 2;;
  --music) music=$2; shift 2;; --title) title=$2; shift 2;;
  --landscape) portrait=0; shift;; --no-captions) captions=0; shift;;
  --upscale) upscale=1; shift;; *) echo "unknown arg: $1"; exit 1;;
esac; done
[ -n "$in" ] && [ -n "$out" ] || { echo "usage: -i in.mp4 -o out.mp4 [...]"; exit 1; }

tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT

# ── 1 · base: trim + crop/scale + sharpen ───────────────────────────────────
if [ "$portrait" = 1 ]; then
  geom="crop=ih*9/16:ih,scale=1080:1920:flags=lanczos"
else
  geom="scale=1920:1080:flags=lanczos"
fi
ffmpeg -v error -y -ss "$start" -t "$dur" -i "$in" \
  -vf "$geom,unsharp=5:5:0.5" -c:v libx264 -crf 21 -preset medium \
  -pix_fmt yuv420p -c:a aac "$tmp/base.mp4"

# ── 2 · optional AI upscale (short clips only — frames take minutes) ────────
if [ "$upscale" = 1 ] && command -v realesrgan-ncnn-vulkan >/dev/null 2>&1; then
  mkdir "$tmp/fi" "$tmp/fo"
  ffmpeg -v error -y -i "$tmp/base.mp4" "$tmp/fi/%05d.png"
  realesrgan-ncnn-vulkan -i "$tmp/fi" -o "$tmp/fo" -n realesr-animevideov3 -s 2
  fps=$(ffprobe -v error -select_streams v -show_entries stream=r_frame_rate -of csv=p=0 "$tmp/base.mp4")
  ffmpeg -v error -y -framerate "$fps" -i "$tmp/fo/%05d.png" -i "$tmp/base.mp4" \
    -map 0:v -map 1:a? -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a copy "$tmp/up.mp4"
  mv "$tmp/up.mp4" "$tmp/base.mp4"
elif [ "$upscale" = 1 ]; then
  echo "note: realesrgan-ncnn-vulkan not installed — skipping upscale"
fi

# ── 3 · audio: AI voice-over + music with ducking ───────────────────────────
cur="$tmp/base.mp4"
if [ -n "$vo" ] && command -v edge-tts >/dev/null 2>&1; then
  edge-tts --voice "$voice" --text "$vo" --write-media "$tmp/vo.mp3" 2>/dev/null
fi
[ -z "$music" ] && music=$(ls assets/music/*.mp3 2>/dev/null | head -1 || true)
if [ -f "$tmp/vo.mp3" ] && [ -n "$music" ] && [ -f "$music" ]; then
  ffmpeg -v error -y -i "$cur" -i "$tmp/vo.mp3" -stream_loop -1 -i "$music" \
    -filter_complex "[2:a]volume=0.35[m];[m][1:a]sidechaincompress=threshold=0.05:ratio=8[duck];[duck][1:a]amix=inputs=2:duration=first[a]" \
    -map 0:v -map "[a]" -t "$dur" -c:v copy -c:a aac -b:a 160k "$tmp/audio.mp4"
  cur="$tmp/audio.mp4"
elif [ -f "$tmp/vo.mp3" ]; then
  ffmpeg -v error -y -i "$cur" -i "$tmp/vo.mp3" \
    -map 0:v -map 1:a -c:v copy -c:a aac -b:a 160k -shortest "$tmp/audio.mp4"
  cur="$tmp/audio.mp4"
elif [ -n "$music" ] && [ -f "$music" ]; then
  ffmpeg -v error -y -i "$cur" -stream_loop -1 -i "$music" \
    -map 0:v -map 1:a -t "$dur" -af "volume=0.5,loudnorm=I=-16:TP=-1.5" \
    -c:v copy -c:a aac -b:a 160k "$tmp/audio.mp4"
  cur="$tmp/audio.mp4"
fi

# ── 4 · captions from the voice-over/track (whisper), Gallery White style ───
if [ "$captions" = 1 ] && command -v whisper-cli >/dev/null 2>&1 \
   && [ -f "$HOME/.whisper/ggml-base.bin" ]; then
  if ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$cur" | grep -q audio; then
    ffmpeg -v error -y -i "$cur" -ar 16000 -ac 1 "$tmp/a.wav"
    whisper-cli -m "$HOME/.whisper/ggml-base.bin" -f "$tmp/a.wav" -osrt -of "$tmp/subs" \
      --prompt "Goregaon West, Andheri West, Mumbai. $title. $vo" >/dev/null 2>&1 || true
    if [ -s "$tmp/subs.srt" ]; then
      # ponytail: brew ffmpeg ships without libass — render captions as drawtext
      # overlays generated from the SRT (no new deps, brand-styled anyway)
      python3 - "$tmp/subs.srt" "$FONT" > "$tmp/subs.filter" << 'PYEOF'
import re, sys
srt, font = open(sys.argv[1]).read(), sys.argv[2]
def secs(t):
    h, m, s = t.replace(",", ".").split(":")
    return float(h) * 3600 + float(m) * 60 + float(s)
parts = []
for block in re.split(r"\n\n+", srt.strip()):
    lines = block.strip().splitlines()
    if len(lines) < 3:
        continue
    a, b = [secs(x.strip()) for x in lines[1].split("-->")]
    text = " ".join(lines[2:])
    text = re.sub(r"[\\'\":;,%]", "", text).strip()
    if not text:
        continue
    parts.append(
        f"drawtext=fontfile={font}:text={text}"
        f":fontcolor=white:fontsize=44:borderw=3:bordercolor=0x1f3d4d"
        f":x=(w-tw)/2:y=h-330:enable=between(t\\,{a:.2f}\\,{b:.2f})")
print(",".join(parts))
PYEOF
      if [ -s "$tmp/subs.filter" ]; then
        ffmpeg -v error -y -i "$cur" -vf "$(cat "$tmp/subs.filter")" \
          -c:v libx264 -crf 21 -preset medium -pix_fmt yuv420p \
          -c:a copy "$tmp/subbed.mp4"
        cur="$tmp/subbed.mp4"
      fi
    fi
  fi
fi

# ── 5 · logo watermark + optional title lower-third ─────────────────────────
vf="[1:v]scale=110:-1[logo];[0:v][logo]overlay=W-w-40:40:format=auto"
if [ -n "$title" ]; then
  vf="$vf,drawtext=fontfile=$FONT:text='$title':fontcolor=0x$MIST:fontsize=42:box=1:boxcolor=0x$TEAL@0.85:boxborderw=18:x=40:y=h-th-120:enable='between(t,0.8,5)'"
fi
ffmpeg -v error -y -i "$cur" -i "$LOGO" -filter_complex "$vf" \
  -c:v libx264 -crf 21 -preset medium -pix_fmt yuv420p -c:a copy \
  -movflags +faststart "$out"
ls -lh "$out"
