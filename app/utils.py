from __future__ import annotations

import json
import math
import os
import re
from pathlib import Path
from typing import Any

import yaml


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    ensure_dir(path.parent)
    path.write_text(text, encoding="utf-8")


def read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def safe_slug(text: str) -> str:
    value = re.sub(r"[^\w\-]+", "_", text.strip().lower())
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "item"


def format_hms(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def format_timestamp_srt(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - math.floor(seconds)) * 1000))
    if millis == 1000:
        millis = 0
        secs += 1
    if secs >= 60:
        secs -= 60
        minutes += 1
    if minutes >= 60:
        minutes -= 60
        hours += 1
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def extract_json_from_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("未找到有效 JSON 对象。")
    candidate = cleaned[start : end + 1]
    return json.loads(candidate)


def pick_best_lines(text: str, max_chars_per_line: int = 18) -> str:
    text = " ".join(text.split())
    if len(text) <= max_chars_per_line:
        return text
    parts: list[str] = []
    current = ""
    for token in re.split(r"(\s+)", text):
        if len(current) + len(token) <= max_chars_per_line:
            current += token
        else:
            if current.strip():
                parts.append(current.strip())
            current = token.strip()
        if len(parts) == 1 and len(current.strip()) >= max_chars_per_line:
            parts.append(current.strip())
            current = ""
    if current.strip():
        parts.append(current.strip())
    if len(parts) <= 2:
        return "\n".join(part for part in parts if part)
    return f"{parts[0]}\n{' '.join(parts[1:])}"


def windows_friendly_subtitles_path(path: Path) -> str:
    normalized = path.resolve().as_posix()
    if os.name == "nt":
        normalized = normalized.replace(":", r"\:")
    normalized = normalized.replace("'", r"\'")
    return normalized
