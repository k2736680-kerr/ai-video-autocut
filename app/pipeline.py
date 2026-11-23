from __future__ import annotations

import argparse
import logging
from pathlib import Path

from app.config import load_settings
from app.ingest import choose_primary_asset, discover_assets
from app.logging_utils import setup_logging
from app.models import ProjectManifest, SceneSegment, TranscriptDocument
from app.planner import build_edit_plan
from app.render import render_version
from app.report import write_report
from app.scene_detect import detect_scenes
from app.subtitles import write_srt
from app.timeline import build_timeline
from app.transcribe import transcribe_primary_asset
from app.utils import ensure_dir, read_json, write_json

logger = logging.getLogger(__name__)


def _load_or_run_json(cache_path: Path, force: bool, producer):
    if cache_path.exists() and not force:
        logger.info("读取缓存: %s", cache_path)
        return read_json(cache_path)
    data = producer()
    write_json(cache_path, data)
    return data


def run_pipeline(args) -> None:
    settings = load_settings(args)

    ensure_dir(settings.output_dir)
    ensure_dir(settings.work_dir)

    logger.info("扫描素材目录...")
    assets = discover_assets(settings.input_dir, settings.ffprobe_bin)
    primary_asset, auxiliary_assets = choose_primary_asset(assets)

    manifest = ProjectManifest(
        input_dir=str(settings.input_dir),
        output_dir=str(settings.output_dir),
        template_name=settings.template_name,
        platform=settings.platform,
        duration=settings.duration,
        primary_asset=primary_asset,
        auxiliary_assets=auxiliary_assets,
    )
    write_json(settings.output_dir / "project_manifest.json", manifest.model_dump())

    logger.info("主素材: %s", primary_asset.name)

    scenes_cache = settings.output_dir / "scenes.json"
    if primary_asset.kind == "video":
        scenes_data = _load_or_run_json(
            scenes_cache,
            settings.force,
            lambda: [
                scene.model_dump()
                for scene in detect_scenes(
                    Path(primary_asset.path),
                    threshold=settings.scene_threshold,
                    min_scene_len=settings.scene_min_length_frames,
                )
            ],
        )
    else:
        scenes_data = []
        write_json(scenes_cache, scenes_data)

    scenes = [SceneSegment.model_validate(item) for item in scenes_data]

    transcript_cache = settings.output_dir / "transcript.json"
    if settings.transcript_file:
        if not settings.transcript_file.exists():
            raise FileNotFoundError(f"指定的转写文件不存在: {settings.transcript_file}")
        logger.info("使用外部转写文件，跳过在线转写: %s", settings.transcript_file)
        transcript = TranscriptDocument.model_validate(read_json(settings.transcript_file))
        write_json(transcript_cache, transcript.model_dump())
    elif transcript_cache.exists() and not settings.force:
        transcript = TranscriptDocument.model_validate(read_json(transcript_cache))
        logger.info("读取缓存转写: %s", transcript_cache)
    else:
        logger.info("开始转写主素材...")
        transcript = transcribe_primary_asset(
            primary_asset=primary_asset,
            work_dir=settings.work_dir,
            api_key=settings.openai_api_key,
            ffmpeg_bin=settings.ffmpeg_bin,
            ffprobe_bin=settings.ffprobe_bin,
            transcription_model=settings.transcription_model,
            chunk_seconds=settings.transcription_chunk_seconds,
            timeout_seconds=settings.openai_timeout_seconds,
            base_url=settings.openai_base_url,
        )
        write_json(transcript_cache, transcript.model_dump())

    logger.info("开始生成剪辑方案...")
    plan = build_edit_plan(
        transcript=transcript,
        template_path=settings.template_path,
        api_key=settings.openai_api_key,
        llm_model=settings.llm_model,
        brief=settings.brief,
        duration=settings.duration,
        timeout_seconds=settings.openai_timeout_seconds,
        base_url=settings.openai_base_url,
    )
    write_json(settings.output_dir / "edit_plan.json", plan.model_dump())

    timelines = []
    for version in plan.versions:
        logger.info("构建时间线: %s", version.name)
        timeline = build_timeline(
            version=version,
            transcript=transcript,
            primary_asset=primary_asset,
        )
        version_dir = ensure_dir(settings.output_dir / version.name)
        write_srt(timeline.subtitles, version_dir / "subtitles.srt")
        render_version(settings, timeline, version_dir)
        timelines.append(timeline)

    report_path = settings.output_dir / "report.md"
    write_report(
        output_path=report_path,
        manifest=manifest,
        transcript=transcript,
        scenes=scenes,
        plan=plan,
        timelines=timelines,
    )
    logger.info("全部完成。输出目录: %s", settings.output_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI 自动粗剪 MVP")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="运行完整自动剪辑流程")
    run_parser.add_argument("--input", required=True, help="输入素材目录")
    run_parser.add_argument("--output", required=True, help="输出目录")
    run_parser.add_argument("--template", default="short_talk", help="模板名称")
    run_parser.add_argument(
        "--platform",
        default="douyin",
        choices=["douyin", "xiaohongshu", "bilibili", "youtube"],
        help="输出平台",
    )
    run_parser.add_argument("--duration", default=30, type=int, help="目标时长（秒）")
    run_parser.add_argument("--brief", default="", help="额外剪辑说明")
    run_parser.add_argument("--force", action="store_true", help="忽略缓存，强制重跑")
    run_parser.add_argument(
        "--transcript-file",
        default="",
        help="使用已有 transcript.json，跳过在线转写。适合没有真实素材或想先验证剪辑链路时使用",
    )
    return parser


def main() -> None:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()
    run_pipeline(args)
