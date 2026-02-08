use anyhow::Result;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::env;
use std::fs;
use std::io::{self, BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::process::Command;

#[derive(Debug, Serialize, Deserialize)]
struct JsonRpcRequest {
    jsonrpc: String,
    method: String,
    params: serde_json::Value,
    id: Option<serde_json::Value>,
}

#[derive(Debug, Serialize, Deserialize)]
struct JsonRpcResponse {
    jsonrpc: String,
    result: Option<serde_json::Value>,
    error: Option<serde_json::Value>,
    id: Option<serde_json::Value>,
}

const PROTOCOL_VERSION: &str = "2024-11-05";
const SERVER_NAME: &str = "tv7-media-mcp";
const SERVER_VERSION: &str = "0.1.0";

#[tokio::main]
async fn main() -> Result<()> {
    let stdin = io::stdin();
    let mut reader = BufReader::new(stdin.lock());

    loop {
        let payload = match read_message(&mut reader)? {
            Some(message) => message,
            None => break,
        };

        let request: JsonRpcRequest = match serde_json::from_str(&payload) {
            Ok(req) => req,
            Err(_) => continue,
        };

        let response = handle_request(&request);
        if let Some(response) = response {
            write_response(&response)?;
        }
    }

    Ok(())
}

fn read_message(reader: &mut BufReader<impl Read>) -> io::Result<Option<String>> {
    let mut content_length: Option<usize> = None;
    let mut line = String::new();

    loop {
        line.clear();
        let bytes = reader.read_line(&mut line)?;
        if bytes == 0 {
            return Ok(None);
        }

        let trimmed = line.trim_end_matches(&['\r', '\n'][..]);
        if trimmed.is_empty() {
            break;
        }

        if let Some((key, value)) = trimmed.split_once(':') {
            if key.eq_ignore_ascii_case("content-length") {
                content_length = value.trim().parse::<usize>().ok();
            }
        } else if trimmed.starts_with('{') || trimmed.starts_with('[') {
            return Ok(Some(trimmed.to_string()));
        }
    }

    let length = match content_length {
        Some(len) => len,
        None => return Ok(None),
    };

    let mut buf = vec![0u8; length];
    reader.read_exact(&mut buf)?;
    Ok(Some(String::from_utf8_lossy(&buf).to_string()))
}

fn write_response(response: &JsonRpcResponse) -> io::Result<()> {
    let json = serde_json::to_string(response).unwrap_or_else(|_| "{}".to_string());
    let mut stdout = io::stdout();
    write!(stdout, "Content-Length: {}\r\n\r\n{}", json.as_bytes().len(), json)?;
    stdout.flush()
}

fn handle_request(request: &JsonRpcRequest) -> Option<JsonRpcResponse> {
    if request.id.is_none() {
        if request.method == "notifications/initialized" {
            return None;
        }
        return None;
    }

    let id = request.id.clone();

    let response = match request.method.as_str() {
        "initialize" => rpc_result(
            id,
            json!({
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {
                        "listChanged": true
                    }
                },
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION
                }
            }),
        ),
        "tools/list" => rpc_result(
            id,
            json!({
                "tools": tools_list()
            }),
        ),
        "tools/call" => match handle_tool_call(&request.params) {
            Ok(result) => rpc_result(id, result),
            Err(err) => rpc_error(id, -32602, err),
        },
        _ => rpc_error(id, -32601, "Method not found"),
    };

    Some(response)
}

fn tools_list() -> Value {
    json!([
        {
            "name": "media_probe",
            "description": "Probe a media file for metadata",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": { "type": "string" }
                },
                "required": ["path"]
            }
        },
        {
            "name": "media_thumbnail",
            "description": "Create a still image from a media file at a given timestamp",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input_path": { "type": "string" },
                    "output_path": { "type": "string" },
                    "timestamp_seconds": { "type": "number" },
                    "width": { "type": "integer" },
                    "height": { "type": "integer" },
                    "overwrite": { "type": "boolean" }
                },
                "required": ["input_path", "output_path", "timestamp_seconds"]
            }
        },
        {
            "name": "media_extract_audio",
            "description": "Extract audio from a media file into a separate audio file",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input_path": { "type": "string" },
                    "output_path": { "type": "string" },
                    "audio_codec": { "type": "string" },
                    "audio_bitrate": { "type": "string" },
                    "sample_rate": { "type": "integer" },
                    "channels": { "type": "integer" },
                    "overwrite": { "type": "boolean" }
                },
                "required": ["input_path", "output_path"]
            }
        },
        {
            "name": "media_trim",
            "description": "Trim a media file to a time segment",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input_path": { "type": "string" },
                    "output_path": { "type": "string" },
                    "start_seconds": { "type": "number" },
                    "duration_seconds": { "type": "number" },
                    "reencode": { "type": "boolean" },
                    "overwrite": { "type": "boolean" }
                },
                "required": ["input_path", "output_path", "start_seconds", "duration_seconds"]
            }
        },
        {
            "name": "media_transcode",
            "description": "Transcode a media file with optional format/codec settings",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "input_path": { "type": "string" },
                    "output_path": { "type": "string" },
                    "format": { "type": "string" },
                    "video_codec": { "type": "string" },
                    "audio_codec": { "type": "string" },
                    "video_bitrate": { "type": "string" },
                    "audio_bitrate": { "type": "string" },
                    "width": { "type": "integer" },
                    "height": { "type": "integer" },
                    "fps": { "type": "number" },
                    "overwrite": { "type": "boolean" }
                },
                "required": ["input_path", "output_path"]
            }
        }
    ])
}

