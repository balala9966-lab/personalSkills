---
name: video-pipeline
description: 视频生产主流程编排。从主题关键词到最终 mp4 一气呵成，串接 video-retrieval → video-research → video-script → video-scene-design → video-render，每个内容阶段用 video-content-eval 出质检报告 + review 卡点。当用户说"做一个 X 主题的视频"、"为这份材料生成完整视频"、"一键出视频"时触发本 skill。
---

> 📁 **路径约定（输入数据 / 产物落点 / 渲染引擎）以单一真源为准**：`~/code/video-agent-pipeline/README.md`。

# Video Pipeline Master Skill

主编排 skill，从关键词或一份素材到最终 mp4。

## 触发方式

用户显式：

- 「/video-pipeline <主题>」
- 「做一个关于 X 的学习视频」
- 「用这份资料 <path> 生成完整视频」
- 「一键出视频」

## 输入

最低要求：`keywords`（主题关键词）。

可选：

- `script_type`: `科普` | `故事` | `漫剧` | `学习` | `教程` | `开源速递`（默认 `科普`）
- `materials_path` 或 `materials_text`: 种子素材（markdown / 文档 / 笔记）。如果没有，提示用户提供，否则尝试不带素材的自主研究模式（质量会降低）
- `output_root`: 产物目录（默认按 **类型/课程** 组织：`~/code/video-agent-pipeline/output/<script_type>/<topic>/`；学习系列课再嵌课程层，如 `output/学习/大模型学习/Day8_MiniGPT实战/`）。渲染时把此目录作为 `--out-dir` 传给 video-render，成片直接落到这里
- `auto_continue`: 是否自动跳过 review 卡点（默认 `false`，每步都让用户确认）
- `voice` / `rate`: 渲染参数（默认 `zh-CN-YunyangNeural` / `+0%`）

## 总流程

```
keyword + materials
    ↓
[STEP 1] /video-retrieval  → 0_materials.json   ←──┐ 补检循环（自动）
    ↓                                              │
[STEP 2] /video-research   → 1_knowledge_base.json │
    ↓ ── content-eval 卡点 1 ──────────────────────┤
[STEP 3] /video-script     → 2_outline.json        │ 缺口→retrieval_requests.json
    ↓ ── content-eval 卡点 2（最关键）─────────────┤
[STEP 4] /video-scene-design → 脊柱 scene_spine.json + bespoke 场景.tsx + manifest ─┘
    ↓ ── content-eval 卡点 3 ──                                        ↑ 帧级回灌
[STEP 5] /video-render     → <topic>.mp4 + litterbox 链接              │（音画错位/重叠）
    ↓ ── video-eval 帧级审查 卡点 4 ──────────────────────────────────┘
[STEP 6] 完成 / 投递
```

**三个循环**（详见末尾「循环的控制流」）：

- **补检循环（自动）**：任一阶段写了 `retrieval_requests.json`，回调 video-retrieval 补搜，`max_gapfill=2` 兜底
- **内容质量卡点（C 方案·诊断不改）**：每个内容阶段后调 `video-content-eval` 出报告，摆给用户拍板，**绝不自动重写**。**质检一律走独立 fresh-context 子代理**（写产物的人不评自己的产物，同上下文自评=橡皮图章）；有 `framework_path` 就传给 eval 做外部框架核对
- **帧级修复循环（渲染后）**：`video-eval` 抽帧查音画错位/组件重叠，点名的段回灌 `video-scene-design` 定向修，`max_framefix=2` 兜底

## 你要做的事

### Step 0: 收集输入

用 AskUserQuestion 确认：

- keywords（如未给）
- script_type（建议根据上下文推断：如果材料含代码/教程结构，推 `学习`；否则 `科普`）。若 keywords 是一个 GitHub repo（来自 `tools/trending_repos.py` 的每周 AI 热门候选），推 `开源速递`——干货速览，弱钩子，绕开 curriculum（`active_node_id=null`），materials 优先用 repo 的 README/url
- materials（如果用户没主动提供，问"你有现成材料文件吗？还是让我自主研究？"）
- **权威框架文档（关键·别等做完 KB 才拿到）**：问"你有没有现成的权威框架/分层结构/大纲/术语表？"。有就**全程作为外部比对标尺**——retrieval 按它定补检靶、research 按它逐子项填 KB、scene-design 框架总览主视觉按它画全、每个内容卡点把 `framework_path` 传给 content-eval 的 `external_framework_fidelity` 维度逐项核对。中途才拿到 = KB 要返工一轮。
- 用户的**导向/风格偏好**（若 memory 有则照用）：如"不走就业指导、导向真实项目应用"、"讲清因果别只陈述"、"详略分明"等。
- auto_continue（"每步是否都让你 review？还是 auto 跑完？"）

