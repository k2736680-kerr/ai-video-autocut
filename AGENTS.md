# AI 视频粗剪 MVP · Agent 持久记忆

> GitHub：`k2736680-kerr/ai-video-autocut`（`~/AutoTestTools/Projects/ai_video_autocut_mvp`）

## 是什么

CLI：口播/播客素材 → 转写 → AI 剪辑方案 → FFmpeg 导出 3 条短视频草案 + 报告。无 Key 时 planner 用本地兜底。

## 怎么跑

```bash
cd ~/AutoTestTools/Projects/ai_video_autocut_mvp
pip install -r requirements.txt   # 建议 .venv
# 确认 ffmpeg / ffprobe 在 PATH
cp .env.example .env              # OPENAI_API_KEY 等，勿提交 .env
python main.py --help
./run_demo.ps1                    # Windows 演示；Mac 等价见 README 命令
```

演示素材：`inputs/demo/`（含可跳过在线转写的 `demo_transcript.json`）。

## 关键目录

| 路径 | 作用 |
|------|------|
| `app/` | pipeline、transcribe、render、scene_detect |
| `app/config.py` | .env + 环境变量；Windows 另有注册表兜底 |
| `templates/*.yaml` | 剪辑模板 |
| `tools/make_demo_assets.py` | 再生 demo 素材 |

## 约定

- 主链路在 `app/pipeline.py`；改行为先跑 demo fixture。
- API Key 仅 `.env` 或环境变量，不进 git。

## Mac 注意

- **FFmpeg 必装**；`config.py` 的 Windows 注册表路径在 Mac 无意义，只用 `.env`。
- `run_demo.ps1` 可改 bash：`python main.py` + README 参数。

## 先读

- `README.md`