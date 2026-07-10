---
name: video-eval
description: 对生成的视频做多模态视觉质量评估。按句子时间点渲染每段多帧 PNG，用 Claude 多模态能力打分（信息密度/视觉层级/配色/动画时机/独特性），并重点检测「人声与动画错位」和「组件相互重叠」两类硬伤，定位到具体段/时点，回灌 video-scene-design 修。当用户说"评估这个视频"、"看看视频效果"、"和上一个视频对比"，或主 video-pipeline 在渲染后调用时触发。输入 bespoke 场景 + manifest/timing 或现有 mp4，输出评估报告 + 每段修正要点。
---

> 📁 **路径约定（输入数据 / 产物落点 / 渲染引擎）以单一真源为准**：`~/code/video-agent-pipeline/README.md`。

# Video Eval Skill（帧级视觉 + 音画/重叠审查）

用多模态评估 bespoke 视频的视觉质量，**重点抓三类高频硬伤**：

- **音画错位**：旁白讲到某内容时，对应动画没跟上 / 跑在前面 / 被切掉；字幕句与画面对不上。
- **组件重叠**：元素叠在一起、文字压住字幕、相位交叠没淡净、内容溢出安全区。
- **开局炫技不足（seq0·留人生死线）**：开场前 2 秒静止画面 / 小字矩阵 / 抽象曲线柱图 / 温吞清单缓慢填色 / 抽象粒子星图——一眼 AI 味、留不住人。对照 rubric `opening_viz_richness`（**critical 级**），命中红线**直接判回**，和错位/重叠一样死磕（详见 memory `video-viz-cold-open`）。

> 与 `video-content-eval` 区分：那个读 JSON 评文字内容；本 skill 渲染真实帧、用眼睛看画面。

## 触发方式

- 用户显式：「/video-eval」、「评估视频质量」、「这视频有没有错位/重叠」
- 主 skill 调用：`video-pipeline` 渲染完成后

## 输入

1. `manifest_path`: `~/code/remotion-rlhf-poc/src/scenes/bespoke/manifest.ts`（场景顺序 + audioId）
2. `timing_path`: `~/code/remotion-rlhf-poc/src/timing.json`（各段 audioSec/sceneSec；由 render 生成）
3. `outline_path`: 可选，`2_outline.json`（核对画面是否忠实承接大纲；也是 narration 来源之一）
4. 或 `mp4_path`: 现有 mp4（直接按时间点抽帧）
5. `compare_with`: 可选，对比参照的 mp4（检测雷同）
6. `output_path`: 报告路径（默认 `<同目录>/eval/video_frames_report.md`）

## 核心思路：按「句子时间轴」抽帧（不是只取中点）

错位/重叠都是**时间局部**问题，单取每段中点一帧抓不到。本 skill 按**句子边界**密集抽帧——因为字幕和动画 beat 都锚在同一句子时间轴（`beats.ts`），所以"第 i 句讲到的时点"正是该检查"动画 beat 是否同步入场、是否和上一相淡净"的时点。

> ⚠️ **不许走捷径（血泪教训）**：图省成本只抽"每段中点 1 帧"或只抽"高风险子集"，会系统性漏掉相位局部的重叠（如最后一相柱压金句）和末段位置问题（如内容贴字幕带）——这些恰恰不在中点。**必须全 N 段覆盖 + 每段按句子/相位边界抽帧**。
> 先**验产物再评**：`ls mp4 && ffprobe -show_entries format=duration` 确认成片存在且时长合理——别信后台渲染的 exit-code 摘要（曾报 exit0 实则崩了）。

### 帧时点算法

