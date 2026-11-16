# Portable edit plans

TV7's portable edit tools turn a short sequence of source ranges into an MP4 preview or an editable FCPXML cut list. They run locally with Python 3.10+ and FFmpeg/ffprobe, independently of the desktop app and account services.

## Run the sample

From Core, use a new scratch directory:

```sh
project="$(mktemp -d)"
sh examples/portable-edit/generate.sh "$project"
python3 tooling/portable_edit.py --root "$project" inspect edit.json
python3 tooling/portable_edit.py --root "$project" preview edit.json preview.mp4
python3 tooling/portable_edit.py --root "$project" fcpxml edit.json timeline.fcpxml
```

The synthetic media is generated locally. Its origin labels illustrate interchange. You can import the preview as an MP4 in Studio or try importing the FCPXML as a timeline in Resolve. The timeline references local source files by absolute URL, so preserve or relink the media when moving it. Timeline import is editor- and version-dependent. The fixture verifies XML structure and timing, not a live Resolve conform.

## Version 1

See [edit.json](../../examples/portable-edit/edit.json) for the complete shape.

- The plan has a title, an integer frame rate (1–60), and even output dimensions. Asset IDs point to project-relative MP4, MOV, PNG or JPEG files. The optional origin label can identify capture, Pixelorama, Blender, Resolve or another tool.
- Video inputs should be constant frame rate, zero-start and match the plan frame rate. The validator checks the reported average frame rate, frame count and video duration. Normalize footage before authoring frame ranges if it has variable timing or an offset.
- Cuts are ordered. Each uses inclusive source frame **in** and exclusive **out**. A still starts at zero and can run for up to 30 seconds. The optional purpose field lets an editor explain what a cut contributes. Its inclusion does not affect the render.
- Preview uses fitted framing, black padding, normalized stereo audio and silence for unscored assets. FCPXML carries the basic ordered cuts and source references. Optional timed preview effects are described below. Layered compositing, custom reframing, captions and custom mixes are outside version 1.
- Pixelorama can supply full-frame cards as PNGs. For animation or layered graphics, composite the frames in your editor or render them to a normalized clip first. Blender and Resolve can supply MP4 or MOV shots through the same manifest. Preserve editable source files in the originating project.

## Local MCP

Configure your MCP client to launch the following command as a stdio server. Use an absolute Core path and a dedicated project directory.

```sh
python3 -B /absolute/path/to/tv7-core/tooling/portable_edit_mcp.py --root /absolute/path/to/project
```

The tools are `inspect_edit`, `save_edit`, `render_preview`, `export_timeline`, and `render_clip_batch`. Results return the project-relative artifact path and render length when applicable. All writes create new files. Render is synchronous and bounded, so configure a suitable client timeout. The adapter uses the same validator and renderer as the CLI. Native Studio editing of these JSON plans is a separate integration.

The configured root limits high-level file access. Use a dedicated working directory with trusted media. The tools run FFmpeg as your OS user. They do not provide a media decoder sandbox. Keep output files and manifests containing local media references out of public repos unless explicitly intended as samples.

## Agent-directed promotional batches

Ask the calling agent for a count (1–8) and an overall creative brief, such as
“Three clips from this finished film, each with a different hook. Keep the
dialogue and give the best reveal one sound accent.” The agent inspects the
supplied footage, chooses distinct shot sequences and calls
`render_clip_batch`. Pass `count`, `brief`, a new project-relative `output`
directory, and exactly that many `clips`. Each clip has an `edit` object and
can have a `prompt` overriding the overall brief. The server records the prompts
and renders the edits supplied by the agent. It does not prompt a model itself.

For each clip the batch returns an MP4, editable plan and FCPXML cut list. The
output directory also contains `batch.json`, written last as a completion
receipt. Asset paths in saved plans remain relative to the configured project
root, including when plans are saved in a subdirectory. Batch rendering is
synchronous. Set the MCP client timeout for the desired clip count.

A plan can include an optional `fx` list. For example, use a short sound and
border together at output frame 90:

```json
[
  {"preset": "impact", "at": 90, "frames": 8, "amount": 14},
  {"preset": "warm_frame", "at": 90, "frames": 8, "amount": 65}
]
```

`at` and `frames` use the assembled clip timeline, while source in/out points
remain relative to each original asset. Available visual presets are `frame`
and `warm_frame`. Available sound presets are `impact`, `sweep`, and `chime`.
They are synthesized by FFmpeg, with no downloaded assets. Sound amount is
capped at 30% and mixed over the original track. Use sparse cues and play the
preview with sound before adding more. FCPXML carries the ordered cuts only,
and the receipt counts omitted preview effects for the finishing editor.
