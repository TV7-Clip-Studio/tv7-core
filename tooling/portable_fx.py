"""Small, deterministic post-production effects for portable previews."""

SOUND = {
    "impact": "exp(-24*t)*(sin(2*PI*85*t)+0.25*sin(2*PI*260*t))/1.25",
    "sweep": "sin(2*PI*(180*t+650*t*t))*sin(PI*t/D)^2",
    "chime": "exp(-9*t)*(sin(2*PI*784*t)+0.3*sin(2*PI*1176*t))/1.3",
}
PICTURE = {"frame": "0x9befff", "warm_frame": "0xffbc5a"}


def validate_fx(plan, total, fields, integer):
    events = plan.get("fx", [])
    if not isinstance(events, list) or len(events) > 12:
        raise ValueError("Expected at most 12 effects")
    fps = plan["fps"]
    for event in events:
        fields(event, ("preset", "at", "frames", "amount"))
        preset = event["preset"]
        if not isinstance(preset, str) or preset not in SOUND and preset not in PICTURE:
            raise ValueError("Unknown FX preset")
        at = integer(event["at"], 0, total - 1)
        integer(event["frames"], 1, min(fps * 2, total - at))
        integer(event["amount"], 1, 100 if preset in PICTURE else 30)


def apply_fx(filters, events, fps):
    picture = [event for event in events if event["preset"] in PICTURE]
    sounds = [event for event in events if event["preset"] in SOUND]
    video, audio = "base_v", "base_a"
    for index, event in enumerate(picture):
        end = event["at"] + event["frames"] - 1
        color = PICTURE[event["preset"]]
        alpha = event["amount"] / 100
        target = f"picture{index}"
        filters.append(
            f"[{video}]drawbox=x=0:y=0:w=iw:h=ih:t=ih/90:"
            f"color={color}@{alpha}:enable='between(n,{event['at']},{end})'[{target}]"
        )
        video = target
    for index, event in enumerate(sounds):
        length = event["frames"] / fps
        expression = SOUND[event["preset"]].replace("/D", f"/{length:.9f}")
        delay = round(event["at"] * 48000 / fps)
        volume = event["amount"] / 100
        filters.append(
            f"aevalsrc='{expression}':s=48000:d={length:.9f},"
            f"aformat=channel_layouts=stereo,volume={volume},adelay={delay}S:all=1[sound{index}]"
        )
    if sounds:
        labels = "".join(f"[sound{index}]" for index in range(len(sounds)))
        filters.append(f"[{audio}]volume=0.85[headroom]")
        filters.append(
            f"[headroom]{labels}amix=inputs={1 + len(sounds)}:duration=first:"
            "normalize=0,alimiter=limit=0.95:level=0:latency=1[mix]"
        )
        audio = "mix"
    return f"[{video}]", f"[{audio}]"
