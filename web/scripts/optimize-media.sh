#!/usr/bin/env bash
# Compress a photo/video to web spec before it goes into public/.
# Usage: scripts/optimize-media.sh input.mp4 [output]
# Videos → 720p H.264 CRF27, muted, faststart. Photos → max 1600w JPEG q6.
set -euo pipefail
in=$1
ext=$(echo "${in##*.}" | tr '[:upper:]' '[:lower:]')
case "$ext" in
  mp4 | mov | webm)
    out=${2:-${in%.*}-web.mp4}
    ffmpeg -v error -y -i "$in" -an -vf "scale='min(1280,iw)':-2" \
      -c:v libx264 -crf 27 -preset slow -pix_fmt yuv420p -movflags +faststart "$out"
    ;;
  jpg | jpeg | png)
    out=${2:-${in%.*}-web.jpg}
    ffmpeg -v error -y -i "$in" -vf "scale='min(1600,iw)':-2" -q:v 6 "$out"
    ;;
  *)
    echo "unsupported: $in" >&2
    exit 1
    ;;
esac
ls -lh "$in" "$out"
