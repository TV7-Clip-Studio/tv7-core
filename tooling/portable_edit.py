#!/usr/bin/env python3
"""Validate, preview, and interchange a portable TV7 cut list."""

import argparse
from fractions import Fraction
import json
from pathlib import Path
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from portable_fx import apply_fx, validate_fx


def within(root, relative, *, exists=True):
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError("Use a project-relative path")
    path = (root / relative).resolve(strict=exists)
    if not path.is_relative_to(root) or path == root:
        raise ValueError("Path must stay inside the project")
    return path


def fields(obj, required, optional=()):
    if not isinstance(obj, dict) or not set(required) <= obj.keys() <= set(required) | set(optional):
        raise ValueError(f"Expected fields {', '.join(required)}")


def integer(value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"Expected integer between {low} and {high}")
    return value


def run(args, timeout):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise ValueError(f"{args[0]} failed: {result.stderr[-600:].strip()}")
    return result.stdout


def input_options(still):
    # Choose the demuxer explicitly so an uploaded playlist cannot masquerade as media.
    demuxer = ["-f", "image2", "-pattern_type", "none"] if still else ["-f", "mov"]
    return ["-protocol_whitelist", "file", *demuxer]


def probe(path, still):
    info = json.loads(run(["ffprobe", "-v", "error", *input_options(still),
                           "-show_streams", "-of", "json", str(path)], 30))
    streams = info.get("streams") if isinstance(info, dict) else None
    if not isinstance(streams, list) or not all(isinstance(stream, dict) for stream in streams):
        raise ValueError("ffprobe returned no stream metadata")
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if not video:
        raise ValueError("Asset needs a video or image stream")
    return video, any(stream.get("codec_type") == "audio" for stream in streams)


def load(root, name):
    path = within(root, name)
    if not path.is_file() or path.stat().st_size > 256_000:
        raise ValueError("Expected a plan file no larger than 256 KB")
    return json.loads(path.read_text())


def validate(root, plan):
    fields(plan, ("version", "title", "fps", "width", "height", "assets", "cuts"), ("fx",))
    integer(plan["version"], 1, 1)
    fps = integer(plan["fps"], 1, 60)
    for dim in ("width", "height"):
        if integer(plan[dim], 16, 4096) % 2:
            raise ValueError("Dimensions must be even")
    if not isinstance(plan["title"], str) or not re.fullmatch(r"[^\x00-\x1f]{1,120}", plan["title"]):
        raise ValueError("Invalid title")
    for key in ("assets", "cuts"):
        if not isinstance(plan[key], list) or not 1 <= len(plan[key]) <= 32:
            raise ValueError(f"Expected 1–32 {key}")
    assets = {}
    for entry in plan["assets"]:
        fields(entry, ("id", "path"), ("origin",))
        key = entry["id"]
        if not isinstance(key, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,60}", key) or key in assets:
            raise ValueError("Invalid or repeated asset ID")
        if entry.get("origin", "capture") not in ("capture", "pixelorama", "blender", "resolve", "other"):
            raise ValueError("Unknown asset origin")
        path = within(root, entry["path"])
        if not path.is_file() or path.suffix.lower() not in (".mp4", ".mov", ".png", ".jpg", ".jpeg"):
            raise ValueError("Assets must be MP4, MOV, PNG or JPEG files")
        still = path.suffix.lower() in (".png", ".jpg", ".jpeg")
        video, audio = probe(path, still)
        if still:
            frames = fps * 30
        else:
            try:
                source_fps = Fraction(video["avg_frame_rate"])
                frames = int(video["nb_frames"])
                seconds = Fraction(video["duration_ts"]) * Fraction(video["time_base"])
                start = Fraction(video.get("start_time", "0"))
            except (KeyError, ValueError, ZeroDivisionError) as error:
                raise ValueError("Normalize video to a frame-counted, zero-start source first") from error
            if source_fps != fps or start != 0 or abs(seconds * fps - frames) > 1:
                raise ValueError("Normalize video to the plan frame rate and zero start first")
        assets[key] = (path, video, audio, still, frames)
    total = 0
    for cut in plan["cuts"]:
        fields(cut, ("asset", "in", "out"), ("purpose",))
        if not isinstance(cut["asset"], str) or cut["asset"] not in assets:
            raise ValueError("Unknown cut asset")
        _, _, _, still, frames = assets[cut["asset"]]
        start = integer(cut["in"], 0, frames - 1)
        end = integer(cut["out"], start + 1, frames)
        if still and start:
            raise ValueError("A still must start at frame zero")
        if "purpose" in cut and (not isinstance(cut["purpose"], str) or len(cut["purpose"]) > 500):
            raise ValueError("Invalid edit purpose")
        total += end - start
    if total > fps * 180:
        raise ValueError("Preview may run at most 180 seconds")
    validate_fx(plan, total, fields, integer)
    return assets, total


def timing(frames, fps):
    value = Fraction(frames, fps)
    return f"{value}s"


