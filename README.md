# AI 一键粗剪 MVP（方案 1）

这是一个可以直接运行的 Python 命令行项目，用来把视频/音频/文案快速变成 3 个短视频草案。

当前版本主打“语音驱动剪辑”：优先围绕一个口播视频、播客视频或音频素材做自动粗剪。辅助视频/音频会被扫描并写入报告，后续可以继续扩展成自动 B-roll 覆盖。

---

## 1. 已包含的文件

```text
ai_video_autocut_mvp/
├─ app/
│  ├─ config.py              # 配置读取：.env、系统环境变量、Windows 注册表兜底
│  ├─ env_loader.py          # 环境变量读取工具
│  ├─ ffmpeg_tools.py        # FFmpeg / FFprobe 封装
│  ├─ ingest.py              # 扫描素材，选择主素材
│  ├─ pipeline.py            # 主流程编排
│  ├─ planner.py             # AI 生成剪辑方案；无 Key 时使用本地兜底方案
│  ├─ render.py              # 渲染导出
│  ├─ report.py              # 输出报告
│  ├─ scene_detect.py        # 镜头检测
│  ├─ subtitles.py           # SRT 字幕
│  ├─ timeline.py            # 时间线生成
│  ├─ transcribe.py          # OpenAI 转写
│  └─ utils.py
├─ inputs/demo/
│  ├─ demo_talk.mp4          # 已生成的测试视频素材
│  ├─ demo_voice.wav         # 已生成的测试音频素材
│  ├─ broll_color.mp4        # 辅助 B-roll 示例素材
│  ├─ demo_transcript.json   # 测试用转写文件，可跳过在线转写
│  └─ notes.txt
├─ templates/
│  ├─ short_talk.yaml
│  ├─ podcast_clip.yaml
│  └─ product_promo.yaml
├─ tools/
│  └─ make_demo_assets.py    # 重新生成 demo 素材
├─ .env.example
├─ main.py
├─ requirements.txt
├─ run_demo.ps1
└─ run_demo_fixture.ps1
```

---

## 2. 你需要提前准备

你已经有 Python，所以还需要确认：

1. 已安装 FFmpeg，并且 `ffmpeg` / `ffprobe` 能在命令行直接执行。
2. 已安装依赖：

```powershell
pip install -r requirements.txt
```

---

## 3. API Key 读取方式

我已经按照你给的思路改好了：代码会优先读取你本机的系统环境变量，不需要你把 Key 写死到代码里。

读取顺序是：

1. 当前进程环境变量，比如 PowerShell 里已有的 `OPENAI_API_KEY`
2. `.env` 文件，如果你创建了它
3. Windows 用户级注册表：`HKEY_CURRENT_USER\Environment`

也就是说，你可以直接在 Windows 用户环境变量里配置：

```text
OPENAI_API_KEY=你的 OpenAI Key
```

然后重新打开 PowerShell 运行项目即可。

如果你想继续用 `.env`，也支持：

```powershell
copy .env.example .env
```

再编辑 `.env`：

```env
OPENAI_API_KEY=你的_key
LLM_MODEL=gpt-5
TRANSCRIPTION_MODEL=whisper-1
```

---

## 4. 先不消耗 Key 的本地验证方式

因为你现在没有真实素材，我已经放了一套 demo 素材在 `inputs/demo/` 里，并且提供了 `demo_transcript.json`。

这个命令会：

- 扫描 demo 视频/音频
- 使用现成转写文件，跳过在线转写
- 如果没有读取到 `OPENAI_API_KEY`，自动使用本地启发式剪辑方案
- 导出 3 个版本的视频、字幕、时间线和报告

```powershell
$env:OUTPUT_WIDTH="360"
$env:OUTPUT_HEIGHT="640"
$env:OUTPUT_FPS="8"

python main.py run `
  --input .\inputs\demo `
  --output .\outputs\demo_fixture `
  --template short_talk `
  --platform douyin `
  --duration 12 `
  --transcript-file .\inputs\demo\demo_transcript.json `
  --brief "demo validation" `
  --force
```