初始化产物目录 `<output_root>/<topic>/`，并写一个空的 `retrieval_requests.json`（内容 `[]`）。

**解析课程节点（系列学习课程）**：把 keywords 对到 `input/学习/curriculum.json` 的一个节点，定下 `active_node_id`（如"概率与优化"→`prob-opt`）。这个 id 之后**通过 KB 的 `series_context` 自动往下游流**（retrieval 锚 → research 装配 series_context → script 写系列定位 / scene-design 开篇路线图取 `active_node`），无需单独配置文件。对不上节点（自由主题）则 `active_node_id=null`，按非系列处理。

如果输入完整、有把握，可跳过 AskUserQuestion 直接开干。

### Step 1: 素材搜集（联网）

调用 `video-retrieval` skill。它**多路并行召回**（roadmap 课程文本 + curriculum 课程表 + Web + GitHub，委派子代理）再整合，产出 `0_materials.json`（含 `knowledge_outline`）+ `0_materials_review.md`（召回审查）。

- 简短报告：知识点覆盖 / 素材条数（P0/P1/P2）/ 对标视频数 / GitHub repos
- **召回审查 gate（轻量·只查覆盖与故事完整性，不评写作质量）**：读 `0_materials_review.md` 的结论。
  - `gate=pass`（无 P0 缺口）→ 直接进 Step 2。
  - `gate=blocked`（有 P0 缺口，会导致故事断/推导缺环）→ 先走**补检循环**（retrieval 已把 P0 缺口写成 `blocking=true` 的 `retrieval_requests`）补一轮；`max_gapfill` 内补齐则继续，超限仍缺则带缺口继续并**显式提示用户哪些 P0 缺口未补到**（不静默前进、不假填）。
- 这步**不评写作质量**（那是下游 KB content-eval 的活），只用 P0 覆盖账目尽早拦"信息缺失/故事不完整"。

### Step 2: 知识库构建

调用 `video-research` skill，输入 `0_materials.json`。等它完成，产出 `1_knowledge_base.json`。

**先处理补检**：读 `1_knowledge_base.json` 的 `retrieval_requests` 字段——若非空，执行补检循环（见末尾），补完再继续。

**质量卡点 1（content-eval）**：

- 调 `video-content-eval`（target_type=knowledge_base），出 `eval/knowledge_base_report.md`
- 给用户看：overall 判定 + 关键维度分 + critical/high 问题摘要
- 用 AskUserQuestion 问："知识库是否合格？1) 进入下一步；2) 按报告让 video-research 重写；3) 我手工调；4) 中止"
- 选 2 时，把报告末尾的「修正要点」传给 video-research 重写，再重新 eval
- `auto_continue=true`：仍跑 eval 并报告；overall=fail 才停下问，否则自动放行

### Step 3: 大纲生成

调用 `video-script` skill，输入 `1_knowledge_base.json`。产出 `2_outline.json`。

**先处理补检**：检查 `retrieval_requests.json`——video-script 可能在写作时发现缺口写了进去。非空则执行补检循环（补完后视情况回灌 research 更 KB，再重跑 script）。

**质量卡点 2（最关键，影响视频质量上限）**：

- 调 `video-content-eval`（target_type=outline，context 带 `1_knowledge_base.json`），出 `eval/outline_report.md`
- content-eval 会重点查：concept_grounding（术语两段式）、visualization（具体可拍）、学习视频强制元素
- 给用户结构化报告（overall + 各维度 + issues）
- 用 AskUserQuestion 问："outline 是否合格？1) 进入下一步；2) 按报告让 video-script 重写；3) 我手工调；4) 中止"
- 选 2 时，把报告「修正要点」传给 video-script 重写，再重新 eval

**质量卡点 2.5（交付前·用户视角验收 = 抢在用户前面当裁判）**：

> 背景：曾出现 content-eval 各维度高分、用户却整体否决（"只讲项目是什么、没指导思想、没效果经验、场景泛泛、干货压结尾"），返工两轮。维度打分会漏掉**格式合格但 gestalt 不达标**的产物。这一步在**最便宜的 outline 阶段**（还没花 scene-design + ~30min 渲染前），派一个独立 agent **扮演挑剔的用户**，整体过一遍"我会不会接受"，把用户从"事后裁判"位置解放出来。

