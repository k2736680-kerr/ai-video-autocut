# 真实视频素材测试包说明

你之前指出的问题是对的：上一版素材更像流程占位符，不适合作为真实剪辑测试素材。

这版新增的是 **case_02_real_stock_test**：

- 从 Samplelib 下载真实 MP4 视频素材：城市道路、公交、车流、公园和行人画面
- 自动生成 `main_talk.mp4`，视频里包含真实画面、中文旁白和背景音乐
- 保留 `broll_bus.mp4`、`broll_traffic.mp4`、`broll_park_people.mp4`
- 配套生成/提供：
  - `script.txt`
  - `brief.txt`
  - `transcript.json`
  - `voiceover.wav`
  - `background_music.wav`
  - `case_info.json`

## 使用方式

在项目根目录执行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\run_real_stock_test.ps1
```

这个脚本会做两件事：

1. 下载真实视频素材，并生成 `inputs\case_02_real_stock_test\main_talk.mp4`
2. 调用自动剪辑工具，输出到 `outputs\case_02_real_stock_test`

## 输出检查

跑完后打开：

```powershell
start .\outputs\case_02_real_stock_test\version_A\version_A_subtitled.mp4
```

重点看：

- 有没有真实视频画面
- 有没有声音
- 有没有字幕
- 有没有自动裁切后的多个版本
- `version_A / version_B / version_C` 是否都生成

## 注意

当前项目的主流程主要使用 `main_talk.mp4` 作为主素材来裁切和拼接；B-roll 文件会被扫描进 manifest，但当前版本还没有真正实现“自动插入 B-roll 覆盖主视频”的逻辑。

所以这版测试的重点是验证：

- 真实视频输入
- 有声主素材
- 文案/转写驱动剪辑
- 字幕烧录
- 多版本导出

下一步如果要更像专业剪辑工具，需要继续改代码，让时间线支持：

- 主素材音频保留
- B-roll 覆盖画面
- background_music 自动混音
- 不同片段按内容选择不同 B-roll
