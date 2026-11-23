# 路演直播记录与总结（roadshow-copilot）

一套本地工具：录屏截帧 + 系统声音录音 → Whisper 转写 → 幻灯片去重 → 生成 Word 路演纪要。
不依赖云服务，会议内容不出本机。

## 目录

```
roadshow_copilot/
├─ SKILL.md               # 给 AI 的操作说明（安装到 ~/.dsh/skills 后生效）
├─ scripts/
│  ├─ start.ps1           # 开始录制（截帧 + 录音）
│  ├─ stop.ps1            # 结束录制并修复 WAV
│  ├─ capture_frames.py   # 前台窗口截帧（标题关键词过滤 + 去重）
│  ├─ record_audio.py     # WASAPI 回环录音，10 分钟分段
│  ├─ finalize_wav.py     # 修复 WAV 头
│  ├─ transcribe.py       # whisper.cpp 中文转写
│  ├─ slides.py           # 关键帧去重
│  ├─ build_report.py     # JSON → docx
│  ├─ dl.py               # 多线程断点下载（模型）
│  └─ fetch_purepy.py     # 纯 Python 依赖安装
├─ models/
│  └─ whisper/ggml-small.bin   (487MB)
└─ vendor/                # pywhispercpp + DLL + 依赖
```

## 快速开始

```powershell
# 1. 开始录制（默认存到 文档\路演记录\<时间戳>）
powershell -ExecutionPolicy Bypass -File scripts\start.ps1

# 2. 会议结束后
powershell -ExecutionPolicy Bypass -File scripts\stop.ps1

# 3. 转写（后台跑）
$env:PYTHONPATH="$PWD\vendor"
python scripts\transcribe.py "$env:USERPROFILE\Documents\路演记录\<时间戳>" --threads 4

# 4. 幻灯片去重
python scripts\slides.py "$env:USERPROFILE\Documents\路演记录\<时间戳>"

# 5. 写 report_spec.json 后出 Word
python scripts\build_report.py "$env:USERPROFILE\Documents\路演记录\<时间戳>"
```

## 工作原理

- **截帧**：每 6 秒枚举标题命中关键词（腾讯会议/路演/直播/飞书/Zoom…）、未最小化且未被遮挡的窗口，逐个裁图；同一窗口画面无变化不存盘。多个窗口平铺时可同时记录，`frames.jsonl` 按标题区分。
- **录音**：WASAPI loopback 抓扬声器输出，每 10 分钟一段 WAV，每 15 秒回写一次头部，异常退出也能恢复。
- **转写**：whisper.cpp small（int8 量化 ggml），4 线程 CPU 约 0.5–1× 实时。
- **纪要**：幻灯片 + 转写 → 人工（AI）整理成 JSON → python-docx 排版。

## 环境要求

- Windows 10/11 x64
- DSH 自带 Python 3.12（`%USERPROFILE%\.dsh\dsh-runtimes\...\python.exe`）
- 无需安装 ffmpeg / 声卡驱动
- 内存：转写时约 1–1.5GB 空闲

## 已知限制

- 只能录到本机播放的声音；耳机、外放都可以，但纯手机参会录不到。
- 多个窗口同时出声时，回环录音会把它们混成一条音轨，转写会串词；建议同时只让一场出声（音量合成器静音其它应用）。
- 会议软件若使用独占音频模式，可能录到静音。
- 中文专有名词（公司名、人名）转写会有错字，数字与联系方式以幻灯片为准。
- 幻灯片是“画面变化才存”，快速翻页可能漏页；重要页面可让用户停留几秒。