- 派**独立 fresh-context 子代理**，扮演用户角色，读 `2_outline.json` + `1_knowledge_base.json`，用**六问验收尺子**逐条判 accept/reject（grounded 到具体 seq）：
  1. **指导思想**：有没有一条贯穿全片、能改观众判断力的 thesis，还是把要点罗列一遍？（rubric `guiding_thesis`）
  2. **可实践 how**：最关键的"怎么做"给了**可操作配方 + 真实例子**吗，还是只说"很重要/很难"？（`actionability_recipe`）
  3. **场景尺子**：适用场景给了**能用的判据**（尺子/checklist/正反例），还是泛泛"XX 就适合"？（`scenario_specificity`）
  4. **干货前置**：最 actionable 的干货在 ≤60% 处，还是压到结尾多数人看不到？（`payoff_frontloading`）
  5. **可视化讲清（规划层）**：优化/搜索/演进类段的 `visual_anchor` 是否能看出"走向/逐步变化"，还是一团静态？（`viz_communicates` 前瞻）
  6. **可读性**：旁白有无 TTS 符号/多音字、字幕长句一坨？（先跑 `preflight_lint`，把结果带给子代理复核）
- 子代理产出 `eval/user_acceptance_report.md`：**会接受 / 会打回** + 被打回的条目（哪条尺子 + 具体 seq + 怎么改）。
- **判定**：有"会打回"项 → 视为不达标，**在这里就回 video-script 修**（带"修正要点"），别带着内容缺陷去 scene-design/render。`auto_continue=true` 时：有打回项也先停下报告（这是最关键的内容门，不自动放行）。
- 这是"front-run the judge"——它用的是**用户验收尺子**而非内部代理指标，专治 v1 那类"合格但不达标"。

### Step 4: 场景设计（bespoke）

调用 `video-scene-design` skill，输入 `2_outline.json` + `1_knowledge_base.json`（`active_node_id` 取 KB 的 `series_context.active_node`）。它先用一次全局 pass 定**脊柱 `scene_spine.json`**（保证连贯 + 组件多样），再**每段派独立子代理并行现写 bespoke 场景 .tsx**（每段只带自己那片知识，注意力集中），最后装配 `manifest.ts` 到 `~/code/remotion-rlhf-poc/src/scenes/bespoke/`。时序一律 beat 锚定旁白（防音画错位）、布局守三分区（防组件重叠）。开篇用 `RoadmapFromCurriculum` 定位今天节点。

**先处理补检**：检查 `retrieval_requests.json`，非空则补检循环。

**质量卡点 3（脊柱文本 + 画面双查）**：

- 脊柱建好后，调 `video-content-eval`（target_type=scene_spine，context 带 outline）查**规划层**：组件多样性 / 可视化贴合 / kb_slice 深度落地 / beat 映射 / 强制元素没丢，出 `eval/scene_spine_report.md`
- scene-design 装配后自己会渲句子边界帧 still 多模态审图（画面对得上旁白、运算过程算出来、公式 KaTeX、无重叠不局促）——画面级
- 给用户：脊柱 eval 摘要 + 每段用了什么可视化形式
- 用 AskUserQuestion 问："场景是否合格？1) 进入渲染；2) 让 video-scene-design 调某段；3) 中止"
- `auto_continue=true`：脊柱 eval pass + still 无硬伤则放行

### Step 5: 渲染

**渲前预检（preflight_lint · advisory · 不阻塞）**：场景写好、配音前，先跑
`python3 ~/code/video-agent-pipeline/tools/preflight_lint.py --project <topic_slug>`
它扫各段 NARRATION 查三类可读性坑：①TTS 代码符号（下划线/`.py`/`.md` 等未进 `tts_fixes` → 会读"下划线/点"）②多音字/易误读词（如"重头"读 chóng）③字幕长句一坨（单句 >32 字）。**纯建议、退出码恒 0、绝不阻塞**——据它**按需补 `tts_fixes.json` 或把长句拆短再渲**（拆短改了 NARRATION 要重生成 timing）。这步专治"配音读符号 / 字幕糊一坨"那类等用户事后才发现的坑。

调用 `video-render` skill（走 `render_bespoke.py`：TTS+读音字典+**默认按段增量渲染**+ffmpeg 拼接）。**后台跑**，等通知。渲染会生成/更新 `timing.json`（各段真实音频秒长）——这是后续帧级审查算句子时点的依据。

