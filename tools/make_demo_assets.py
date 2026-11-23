from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def run(command: list[str]) -> None:
    print("$", " ".join(command))
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(
            "命令执行失败\n"
            + " ".join(command)
            + "\nSTDOUT:\n"
            + result.stdout
            + "\nSTDERR:\n"
            + result.stderr
        )


def build_words(segments: list[dict]) -> list[dict]:
    words: list[dict] = []
    for seg in segments:
        tokens = seg["text"].replace(".", " .").replace(",", " ,").replace("?", " ?").split()
        start = float(seg["start"])
        end = float(seg["end"])
        step = max(0.08, (end - start) / max(1, len(tokens)))
        cursor = start
        for token in tokens:
            token_end = min(end, cursor + step * 0.82)
            words.append({"word": token, "start": round(cursor, 3), "end": round(token_end, 3)})
            cursor += step
    return words


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    input_dir = root / "inputs" / "demo"
    input_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg = shutil.which("ffmpeg")
    espeak = shutil.which("espeak") or shutil.which("espeak-ng")
    if not ffmpeg:
        raise RuntimeError("没有找到 ffmpeg。请先安装 FFmpeg，并确认 ffmpeg 在 PATH 中。")
    # espeak is optional. If it is missing, the script falls back to a sine wave audio track.
    # The included demo_transcript.json still lets you validate the complete render pipeline.

    script_text = (
        "This is a demo for the automatic video editing tool. "
        "The goal is simple. Give the program a video, an audio track, and a short brief. "
        "It will transcribe the voice, select the strongest moments, build three timelines, "
        "create subtitles, and export draft videos. "
        "This first version is not a professional editor. It is a reliable assistant for fast rough cuts. "
        "After the rough cut is ready, you can review the report and improve the final edit."
    )

    wav_path = input_dir / "demo_voice.wav"
    video_path = input_dir / "demo_talk.mp4"
    broll_path = input_dir / "broll_color.mp4"
    notes_path = input_dir / "notes.txt"
    transcript_path = input_dir / "demo_transcript.json"

    
    if espeak:
        run([espeak, "-w", str(wav_path), "-s", "150", script_text])
    else:
        run([
            ffmpeg, "-y", "-f", "lavfi", "-i",
            "sine=frequency=880:sample_rate=16000:duration=31",
            "-ac", "1", str(wav_path)
        ])

    # A simple colorful test video with the spoken demo audio.
    run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=640x360:rate=15:duration=32",
            "-i",
            str(wav_path),
            "-shortest",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(video_path),
        ]
    )

    # A helper B-roll file. The current MVP scans it, records it, and can be extended later to use it.
    run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x223344:size=640x360:rate=15:duration=8",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            str(broll_path),
        ]
    )

    notes_path.write_text(
        "Demo brief: make a fast short video explaining what the automatic editing tool can do.\n",
        encoding="utf-8",
    )

    segments = [
        {"id": 1, "text": "This is a demo for the automatic video editing tool.", "start": 0.20, "end": 3.40},
        {"id": 2, "text": "The goal is simple.", "start": 3.65, "end": 5.10},
        {"id": 3, "text": "Give the program a video, an audio track, and a short brief.", "start": 5.30, "end": 9.10},
        {"id": 4, "text": "It will transcribe the voice, select the strongest moments, and build three timelines.", "start": 9.35, "end": 14.50},
        {"id": 5, "text": "Then it creates subtitles and exports draft videos.", "start": 14.75, "end": 18.10},
        {"id": 6, "text": "This first version is not a professional editor.", "start": 18.35, "end": 21.10},
        {"id": 7, "text": "It is a reliable assistant for fast rough cuts.", "start": 21.35, "end": 24.20},
        {"id": 8, "text": "After the rough cut is ready, you can review the report and improve the final edit.", "start": 24.45, "end": 30.30},
    ]

    transcript = {
        "source_asset_path": str(video_path),
        "source_audio_path": str(wav_path),
        "full_text": "\n".join(seg["text"] for seg in segments),
        "language": "en",
        "words": build_words(segments),
        "segments": segments,
    }
    transcript_path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n生成完成：")
    print("-", video_path)
    print("-", wav_path)
    print("-", broll_path)
    print("-", transcript_path)
    print("\n你可以运行：")
    print(
        "python main.py run --input .\\inputs\\demo --output .\\outputs\\demo_fixture "
        "--template short_talk --platform douyin --duration 20 "
        "--transcript-file .\\inputs\\demo\\demo_transcript.json --brief \"demo validation\" --force"
    )


if __name__ == "__main__":
    main()
