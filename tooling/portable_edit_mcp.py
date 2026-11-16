#!/usr/bin/env python3
"""Local stdio MCP adapter for the portable edit tools."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from portable_edit import execute, validate, within
from portable_edit_batch import render_batch

MAX_MESSAGE = 256_000


def schema(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


STRING = {"type": "string"}
TOOLS = {
    "render_clip_batch": (
        "Render exactly count distinct clips. Supply the overall brief and agent-authored "
        "edit plans, optionally with a prompt per clip. Uses preview FX and exports basic timelines.",
        {"count": {"type": "integer", "minimum": 1, "maximum": 8}, "brief": STRING,
         "clips": {"type": "array", "minItems": 1, "maxItems": 8,
                   "items": {"type": "object", "required": ["edit"],
                             "properties": {"edit": {"type": "object"}, "prompt": STRING},
                             "additionalProperties": False}}, "output": STRING},
    ),
    "inspect_edit": ("Inspect a saved edit plan and its source timing.", {"plan": STRING}),
    "save_edit": ("Validate and save a new project-relative JSON plan.",
                  {"output": STRING, "draft": {"type": "object"}}),
    "render_preview": ("Render a saved edit as a local MP4.", {"plan": STRING, "output": STRING}),
    "export_timeline": ("Export a saved edit as local FCPXML.", {"plan": STRING, "output": STRING}),
}


def dispatch(root, method, params):
    if method == "initialize":
        requested = params.get("protocolVersion")
        supported = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")
        version = requested if requested in supported else supported[-1]
        return {"protocolVersion": version, "capabilities": {"tools": {}},
                "serverInfo": {"name": "tv7-portable-edit", "version": "0.2.0"}}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": [{"name": name, "description": description,
                           "inputSchema": schema(properties)}
                          for name, (description, properties) in TOOLS.items()]}
    if method != "tools/call":
        raise LookupError("Method not found")

    try:
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or name not in TOOLS:
            raise ValueError("Unknown tool")
        if not isinstance(arguments, dict) or set(arguments) != set(TOOLS[name][1]):
            raise ValueError("Invalid tool arguments")
        if name == "render_clip_batch":
            result = render_batch(root, **arguments)
        elif name == "save_edit":
            draft = arguments["draft"]
            output = within(root, arguments["output"], exists=False)
            if output.suffix != ".json":
                raise ValueError("Choose a new JSON file")
            _, frames = validate(root, draft)
            with TemporaryDirectory(dir=output.parent, prefix=".tv7-") as directory:
                temp = Path(directory) / "draft.json"
                temp.write_text(json.dumps(draft, indent=2) + "\n")
                output.hardlink_to(temp)
            result = {"output": str(output.relative_to(root)), "frames": frames}
        else:
            action = {"inspect_edit": "inspect", "render_preview": "preview",
                      "export_timeline": "fcpxml"}[name]
            result = execute(root, action, arguments["plan"], arguments.get("output"))
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        return {"isError": True, "content": [{"type": "text", "text": str(error)}]}


def serve(root):
    while line := sys.stdin.buffer.readline(MAX_MESSAGE + 1):
        if len(line) > MAX_MESSAGE:
            return
        response = {"jsonrpc": "2.0", "id": None}
        try:
            message = json.loads(line)
            if not isinstance(message, dict):
                raise TypeError()
            method = message.get("method")
            params = message.get("params", {})
            response["id"] = message.get("id")
            if message.get("jsonrpc") != "2.0" or not isinstance(method, str):
                raise TypeError()
            if "id" not in message:
                continue
            if not isinstance(params, dict):
                raise TypeError()
            response["result"] = dispatch(root, method, params)
        except LookupError:
            response["error"] = {"code": -32601, "message": "Method not found"}
        except (json.JSONDecodeError, UnicodeDecodeError):
            response["error"] = {"code": -32700, "message": "Invalid JSON"}
        except TypeError:
            response["error"] = {"code": -32600, "message": "Invalid request"}
        print(json.dumps(response), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir() or root == Path(root.anchor):
        parser.error("Choose a project directory")
    serve(root)


if __name__ == "__main__":
    main()