fn handle_tool_call(params: &Value) -> Result<Value, String> {
    let tool_name = params.get("name").and_then(|v| v.as_str()).unwrap_or("");
    let arguments = params
        .get("arguments")
        .cloned()
        .unwrap_or_else(|| json!({}));

    match tool_name {
        "media_probe" => media_probe(&arguments),
        "media_thumbnail" => media_thumbnail(&arguments),
        "media_extract_audio" => media_extract_audio(&arguments),
        "media_trim" => media_trim(&arguments),
        "media_transcode" => media_transcode(&arguments),
        _ => Err("Tool not found".to_string()),
    }
}

fn media_probe(args: &Value) -> Result<Value, String> {
    let path = get_required_string(args, "path")?;
    let input_path = ensure_input_path(&path)?;
    enforce_allowed_path(&input_path)?;

    match engine_core::probe_media(input_path.to_string_lossy().as_ref()) {
        Ok(meta) => Ok(json!({
            "content": [
                {
                    "type": "text",
                    "text": format!("Media metadata for {}", meta.path)
                }
            ],
            "metadata": {
                "path": meta.path,
                "duration_seconds": meta.duration_seconds,
                "width": meta.width,
                "height": meta.height,
                "format": meta.format
            }
        })),
        Err(err) => Err(err),
    }
}

fn media_thumbnail(args: &Value) -> Result<Value, String> {
    let input_path = get_required_string(args, "input_path")?;
    let output_path = get_required_string(args, "output_path")?;
    let timestamp = get_required_f64(args, "timestamp_seconds")?;
    let overwrite = get_optional_bool(args, "overwrite").unwrap_or(false);
    let width = get_optional_u32(args, "width");
    let height = get_optional_u32(args, "height");

    let input_path = ensure_input_path(&input_path)?;
    let output_path = ensure_output_path(&output_path, overwrite)?;
    enforce_allowed_path(&input_path)?;
    enforce_allowed_path(&output_path)?;

    let mut args_list = vec![String::from("-hide_banner")];
    args_list.push(if overwrite { "-y" } else { "-n" }.to_string());
    args_list.push(String::from("-ss"));
    args_list.push(format!("{timestamp}"));
    args_list.push(String::from("-i"));
    args_list.push(input_path.to_string_lossy().to_string());
    args_list.push(String::from("-frames:v"));
    args_list.push(String::from("1"));
    if width.is_some() || height.is_some() {
        let w = width.map(|v| v.to_string()).unwrap_or_else(|| "-1".to_string());
        let h = height.map(|v| v.to_string()).unwrap_or_else(|| "-1".to_string());
        args_list.push(String::from("-vf"));
        args_list.push(format!("scale={w}:{h}"));
    }
    args_list.push(output_path.to_string_lossy().to_string());

    run_ffmpeg(&args_list)?;

    Ok(json!({
        "content": [
            {
                "type": "text",
                "text": format!("Thumbnail created at {}", output_path.display())
            }
        ],
        "metadata": {
            "output_path": output_path.to_string_lossy()
        }
    }))
}

