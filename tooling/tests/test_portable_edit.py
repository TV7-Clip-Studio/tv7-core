import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from portable_edit import execute, within


CORE = Path(__file__).resolve().parents[2]


class PortableEditTest(unittest.TestCase):
    def test_project_root_rejects_symlink_and_parent_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "escape").symlink_to(root.parent)
            for relative in ("../outside", "escape/outside"):
                with self.assertRaises(ValueError):
                    within(root, relative, exists=False)

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires FFmpeg")
    def test_neutral_edit_renders_and_exports_through_mcp(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            subprocess.run(["sh", str(CORE / "examples/portable-edit/generate.sh"), str(root)],
                           check=True)
            draft = json.loads((root / "edit.json").read_text())
            requests = [
                {"id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}},
                {"method": "notifications/initialized"},
                {"id": 2, "method": "tools/list"},
            ]
            for index, (name, arguments) in enumerate((
                ("save_edit", {"draft": draft, "output": "draft.json"}),
                ("inspect_edit", {"plan": "draft.json"}),
                ("render_preview", {"plan": "draft.json", "output": "preview.mp4"}),
                ("export_timeline", {"plan": "draft.json", "output": "timeline.fcpxml"}),
                ("render_preview", {"plan": "draft.json", "output": "preview.mp4"}),
            ), 3):
                requests.append({"id": index, "method": "tools/call",
                                 "params": {"name": name, "arguments": arguments}})
            result = subprocess.run(
                [sys.executable, str(CORE / "tooling/portable_edit_mcp.py"), "--root", str(root)],
                text=True, capture_output=True, check=True, timeout=40,
                input="".join(json.dumps({"jsonrpc": "2.0", **item}) + "\n" for item in requests),
            )
            responses = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual([r["id"] for r in responses], list(range(1, 8)))
            self.assertEqual(len(responses[1]["result"]["tools"]), 5)
            for response in responses[2:-1]:
                record = response["result"]
                self.assertFalse(record.get("isError"), record)
                self.assertEqual(json.loads(record["content"][0]["text"])["frames"], 105)
            self.assertTrue(responses[-1]["result"]["isError"])
            clips = ET.parse(root / "timeline.fcpxml").findall(".//asset-clip")
            self.assertEqual([clip.get("offset") for clip in clips], ["0s", "3/2s", "3s"])
            output = subprocess.check_output([
                "ffprobe", "-v", "error", "-show_streams", "-of", "json", str(root / "preview.mp4"),
            ], text=True)
            video, audio = json.loads(output)["streams"]
            self.assertEqual((video["width"], video["height"], video["nb_frames"]), (540, 960, "105"))
            self.assertEqual(audio["codec_name"], "aac")

            draft["cuts"][0]["out"] = 9999
            (root / "invalid.json").write_text(json.dumps(draft))
            with self.assertRaises(ValueError):
                execute(root, "inspect", "invalid.json")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "requires FFmpeg")
    def test_batch_keeps_prompts_and_effects_and_validates_before_writing(self):
        from portable_edit_batch import render_batch

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            subprocess.run(["sh", str(CORE / "examples/portable-edit/generate.sh"), str(root)],
                           check=True)
            base = json.loads((root / "edit.json").read_text())
            silent = copy.deepcopy(base)
            silent["cuts"] = [{"asset": "reveal", "in": 0, "out": 30}]
            accented = copy.deepcopy(silent)
            accented["cuts"][0]["in"], accented["cuts"][0]["out"] = 15, 45
            accented["fx"] = [
                {"preset": "frame", "at": 5, "frames": 7, "amount": 100},
                {"preset": "impact", "at": 5, "frames": 7, "amount": 25},
            ]
            clips = [{"edit": silent}, {"prompt": "Accent the reveal", "edit": accented}]
            for count, drafts in ((1, clips), (2, [clips[0], clips[0]])):
                with self.assertRaises(ValueError):
                    render_batch(root, count, "Two views", drafts, "rejected")
                self.assertFalse((root / "rejected").exists())

            messages = [
                {"id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25"}},
                {"method": "notifications/initialized"},
                {"id": 2, "method": "tools/list"},
                {"id": 3, "method": "tools/call", "params": {
                    "name": "render_clip_batch", "arguments": {
                        "count": 2, "brief": "Two views", "clips": clips, "output": "review"
                    }
                }},
            ]
            process = subprocess.run(
                [sys.executable, str(CORE / "tooling/portable_edit_mcp.py"), "--root", str(root)],
                text=True, capture_output=True, check=True, timeout=40,
                input="".join(json.dumps({"jsonrpc": "2.0", **message}) + "\n"
                              for message in messages),
            )
            _, discovery, batch = map(json.loads, process.stdout.splitlines())
            self.assertIn("render_clip_batch", [tool["name"] for tool in discovery["result"]["tools"]])
            receipt = json.loads(batch["result"]["content"][0]["text"])
            for entry in receipt["clips"]:
                timeline = ET.parse(root / "review" / entry["timeline"])
                self.assertEqual(timeline.find(".//asset-clip").get("offset"), "0s")
            self.assertEqual([item["prompt"] for item in receipt["clips"]],
                             ["Two views", "Accent the reveal"])
            self.assertEqual(receipt["clips"][1]["preview_fx_omitted_from_timeline"], 2)
            paths = [root / "review" / item["preview"] for item in receipt["clips"]]
            decoded = [subprocess.check_output([
                "ffmpeg", "-v", "error", "-i", str(path), "-vn", "-f", "s16le", "-",
            ]) for path in paths]
            self.assertFalse(any(decoded[0]))
            self.assertTrue(any(decoded[1]))

            def frame(path, time):
                return subprocess.check_output([
                    "ffmpeg", "-v", "error", "-ss", time, "-i", str(path),
                    "-frames:v", "1", "-vf", "crop=8:8:0:0",
                    "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
                ])
            active = frame(paths[1], "0.2")
            inactive = frame(paths[1], "0.7")
            self.assertGreater(sum(active) / len(active), 80)
            self.assertLess(sum(inactive) / len(inactive), 5)
