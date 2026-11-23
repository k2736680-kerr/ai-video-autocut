from __future__ import annotations

import logging
from pathlib import Path

from app.ffmpeg_tools import ffprobe_json
from app.models import MediaAsset
from app.utils import safe_slug

logger = logging.getLogger(__name__)

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".webm"}


def discover_assets(input_dir: Path, ffprobe_bin: str) -> list[MediaAsset]:
    if not input_dir.exists():
        raise FileNotFoundError(f"输入目录不存在: {input_dir}")

    assets: list[MediaAsset] = []
    for path in sorted(input_dir.rglob("*")):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext not in VIDEO_EXTS and ext not in AUDIO_EXTS:
            continue

        kind = "video" if ext in VIDEO_EXTS else "audio"
        probe = ffprobe_json(ffprobe_bin, path)
        streams = probe.get("streams", [])
        format_data = probe.get("format", {})
        duration = float(format_data.get("duration", 0.0) or 0.0)
        size_bytes = int(format_data.get("size", path.stat().st_size))
        width = None
        height = None
        fps = None
        has_audio = kind == "audio"

        for stream in streams:
            codec_type = stream.get("codec_type")
            if codec_type == "video":
                width = stream.get("width")
                height = stream.get("height")
                raw_fps = stream.get("avg_frame_rate")
                if raw_fps and raw_fps != "0/0":
                    try:
                        num, den = raw_fps.split("/")
                        fps = float(num) / float(den)
                    except Exception:
                        fps = None
            elif codec_type == "audio":
                has_audio = True

        if duration <= 0:
            logger.warning("跳过无法识别时长的素材: %s", path)
            continue

        assets.append(
            MediaAsset(
                id=safe_slug(path.stem),
                path=str(path.resolve()),
                name=path.name,
                kind=kind,
                duration=duration,
                size_bytes=size_bytes,
                width=width,
                height=height,
                fps=fps,
                has_audio=has_audio,
            )
        )
    if not assets:
        raise RuntimeError("输入目录下未找到可用的视频或音频素材。")
    return assets


def choose_primary_asset(assets: list[MediaAsset]) -> tuple[MediaAsset, list[MediaAsset]]:
    video_candidates = [a for a in assets if a.kind == "video" and a.has_audio]
    audio_candidates = [a for a in assets if a.kind == "audio"]

    if video_candidates:
        primary = sorted(video_candidates, key=lambda x: (x.duration, x.size_bytes), reverse=True)[0]
    elif audio_candidates:
        primary = sorted(audio_candidates, key=lambda x: (x.duration, x.size_bytes), reverse=True)[0]
    else:
        raise RuntimeError("没有找到带可转写音频的主素材。")

    auxiliaries = [a for a in assets if a.path != primary.path]
    return primary, auxiliaries