fn media_extract_audio(args: &Value) -> Result<Value, String> {
    let input_path = get_required_string(args, "input_path")?;
    let output_path = get_required_string(args, "output_path")?;
    let overwrite = get_optional_bool(args, "overwrite").unwrap_or(false);
    let audio_codec = get_optional_string(args, "audio_codec");
    let audio_bitrate = get_optional_string(args, "audio_bitrate");
    let sample_rate = get_optional_u32(args, "sample_rate");
    let channels = get_optional_u32(args, "channels");

    let input_path = ensure_input_path(&input_path)?;
    let output_path = ensure_output_path(&output_path, overwrite)?;
    enforce_allowed_path(&input_path)?;
    enforce_allowed_path(&output_path)?;

    let mut args_list = vec![String::from("-hide_banner")];
    args_list.push(if overwrite { "-y" } else { "-n" }.to_string());
    args_list.push(String::from("-i"));
    args_list.push(input_path.to_string_lossy().to_string());
    args_list.push(String::from("-vn"));
    if let Some(codec) = audio_codec {
        args_list.push(String::from("-c:a"));
        args_list.push(codec);
    }
    if let Some(bitrate) = audio_bitrate {
        args_list.push(String::from("-b:a"));
        args_list.push(bitrate);
    }
    if let Some(rate) = sample_rate {
        args_list.push(String::from("-ar"));
        args_list.push(rate.to_string());
    }
    if let Some(ch) = channels {
        args_list.push(String::from("-ac"));
        args_list.push(ch.to_string());
    }
    args_list.push(output_path.to_string_lossy().to_string());

    run_ffmpeg(&args_list)?;

    Ok(json!({
        "content": [
            {
                "type": "text",
                "text": format!("Audio extracted to {}", output_path.display())
            }
        ],
        "metadata": {
            "output_path": output_path.to_string_lossy()
        }
    }))
}

fn media_trim(args: &Value) -> Result<Value, String> {
    let input_path = get_required_string(args, "input_path")?;
    let output_path = get_required_string(args, "output_path")?;
    let start = get_required_f64(args, "start_seconds")?;
    let duration = get_required_f64(args, "duration_seconds")?;
    let overwrite = get_optional_bool(args, "overwrite").unwrap_or(false);
    let reencode = get_optional_bool(args, "reencode").unwrap_or(false);

    let input_path = ensure_input_path(&input_path)?;
    let output_path = ensure_output_path(&output_path, overwrite)?;
    enforce_allowed_path(&input_path)?;
    enforce_allowed_path(&output_path)?;

    let mut args_list = vec![String::from("-hide_banner")];
    args_list.push(if overwrite { "-y" } else { "-n" }.to_string());
    args_list.push(String::from("-ss"));
    args_list.push(format!("{start}"));
    args_list.push(String::from("-i"));
    args_list.push(input_path.to_string_lossy().to_string());
    args_list.push(String::from("-t"));
    args_list.push(format!("{duration}"));
    if !reencode {
        args_list.push(String::from("-c"));
        args_list.push(String::from("copy"));
    }
    args_list.push(output_path.to_string_lossy().to_string());

    run_ffmpeg(&args_list)?;

    Ok(json!({
        "content": [
            {
                "type": "text",
                "text": format!("Trimmed media saved to {}", output_path.display())
            }
        ],
        "metadata": {
            "output_path": output_path.to_string_lossy(),
            "start_seconds": start,
            "duration_seconds": duration
        }
    }))
}

fn media_transcode(args: &Value) -> Result<Value, String> {
    let input_path = get_required_string(args, "input_path")?;
    let output_path = get_required_string(args, "output_path")?;
    let overwrite = get_optional_bool(args, "overwrite").unwrap_or(false);
    let format = get_optional_string(args, "format");
    let video_codec = get_optional_string(args, "video_codec");
    let audio_codec = get_optional_string(args, "audio_codec");
    let video_bitrate = get_optional_string(args, "video_bitrate");
    let audio_bitrate = get_optional_string(args, "audio_bitrate");
    let width = get_optional_u32(args, "width");
    let height = get_optional_u32(args, "height");
    let fps = get_optional_f64(args, "fps");

    let input_path = ensure_input_path(&input_path)?;
    let output_path = ensure_output_path(&output_path, overwrite)?;
    enforce_allowed_path(&input_path)?;
    enforce_allowed_path(&output_path)?;

    let mut args_list = vec![String::from("-hide_banner")];
    args_list.push(if overwrite { "-y" } else { "-n" }.to_string());
    args_list.push(String::from("-i"));
    args_list.push(input_path.to_string_lossy().to_string());
    if let Some(codec) = video_codec {
        args_list.push(String::from("-c:v"));
        args_list.push(codec);
    }
    if let Some(codec) = audio_codec {
        args_list.push(String::from("-c:a"));
        args_list.push(codec);
    }
    if let Some(bitrate) = video_bitrate {
        args_list.push(String::from("-b:v"));
        args_list.push(bitrate);
    }
    if let Some(bitrate) = audio_bitrate {
        args_list.push(String::from("-b:a"));
        args_list.push(bitrate);
    }
    if width.is_some() || height.is_some() {
        let w = width.map(|v| v.to_string()).unwrap_or_else(|| "-1".to_string());
        let h = height.map(|v| v.to_string()).unwrap_or_else(|| "-1".to_string());
        args_list.push(String::from("-vf"));
        args_list.push(format!("scale={w}:{h}"));
    }
    if let Some(rate) = fps {
        args_list.push(String::from("-r"));
        args_list.push(rate.to_string());
    }
    if let Some(fmt) = format {
        args_list.push(String::from("-f"));
        args_list.push(fmt);
    }
    args_list.push(output_path.to_string_lossy().to_string());

    run_ffmpeg(&args_list)?;

    Ok(json!({
        "content": [
            {
                "type": "text",
                "text": format!("Transcoded media saved to {}", output_path.display())
            }
        ],
        "metadata": {
            "output_path": output_path.to_string_lossy()
        }
    }))
}

