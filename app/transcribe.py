from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.ffmpeg_tools import extract_audio_for_transcription, media_duration_seconds, split_audio_if_needed
from app.models import MediaAsset, TranscriptDocument, TranscriptSegment, TranscriptWord
from app.utils import ensure_dir

logger = logging.getLogger(__name__)

SENTENCE_ENDINGS = {".", "!", "?", "。", "！", "？", ";", "；"}


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return {}


def _build_segments_from_words(words: list[TranscriptWord]) -> list[TranscriptSegment]:
    import re

    if not words:
        return []

    segments: list[TranscriptSegment] = []
    current_words: list[TranscriptWord] = []
    seg_id = 1

    def flush() -> None:
        nonlocal seg_id, current_words
        if not current_words:
            return
        text = " ".join(word.word for word in current_words).strip()
        text = re.sub(r"\s+([,.;:!?，。；：！？])", r"\1", text)
        text = " ".join(text.split())
        if text:
            segments.append(
                TranscriptSegment(
                    id=seg_id,
                    text=text,
                    start=current_words[0].start,
                    end=current_words[-1].end,
                )
            )
            seg_id += 1
        current_words = []

    previous_end = None
    for word in words:
        if previous_end is not None and word.start - previous_end > 0.8:
            flush()
        current_words.append(word)
        previous_end = word.end

        last_token = word.word.strip()
        duration = current_words[-1].end - current_words[0].start
        if (
            last_token.endswith(tuple(SENTENCE_ENDINGS))
            or duration >= 4.8
            or len(" ".join([w.word for w in current_words])) >= 72
        ):
            flush()

    flush()
    return segments


def _normalize_transcript_words(raw_words: list, chunk_offset: float) -> list[TranscriptWord]:
    words: list[TranscriptWord] = []
    for item in raw_words or []:
        data = _as_dict(item)
        token = getattr(item, "word", None) or data.get("word")
        start = getattr(item, "start", None) if hasattr(item, "start") else data.get("start")
        end = getattr(item, "end", None) if hasattr(item, "end") else data.get("end")
        if token is None or start is None or end is None:
            continue
        words.append(
            TranscriptWord(
                word=str(token),
                start=float(start) + chunk_offset,
                end=float(end) + chunk_offset,
            )
        )
    return words


def transcribe_primary_asset(
    primary_asset: MediaAsset,
    work_dir: Path,
    api_key: str,
    ffmpeg_bin: str,
    ffprobe_bin: str,
    transcription_model: str,
    chunk_seconds: int,
    timeout_seconds: int,
    base_url: str | None = None,
) -> TranscriptDocument:
    if not api_key:
        raise RuntimeError(
            "缺少 OPENAI_API_KEY，无法执行自动转写。"
            "如果只是验证剪辑链路，请使用 --transcript-file 指定 demo_transcript.json。"
        )
    if transcription_model != "whisper-1":
        raise RuntimeError(
            "当前 MVP 依赖词级时间戳做自动裁切，请把 TRANSCRIPTION_MODEL 设置为 whisper-1。"
        )

    work_audio_dir = ensure_dir(work_dir / "audio")
    source_path = Path(primary_asset.path)
    audio_path = work_audio_dir / "transcription_source.mp3"

    extract_audio_for_transcription(ffmpeg_bin, source_path, audio_path)
    chunk_dir = ensure_dir(work_audio_dir / "chunks")
    chunks = split_audio_if_needed(
        ffmpeg_bin=ffmpeg_bin,
        ffprobe_bin=ffprobe_bin,
        source_audio=audio_path,
        output_dir=chunk_dir,
        chunk_seconds=chunk_seconds,
    )

    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)
    all_words: list[TranscriptWord] = []
    full_text_parts: list[str] = []
    running_offset = 0.0

    for index, chunk_path in enumerate(chunks, start=1):
        logger.info("开始转写音频分块 %s/%s: %s", index, len(chunks), chunk_path.name)
        with open(chunk_path, "rb") as audio_file:
            response = client.audio.transcriptions.create(
                model=transcription_model,
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["word"],
            )

        response_data = _as_dict(response)
        text = getattr(response, "text", None) or response_data.get("text", "")
        words = getattr(response, "words", None) or response_data.get("words", [])
        normalized_words = _normalize_transcript_words(words, running_offset)
        all_words.extend(normalized_words)
        if text:
            full_text_parts.append(str(text).strip())

        chunk_duration = media_duration_seconds(ffprobe_bin, chunk_path)
        running_offset += chunk_duration

    segments = _build_segments_from_words(all_words)
    full_text = "\n".join(segment.text for segment in segments) if segments else "\n".join(full_text_parts)

    return TranscriptDocument(
        source_asset_path=str(source_path),
        source_audio_path=str(audio_path),
        full_text=full_text,
        language=None,
        words=all_words,
        segments=segments,
    )
