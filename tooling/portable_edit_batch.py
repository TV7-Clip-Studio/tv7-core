"""Publish a validated batch of agent-authored cuts into a new project folder."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from portable_edit import fcpxml, fields, integer, render, validate, within


def prompt(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise ValueError("Creative prompts must be 1–2000 characters")
    return value.strip()


def render_batch(root, count, brief, clips, output):
    integer(count, 1, 8)
    brief = prompt(brief)
    if not isinstance(clips, list) or len(clips) != count:
        raise ValueError("Supply exactly count agent-authored clips")
    destination = within(root, output, exists=False)
    if destination.exists() or not destination.parent.is_dir():
        raise ValueError("Choose a new batch directory with an existing parent")

    prepared = []
    signatures = set()
    for clip in clips:
        fields(clip, ("edit",), ("prompt",))
        direction = prompt(clip.get("prompt", brief))
        plan = clip["edit"]
        assets, frames = validate(root, plan)
        signature = tuple((assets[cut["asset"]][0], cut["in"], cut["out"]) for cut in plan["cuts"])
        if signature in signatures:
            raise ValueError("Each clip needs a distinct cut sequence")
        signatures.add(signature)
        prepared.append((direction, plan, assets, frames))

    receipt = {"version": 1, "count": count, "prompt": brief, "clips": [],
               "output": str(destination.relative_to(root))}
    with TemporaryDirectory(dir=destination.parent, prefix=".tv7-batch-") as directory:
        stage = Path(directory)
        for index, (direction, plan, assets, frames) in enumerate(prepared, 1):
            stem = f"clip-{index:02d}"
            (stage / f"{stem}.json").write_text(json.dumps(plan, indent=2) + "\n")
            render(plan, assets, stage / f"{stem}.mp4")
            (stage / f"{stem}.fcpxml").write_text(fcpxml(plan, assets, frames))
            receipt["clips"].append({
                "title": plan["title"], "prompt": direction, "frames": frames,
                "seconds": frames / plan["fps"], "edit": f"{stem}.json",
                "preview": f"{stem}.mp4", "timeline": f"{stem}.fcpxml",
                "preview_fx_omitted_from_timeline": len(plan.get("fx", [])),
            })
        (stage / "batch.json").write_text(json.dumps(receipt, indent=2) + "\n")
        destination.mkdir()
        published = []
        try:
            for file in sorted(stage.iterdir(), key=lambda item: item.name == "batch.json"):
                target = destination / file.name
                target.hardlink_to(file)
                published.append(target)
        except OSError:
            for target in published:
                target.unlink(missing_ok=True)
            if not any(destination.iterdir()):
                destination.rmdir()
            raise
    return receipt
