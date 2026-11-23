from __future__ import annotations

from pathlib import Path

from app.models import SubtitleCue
from app.utils import ensure_dir, format_timestamp_srt


def write_srt(cues: list[SubtitleCue], output_path: Path) -> Path:
    ensure_dir(output_path.parent)
    lines: list[str] = []
    for idx, cue in enumerate(cues, start=1):
        lines.append(str(idx))
        lines.append(f"{format_timestamp_srt(cue.start)} --> {format_timestamp_srt(cue.end)}")
        lines.append(cue.text.strip())
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