def fcpxml(plan, assets, total):
    fps = plan["fps"]
    xml = ET.Element("fcpxml", version="1.9")
    resources = ET.SubElement(xml, "resources")

    def add_format(identifier, width, height):
        ET.SubElement(resources, "format", id=identifier, width=str(width),
                      height=str(height), frameDuration=timing(1, fps))

    add_format("r1", plan["width"], plan["height"])
    refs = {}
    for i, (key, (path, video, audio, still, frames)) in enumerate(assets.items(), 2):
        format_id, asset_id = f"r{i * 2}", f"r{i * 2 + 1}"
        add_format(format_id, video["width"], video["height"])
        asset = ET.SubElement(resources, "asset", id=asset_id, name=path.name,
                              start="0s", duration=timing(0 if still else frames, fps),
                              hasVideo="1", hasAudio=str(int(audio)), format=format_id)
        ET.SubElement(asset, "media-rep", kind="original-media", src=path.as_uri())
        refs[key] = asset_id
    event = ET.SubElement(ET.SubElement(xml, "library"), "event", name="TV7 Edits")
    project = ET.SubElement(event, "project", name=plan["title"])
    spine = ET.SubElement(ET.SubElement(project, "sequence", format="r1",
                                       duration=timing(total, fps), tcStart="0s"), "spine")
    offset = 0
    for cut in plan["cuts"]:
        length = cut["out"] - cut["in"]
        clip = ET.SubElement(spine, "asset-clip", ref=refs[cut["asset"]],
                             offset=timing(offset, fps), start=timing(cut["in"], fps),
                             duration=timing(length, fps))
        ET.SubElement(clip, "adjust-conform", type="fit")
        offset += length
    ET.indent(xml)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n' + ET.tostring(xml, encoding="unicode") + "\n"


def render(plan, assets, output):
    fps, width, height = plan["fps"], plan["width"], plan["height"]
    args = ["ffmpeg", "-v", "error", "-nostdin", "-y"]
    filters = []
    for i, cut in enumerate(plan["cuts"]):
        path, _, audio, still, _ = assets[cut["asset"]]
        start, end = cut["in"], cut["out"]
        duration = f"{(end - start) / fps:.9f}"
        if still:
            args += ["-loop", "1", "-framerate", str(fps), "-t", duration]
        args += [*input_options(still), "-i", str(path)]
        filters.append(
            f"[{i}:v]trim=start_frame={start}:end_frame={end},setpts=N/({fps}*TB),"
            f"scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[v{i}]"
        )
        sound = (f"[{i}:a]atrim=start={start / fps:.9f},asetpts=PTS-STARTPTS,"
                 "aformat=sample_rates=48000:channel_layouts=stereo,apad" if audio else
                 "anullsrc=r=48000:cl=stereo")
        filters.append(f"{sound},atrim=duration={duration}[a{i}]")
    labels = "".join(f"[v{i}][a{i}]" for i in range(len(plan["cuts"])))
    filters.append(f"{labels}concat=n={len(plan['cuts'])}:v=1:a=1[base_v][base_a]")
    video_map, audio_map = apply_fx(filters, plan.get("fx", []), fps)
    run(args + ["-filter_complex_threads", "1", "-filter_complex", ";".join(filters),
                "-map", video_map, "-map", audio_map, "-r", str(fps), "-c:v", "libx264",
                "-preset", "veryfast", "-c:a", "aac", "-movflags", "+faststart", str(output)], 180)


def execute(root, action, plan_name, output=None):
    plan = load(root, plan_name)
    assets, total = validate(root, plan)
    info = {"frames": total, "fps": plan["fps"], "seconds": total / plan["fps"]}
    if action == "inspect":
        return {**info, "plan": plan}
    destination = within(root, output, exists=False)
    suffix = ".mp4" if action == "preview" else ".fcpxml"
    if destination.suffix != suffix or destination.exists() or not destination.parent.is_dir():
        raise ValueError(f"Choose a new {suffix} file in an existing project directory")
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix=".tv7-") as directory:
        temp = Path(directory) / destination.name
        if action == "preview":
            render(plan, assets, temp)
        else:
            temp.write_text(fcpxml(plan, assets, total))
        # Exclusive publication also prevents a second invocation from overwriting a result.
        destination.hardlink_to(temp)
    if action == "fcpxml":
        info["preview_fx_omitted"] = len(plan.get("fx", []))
    return {**info, "output": str(destination.relative_to(root))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("action", choices=("inspect", "preview", "fcpxml"))
    parser.add_argument("plan")
    parser.add_argument("output", nargs="?")
    args = parser.parse_args()
    try:
        root = args.root.resolve(strict=True)
        if not root.is_dir() or root == Path(root.anchor):
            raise ValueError("Choose a project directory")
        if (args.action == "inspect") != (args.output is None):
            raise ValueError("Provide an output path only for preview or fcpxml")
        print(json.dumps(execute(root, args.action, args.plan, args.output), indent=2))
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(2, f"{error}\n")


if __name__ == "__main__":
    main()