> **迭代修问题默认增量**：帧级修复循环里 scene-design 改完某几段，重渲走默认增量（只渲改动段再拼接），大幅缩短环路；改基元/主题等共享文件时增量会自动全量重渲。
> **渲染前**：scene-design 应已做"全段冒烟渲帧"。首次/全量 render 全或无、~10min/700s，一个边界 bug（单 beat `seg(0,0)` 等）会废掉整轮——冒烟过了再 render。
> **节奏**：`render_bespoke.py` 的 pad 按段长配（短开头/金句段 0.9-1.2s），别统一 DEFAULT_PAD=2.2 套到短段造成长留白。
> **进度可视化**：remotion 进度用 `\r` 不落盘、日志空——数临时帧目录 `/tmp/.../react-motion-render*/` 帧数 ÷ 总帧数(秒×30) 做进度条。

**完成后**（**验产物，别信后台 exit-code 摘要——曾报 exit0 实则崩了**）：

- `ls mp4 && ffprobe -show_entries format=duration` 确认成片存在且时长合理
- 给用户 mp4 路径 + 时长 + 文件大小
- 列出本次 pipeline 的所有产物路径

**质量卡点 4（帧级音画/重叠审查）**：

- 调 `video-eval`（输入 manifest.ts + timing.json + outline，渲染后也可直接用 mp4），按句子时点抽帧，重点查 **audio_anim_sync（人声/动画错位）** 和 **element_overlap（组件重叠）**，出 `eval/video_frames_report.md`
- 给用户：overall + 两类硬伤计数 + 被点名的段
- 用 AskUserQuestion 问："视频帧级是否合格？1) 完成；2) 按报告让 video-scene-design 定向修被点名的段；3) 我手工调；4) 中止"
- 选 2 时：把报告「回写给 video-scene-design 的修正要点」+ 段 id 列表，作为 `current_eval` 传给 `video-scene-design`——**它只重做被点名的那几段**（不整片重来），改完重渲该段、再回 video-eval 复审（最多 2 轮，`max_framefix=2` 兜底）
- `auto_continue=true`：仍跑审查并报告；出现 audio_anim_sync≤3 或 element_overlap≤3（critical 硬伤）才停下问，否则自动放行

### Step 6: 收尾

简短总结：

- 主题
- script_type
- 总耗时（粗略）
- 最终视频时长 / 大小 / 链接
- 各阶段产物路径供后续复用

**交付后动作（可选）**：用户要发布物料时调 `video-publish` skill——基于成片核心内容出两张封面（3:4+4:3）+ 标题/描述/标签，整体发飞书（封面图片 + 物料文档 + 成片 mp4 三样都发）。

## 循环的控制流

### 循环 1 · 补检（信息完整性，自动）

任一内容阶段发现信息缺口（research 写进 KB 的 `retrieval_requests` 字段；script/scene-design 追加进 `retrieval_requests.json`）时：

1. 读 `retrieval_requests.json`（或 KB 的 retrieval_requests 字段），若非空且 `gapfill_count < max_gapfill(=2)`
2. 调 `video-retrieval`（补检模式），它定向补搜、追加进 `0_materials.json`、清空 `retrieval_requests.json`
3. `gapfill_count += 1`
4. 视缺口性质：若缺的是知识库层面，回灌 `video-research` 更新 KB；然后回到触发缺口的阶段重跑
5. `gapfill_count` 达上限仍有缺口 → 不再补，带着缺口继续并提示用户

**这是自动循环**——信息缺失是客观事实，不需要用户拍板。

### 循环 2 · 质量卡点（C 方案：诊断不改，用户拍板）

每个内容阶段产物出来后，调 `video-content-eval` 出质检报告：

- eval **只诊断不改**，产出 `eval/<stage>_report.md`
- 把 overall 判定 + 关键维度分 + critical/high 问题摆给用户
- 用户决定：放行 / 按报告让上游 skill 重写 / 手工调 / 中止
- 选"重写"时，把报告末尾「修正要点」直接传给上游 skill（video-research/script/scene-design）作为重写依据，重写后再 eval 一次
- **eval 绝不自动触发重写**，决定权始终在用户

### 循环 3 · 帧级修复（渲染后，用户拍板）

渲染出 mp4 后，`video-eval` 按句子时点抽帧查音画错位/组件重叠：

1. 出 `eval/video_frames_report.md`，点名哪几段有 critical/high 硬伤
2. 用户选"修"时，把报告「修正要点」+ 段 id 列表作为 `current_eval` 传给 `video-scene-design`
3. scene-design **只重做被点名的段**（派对应子代理），改完只重渲那几段，回 video-eval 复审
4. `max_framefix=2` 兜底，仍有硬伤则带问题交付并提示用户

三循环职责不重叠：循环 1 管"信息够不够全"，循环 2 管"文字内容好不好"，循环 3 管"成片画面对不对（音画同步、无重叠）"。

