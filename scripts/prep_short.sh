#!/usr/bin/env bash
# Render a YouTube Short from our footage (₹0 stack, runs fine on M1 8GB).
# Usage: scripts/prep_short.sh input.mp4 output.mp4 [start_s] [duration_s]
# 9:16 center crop → 1080x1920, mild sharpen, loudness normalize, faststart.
# Captions: if whisper-cli (whisper.cpp) is installed, burns word captions.
# Upscaling note: for real AI upscale of short clips install realesrgan-ncnn
# and run it on extracted frames overnight — feasible for ≤60s clips only.
set -euo pipefail
in=$1; out=$2; start=${3:-0}; dur=${4:-45}

ffmpeg -v error -y -ss "$start" -t "$dur" -i "$in" \
  -vf "crop=ih*9/16:ih,scale=1080:1920:flags=lanczos,unsharp=5:5:0.5:5:5:0.0" \
  -c:v libx264 -crf 23 -preset medium -pix_fmt yuv420p \
  -af "loudnorm=I=-16:TP=-1.5" -c:a aac -b:a 128k \
  -movflags +faststart "$out"

# optional caption burn-in via whisper.cpp (brew install whisper-cpp)
if command -v whisper-cli >/dev/null 2>&1; then
  model="${WHISPER_MODEL:-$HOME/.whisper/ggml-base.en.bin}"
  if [ -f "$model" ]; then
    tmp=$(mktemp -d)
    ffmpeg -v error -y -i "$out" -ar 16000 -ac 1 "$tmp/a.wav"
    whisper-cli -m "$model" -f "$tmp/a.wav" -osrt -of "$tmp/subs" >/dev/null
    ffmpeg -v error -y -i "$out" -vf "subtitles=$tmp/subs.srt:force_style='FontSize=14,Bold=1,Alignment=2,MarginV=60'" \
      -c:a copy "${out%.mp4}-captioned.mp4"
    rm -rf "$tmp"
    echo "captioned: ${out%.mp4}-captioned.mp4"
  fi
fi
ls -lh "$out"
