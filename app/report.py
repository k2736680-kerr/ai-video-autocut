from __future__ import annotations

from pathlib import Path

from app.models import MediaAsset, ProjectManifest, SceneSegment, TimelinePackage, TranscriptDocument, VideoPlan
from app.utils import ensure_dir, write_text


def _asset_line(asset: MediaAsset) -> str:
    base = f"- {asset.name} | {asset.kind} | {asset.duration:.2f}s"
    if asset.width and asset.height:
        base += f" | {asset.width}x{asset.height}"
    return base


def write_report(
    output_path: Path,
    manifest: ProjectManifest,
    transcript: TranscriptDocument,
    scenes: list[SceneSegment],
    plan: VideoPlan,
    timelines: list[TimelinePackage],
) -> Path:
    ensure_dir(output_path.parent)

    lines: list[str] = []
    lines.append("# 自动剪辑报告")
    lines.append("")
    lines.append("## 项目基本信息")
    lines.append(f"- 输入目录: `{manifest.input_dir}`")
    lines.append(f"- 输出目录: `{manifest.output_dir}`")
    lines.append(f"- 模板: `{manifest.template_name}`")
    lines.append(f"- 平台: `{manifest.platform}`")
    lines.append(f"- 目标时长: `{manifest.duration}s`")
    lines.append("")
    lines.append("## 主素材")
    lines.append(_asset_line(manifest.primary_asset))
    lines.append("")
    lines.append("## 辅助素材")
    if manifest.auxiliary_assets:
        for asset in manifest.auxiliary_assets:
            lines.append(_asset_line(asset))
    else:
        lines.append("- 无")
    lines.append("")
    lines.append("## 转写概览")
    lines.append(f"- 片段数: {len(transcript.segments)}")
    lines.append(f"- 词数: {len(transcript.words)}")
    lines.append("")
    lines.append("## 镜头检测")
    lines.append(f"- 检测到镜头数: {len(scenes)}")
    lines.append("")
    lines.append("## LLM 剪辑方案")
    lines.append(f"- 标题: {plan.title}")
    lines.append(f"- 目标: {plan.objective}")
    lines.append(f"- 风格总结: {plan.style_summary}")
    lines.append("")
    for version in plan.versions:
        lines.append(f"### {version.name}")
        lines.append(f"- angle: {version.angle}")
        lines.append(f"- description: {version.description}")
        lines.append(f"- selected_segment_ids: {version.selected_segment_ids}")
        lines.append(f"- cta: {version.cta}")
        lines.append("")

    lines.append("## 时间线结果")
    for timeline in timelines:
        lines.append(f"### {timeline.version_name}")
        lines.append(f"- 输出时长: {timeline.output_duration:.2f}s")
        lines.append(f"- clip 数量: {len(timeline.clips)}")
        lines.append(f"- subtitle 数量: {len(timeline.subtitles)}")
        lines.append("")

    lines.append("## 备注")
    lines.append("- 这版 MVP 以主讲述素材为核心自动粗剪。")
    lines.append("- 辅助素材目前只完成扫描与记录，尚未自动进行 B-roll 匹配。")
    lines.append("- 建议先验证主流程稳定，再继续加智能覆盖和前端界面。")
    lines.append("")

    write_text(output_path, "\n".join(lines))
    return output_path
