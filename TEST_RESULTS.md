# 本地验证结果

我已经用项目内置 demo 素材跑过一次完整链路，使用的是 `--transcript-file inputs/demo/demo_transcript.json`，因此没有消耗 OpenAI API。

验证命令等价于：

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

已生成：

- `outputs/demo_fixture/version_A/version_A_subtitled.mp4`
- `outputs/demo_fixture/version_B/version_B_subtitled.mp4`
- `outputs/demo_fixture/version_C/version_C_subtitled.mp4`
- `outputs/demo_fixture/report.md`
- `outputs/demo_fixture/edit_plan.json`
- `outputs/demo_fixture/transcript.json`
- 每个版本对应的 `timeline.json` 和 `subtitles.srt`

说明：

- 这次验证没有调用 OpenAI，因为本地没有你的 Key，也不会读取你电脑上的环境变量。
- 代码已经支持在你自己的 Windows 电脑上读取系统环境变量和用户级注册表里的 `OPENAI_API_KEY`。
- 你真实运行时，不传 `--transcript-file` 就会走真实转写和 AI 剪辑规划。
