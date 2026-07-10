---
name: video-render
description: 把 video-scene-design 写好的 bespoke 场景渲染成最终 mp4（含 TTS 配音）。调用 render_bespoke.py（edge-tts + 读音字典 + Remotion）。当用户说"渲染视频"、"出 mp4"，或主 video-pipeline skill 调用时触发。输出 1920×1080 mp4。
---

> 📁 **路径约定（输入数据 / 产物落点 / 渲染引擎）以单一真源为准**：`~/code/video-agent-pipeline/README.md`。

# Video Render Skill

把 bespoke 场景（manifest.ts + 场景 .tsx）渲染成 1920×1080 mp4。

## 触发方式

- 用户显式：「/video-render」、「渲染视频」、「出 mp4」（场景已由 video-scene-design 写好 manifest + .tsx）
- 主 skill 调用：`video-pipeline` 最后一步

## 输入

1. `output_name`: mp4 文件名（如 `day1.mp4`）
2. `voice`: 可选，edge-tts voice（默认 `zh-CN-YunyangNeural` 男声播音员）
3. `rate`: 可选，语速（默认 `+0%`；`+15%` 偏快；`-10%` 偏慢）
4. `engine`: 可选配音引擎（默认 `edge`）。见下「配音引擎」。

### 配音引擎（默认 edge，本地模型有限/隔离）

- **默认 `--engine edge`**：edge-tts 播音男声云扬。合成时用 `Communicate` API 抓 **SentenceBoundary 逐句真实时间**，写入 `timing.json` 的 `sentenceTimes` → `beats.ts` 字幕/动画按真实句边界对齐（根治跨句漂移），缺失/句数不符自动回退字数估算。多音字走 `tts_fixes.json` + `polyphone_fixes.json`，渲前 `preflight_lint.py` 全量过审。
- **可选 `--engine indextts`**：本地 IndexTTS-2 神经模型，**仅特殊场景手动用**（音色克隆 / 顽固多音字）。跑在 `~/code/indextts2-demo/`（独立 venv 子进程，**主管线不 import torch、不调用即零内存零 GPU**）；慢（RTF≈2.25，10min 视频约 20min），不进默认自动流程。装/用见 `~/code/indextts2-demo/README.md`。

前置：video-scene-design 已在 `~/code/remotion-rlhf-poc/src/scenes/bespoke/` 写好 bespoke 场景 + `manifest.ts`。

## 你要做的事

这个 skill **不是内化型**——它是**对本地 Python 工具的调度封装**。

### Step 0: 同步课程表（开篇路线图依赖它）

渲染前先把课程权威源同步到渲染项目（开篇 `RoadmapFromCurriculum` 读这份副本）：

```bash
bash ~/code/video-agent-pipeline/tools/sync_curriculum.sh
```

课程表权威源在 `video-agent-pipeline/input/学习/curriculum.json`，渲染项目的 `src/curriculum.json` 只是同步副本——若大纲有改动而没同步，路线图会显示旧结构。

### Step 1: 渲染（bespoke 主路径 · 默认增量）

一条命令搞定 TTS + 渲染：

```bash
cd ~/code/remotion-rlhf-poc
# 项目化（推荐）：读 src/projects/<topic>/manifest.ts；--out-dir 指定产物落点（按 类型/课程）
python3 tools/render_bespoke.py --project "<topic_slug>" \
  --out-dir "~/code/video-agent-pipeline/output/<类型>/<课程>/<主题>" \
  --voice "<voice>" --rate "<rate>"
# 旧扁平方式（无 --project，读 src/scenes/bespoke/manifest.ts）仍兼容：
# python3 tools/render_bespoke.py --out "<output_name>"
```

> **项目化渲染（per-project 作用域）**：`--project <topic>` 读 `src/projects/<topic>/manifest.ts`（scene-design 写），入口 `Root.tsx`/`index.ts` 首次渲染自动脚手架。每片只打包自己的场景（按 manifest import tree-shake），**渲染算力不随历史片增长**；段缓存/timing 各片隔离 → **多片可并发渲染互不干扰，免 rsync 副本**。
> **产物统一落点（视频生产项目，按 类型/课程）**：用 `--out-dir` 把最终 mp4 输出到 `~/code/video-agent-pipeline/output/<类型>/<课程>/<主题>/`（与该主题的 KB/outline/封面等产物同目录，**无需再从 remotion out/ 拷回**）。类型=科普/学习/教程/故事/漫剧/开源速递；学习系列课再嵌一层课程（如 `学习/大模型学习/Day8_MiniGPT实战`）。`--out-dir` 缺省兜底 `output/<topic>/`。段缓存（构建中间物）留渲染引擎 `~/code/remotion-rlhf-poc/out/<topic>/segments/`。

`render_bespoke.py` 内部会：

1. 解析 manifest（`--project` 时为 `src/projects/<topic>/manifest.ts`，否则扁平 `src/scenes/bespoke/manifest.ts`）（场景顺序 + audioId + 文件）
2. 从每个场景 `.tsx` 提取 `NARRATION` 常量
3. 应用读音字典 `src/tts_fixes.json`（**配音侧修多音字**，如行 háng/调 tiáo），edge-tts 合成各段 mp3 + 写 `src/timing.json`（含逐句真实时间 `sentenceTimes`，驱动字幕/动画精确对齐）
4. **按段渲 clip → 哈希缓存 → ffmpeg 拼接**（默认增量），输出 `out/<output_name>`（1920×1080）