`OUTPUT_WIDTH / OUTPUT_HEIGHT / OUTPUT_FPS` 是为了快速验证用的。正式导出时可以删掉这 3 个临时环境变量，程序会自动按平台尺寸导出。

也可以直接运行：

```powershell
.\run_demo_fixture.ps1
```

---

## 5. 使用真实素材 + 真实 Key 的方式

把你自己的素材放到一个目录，例如：

```text
inputs/my_case/
├─ talking.mp4
├─ broll_01.mp4
├─ broll_02.mp4
└─ notes.txt
```

然后执行：

```powershell
python main.py run `
  --input .\inputs\my_case `
  --output .\outputs\my_case `
  --template short_talk `
  --platform douyin `
  --duration 30 `
  --brief "围绕核心卖点，做一个节奏快一点的短视频" `
  --force
```

真实模式下不传 `--transcript-file`，程序会自动：

1. 用 FFmpeg 抽取音频
2. 调 OpenAI 转写
3. 调模型生成剪辑方案
4. 生成 3 条时间线
5. 自动渲染视频和字幕

---

## 6. 输出结果

运行完成后，输出目录会生成：

```text
outputs/demo_fixture/
├─ project_manifest.json
├─ scenes.json
├─ transcript.json
├─ edit_plan.json
├─ report.md
├─ version_A/
│  ├─ timeline.json
│  ├─ subtitles.srt
│  ├─ version_A_plain.mp4
│  └─ version_A_subtitled.mp4
├─ version_B/
│  ├─ timeline.json
│  ├─ subtitles.srt
│  ├─ version_B_plain.mp4
│  └─ version_B_subtitled.mp4
└─ version_C/
   ├─ timeline.json
   ├─ subtitles.srt
   ├─ version_C_plain.mp4
   └─ version_C_subtitled.mp4
```

---

## 7. 模块调用关系

```text
main.py
  └─ app.pipeline.run_pipeline()
      ├─ config.load_settings()
      │   └─ env_loader.get_env_value()
      ├─ ingest.discover_assets()
      ├─ ingest.choose_primary_asset()
      ├─ scene_detect.detect_scenes()
      ├─ transcribe.transcribe_primary_asset()
      │   ├─ ffmpeg_tools.extract_audio_for_transcription()
      │   ├─ ffmpeg_tools.split_audio_if_needed()
      │   └─ OpenAI Audio Transcriptions API
      ├─ planner.build_edit_plan()
      │   ├─ OpenAI Responses API
      │   └─ 本地启发式兜底方案
      ├─ timeline.build_timeline()
      ├─ subtitles.write_srt()
      ├─ render.render_version()
      │   ├─ ffmpeg_tools.make_video_clip()
      │   ├─ ffmpeg_tools.make_audio_visual_clip()
      │   ├─ ffmpeg_tools.concat_clips()
      │   └─ ffmpeg_tools.burn_subtitles()
      └─ report.write_report()
```

---

## 8. 重新生成 demo 素材

项目已经带了 demo 素材，一般不需要重新生成。

如果你想重新生成：

```powershell
python .\tools\make_demo_assets.py
```

脚本会优先用 `espeak` 生成英文测试人声；如果本机没有 `espeak`，会退回生成一段测试音频。即使没有真实人声，也可以配合 `demo_transcript.json` 验证剪辑链路。

---

## 9. 注意事项

- 当前 MVP 还没有真正使用辅助 B-roll 做智能覆盖，辅助素材目前只扫描并写入报告。
- 当前 MVP 主要适合口播、播客、讲解类视频。
- 首次真实转写会消耗 API；本地验证请先用 `--transcript-file`。
- 正式输出竖屏 1080x1920 会比测试尺寸慢，属于正常现象。