1. 读 `manifest.ts` 拿场景顺序 + 各段 `audioId`；读 `timing.json` 拿每段 `audioSec`、`sceneSec`。
2. 累加 `sceneSec` 得每段起始秒 `from[k]`（FPS=30）。
3. 每段读它的 `NARRATION`（从该段 .tsx 的 `export const NARRATION`，或 outline.json 对应段），按 `。！？；` 拆句，按**字数比例 × audioSec** 算每句 `[start,end]`（与 `SyncSubtitle`/`beatsOf` 同算法）。
4. 为每段渲染这些帧（绝对帧号 = 秒 × 30）：
   - **seq0 开局必抽前 2 秒帧**（绝对帧 15 / 30 / 60，即 0.5s / 1s / 2s）—— 专查 `opening_viz_richness`：前 2 秒有没有运动 + 尺度 + 具体性（一个有分量的真实示例在发生），还是静止 / 小字矩阵 / 抽象曲线 / 温吞清单 / 粒子星图（命中即 critical 判回）。**这三帧必抽，和错位/重叠的抽帧一样不许省**。
   - **每句中点帧** `(from[k] + (s.start+s.end)/2) * 30` —— 查音画同步（这一刻画面是否在讲这句）
   - **每个相位边界帧** `(from[k] + s.start) * 30` 和 `±0.3s` —— 查相位交叠是否淡净、有无瞬时重叠
   - **establishing 镜头的可读时长帧**（查 readability_dwell）：识别信息密集主视觉所在的相位（架构图/公式/代码/矩阵），额外抽该相位的 **入场后 0.4s / 中段 / 退场前 0.2s** 三帧——0.4s 帧看 reveal 画完没、退场前帧看够不够静止时间。短相位（窗 <2s）尤其要抽，正是一闪而过高发区。
   - 段太长时一句一帧即可；务必覆盖到每个主要 beat。

> ⚠️ **禁捷径是硬机制不是建议**：必须**全 N 段覆盖** + 每段按上面四类时点抽帧，**不许降分辨率拼 montage、不许只抽中点、不许只挑高风险子集**——重叠是相位局部的、一闪而过是短相位的、贴字幕带是末段的，都不在中点。走捷径漏检 = 本次评估作废。

### 抽帧命令（bespoke）

```bash
cd ~/code/remotion-rlhf-poc
# 抽帧前先做同步一致性自检（只读）：确认 timing/mp3 对齐当前 NARRATION，否则抽出来的帧 beat 是错的
# 项目化片传 --project <topic>（与 render 一致）；旧扁平片省略 --project
python3 tools/render_bespoke.py --project <topic> --check-timing || python3 tools/render_bespoke.py --project <topic> --tts-only  # 过期(exit 3)就只重配过期段
# ⚠️ 别用 gen_tts.sh（旁白写死成 Day1）
# 按算好的帧号逐帧渲（合成名 = MainBespoke；项目化片用项目入口，旧扁平用 src/index.ts）：
npx remotion still src/projects/<topic>/index.ts MainBespoke out/eval_<sceneId>_s<i>.png --frame=<N>
```

mp4 输入时：把上面算出的「绝对秒」喂 ffmpeg 精确抽帧：

```bash
ffmpeg -ss <sec> -i <mp4_path> -frames:v 1 -q:v 2 out/eval_<sceneId>_s<i>.png
```

## Step 2: 逐帧多模态评估（Read PNG）

逐张 Read PNG。每帧按下面维度打分（1-10），**前两维 + seq0 的 `opening_viz_richness` 是本次重点**：

> **元标准对齐（防漂移）**：评分标尺(1-10) / severity / grounded / pass·conditional_pass·fail 判定格式 / 质检纪律，统一见 `~/code/video-agent-pipeline/docs/quality_rubric.md`（§一 元标准 + §三 视觉维度目录）。下列维度分档为本 skill 操作细则，二者并用。

