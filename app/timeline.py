from __future__ import annotations

import logging
from pathlib import Path

from app.models import MediaAsset, SubtitleCue, TimelineClip, TimelinePackage, TranscriptDocument, VersionPlan
from app.utils import clamp, pick_best_lines

logger = logging.getLogger(__name__)


def _merge_ranges(items: list[tuple[float, float, list[int], str]], merge_gap: float = 0.35):
    if not items:
        return []

    merged = [items[0]]
    for start, end, ids, text in items[1:]:
        prev_start, prev_end, prev_ids, prev_text = merged[-1]
        if start - prev_end <= merge_gap:
            merged[-1] = (prev_start, max(prev_end, end), prev_ids + ids, f"{prev_text} {text}".strip())
        else:
            merged.append((start, end, ids, text))
    return merged


def _fallback_ids(transcript: TranscriptDocument, target_duration: int) -> list[int]:
    total = 0.0
    selected = []
    for seg in transcript.segments:
        selected.append(seg.id)
        total += seg.end - seg.start
        if total >= target_duration:
            break
    return selected


def build_timeline(
    version: VersionPlan,
    transcript: TranscriptDocument,
    primary_asset: MediaAsset,
) -> TimelinePackage:
    segment_map = {seg.id: seg for seg in transcript.segments}
    selected_ids = [seg_id for seg_id in version.selected_segment_ids if seg_id in segment_map]
    if not selected_ids:
        selected_ids = _fallback_ids(transcript, version.target_duration_seconds)

    ordered_segments = [segment_map[seg_id] for seg_id in selected_ids]
    raw_ranges = []
    for seg in ordered_segments:
        start = clamp(seg.start - 0.10, 0.0, max(seg.start, 0.0))
        end = max(seg.end + 0.12, start + 0.05)
        raw_ranges.append((start, end, [seg.id], seg.text))

    merged_ranges = _merge_ranges(raw_ranges)

    clips: list[TimelineClip] = []
    subtitles: list[SubtitleCue] = []
    output_cursor = 0.0
    subtitle_index = 1
    target = version.target_duration_seconds

    for start, end, ids, text in merged_ranges:
        source_duration = end - start
        if output_cursor >= target * 1.12:
            break

        if output_cursor + source_duration > target * 1.12:
            overflow = output_cursor + source_duration - target
            end = max(start + 0.30, end - max(0.0, overflow))
            source_duration = end - start

        clip = TimelineClip(
            source_path=primary_asset.path,
            source_kind=primary_asset.kind,
            start=start,
            end=end,
            text=text,
            segment_ids=ids,
            output_start=output_cursor,
            output_end=output_cursor + source_duration,
        )
        clips.append(clip)

        for seg_id in ids:
            seg = segment_map[seg_id]
            cue_start = output_cursor + max(0.0, seg.start - start)
            cue_end = min(output_cursor + source_duration, output_cursor + max(0.25, seg.end - start))
            subtitles.append(
                SubtitleCue(
                    index=subtitle_index,
                    start=cue_start,
                    end=max(cue_start + 0.25, cue_end),
                    text=pick_best_lines(seg.text),
                )
            )
            subtitle_index += 1

        output_cursor += source_duration

    # 太短时补片段
    if output_cursor < max(8.0, target * 0.65):
        already = {seg_id for clip in clips for seg_id in clip.segment_ids}
        for seg in transcript.segments:
            if seg.id in already:
                continue
            start = clamp(seg.start - 0.10, 0.0, max(seg.start, 0.0))
            end = seg.end + 0.12
            duration = end - start
            clip = TimelineClip(
                source_path=primary_asset.path,
                source_kind=primary_asset.kind,
                start=start,
                end=end,
                text=seg.text,
                segment_ids=[seg.id],
                output_start=output_cursor,
                output_end=output_cursor + duration,
            )
            clips.append(clip)
            subtitles.append(
                SubtitleCue(
                    index=subtitle_index,
                    start=output_cursor,
                    end=output_cursor + duration,
                    text=pick_best_lines(seg.text),
                )
            )
            subtitle_index += 1
            output_cursor += duration
            if output_cursor >= target:
                break

    return TimelinePackage(
        version_name=version.name,
        angle=version.angle,
        description=version.description,
        target_duration_seconds=version.target_duration_seconds,
        clips=clips,
        subtitles=subtitles,
        output_duration=output_cursor,
    )
