from __future__ import annotations

import logging
from pathlib import Path

from app.models import TranscriptDocument, VideoPlan, VersionPlan
from app.utils import extract_json_from_text, read_yaml

logger = logging.getLogger(__name__)


def _sample_segments(transcript: TranscriptDocument, max_count: int = 160):
    segments = transcript.segments
    if len(segments) <= max_count:
        return segments
    head = segments[:80]
    middle_start = max(80, len(segments) // 2 - 20)
    middle = segments[middle_start : middle_start + 40]
    tail = segments[-40:]
    seen = set()
    sampled = []
    for segment in head + middle + tail:
        if segment.id not in seen:
            sampled.append(segment)
            seen.add(segment.id)
    return sampled[:max_count]


def _heuristic_plan(transcript: TranscriptDocument, duration: int) -> VideoPlan:
    segments = transcript.segments

    def score(seg):
        text = seg.text
        value = 0
        if any(ch in text for ch in "!?！？"):
            value += 3
        if any(ch.isdigit() for ch in text):
            value += 2
        if len(text) >= 15:
            value += 2
        if seg.id <= 8:
            value += 1
        return value, -(seg.end - seg.start)

    ranked = sorted(segments, key=score, reverse=True)
    base_ids = [seg.id for seg in ranked[: min(12, len(ranked))]]
    ordered = sorted(base_ids)
    if not ordered:
        ordered = [seg.id for seg in segments[:8]]

    return VideoPlan(
        title="自动生成粗剪方案",
        objective="围绕最有信息量的句子生成多个可发布草案",
        style_summary="当 LLM 规划失败或未配置 Key 时使用的本地兜底方案",
        versions=[
            VersionPlan(
                name="version_A",
                angle="balanced",
                description="均衡版：保留最完整的信息链路。",
                selected_segment_ids=ordered[:8],
                cta="了解更多",
                target_duration_seconds=duration,
            ),
            VersionPlan(
                name="version_B",
                angle="punchy",
                description="节奏版：优先高信息密度句子。",
                selected_segment_ids=ordered[:6],
                cta="现在就试试",
                target_duration_seconds=max(15, duration - 5),
            ),
            VersionPlan(
                name="version_C",
                angle="concise",
                description="简洁版：更短、更直接。",
                selected_segment_ids=ordered[:5],
                cta="马上行动",
                target_duration_seconds=max(12, duration - 10),
            ),
        ],
    )


def _sanitize_version(version: dict, valid_ids: set[int], fallback_name: str, target_duration: int) -> VersionPlan:
    ids = []
    for item in version.get("selected_segment_ids", []):
        try:
            value = int(item)
        except Exception:
            continue
        if value in valid_ids and value not in ids:
            ids.append(value)
    return VersionPlan(
        name=version.get("name", fallback_name),
        angle=version.get("angle", "balanced"),
        description=version.get("description", ""),
        selected_segment_ids=ids,
        cta=version.get("cta", ""),
        target_duration_seconds=int(version.get("target_duration_seconds", target_duration)),
    )


def build_edit_plan(
    transcript: TranscriptDocument,
    template_path: Path,
    api_key: str,
    llm_model: str,
    brief: str,
    duration: int,
    timeout_seconds: int,
    base_url: str | None = None,
) -> VideoPlan:
    if not transcript.segments:
        raise RuntimeError("转写结果没有可用片段，无法生成剪辑方案。")

    if not api_key:
        logger.warning("缺少 OPENAI_API_KEY，使用本地启发式剪辑方案。")
        return _heuristic_plan(transcript, duration)

    template = read_yaml(template_path)
    sampled_segments = _sample_segments(transcript)

    segment_lines = []
    for seg in sampled_segments:
        segment_lines.append(f"[{seg.id}] {seg.start:.2f}-{seg.end:.2f} | {seg.text}")

    system_prompt = """
你是资深短视频剪辑导演。你的任务不是写文案，而是根据已转写的片段编号选择“应该被剪进成片”的片段。
你必须输出严格 JSON，不要输出任何解释，不要输出 markdown 代码块。
你只能从给定的 segment id 中选择，且必须保持时间顺序。
请输出 3 个版本：version_A / version_B / version_C。
"""

    user_prompt = f"""
模板信息：
- template_name: {template.get("name")}
- description: {template.get("description")}
- hook_rules: {template.get("hook_rules")}
- body_rules: {template.get("body_rules")}
- style_notes: {template.get("style_notes")}
- target_duration_seconds: {duration}
- extra_brief: {brief or "无"}

可选转写片段：
{chr(10).join(segment_lines)}

请输出 JSON，格式如下：
{{
  "title": "项目标题",
  "objective": "一句话目标",
  "style_summary": "风格概括",
  "versions": [
    {{
      "name": "version_A",
      "angle": "balanced",
      "description": "这个版本的剪法说明",
      "selected_segment_ids": [1, 3, 4, 9],
      "cta": "结尾短句",
      "target_duration_seconds": {duration}
    }},
    {{
      "name": "version_B",
      "angle": "punchy",
      "description": "这个版本的剪法说明",
      "selected_segment_ids": [2, 5, 6],
      "cta": "结尾短句",
      "target_duration_seconds": {max(15, duration - 5)}
    }},
    {{
      "name": "version_C",
      "angle": "concise",
      "description": "这个版本的剪法说明",
      "selected_segment_ids": [1, 7, 8],
      "cta": "结尾短句",
      "target_duration_seconds": {max(12, duration - 10)}
    }}
  ]
}}
"""

    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)
    response = client.responses.create(
        model=llm_model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw_text = response.output_text
    logger.info("LLM 规划结果原文长度: %s", len(raw_text))

    try:
        data = extract_json_from_text(raw_text)
        valid_ids = {seg.id for seg in transcript.segments}
        versions = data.get("versions", [])
        sanitized_versions = [
            _sanitize_version(item, valid_ids, f"version_{idx}", duration)
            for idx, item in enumerate(versions, start=1)
        ]
        sanitized_versions = [item for item in sanitized_versions if item.selected_segment_ids]
        if len(sanitized_versions) < 3:
            raise ValueError("LLM 返回的版本数不足或无有效片段。")

        return VideoPlan(
            title=data.get("title", "自动剪辑方案"),
            objective=data.get("objective", "生成多个可发布草案"),
            style_summary=data.get("style_summary", ""),
            versions=sanitized_versions[:3],
        )
    except Exception as exc:
        logger.warning("LLM 规划解析失败，回退到本地方案。错误: %s", exc)
        return _heuristic_plan(transcript, duration)
