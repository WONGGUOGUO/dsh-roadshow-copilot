---
name: roadshow-copilot
description: 录屏+录系统声音记录线上路演/直播会议，自动转写，提取每个项目的要点、融资需求、联系方式与二维码，并生成 Word 版路演会议纪要。适用于腾讯会议、飞书、Zoom、微信直播等在线路演。
whenToUse: 用户说“开始录路演/直播”“帮我记录这个路演会议”“结束录制并总结”“生成路演纪要”时使用。需要持续录制屏幕与系统声音的场景。
---

# 路演直播记录与总结（roadshow-copilot）

把一场线上路演变成一份可转发的 Word 纪要：录屏截帧 + 系统声音回环录音 → 本地语音转写 → 提取项目信息 → 生成 docx。
全部本地运行，不上传会议内容。

## 组件与路径

- 技能根目录：`%USERPROFILE%\.dsh\skills\roadshow-copilot`（本文件所在目录）
- 脚本：`scripts\`
- 模型：`models\whisper\ggml-small.bin`（约 465MB，whisper.cpp small）
- 依赖库：`vendor\`（sherpa-onnx、pywhispercpp 及其 DLL）
- Python：优先用 DSH 自带解释器
  `%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`
- 录制产物：默认 `%USERPROFILE%\Documents\路演记录\<yyyyMMdd_HHmmss>\`；无权限时自动落到当前目录 `.roadshow\<时间戳>\`
  - `frames\` 截帧，`frames.jsonl` 元数据
  - `audio\audio_HHMMSS.wav` 每 10 分钟一段
  - `transcript.txt` / `transcript.jsonl`
  - `keyframes\` 去重后的幻灯片
  - `report_spec.json` → `路演会议纪要.docx`

## 标准流程

### 1. 开始录制

```powershell
powershell -ExecutionPolicy Bypass -File "<技能目录>\scripts\start.ps1"
```

可选参数：`-SessionDir <路径>`、`-Keywords "腾讯会议|路演|直播"`、`-Interval 6`、`-SegmentMinutes 10`。

说明：
- 只截**标题命中关键词**的窗口；聊天、文档、浏览器普通标签页不会被录入。
- 同时可见的多个路演窗口会**分别截帧**（见下节），不是只录最前面那个。
- 声音走 WASAPI 回环（录的是扬声器输出），不需要麦克风权限，也没有“立体声混音”设备要求。
- 录制中可随时用 `Get-Content <session>\frames.log -Tail 5` 看状态。

把 session 路径记下来，告诉用户“已开始录制”。

### 2. 结束录制

```powershell
powershell -ExecutionPolicy Bypass -File "<技能目录>\scripts\stop.ps1" [-SessionDir <路径>]
```

脚本会写 stop.flag、等进程退出、必要时强杀，并修复 WAV 头（硬杀也不丢数据）。

### 3. 转写（可后台跑，5–10 分钟/小时音频）

```powershell
$env:PYTHONPATH="<技能目录>\vendor"
& <python> "<技能目录>\scripts\transcribe.py" <session> --threads 4
```

- 模型 `ggml-small.bin`，中文效果可用；想更快可换 `ggml-base.bin`（需另下）。
- 首次跑会加载 487MB 模型，内存占用约 1GB；机器忙时用 `--threads 2`。
- 输出带时间戳的 `transcript.txt`，用 `read` 工具分段读，不要一次全读进来。

### 4. 提取幻灯片

```powershell
& <python> "<技能目录>\scripts\slides.py" <session>
```

然后用 `read_image` 看 `keyframes\` 里的图（按时间排序，通常每场 15–40 张）。
重点抓：**项目名/公司、一句话定位、核心亮点、融资需求（轮次/金额/估值/用途）、落地诉求、联系人手机/微信/二维码**。
二维码页用截图裁出二维码区域存成 `qr.jpg`，在 spec 里引用。

### 5. 写 report_spec.json 并出 Word

```powershell
& <python> "<技能目录>\scripts\build_report.py" <session>
```

spec 字段见 `scripts\build_report.py` 顶部注释。最低要求：`title`、`meta`、`overview`、`projects[]`（含 `name/tagline/highlights/financing/contact`）。
生成后用 `present` 把 docx 给用户，并在回复里给 5–8 行要点。

## 多窗口同时观看

- **画面**：每轮枚举所有标题命中、未最小化、且未被遮挡（采样点可见率 ≥60%）的窗口，逐个截帧，单轮最多 4 个；文件名带标题摘要，`frames.jsonl` 里有 `title` 和 `hwnd`，可按场次拆 keyframes。
- **切换/遮挡**：切到别的窗口不中断；被盖住或最小化的自动跳过，重新露出即恢复。窗口被遮住 40% 以上会被判定为不可见，尽量平铺摆放。
- **声音**：回环录的是整个系统输出，两场同时出声会混成一条轨、转写串词。建议同时只让一场出声（音量合成器静音另一场），或分时段录。
- **出纪要**：一个 session 里有多场时，先按 `frames.jsonl` 的 title 分组，再分别写 `report_spec.json`，用 `--out` 生成多份 docx。

## 关键注意事项

- **隐私**：录屏只在前台窗口命中关键词时进行；产物在用户本机。若用户要求删除，直接删 session 目录。
- **声音来源**：回环录的是本机扬声器输出。用户戴耳机也照样能录到（WASAPI loopback 在渲染端点取流）。
- **窗口标题不匹配**：录不到帧时让用户把会议窗口切到前台，或在 `start.ps1 -Keywords` 里加平台名；`frames.jsonl` 里有每帧的标题可排查。
- **WAV 只有 0 字节**：文件句柄未关闭时资源管理器/沙箱里看不到大小，属正常；`stop.ps1` 会修复。
- **转写太慢**：`--threads` 调低避免抢占会议；或只转写关键片段（`--limit-min`）。
- **模型缺失**：用 `scripts\dl.py` 下载（支持断点/多线程）：
  `python scripts\dl.py https://hf-mirror.com/ggerganov/whisper.cpp/resolve/main/ggml-small.bin models\whisper\ggml-small.bin 8`
- **不要**把整段 transcript 或原始帧直接贴进回答；只给结论和必要截图。

## 质量检查清单

- [ ] session 下 audio 有多个 wav，总时长与会议时长吻合
- [ ] transcript.txt 前 20 行语义通顺（若不顺，检查是否录到了声音）
- [ ] 每个项目的融资数字在幻灯片或转写中有出处，不臆造
- [ ] 联系人手机号与二维码来自画面，逐位核对
- [ ] docx 打开正常，图片不超出页面
