from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel

from app.env_loader import get_env_float, get_env_int, get_env_value


Platform = Literal["douyin", "xiaohongshu", "bilibili", "youtube"]


class Settings(BaseModel):
    input_dir: Path
    output_dir: Path
    work_dir: Path
    template_path: Path
    template_name: str
    platform: Platform
    duration: int
    brief: str = ""
    force: bool = False
    transcript_file: Optional[Path] = None
    openai_api_key: str
    openai_base_url: Optional[str] = None
    llm_model: str = "gpt-5"
    transcription_model: str = "whisper-1"
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    output_fps: int = 30
    output_width: int = 0
    output_height: int = 0
    transcription_chunk_seconds: int = 1200
    openai_timeout_seconds: int = 120
    scene_threshold: float = 27.0
    scene_min_length_frames: int = 15

    def platform_size(self) -> tuple[int, int]:
        if self.output_width > 0 and self.output_height > 0:
            return self.output_width, self.output_height
        mapping = {
            "douyin": (1080, 1920),
            "xiaohongshu": (1080, 1440),
            "bilibili": (1920, 1080),
            "youtube": (1920, 1080),
        }
        return mapping[self.platform]


def _template_path(template_name: str) -> Path:
    # Make the command work whether it is executed from the project root or via an absolute path.
    project_root = Path(__file__).resolve().parents[1]
    candidate = project_root / "templates" / f"{template_name}.yaml"
    if not candidate.exists():
        candidate = Path("templates") / f"{template_name}.yaml"
    if not candidate.exists():
        raise FileNotFoundError(f"模板不存在: {candidate}")
    return candidate.resolve()


def load_settings(args) -> Settings:
    # `.env` is still supported, but system/user environment variables work without creating `.env`.
    load_dotenv(override=False)

    output_dir = Path(args.output).resolve()
    transcript_file = Path(args.transcript_file).resolve() if getattr(args, "transcript_file", None) else None

    return Settings(
        input_dir=Path(args.input).resolve(),
        output_dir=output_dir,
        work_dir=(output_dir / "_work"),
        template_path=_template_path(args.template),
        template_name=args.template,
        platform=args.platform,
        duration=int(args.duration),
        brief=args.brief or "",
        force=bool(args.force),
        transcript_file=transcript_file,
        openai_api_key=get_env_value("OPENAI_API_KEY"),
        openai_base_url=get_env_value("OPENAI_BASE_URL") or None,
        llm_model=get_env_value("LLM_MODEL", "gpt-5"),
        transcription_model=get_env_value("TRANSCRIPTION_MODEL", "whisper-1"),
        ffmpeg_bin=get_env_value("FFMPEG_BIN", "ffmpeg"),
        ffprobe_bin=get_env_value("FFPROBE_BIN", "ffprobe"),
        output_fps=get_env_int("OUTPUT_FPS", 30),
        output_width=get_env_int("OUTPUT_WIDTH", 0),
        output_height=get_env_int("OUTPUT_HEIGHT", 0),
        transcription_chunk_seconds=get_env_int("TRANSCRIPTION_CHUNK_SECONDS", 1200),
        openai_timeout_seconds=get_env_int("OPENAI_TIMEOUT_SECONDS", 120),
        scene_threshold=get_env_float("SCENE_THRESHOLD", 27.0),
        scene_min_length_frames=get_env_int("SCENE_MIN_LENGTH_FRAMES", 15),
    )