| 维度                                   | 1-10           | 评分要点                                                                                                                                                                                                                                                         |
| -------------------------------------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **audio_anim_sync**（重点）            | 音画同步       | 这一刻字幕显示的是第 i 句吗？画面主可视是否正是这句在讲的东西？该入场的 beat 入场了吗（没缺、没提前演完）？详见下方分档                                                                                                                                          |
| **element_overlap**（重点）            | 组件不重叠     | 有没有元素叠一起/文字压字幕/被边缘切掉/两个大件并排挤？相位切换处上一相淡净没？详见下方分档                                                                                                                                                                      |
| **opening_viz_richness**（seq0·留人生死线·重点·仅评开局前2秒帧） | 开局够不够炫技/吸引 | 只看 seq0 帧15/30/60：是否一个**有分量的真实示例在发生**（运动+尺度+产品级精致：多元素协同/大计数器狂飙/流式日志/图表动效）？命中 ❌静止/❌小字矩阵/❌抽象曲线柱图/❌温吞清单填色/❌抽象粒子星图 任一红线 = **critical 打回**。判据：缩到手机尺寸前2秒会不会立刻划走。详见 rubric `opening_viz_richness` + memory `video-viz-cold-open` |
| **layout_quality**（位置质量）         | 位置/留白      | 不只查硬重叠：内容是否贴字幕带(<160px留白)、明显偏心、整体偏下局促？多项浮现的场景是否每项都充分可见（禁中间项永不显示）？                                                                                                                                       |
| **pacing**（节奏/留白）                | 时间体验       | 有没有死气的长留白（讲完后尾部静音过长，短段尤甚）？看 timing.json 各段 (sceneSec−audioSec) 尾静音 >2s 或占比 >20% 即扣分、标出来                                                                                                                                |
| **readability_dwell**（可读时长·重点） | 关键镜头看得清 | pacing 管"太长留白"，本维度管反方向的**"太短一闪而过"**：架构总览图/完整公式/代码块/矩阵这类信息密集主视觉，**有效可见时长够不够看清**？逐个 establishing 镜头算它的相位窗时长（退场秒−入场秒），<2s = 大概率一闪而过（reveal 动画还要吃掉 ~0.5s）。详见下方分档 |
| information_density                    | 信息密度       | 不空也不挤；学习视频信息量可高但不能糊                                                                                                                                                                                                                           |
| visual_hierarchy                       | 视觉层级       | 主标题/次标题/正文/装饰 对比清晰                                                                                                                                                                                                                                 |
| color_harmony                          | 配色协调       | 主色+强调+中性搭配舒服，避免过暗；**一致性锁**：全片强调色是否只用暖橙(蓝/绿仅语义角色)、同一语义是否同色、有无纯黑投影                                                                                                                                          |
| **taste_antislop**（品味/反默认·新）   | 不一眼 AI 味   | 移植自 taste-skill 的视觉品味红旗(见下方分档)：AI 紫/彩虹渐变文字/霓虹发光/无信息装饰线/角标编号/破折号上屏/堆大字号当层级/又一个居中构图/为炫而动的无意义动画。命中即扣，是 study-dark 高级感掉档的主因                                                         |
| font_legibility                        | 字体可读       | 中/英/代码 字体字号合适                                                                                                                                                                                                                                          |
| animation_timing                       | 动画节奏       | 跨帧看入场节奏，过快/过慢扣分（多帧才评得准）                                                                                                                                                                                                                    |
| scene_distinctiveness                  | 独特性         | 一眼记得住，不和其他视频雷同；**高潮/框架图/飞轮等 hero 主视觉提权重——朴素通用基元撑不起高潮要打回，要求精致、配得上 study-dark 高级感**                                                                                                                         |

### audio_anim_sync 分档（硬标准）

- **1-3（fail）**：字幕在讲 A、画面还停在 B（或空白）；或该句的可视化 beat 根本没出现 / 早就演完定格。明显错位。
- **4-6**：大致对得上但有 ~1 句的滞后/超前，或 beat 入场时机偏。
- **7-8**：画面紧跟旁白，beat 在讲到时入场。
- **9-10**：逐句严丝合缝，动画在配音结束前演完、pad 尾段干净定格。

判定方法：把帧上的**字幕文字**读出来，和"这一刻应是第 i 句"比对（字幕错位＝时间轴问题）；再看**主可视**是否就是第 i 句的主题（画面错位＝beat 锚错）。

### element_overlap 分档（硬标准）

- **1-3（fail）**：元素明显叠压、文字互相覆盖看不清；内容压住底部字幕带；主件被屏幕边缘切掉。
- **4-6**：轻微拥挤/贴边，或相位交叠处两相同时半可见超过 0.6s。
- **7-8**：分区清楚，无重叠。
- **9-10**：严守标题带/主舞台/字幕带三分区，主舞台同一刻单主可视，留白舒服。

判定方法：检查 (a) 任意两个可视元素的包围盒是否相交；(b) 底部 ~160px 字幕带内有没有混入别的内容；(c) 边缘有没有被切；(d) 同一帧是否出现了本应分属不同相位的两组内容（相位没淡净）。