**重要**：必须**后台跑**（`run_in_background: true`）。首次渲染 5-15 分钟（逐段渲一遍建缓存）。退出码 0 即成功，产物在 `out/<output_name>`。

**增量渲染（默认行为·改一段只渲一段）**：

- 默认走增量：逐段比对指纹，命中且 clip 在则复用，只重渲改动段，再按 manifest 顺序 `ffmpeg concat` 成片。改 1 段渲染量约降到 1/N（23 段省 ~90%+ 时间）；只改视觉不动旁白连 TTS 都跳。**迭代修问题（如 video-eval 回灌某段）默认就用这条，不要 `--full`。**
- **每段指纹** = `hash(场景.tsx + 旁白 + voice + rate + engine)`；**全局指纹** = `hash(共享文件: design/ + primitives/ + components/ + _Scene/MainBespoke/SegmentBespoke/manifest/script + tts_fixes.json)`。改基元/主题/段顺序 → 全局指纹变 → **全部段重渲**（自动，无需手动）。
- 段缓存目录（构建中间物，留渲染引擎）：`--project` 时 `~/code/remotion-rlhf-poc/out/<topic>/segments/`；旧扁平为 `out/segments/<片名>/`（`<片名>` = `--out` 去扩展名）。含各段 `<audioId>.mp4` clip + `cache.json`。**最终 mp4 不在这里**，见上：经 `--out-dir` 统一落到视频生产项目 `output/<类型>/<课程>/<主题>/`。
- `--full`：强制全量渲 `MainBespoke`（老路径，单次大渲染）。一般不需要——增量在共享文件变时会自动全量重渲。
- `--clean-cache`：清 `out/segments/<片名>/` 后重建（缓存疑似脏/手动删过 clip 时用）。
- `--concat-aac`：段边界出杂音时启用（只重编码音频 `-c:a aac`，仍秒级）；默认 `-c copy` 最快无损。

**进度可视化**：增量按**待渲段数**报（`段缓存：18/23 命中复用，待渲 5 段` → `渲段 [3/5] p7_eb`）；`--full` 全量则每 ~4 秒打印帧进度条 `渲帧 [████░░] 42.3%`。后台日志 `tail` 即可拿最新进度贴给用户。完成后**验产物**：`ls mp4 && ffprobe -show_entries format=duration`（别只信 exit-code 摘要）。

发现新的读音错字 → 往 `src/tts_fixes.json` 的 `fixes` 加一条 `{match, tts, sub}`（一次补全部视频受益）；`tts_fixes.json` 在全局指纹里，改它会触发全部段重渲（配音侧），符合预期。`--skip-tts` 含义不变（复用现有 mp3 + timing.json）；增量下它进一步意味着**永不跑 TTS**，只按 tsx/全局指纹判断重渲——想让读音修正生效就别加 `--skip-tts`。

### Step 2: 产物落地

`--project` + `--out-dir` 时，成片**直接落到** `~/code/video-agent-pipeline/output/<类型>/<课程>/<主题>/`（与该主题 KB/outline/封面/eval 同目录），**无需再手动 mv**。段缓存留渲染引擎 `out/<topic>/segments/`。脚本退出码 0 即成功。（旧 `render_from_specs.py` 已废弃，一律走 `render_bespoke.py`。）

### Step 3: 报告

完成后（task-notification 自动收到，确认退出码 0）给用户：

- mp4 路径（本地）
- 时长（`ffprobe -v error -show_entries format=duration ...`）+ 文件大小
- 关键参数（voice / rate）

## 环境依赖

- edge-tts + ffmpeg/ffprobe + node/npm + Remotion 项目已 `npm install`（含 `katex`）
- 代理: `http://127.0.0.1:10809`（edge-tts 走微软 Azure）

## 隔离渲染副本（共享项目被并行生产占用时·必看）

`remotion-rlhf-poc` 是共享项目。**当有另一路视频正在用它生产**（manifest.ts / timing.json / public/audio 被另一套场景占着）时，直接在主项目渲会撞 manifest、timing、audio 撞名——两路互相覆盖。此时走**隔离副本**：

```bash
SRC=~/code/remotion-rlhf-poc; DST=~/code/remotion-<topic>     # 如 remotion-tf
rsync -a --exclude node_modules --exclude out "$SRC/" "$DST/"
ln -s "$SRC/node_modules" "$DST/node_modules"                  # 软链 node_modules，不复制
cd "$DST" && python3 tools/render_bespoke.py --out <name>.mp4  # 在副本里渲，互不干扰
```

判断要不要隔离：渲染前看 `remotion-rlhf-poc/src/scenes/bespoke/manifest.ts` 当前装的是不是本次的场景；不是（被另一路占着）就隔离。见 memory [[video-render-isolated-copy]]。
段缓存 `out/segments/<片名>/` 落在副本自己的 `out/` 下，与主项目天然隔离，无需额外处理；rsync 时已 `--exclude out`，副本首次渲会自建缓存。
⚠️ **隔离副本是临时的**：基元/`beats.ts`/`PRIMITIVES.md` 的改动**必须改真源** `remotion-rlhf-poc` 再 `cp` 到副本，绝不只改副本（下次 rsync 被覆盖）。

## 注意

- 这个 skill **必须调用本地工具**，不是内化思考
- **必须后台跑** + task-notification，不阻塞对话
- 渲染前确保 video-scene-design 已写好 manifest.ts + 场景 .tsx
- 旧的 `render_from_specs.py`（8 模板 + scene_specs.json）已废弃，一律走 `render_bespoke.py`
