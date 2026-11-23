from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


class MediaAsset(BaseModel):
    id: str
    path: str
    name: str
    kind: Literal["video", "audio"]
    duration: float
    size_bytes: int
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    has_audio: bool = True


class TranscriptWord(BaseModel):
    word: str
    start: float
    end: float


class TranscriptSegment(BaseModel):
    id: int
    text: str
    start: float
    end: float


class TranscriptDocument(BaseModel):
    source_asset_path: str
    source_audio_path: str
    full_text: str
    language: Optional[str] = None
    words: list[TranscriptWord] = Field(default_factory=list)
    segments: list[TranscriptSegment] = Field(default_factory=list)


class SceneSegment(BaseModel):
    id: int
    start: float
    end: float


class VersionPlan(BaseModel):
    name: str
    angle: str
    description: str
    selected_segment_ids: list[int]
    cta: str = ""
    target_duration_seconds: int


class VideoPlan(BaseModel):
    title: str
    objective: str
    style_summary: str
    versions: list[VersionPlan]


class TimelineClip(BaseModel):
    source_path: str
    source_kind: Literal["video", "audio"]
    start: float
    end: float
    text: str
    segment_ids: list[int] = Field(default_factory=list)
    output_start: float = 0.0
    output_end: float = 0.0


class SubtitleCue(BaseModel):
    index: int
    start: float
    end: float
    text: str


class TimelinePackage(BaseModel):
    version_name: str
    angle: str
    description: str
    target_duration_seconds: int
    clips: list[TimelineClip]
    subtitles: list[SubtitleCue]
    output_duration: float


class ProjectManifest(BaseModel):
    input_dir: str
    output_dir: str
    template_name: str
    platform: str
    duration: int
    primary_asset: MediaAsset
    auxiliary_assets: list[MediaAsset]