> **复发盲区·必查（组件重叠是 #1 复发硬伤·本期 A2 又踩）**：
>
> - **自定义 SVG / 画布基元上的绝对定位卡片**（如 `McpConnection` 的握手 / 调用卡、脊柱 Rail 的节点标签、安全段投毒卡）——`check_layout.py` 抓不到这类手填 `x/y` 卡的碰撞（它只拦 AbsoluteFill 偏下），所以渲前全绿不代表没重叠。eval 必须**逐卡核对"本应并列的独立内容卡是否彼此压住读不清"**（含压住 SVG 内连线 / Server 盒）。**合法重叠不报**（防误判 → 防无谓返工）：标签贴自己目标、数字压自己的柱、装饰 / 辉光层、容器套子元素、≤0.6s 交叉淡变——这些是设计。只报"两张独立数据卡 / 步骤卡互相覆盖看不清"那种（如 init 卡压 tools/call 卡）。**多模态 eval 看得见美丑**，按"这俩叠一起糊了吗 / 好不好看"判，不做纯几何零容忍。
> - **峰值并存帧**：累积揭示类场景（步骤逐个长出、扇出多端），重叠峰值在"**所有步骤都揭示完的那一帧**"（通常是最后一步累积态，不在句子中点）——必须额外抽这一帧专查碰撞；只抽中点会系统性漏掉（本期 2:59、5:11 等正是这样漏的）。
> - 渲前 scene-design 侧的对应预防（列"包围盒账本"+ 按峰值态排坐标 + 步骤揭示后常驻不淡出）见 `video-scene-design`「知识最佳可视化展示原理 + 渲前防重叠」第三条。

### readability_dwell 分档（信息密集 establishing 镜头·硬标准）

只对**信息密集主视觉**评（架构总览图 / 完整公式 / 代码块 / 矩阵 / 分层图等需要看清的镜头）；纯标题/单个大数字不评。

- **1-3（fail·一闪而过）**：该镜头有效可见 <1.5s，或抽帧时它正在 reveal 还没画完就要退场——观众根本没看清。
- **4-6**：1.5-2.2s，勉强扫一眼，复杂图看不全。
- **7-8**：2.2-3.5s，够看清主结构。
- **9-10**：≥2.6s 且 reveal ≤0.4s 已画完，留足阅读时间后再退场。

判定方法：对每个 establishing 镜头，从场景代码/相位窗算它的"入场秒→退场秒"时长；并**额外抽该镜头「入场后 0.4s / 中段 / 退场前 0.2s」三帧**——入场后 0.4s 那帧若主视觉还没画完整（还在淡入/画框），即 reveal 太慢；退场前那帧确认观众有足够静止时间看清。<2s 的信息密集镜头一律标 high，建议用 `holdEnd()` 从相邻长 beat 借时间延长停留（见 PRIMITIVES.md「时序铁律」第 5 条）。

### taste_antislop 分档（视觉品味红旗·硬标准）

移植自 `taste-skill`，定位"一眼 AI 味/不够高级"。逐帧扫这组红旗（命中即记，附帧+时点）。**红旗清单**（详见 video-scene-design 的 `references/visual-taste.md`）：

- **配色**：AI 紫/蓝大渐变背景、彩虹渐变文字、霓虹外发光、纯黑投影；强调色不统一（蓝/绿被当装饰乱撒，而非语义角色）；同一语义换了色。
- **排版**：靠堆大字号制造层级（每个标题都顶天）、行宽拉满一行到底、混异族字体词做强调、出现 `S` 档位外的手写中间字号。
- **装饰**：无信息含义的网格线/十字准星/旋转竖排文字、角标编号（`01/4`、`SECTION 02`、`Phase 03`）、地点时间天气条。
- **构图**：又一个"居中标题+居中主件"、三等大卡片排排站、同构图家族连用 >2 段。
- **动画**：无意义的持续漂浮/呼吸脉冲/全员飘入、线性匀速位移（廉价机械感）——抢眼但说不清动机。
- **文案**：屏幕额外文字出现破折号 `—`/`–`、AI 腔填充词（赋能/无缝/重塑/下一代）、编造的假精度数字、"步骤1/阶段2"式空标签。