fn run_ffmpeg(args: &[String]) -> Result<(), String> {
    let output = Command::new("ffmpeg")
        .args(args)
        .output()
        .map_err(|err| format!("Failed to run ffmpeg: {err}"))?;

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        let message = stderr.trim().lines().last().unwrap_or("ffmpeg failed");
        return Err(message.to_string());
    }

    Ok(())
}

fn get_required_string(args: &Value, key: &str) -> Result<String, String> {
    args.get(key)
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .ok_or_else(|| format!("Missing required field '{}'", key))
}

fn get_optional_string(args: &Value, key: &str) -> Option<String> {
    args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
}

fn get_optional_bool(args: &Value, key: &str) -> Option<bool> {
    args.get(key).and_then(|v| v.as_bool())
}

fn get_optional_u32(args: &Value, key: &str) -> Option<u32> {
    args.get(key).and_then(|v| v.as_u64()).and_then(|v| u32::try_from(v).ok())
}

fn get_optional_f64(args: &Value, key: &str) -> Option<f64> {
    args.get(key).and_then(|v| v.as_f64())
}

fn get_required_f64(args: &Value, key: &str) -> Result<f64, String> {
    get_optional_f64(args, key).ok_or_else(|| format!("Missing required field '{}'", key))
}

fn ensure_input_path(path: &str) -> Result<PathBuf, String> {
    let resolved = resolve_path(path)?;
    if !resolved.exists() {
        return Err(format!("Input path does not exist: {}", resolved.display()));
    }
    if !resolved.is_file() {
        return Err(format!("Input path is not a file: {}", resolved.display()));
    }
    Ok(resolved)
}

fn ensure_output_path(path: &str, overwrite: bool) -> Result<PathBuf, String> {
    let resolved = resolve_path(path)?;
    if resolved.exists() && !overwrite {
        return Err(format!(
            "Output path already exists (set overwrite=true to replace): {}",
            resolved.display()
        ));
    }
    if let Some(parent) = resolved.parent() {
        if !parent.exists() {
            fs::create_dir_all(parent)
                .map_err(|err| format!("Failed to create output directory: {err}"))?;
        }
    }
    Ok(resolved)
}

fn resolve_path(path: &str) -> Result<PathBuf, String> {
    let raw = PathBuf::from(path);
    if raw.is_absolute() {
        Ok(raw)
    } else {
        let cwd = env::current_dir().map_err(|err| format!("Failed to get cwd: {err}"))?;
        Ok(cwd.join(raw))
    }
}

fn enforce_allowed_path(path: &Path) -> Result<(), String> {
    let roots = match env::var("TV7_MCP_ALLOWED_ROOTS") {
        Ok(raw) => raw,
        Err(_) => return Ok(()),
    };
    let allowed = roots
        .split(',')
        .map(|value| value.trim())
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
        .collect::<Vec<_>>();

    if allowed.is_empty() {
        return Ok(());
    }

    let target = if path.is_absolute() {
        path.to_path_buf()
    } else {
        resolve_path(path.to_string_lossy().as_ref())?
    };

    for root in allowed {
        let root_path = if root.is_absolute() {
            root
        } else {
            resolve_path(root.to_string_lossy().as_ref())?
        };
        if target.starts_with(&root_path) {
            return Ok(());
        }
    }

    Err(format!(
        "Path '{}' is outside allowed roots (TV7_MCP_ALLOWED_ROOTS)",
        target.display()
    ))
}

fn rpc_result(id: Option<Value>, result: Value) -> JsonRpcResponse {
    JsonRpcResponse {
        jsonrpc: "2.0".to_string(),
        result: Some(result),
        error: None,
        id,
    }
}

fn rpc_error(id: Option<Value>, code: i64, message: impl Into<String>) -> JsonRpcResponse {
    JsonRpcResponse {
        jsonrpc: "2.0".to_string(),
        result: None,
        error: Some(json!({
            "code": code,
            "message": message.into()
        })),
        id,
    }
}
