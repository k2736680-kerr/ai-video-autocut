from __future__ import annotations

import logging
from pathlib import Path

from app.models import SceneSegment

logger = logging.getLogger(__name__)


def detect_scenes(video_path: Path, threshold: float = 27.0, min_scene_len: int = 15) -> list[SceneSegment]:
    try:
        from scenedetect import SceneManager, open_video
        from scenedetect.detectors import ContentDetector
    except Exception as exc:
        logger.warning("PySceneDetect 不可用，跳过镜头检测。错误: %s", exc)
        return []

    try:
        video = open_video(str(video_path))
        manager = SceneManager()
        manager.add_detector(ContentDetector(threshold=threshold, min_scene_len=min_scene_len))
        manager.detect_scenes(video)
        scene_list = manager.get_scene_list()
        result: list[SceneSegment] = []
        for idx, (start, end) in enumerate(scene_list, start=1):
            result.append(
                SceneSegment(
                    id=idx,
                    start=float(start.get_seconds()),
                    end=float(end.get_seconds()),
                )
            )
        return result
    except Exception as exc:
        logger.warning("镜头检测失败，继续后续流程。错误: %s", exc)
        return []