- **1-3（fail）**：多处红旗叠加，整帧明显 AI 默认味、撑不起 study-dark 高级感（尤其高潮/架构图 hero 镜头踩雷）。
- **4-6**：1-2 处红旗，能看但有廉价感。
- **7-8**：基本干净，无明显红旗。
- **9-10**：克制精致，配色/排版/构图/动画都贴 study-dark，看不出 AI 默认痕迹。

判定方法：逐帧对照上面红旗清单勾选；命中项写进该段问题列表并标 severity（hero/高潮镜头命中升一级）。**这是诊断,不改**——修法回灌 video-scene-design，让它对照 `references/visual-taste.md` 改。

## Step 3: 对比检测（compare_with 非空时）

同样按句子帧渲染参照视频的对应时点，比配色/布局/动画风格，输出**相似度 0-100** + 重合点列表。

## Step 4: 生成报告（按段组织 + 回写修正要点）

写 markdown 到 `output_path`：

```markdown
# 视频帧级评估报告

## 基本信息

- manifest: <path> | 总时长: Ns | 段数: N | 抽帧数: M

## 逐段评估

### Scene k: <id>（from <sec>s, audioSec <sec>s, 句数 <n>）

- 帧: out/eval\_<id>\_s0.png ...
- 评分: audio_anim_sync X/10 | element_overlap X/10 | information_density .. | ...
- 问题（每条 quote 具体帧 + 时点）:
  - [critical] @ eval_steps_s3.png（第3句 ~21s）: 字幕在讲"加权求和"，画面还停在 softmax 柱状图 → 音画错位
  - [high] @ eval_steps_s2.png（~14s）: SoftmaxViz 与上一相 DotProductViz 同屏半透叠在一起 → 相位没淡净
- 修法（指明给 scene-design 怎么改）:
  - 错位 → 该段 startSec/seg 是否还在用硬编码秒？改成 beatsOf 锚定
  - 重叠 → 相位窗用 seg(beats[i].start, beats[j].start) 互斥；主舞台别同屏两件

## 整体

- 平均分 + 音画/重叠硬伤计数（critical/high）
- 关键改进项（按 ROI 排序）

## 回写给 video-scene-design 的修正要点（卡点决定重做时直接喂）

按 severity 取前 N 条，每条：[severity] @ 段id/时点 / 现象 / 改法。**点名要重做的段 id 列表**，scene-design 用 current_eval 只修这几段。

## 相似度分析（如有 compare_with）

- 整体相似度 X/100 + 重合点 + 建议
```

## Step 5: 写入 + 反馈

写报告，打印关键指标。**若出现任一 audio_anim_sync≤3 或 element_overlap≤3（critical 硬伤）**，明确建议：让 `video-scene-design` 带 `current_eval=本报告` 定向重做被点名的段（不用整片重来）。

> 修完重渲走 `render_bespoke.py` **默认增量**：只重渲被点名的改动段再拼接（改一段 ~1/N 渲染量），明显缩短"评估→修→重渲"环路，别用 `--full`。本 skill 抽帧仍走 `--tts-only`（只产 timing.json），不受增量影响。

## overall 判定

- **pass**：无 critical/high；音画同步、无重叠均 ≥7，且关键 establishing 镜头 readability_dwell ≥7、taste_antislop ≥7（无明显 AI 默认味）
- **conditional_pass**：仅少量 medium（含 taste_antislop 4-6 的廉价感红旗，建议修但不阻塞）
- **fail**：有 audio_anim_sync≤3 或 element_overlap≤3 或 readability_dwell≤3（关键架构图/公式一闪而过）或 taste_antislop≤3（hero/高潮镜头一眼 AI 味），或其他 critical → 必须修后复审

## 注意

- 用 Bash 渲帧 + Read 看图，依赖你（Claude）的多模态能力
- 合成名是 **MainBespoke**（不是旧的 MainComp）；现在走 bespoke 场景 + manifest.ts，不再有 scene_specs.json
- 评估是"诊断不改"，不动场景代码，只出报告；改由 video-scene-design 按 current_eval 做
- 所有问题必须 quote 具体帧文件 + 时点（"eval_steps_s3.png ~21s 字幕讲加权、画面停在 softmax"）
- 帧数控制：一句一帧 + 关键相位边界帧即可，别无脑全片逐帧