## 关键设计原则

1. **不绕过质量卡点**：除非用户明确说 `auto_continue=true`（即便如此 eval 仍要跑、报告仍要出，只是 pass/conditional_pass 自动放行）
2. **每个 sub-skill 用 Skill 工具调用**：不要直接 inline 执行其逻辑
3. **失败处理**：任何 sub-skill 失败，先告诉用户具体哪里失败，让用户决定重试 / 调整 / 中止，**不要默默重试**
4. **产物可复用**：materials / 知识库 / outline / scene_spine + bespoke 场景 都是独立文件，下次跑同主题可以从任意步骤接续
5. **子 skill 互相独立、不污染上下文**：彼此只通过磁盘 JSON 通信
6. **子代理驱动执行（已验证·返工小）**：每个可分解的阶段都派**独立 fresh-context 子代理**去做、主 skill 只编排 + 审子代理输出 + 管上下文——retrieval 四路并行、content-eval/outline-eval/scene_spine-eval 各一个独立评审、scene-design 每段一个子代理、画面审查每批一个子代理。好处：写产物的人不评自己的产物（防自评橡皮章）、注意力集中（每段只带自己那片知识）、可并行更快、上下文不爆（子代理只回精炼摘要、不回灌全文）。主 skill 必须**复核子代理摘要**（别盲信"PASS"），把 critical/high/medium 落实到定向修改。
7. **全自动质量门（`auto_continue=true` / 无人值守时）**：门槛从"pass 即过"升级为**所有质检问题（含 medium + high）全部修复到 0 才往下**（low 视成本酌情）；卡点报告里每条 medium/high 都定向编辑上游产物落实（不整篇重写）。画面审查重点 = **组件展示合理性 + 位置准确性**，用"组件充分展示的那一帧"按**句子时间轴**抽帧（句中点 + 相位边界 + 应显示句子映射），别用粗略的时长分数抽帧——音画错位/相位漂移只有句级抽帧能抓到（见 [[video-autonomous-quality-bar]]）。

## 跨阶段产物路径约定

```
<output_root>/<topic>/
├── 0_materials.json          # video-retrieval 产物
├── 0_materials_review.md      # video-retrieval 召回审查（覆盖/优先级/P0缺口 gate）
├── 1_knowledge_base.json     # video-research 产物
├── 2_outline.json            # video-script 产物
├── scene_spine.json          # video-scene-design 脊柱（全局规划，子代理按它现写各段）
├── retrieval_requests.json   # 补检契约（下游写缺口，video-retrieval 读后清空）
├── eval/                     # content-eval + video-eval 各阶段报告
├── <topic>.mp4               # video-render 产物（--project 直接输出到此，无需从 remotion 拷回）
└── README.md                 # 可选: 本次 pipeline 摘要

# bespoke 场景是代码，住在 remotion 项目里（不在 output/）：
~/code/remotion-rlhf-poc/src/scenes/bespoke/{Intro,Hook,...}_<slug>.tsx + manifest.ts
```

主 skill 跑完后写一份 README.md 总结本次 pipeline 配置和产物。

## 注意

- 主 skill 自己不做"内化思考"，所有内容生成由 sub-skill 完成
- 主 skill 是"协调者 + 质检员"，负责 review 卡点 + 失败处理 + 产物管理
- 不要修改 sub-skill 的产物，让 sub-skill 自己负责修
- 用户在某个卡点说"我手工调"时，等用户编辑完文件再继续，**不要催**

## P1《数据工程》自进化补丁（2026-07-06 · append-only）

- **子代理报"完成"必先 `ls` 验产物存在再信**：长任务可能后台仍在跑（P1 outline 子代理首轮报完成但文件不存在、其实后台又跑了 17min），别凭摘要判"幻觉"就自己重做——先验文件是否真落盘、内容是否合法（`python3 -c "import json;json.load(...)"`），产物确实缺失再补救。呼应「验产物，别信后台 exit-code 摘要」。
- **默认只交付 1.25x 版、不产不留 1 倍速**（2026-07 用户定："以后直接渲1.25x，不需要1倍速，省时省盘"）：render 出 1x → `setpts/1.25+atempo=1.25` 出 `<topic>_1.25x.mp4`（CBR 10M）→ **删掉 1x 中间产物**，只把 1.25x 交付。省时优化方向见 memory `video-playback-speed`。
- **飞书只在用户明说"发飞书"时才发**：出片/出物料后**不自动发飞书**，只报本地路径等用户发话（`video-publish` 的 `send` 默认已改 false）。
