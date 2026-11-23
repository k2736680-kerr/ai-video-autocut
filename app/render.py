from __future__ import annotations

import logging
from pathlib import Path

from app.config import Settings
from app.ffmpeg_tools import burn_subtitles, concat_clips, make_audio_visual_clip, make_video_clip
from app.models import TimelinePackage
from app.utils import ensure_dir, write_json

logger = logging.getLogger(__name__)


def render_version(settings: Settings, timeline: TimelinePackage, version_dir: Path) -> dict[str, str]:
    width, height = settings.platform_size()
    ensure_dir(version_dir)
    clips_dir = ensure_dir(version_dir / "clips")

    clip_paths: list[Path] = []
    for idx, clip in enumerate(timeline.clips, start=1):
        out_path = clips_dir / f"clip_{idx:03d}.mp4"
        if clip.source_kind == "video":
            make_video_clip(
                ffmpeg_bin=settings.ffmpeg_bin,
                source_path=Path(clip.source_path),
                out_path=out_path,
                start=clip.start,
                end=clip.end,
                width=width,
                height=height,
                fps=settings.output_fps,
            )
        else:
            make_audio_visual_clip(
                ffmpeg_bin=settings.ffmpeg_bin,
                source_path=Path(clip.source_path),
                out_path=out_path,
                start=clip.start,
                end=clip.end,
                width=width,
                height=height,
                fps=settings.output_fps,
            )
        clip_paths.append(out_path)

    concat_list = version_dir / "concat_list.txt"
    plain_output = version_dir / f"{timeline.version_name}_plain.mp4"
    subtitled_output = version_dir / f"{timeline.version_name}_subtitled.mp4"
    timeline_json = version_dir / "timeline.json"
    subtitle_path = version_dir / "subtitles.srt"

    concat_clips(
        ffmpeg_bin=settings.ffmpeg_bin,
        clip_paths=clip_paths,
        list_path=concat_list,
        out_path=plain_output,
    )

    burn_subtitles(
        ffmpeg_bin=settings.ffmpeg_bin,
        input_video=plain_output,
        subtitle_path=subtitle_path,
        out_path=subtitled_output,
    )

    write_json(timeline_json, timeline.model_dump())

    return {
        "plain_video": str(plain_output),
        "subtitled_video": str(subtitled_output),
        "timeline_json": str(timeline_json),
        "subtitle_path": str(subtitle_path),
    }
