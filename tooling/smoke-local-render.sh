#!/usr/bin/env bash
# Exercise the running local Engine with generated media.
set -euo pipefail
fixture="$(mktemp -d /tmp/tv7-render-smoke.XXXXXX)"
trap 'rm -rf -- "$fixture"' EXIT
ffmpeg -v error -f lavfi -i testsrc2=size=320x180:rate=30 -t 3 \
    -c:v libx264 -pix_fmt yuv420p "$fixture/source.mp4"
python3 - "$fixture" > "$fixture/request.json" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
print(json.dumps({
    "source_path": str(root / "source.mp4"),
    "output_path": str(root / "clip.mp4"),
    "start_seconds": 0.5,
    "end_seconds": 2.5,
}))
PY
curl --fail --silent --show-error --max-time 60 -H 'Content-Type: application/json' \
    --data-binary "@$fixture/request.json" http://127.0.0.1:7070/v1/media/render-clip
ffmpeg -v error -xerror -i "$fixture/clip.mp4" -f null -
duration="$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$fixture/clip.mp4")"
python3 - "$duration" <<'PY'
import sys

duration = float(sys.argv[1])
if abs(duration - 2.0) > 0.05:
    raise SystemExit(f"Expected a two-second export, got {duration:.3f} seconds")
print(f"\nDecoded {duration:.3f}-second synthetic clip.")
PY
