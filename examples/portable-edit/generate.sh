#!/bin/sh
# Synthetic team-neutral demo media. The origin values in edit.json illustrate interchange.
set -eu
output=${1:?Usage: sh generate.sh PROJECT_DIRECTORY}
mkdir -p "$output"
cp "$(dirname "$0")/edit.json" "$output/edit.json"
ffmpeg -v error -n -f lavfi -i 'testsrc2=size=640x360:rate=30:duration=3' \
  -f lavfi -i 'sine=frequency=440:sample_rate=48000:duration=3' -c:v libx264 \
  -pix_fmt yuv420p -c:a aac "$output/setup.mp4"
ffmpeg -v error -n -f lavfi -i 'smptebars=size=640x360:rate=30:duration=2' \
  -c:v libx264 -pix_fmt yuv420p "$output/reveal.mp4"
ffmpeg -v error -n -f lavfi -i 'color=c=purple:s=320x180' -frames:v 1 -threads 1 \
  -update 1 "$output/card.png"
