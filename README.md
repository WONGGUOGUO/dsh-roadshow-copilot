# dsh-roadshow-copilot

**路演 / 直播会议录制与总结**：录屏截帧 + 系统声音回环录音 + 本地 Whisper 转写 + Word 纪要，全流程在本机完成，会议内容不上传。

> Record an online roadshow/pitch meeting (screen + system audio), transcribe locally with Whisper, and produce a Word summary with each project's highlights, funding ask, contacts and QR codes.

## 功能

- **按窗口截帧**：只录标题命中关键词的窗口（腾讯会议、飞书、Zoom、路演、直播…）；多个窗口平铺时分别截帧；被遮挡/最小化的自动跳过；聊天、文档不会被录进去。
- **系统声音回环**：WASAPI loopback 直接抓扬声器输出，不需要麦克风、不需要“立体声混音”、不需要 ffmpeg；每 10 分钟分段，异常退出可修复。
- **本地转写**：whisper.cpp small（ggml，int8），中文效果可用，4 线程约 1× 实时；不调用任何云端接口。
- **自动出稿**：关键帧去重 → 提取项目名、定位、亮点、融资需求（轮次/金额/估值/用途）、落地诉求、联系人手机/微信/二维码 → python-docx 生成 Word 纪要。
- **多场拆分**：`frames.jsonl` 记录每帧的窗口标题，同一 session 里的多场路演可按标题分开出纪要。

## 安装

- **DSH 插件市场**：Plugins → Discover 搜索 `dsh-roadshow-copilot` 一键安装。
- **命令行**：

  ```sh
  dsh plugin --profile <profile> add dsh-roadshow-copilot
  ```

安装后插件会把技能安装到 `~/.dsh/skills/roadshow-copilot`，新会话即可在技能目录看到 `roadshow-copilot`。

## 首次使用：下载模型

插件不携带 465 MB 的 Whisper 模型，首次转写前执行一次（支持断点、多线程）：

```powershell
$sk = "$env:USERPROFILE\.dsh\skills\roadshow-copilot"
python "$sk\scripts\dl.py" `
  "https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-small.bin" `
  "$sk\models\whisper\ggml-small.bin" 8
```

也可以直接对 Agent 说“开始录路演”，按提示下载。

## 使用

1. 打开路演直播/会议窗口（可多个，平铺为佳）。
2. 对 Agent 说 **“开始录路演”**（或运行 `scripts/start.ps1`）。
3. 结束后说 **“结束，出总结”**（或运行 `scripts/stop.ps1`）。
4. Agent 会自动转写、看幻灯片、生成 `路演会议纪要.docx`。

录制产物默认在 `文档\路演记录\<时间戳>\`，包含 `frames/`、`audio/`、`transcript.txt`、`keyframes/` 和纪要。

## 环境要求

- Windows 10/11 x64（插件声明 `os: win32`）
- DSH 自带 Python 3.12 与 Node.js（无需另装）
- 转写时约 1–1.5 GB 空闲内存

## 隐私

- 只截标题命中关键词的窗口，不匹配的窗口（微信、浏览器、文档）不会保存。
- 音频与画面只留在本机；插件的 host 半侧只做一次文件复制，不联网。
- 删除 session 目录即彻底删除该场记录。

## 限制

- 只能录本机播放的声音；纯手机参会录不到。
- 多个窗口同时出声会混成一条音轨，转写会串词——建议同时只让一场出声。
- 中文专有名词、金额、手机号转写可能出错，纪要中的数字以幻灯片画面为准。
- 快速翻页可能漏帧；重要页面停留几秒即可。

## English

Records online pitch/roadshow meetings on Windows: captures only allow-listed windows, records system audio via WASAPI loopback, transcribes locally with whisper.cpp, dedupes slide frames, and builds a Word summary with per-project highlights, funding ask, contacts and QR codes. No cloud calls. Requires DSH on Windows; the Whisper model (~465 MB) is downloaded on first use.

## License

MIT
