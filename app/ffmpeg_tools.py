from __future__ import annotations

import json
import logging
import math
import subprocess
from pathlib import Path

from app.utils import ensure_dir


logger = logging.getLogger(__name__)


def run_command(command: list[str]) -> subprocess.CompletedProcess:
    logger.info("执行命令: %s", " ".join(command))
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"命令执行失败。\nCMD: {' '.join(command)}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def ffprobe_json(ffprobe_bin: str, path: Path) -> dict:
    result = run_command(
        [
            ffprobe_bin,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
    )
    return json.loads(result.stdout)


def media_duration_seconds(ffprobe_bin: str, path: Path) -> float:
    data = ffprobe_json(ffprobe_bin, path)
    return float(data.get("format", {}).get("duration", 0.0) or 0.0)


def extract_audio_for_transcription(ffmpeg_bin: str, source_path: Path, out_path: Path) -> Path:
    ensure_dir(out_path.parent)
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(source_path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-b:a",
        "64k",
        str(out_path),
    ]
    run_command(command)
    return out_path


def split_audio_if_needed(
    ffmpeg_bin: str,
    ffprobe_bin: str,
    source_audio: Path,
    output_dir: Path,
    max_bytes: int = 24_000_000,
    chunk_seconds: int = 1200,
) -> list[Path]:
    ensure_dir(output_dir)
    if source_audio.stat().st_size <= max_bytes:
        return [source_audio]

    total_duration = media_duration_seconds(ffprobe_bin, source_audio)
    if total_duration <= 0:
        raise RuntimeError("无法获取音频时长，不能切分。")

    chunk_count = max(2, math.ceil(source_audio.stat().st_size / max_bytes))
    chunk_seconds = min(chunk_seconds, math.ceil(total_duration / chunk_count))
    chunk_paths: list[Path] = []

    start = 0.0
    idx = 1
    while start < total_duration:
        duration = min(chunk_seconds, total_duration - start)
        chunk_path = output_dir / f"chunk_{idx:03d}.mp3"
        command = [
            ffmpeg_bin,
            "-y",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{duration:.3f}",
            "-i",
            str(source_audio),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-b:a",
            "64k",
            str(chunk_path),
        ]
        run_command(command)
        chunk_paths.append(chunk_path)
        start += duration
        idx += 1

    return chunk_paths


def make_video_clip(
    ffmpeg_bin: str,
    source_path: Path,
    out_path: Path,
    start: float,
    end: float,
    width: int,
    height: int,
    fps: int,
) -> Path:
    ensure_dir(out_path.parent)
    duration = max(0.05, end - start)
    vf = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"
    command = [
        ffmpeg_bin,
        "-y",
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{duration:.3f}",
        "-i",
        str(source_path),
        "-vf",
        vf,
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ar",
        "48000",
        "-ac",
        "2",
        str(out_path),
    ]
    run_command(command)
    return out_path


def make_audio_visual_clip(
    ffmpeg_bin: str,
    source_path: Path,
    out_path: Path,
    start: float,
    end: float,
    width: int,
    height: int,
    fps: int,
) -> Path:
    ensure_dir(out_path.parent)
    duration = max(0.05, end - start)
    command = [
        ffmpeg_bin,
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=black:s={width}x{height}:d={duration:.3f}",
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{duration:.3f}",
        "-i",
        str(source_path),
        "-shortest",
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ar",
        "48000",
        "-ac",
        "2",
        str(out_path),
    ]
    run_command(command)
    return out_path


def concat_clips(ffmpeg_bin: str, clip_paths: list[Path], list_path: Path, out_path: Path) -> Path:
    ensure_dir(list_path.parent)
    lines = []
    for path in clip_paths:
        lines.append(f"file '{path.resolve().as_posix()}'")
    list_path.write_text("\n".join(lines), encoding="utf-8")
    command = [
        ffmpeg_bin,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ar",
        "48000",
        "-ac",
        "2",
        str(out_path),
    ]
    run_command(command)
    return out_path


def burn_subtitles(ffmpeg_bin: str, input_video: Path, subtitle_path: Path, out_path: Path) -> Path:
    ensure_dir(out_path.parent)
    escaped = subtitle_path.resolve().as_posix().replace(":", r"\:").replace("'", r"\'")
    vf = f"subtitles='{escaped}'"
    command = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(input_video),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        str(out_path),
    ]
    run_command(command)
    return out_path
