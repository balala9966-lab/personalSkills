---
name: video-scene-design
description: 把视频大纲 outline.json 转换成可渲染的 bespoke 场景——按每段内容现写 Remotion 场景组件（用基元库 + study-dark 设计系统），不套固定模板。先决定"这段内容理想该怎么可视化"再现写。采用「全局脊柱 + 每段隔离子代理」分段生产，每段专注组织知识、选最贴的可视化。当用户说"把大纲转场景"、"出场景"、"做可视化"，或主 video-pipeline skill 调用时触发。输入 outline.json + knowledge_base.json，输出 Remotion 项目里的 bespoke 场景 .tsx + manifest.ts。
---

> 📁 **路径约定（输入数据 / 产物落点 / 渲染引擎）以单一真源为准**：`~/code/video-agent-pipeline/README.md`。

# Video Scene Designer Skill（bespoke 授权 · 分段生产）

把视频大纲变成**按内容现写的 bespoke 场景**。核心理念：**先决定每段内容理想该怎么可视化，再用基元库现写场景**——不套固定模板（模板套壳会扭曲内容、让每个视频长一样）。

**生产方式：全局规划一次（脊柱）+ 每段隔离生产（子代理并行）。** 整片一次性写所有段，会因上下文太满而后段质量掉、组件单调、知识组织松散。改成：先用一次全局 pass 定脊柱（保证连贯性、组件多样性），再把每段派给独立子代理专注现写——每段只带它需要的那一片知识 + 基元库，注意力集中，知识组织和表现形式都更好。

## 铁律（content → form，不是 form → content）

1. **先内容后形式**：拿到一段，先问"这个知识点最该让观众看见什么"，再去基元库挑最贴的形式；**匹配不上就现写一个新基元**（开放生长），绝不为套现成而扭曲内容。
2. **把过程算出来，不是只说流程**：讲点积就演示逐位相乘求和；讲 softmax 就演示归一；讲缩放就把数字除小给观众看。用 `ComputeViz` 系列。
3. **公式用 KaTeX**：任何正经公式用 `Formula` 基元写 LaTeX（论文级），不要用纯文本拼根号/分数。
4. **可视化贴知识点**：代码→`CodeEditor`、矩阵→`MatrixViz`、注意力→`SentenceAttention`、向量→`VectorStrip`/`VectorSpace`、链路→`DataFlow`。
5. **旁白抛问题，画面必须显式打出问题**：旁白只要出现设问/自检/悬念（"…怎么办？""…够吗？""停下想想…"），就用 `QuestionCard` 把问题文字上屏（问题→停顿→答案→踩坑），**绝不允许光配音念、画面没问题**。
6. **时序 beat 锚定旁白（防音画错位）**：所有入场时点从 `beats.ts` 的句子时间轴取（`beatsOf(audioId, NARRATION)`），**禁止手填绝对秒数**。详见 PRIMITIVES.md「时序铁律」。
7. **布局分区不重叠（防组件叠一起）**：标题带 / 主舞台 / 字幕带三分屏，主舞台同一时刻只放一个主可视，底部 ≥160px 留给字幕。详见 PRIMITIVES.md「布局铁律」。
8. **视觉品味（anti-slop，治"一眼 AI 味"）**：不踩 LLM 视觉默认值（AI 紫/彩虹渐变文字/霓虹发光/无信息装饰线/角标编号）；强调色全片锁 `C.accent`、同一语义同色；用字重+颜色建层级而非堆大字号；圆角统一；构图反居中惯性；**每个动画动机能一句话说清，否则删**；屏幕额外文字不上破折号、不堆 AI 腔。详见 `references/visual-taste.md`。

## 知识最佳可视化展示原理 + 渲前防重叠（最高原则 · 现写每段前必读）

> 来源：用户反馈「知识可视化即讲解是学习视频最大亮点、绝不做成 PPT」+「组件重叠反复返工、要在前置阶段拦」。三条原理，铁律级。详见 memory [[video-visualization-is-the-teaching]] [[video-viz-cold-open]] [[video-overlap-prevention]]。

**一 · 可视化即讲解（反 PPT · 贯穿 · 有深度）**

- **反 PPT 判据（每段过）**：这段是"标题 chip + 静态卡 + 字幕"吗？是 → 重做。可视化必须**演因果 / 过程 / 变换**——关掉声音只看画面动能否看懂这段；截一帧就读完 = PPT = 不合格。
- **每个知识点配最佳可视形式**：先问"这段最该让观众看见什么变化"，再挑 / 现写最贴的基元；现成都不贴就现写新基元（呼应铁律 1），绝不为套现成扭曲内容。
- **整片主画布贯穿**：一张签名可视化 / 脊柱图贯穿全片（Step 1 第 4 点定），各段挂上去展开、讲到哪高亮哪，别每段孤立画。
- **可视化承载深度、不稀释内容**：把 KB 的 `derivation` / `worked_example`（真实数字 / 推导 / 前后对比）画进可视化里；深度与可视化都要，别用漂亮空动画换掉内容厚度。

**二 · 签名可视化冷开场（teaser · 留人）**

outline 第一段标了"签名可视化冷开场"时，现写一个 ~8-12s 的 teaser：**把本片签名可视化 / 主画布快速完整跑一遍**（只演不拆解），作视觉钩子。

- teaser **复用正文主画布的同一基元 / 同一画布**（如 A2 的 `McpConnection`、脊柱 Rail），只是跑得快、不内联深载荷——"开篇演一遍、正文慢放细讲"是同一张图。
- 它就是钩子、快进快出、不额外占时长；正文段再对这张图慢放 / 分模块高亮 / 逐步算（三处锚定见 Step 1 第 4 点 + Step 3）。

**★ 开局炫技铁律（seq0·硬性·绝对要求·rubric `opening_viz_richness`·绝对禁止简单无吸引力开头）**：冷开场是留人生死线，**前 2 秒就要有运动 + 尺度 + 具体性**。必须满足：① 用一个**真实、有分量（最好复杂、有规模）的示例**驱动可视化（不是抽象概念图/曲线）；② 画面就是这个示例**在发生**（看着它跑/搭/变/算）；③ **够炫技**——信息丰富、有运动、产品级精致：多元素协同 + 大计数器狂飙 + 流式日志/终端 + 图表动效 + accent 辉光强调；④ 前段用 **ease-out 提速**让"效果立刻可见"（数字/界面前几秒就猛冲，再稳到收尾，与旁白同步）。

- **critical 红线（命中=打回重做）**：开局前几帧是 ❌静止画面 / ❌小字矩阵 / ❌单调清单缓慢填色 / ❌纯抽象曲线或柱图 / ❌一张静态卡 / ❌抽象发光节点·粒子场·"神经网络"星图（一眼通用 AI-slop、跟本集机制无关）。自检：把 seq0 前 2 秒缩到手机尺寸，"会不会立刻划走"——会就是不合格。
- **正例（A12 定稿·可参照实现 `Hook_a12harness.tsx`）**：「看着一个 AI 把一个复杂全栈应用飞速盖起来」——左 = 运营后台 dashboard（导航+KPI卡+柱状图+数据表）一块块 time-lapse 搭出来；右 = 大计数器狂飙(✅功能 0→200 带进度条 / ⏱运行 0→6h / 🔀commit) + 流式构建日志终端(db/schema.sql→api/...→git commit 一行行刷出) + harness 循环；ease-out 提速、末态 ✓交付完成。**反例（连否两版）**：抽象准确率断崖曲线、默认全红的小格子清单缓慢填绿——都因"温吞、留不住人"被否。
- **炫技要"具体场景隐喻"，不是抽象粒子（A8 记忆系统·连否星图后定调）**：要炫技留人时**别做**抽象发光节点/粒子/"神经网络"星图——一眼通用 AI-slop、跟本集机制无关、观众 get 不到在演什么（用户原话"星图效果比较差"）。赢法 = 把本集**要害机制做成一个一眼认得出的具体场景隐喻**、让画面**字面演出那个机制**（A8 把"记忆出错"做成一卷会卷动的**记忆磁带**：写入『改吃素🥗』→倒带召回时磁头越过新格锁定褪色旧格『爱吃牛排🥩』→读出『推荐牛排店』+红✗→磁带拉长到百万 token 远端腐化成静电雪花乱码=context rot 字面可视化）。判据：隐喻要让观众**"看见机制本身"**（写进去 vs 读出来错位/越长越烂），不是看见漂亮抽象动画。候选先**带 ASCII 预览给用户选隐喻**（磁带/抽屉卡片/便签墙…）再动手，避免白渲一轮。详见 memory `video-viz-cold-open`。
- 复杂主视觉用真 flex/HTML 面板（窗口/dashboard/终端）+ frame 驱动累积揭示 + glow，比朴素 SVG 色块更有产品级高级感。

**三 · 渲前防重叠：自定义 SVG / 画布上的绝对定位卡片（组件重叠是 #1 复发缺陷 · 硬拦）**

> 根因复盘：`check_layout.py` 只拦"AbsoluteFill 缺 bottom / height:auto 致偏下"，**抓不到自定义 SVG / 画布基元上手填 `x/y/w/h` 的卡片两两碰撞**——本期所有重叠（init 卡压 tools/call 卡、Spine 标签压 JSON、投毒卡压主画布）全是这类，所以 check_layout 全绿、still 也常漏（重叠峰值在"所有步骤都揭示出来的那一帧"，不在句子中点）。渲前必须人工补这道关：
>
> - **凡往 SVG / 画布上叠绝对定位卡片 / 标签的段**（握手 / 调用步骤、攻击卡、transport 标签、扇出多端…），现写时列一张「包围盒账本」：每个绝对元素写下 `left / top / right(=left+w) / bottom(=top+h)`，核对**"本不该叠的同层独立内容卡 / 标签"是否相交**（含与 SVG 内既有图元：连线、Server / Host 盒）。这是代码级静态推演，不靠肉眼 still。
> - **合法重叠白名单（别误杀 · 防过度返工·关键）**：容器包含子元素、标签贴在自己的目标上（数字压在自己的柱 / 卡上）、装饰 / 辉光 / 背景 accent 层、≤0.6s 交叉淡变的瞬时交叠、有意的 z 层叠（卡叠在面板上）——这些是**设计、不是 bug**，绝不能为"消除相交"把标签从目标挪开 / 拆散有意层叠（那才是制造新返工）。**只揪一种**：两张本应并列、各自独立的内容卡 / 数据卡彼此压住看不清（如 init 卡 vs tools/call 卡）。判据是"叠在一起糊了 / 读不清"，不是"几何上有没有交集"。
> - **按"同时在屏元素最多"的峰值态排坐标**：累积揭示场景，先算"全部步骤都显示时"有几个卡、为这个最大并存数排好不重叠的坐标**再动手写**——不是写到第 4 步才发现压上了第 1 步。
> - **步骤一旦揭示就常驻、不许为腾地方淡出**（用户否过"4、5 步出现就消失"）；位置不够就**换非重叠区**（下方 / 侧栏 / 独立 zone），不淡掉、不压缩重叠。
> - Step 2 自检 + Step 4 still 都**专抽"全部步骤揭示完的峰值帧"**核对无碰撞（不止中点）。把这道关写进叠卡片段的子代理 prompt。

## 输入

1. `outline_path`: 大纲 JSON（来自 video-script）——每段的 narration / description / visual_anchor / duration / key_quotes / interaction_prompts
2. `knowledge_base_path`: 知识库 JSON（取 worked_example/derivation/everyday_example/knowledge_map 等深度内容）
3. `topic_slug`: 本视频英文短标识（如 `day2-multihead`），用于场景文件名后缀
4. `active_node_id`: 该视频在 curriculum.json 里的节点 id（开篇定位用）。**默认从 `knowledge_base.json` 的 `series_context.active_node` 取**（pipeline 也可显式传）；两者都没有再问用户。**`active_node_id=null`（自由主题 / 开源速递）时不走 RoadmapFromCurriculum 开篇——见 Step 3 末**
5. `current_eval`: 可选。video-eval 的帧级审查报告（音画错位/组件重叠等），按它定位的段做定向修复
6. 渲染项目根：`~/code/remotion-rlhf-poc`

## 必读参考（授权前先读）

- **`~/code/remotion-rlhf-poc/src/primitives/PRIMITIVES.md`** —— 基元库 API + 知识类型→基元映射库 + 场景外壳 + 设计系统 token + **时序铁律（beat 锚定）+ 布局铁律（分区防重叠）**。**这是现写场景的依据，必读。**
- **`~/code/remotion-rlhf-poc/src/primitives/beats.ts`** —— `beatsOf` / `useSeg` 时序 API
- 现成范例：`~/code/remotion-rlhf-poc/src/scenes/bespoke/*_Day1.tsx`（照着学结构；但时序看 PRIMITIVES.md 新写法，别照抄硬编码秒）
- **`references/visual-taste.md`** —— 视觉品味守则（anti-slop，移植自 taste-skill 并适配视频）：配色/排版/构图/动画动机/上屏文案的硬约束。子代理现写场景前必读，末尾品味自检并入 Step 2 自检。视觉自检维度目录与元标准对齐见 `~/code/video-agent-pipeline/docs/quality_rubric.md`（§三 视觉维度目录，与 video-eval 同源防漂移）。

---

## Step 1：建脊柱（全局一次 pass）——保证连贯性 + 组件多样性

读 outline + KB，**自己（主 Claude）一次性**为每一段产出结构化 spec，写到 `<outline 同目录>/scene_spine.json`。这是全局契约：它让各段隔离生产时仍然连贯、不撞车、组件不单调。

每段 spec：

```jsonc
{
  "id": "steps", // 场景 id
  "audioId": "steps", // = id，对应 public/audio/<audioId>.mp3
  "comp_name": "ThreeStepsD2A", // 导出的组件名（唯一）
  "file": "ThreeSteps_<slug>.tsx",
  "narration": "该段旁白原文（= outline 的 narration，配音=字幕单一真源）",
  "sentence_beats": [
    // 把 narration 按句拆，逐句决定该让观众看见什么
    {
      "i": 0,
      "text": "第一句…",
      "show": "点积逐位相乘求和",
      "primitive": "DotProductViz",
    },
    {
      "i": 1,
      "text": "第二句…",
      "show": "softmax 压成权重",
      "primitive": "SoftmaxViz",
    },
  ],
  "primary_primitive": "DotProductViz", // 该段主可视
  "kb_slice": ["depth_layers[2].worked_example", "depth_layers[2].derivation"], // 这段要用 KB 的哪几片
  "layout": "主舞台单件居中", // 分区方案（遵守布局铁律）
  "intent": "让观众看见注意力三步是怎么算出来的",
  "transition_from_prev": "承接上一段的 Q/K/V 定义",
  "is_opening": false, // 第一段=学习地图开篇，固定用 RoadmapFromCurriculum
}
```

建脊柱时务必做三件事：

1. **组件多样性检查（关键·治"组件单调"）**：扫一遍所有段的 `primary_primitive`。**同一基元被 >2 段复用 = 单调预警**——重新想这些段"理想该怎么可视化"，换更贴的基元或现写新基元。目标是整片基元谱系丰富（向量/矩阵/链路/计算/对比/映射/问答各擅其用），不是从头到尾全 BulletReveal。
2. **新基元决策（避免并行冲突）**：哪些段没有贴切现成基元、需要现写新基元，**在这一步定下来并由主 Claude 在派发子代理前先写好**（写进 `src/primitives/` + 补 PRIMITIVES.md）。子代理只**组合**现成基元，不并行新建基元文件（防多段同时改 primitives/ 冲突）。
3. **句=beat 锚点**：`sentence_beats` 是后续时序的锚——句子数 ≈ 可视 beat 数。想清楚每句对应一个可视，别让一段里堆五个无主次的动画。
4. **内容脊柱图：每个学习视频选一张贯穿全片的骨架主视觉（关键·学习视频高价值结构）**：这是 Transformer 视频被认可的核心——**一张完整骨架图贯穿全程，讲到哪个模块就在图上高亮哪里**。它给学习视频四个独特价值：①观众持续有"心智地图"、每讲一块都知道在整体的哪个位置，不在零散知识点里迷路；②各段挂在同一张图上、整片有主心骨不散；③整体→局部→整体的认知节奏；④回顾段直接复用作思维导图。**不止架构主题**——几乎每个学习主题都有可贯穿全片的骨架，按类型选形态：

   | 主题类型      | 脊柱图形态        | 现成/参考基元        |
   | ------------- | ----------------- | -------------------- |
   | 架构 / 模型   | 论文风架构图      | `GptArchitecture` 等 |
   | 数据流 / 管线 | 链路流程图        | `DataFlow`           |
   | 分层体系      | 分层栈图          | `LayerStack`         |
   | 推导 / 算法   | 推导链 / 计算流程 | `ComputeViz` 系列    |
   | 训练 / 循环   | 循环 / 飞轮图     | 飞轮基元             |
   | 落地步骤      | 步骤管线          | 步骤条               |

   **数据来源**：KB 的 `learning_mainline`（学习主线）就是脊柱图的内容骨架——主线每一步 = 图上一个节点/模块。把主线从文字升级成贯穿全片的可视骨架。

   **全片三处锚定**（脊柱里规划好）：①**开篇**亮出完整骨架（整体先行）；②**每个模块段开场拍**高亮该模块、其余压暗（spotlight，"你现在在这里"）；③**回顾段**用完整图作思维导图、逐块回点亮。

   **与开篇 `RoadmapFromCurriculum` 分工**：Roadmap = 宏观「本节在系列路线中的位置」（开篇一次）；内容脊柱图 = 微观「本片各模块在本片整体中的位置」（全片高亮锚定）。两层不冲突、都要有。

   **落地纪律**（脊柱形态错了会拖垮所有引用它的段，所以先确认再铺开）：①主 Claude 派子代理前先把脊柱基元写好（带 `highlight` 入参 + spotlight 压暗）、**渲 1 张样张给用户卡点确认效果**，认可后再铺开；②形态绑定**内容事实**——脊柱里存 `architecture_facts`（如 `{paradigm:"decoder-only", has:["masked-self-attn","ffn","lm-head"], not:["encoder","cross-attention"]}`），按它画、别画上用不到的模块（讲 GPT 就用 decoder-only 图，别套完整 encoder-decoder 论文图——否则圈选位置反复对不准 + 引发"你真懂链路吗"的质疑，真实踩过的坑）。③**系统/架构类有真源 SVG 结构图时，脊柱图优先用「内联 SVG 手工排版」复刻真源**（照其层/模块/连线精确坐标画 + frame 驱动 flowLevel/highlight/showFeedback 动画），别用 flex/HTML 色块堆叠——后者还原不出真源图的分层密度与"见出し+一行役割"设计感、会被连否多版（pipeline-dogfooding 踩过；已落基元 `PipelineArchSvg`）。④**架构图要画全数据流连线，尤其每个消费节点的输入来源**（底层资源/基建→上层消费者的喂料：检索能力/数据仓库→①召回 等），不只画模块盒+主链横向箭头。③④的"用 SVG 还是 flex / 连线画全没"也属样张卡点要先确认的形态决策。

5. **establishing 镜头预留停留时长**：脊柱里标出哪些段含信息密集 establishing 镜头（架构图/公式/代码/矩阵）；若该镜头挂在极短首句上，规划时就注明用 `holdEnd()` 借时间（见下 Step 2 时序写法），别让它一闪而过。

报告脊柱：段数 / 各段主基元 / 多样性自评 / 需新写的基元清单 / **内容脊柱图形态 + 样张是否已确认 + 三处锚定（开篇/各模块高亮/回顾）规划了没**。

## Step 2：每段隔离生产（并行子代理）

对脊柱里**每一段**，派一个独立子代理（用 Agent 工具，多段可并行——见 superpowers:dispatching-parallel-agents），各自现写一个场景 .tsx。每个子代理**只带这一段需要的上下文**，注意力集中：

派给子代理的 prompt 必须含：

- 该段的 spine spec（上面那个 JSON 块）
- 该段用到的 **KB 切片**（按 `kb_slice` 摘出来，不是整本 KB）
- 必读：`PRIMITIVES.md`（基元 API + 时序铁律 + 布局铁律）、`beats.ts`、`references/visual-taste.md`（视觉品味守则 anti-slop）
- 一个同构现成范例文件路径（如讲计算就给 `ThreeSteps_D1A.tsx` 看结构，但提醒时序用新写法）
- 输出文件路径：`~/code/remotion-rlhf-poc/src/scenes/bespoke/<file>`

子代理的任务（写进 prompt）：

1. **规划**：把 narration 按句拆，逐句定"该让观众看见什么"（对照 `sentence_beats`），挑/用脊柱指定的基元。**数 beat 按真实分隔符 `。！？；`（注意中文分号 `；` 也分句！）数，别凭句号肉眼数**——数错会让基元挂到错的 `beats[i]`、早入场/错位（踩过）。
2. **现写 .tsx**：
   - 用 `<BespokeScene narration={NARRATION} audioId="...">` 外壳；导出 `NARRATION` 常量 = 该段 narration。
   - **主可视必须包在居中容器里（防偏下·硬规则）**：用 `<MainStage>`（`src/scenes/bespoke/_Stage.tsx`，已含 top/bottom + `height:'auto'`）或自带居中带的 stage 容器。**禁止裸用 `<AbsoluteFill style={{top:..,bottom:..}}>` 定位主可视**——AbsoluteFill 默认 `height:100%` 会盖掉 bottom、内容必偏下（反复踩，check_layout 会拦）。
   - **时序用 beat 锚定**：`const beats = beatsOf(audioId, NARRATION); const seg = useSeg();`，基元 `startSec={beats[i].start}`，相位 `seg(beats[i].start, beats[j].start)`，**最后一相收到 `sceneSecOf(audioId)`（不是 `audioSecOf`！）**——收 sceneSec 才能让末相主视觉保持到镜头结束、不留 pad 尾空台(dead tail)。**零硬编码秒**。
   - **布局守分区**：标题带 0-200px、主舞台 220-880px 单件居中、字幕带 920-1080px 留空。同一时刻主舞台只一个主可视。
   - 配色字体只用 `design/theme.ts` 的 `C/F/S`，不写死 hex。
3. **自检（子代理做·只到代码级）**：
   - `cd ~/code/remotion-rlhf-poc && npx tsc --noEmit`（主要报自己这个文件的错，修到过）
   - **check_layout 自检（强制·静态不渲染，子代理就能跑）**：`python3 tools/check_layout.py 2>&1 | grep <自己的文件名>` → **本文件 0 个「高危·必偏下」才算过**。别把它拖到 Step 4 主 Claude 那里集中发现——子代理写时就拦，否则会攒成几十处高危、多一整轮修复子代理（踩过：一次 79 高危集中返工）。病根=相位层写成 `<AbsoluteFill style={{top:X,…center}}>` 缺 bottom/height:auto；正解=主可视/相位层一律用 `<MainStage style={{opacity:seg(...)}}>`（自带 top200/bottom190/height:auto 居中），**禁止裸 AbsoluteFill+top 定位主内容**。
   - **相位数 = 句数 自检（防 off-by-one 音画漂移·强制）**：按真实分隔符 `。！？；`（含中文分号 `；`）数 narration 句数 N、再数你写了几个主可视相位 M——**M 必须 = N**；若刻意把某相跨多句（如"参数对比"跨"1678万"+"13万"两句），必须在注释里写明"本相跨 sX+sX"、且该相 `seg(beats[i],beats[j])` 的 j 跳过被合并的句。否则相位整体错一拍——字幕讲第 i 句、画面已演第 i+1 句（踩过 paramshrink）。
   - **AbsoluteFill 基元逃逸防呆**：`FinetuneSpine`/`RoadmapFromCurriculum`/各 `*Spine` 等**根是 AbsoluteFill 的基元别直接塞进 flex 列**——它会脱离 flex 铺满父容器居中、和同列元素（如目标 bullet）重叠。要并排/堆叠就包进一个 `position:relative` 定高盒（`<div style={{position:'relative',width:.,height:250}}><FinetuneSpine/></div>`）让它只填这盒（踩过 intro 目标与脊柱重叠）。
   - **极短句防一闪而过**：≤2 字 / 窗 <1.5s 的句（"能。""为什么？"），相位窗可能仅 ~0.3s、reveal 没画完就被切。用 `holdEnd(beats[i].start, beats[j].start, 1.5)` 借时间停留 ≥1.5s、下一相接力（踩过 qpayoff 的"能"）。
   - **代码级推演**（不渲 still）：对照 `sentence_beats` 逐句核对——每个基元 `startSec` 是否挂到对应句的 `beats[i].start`、相位是否首尾相接互斥、主舞台是否同一时刻单主可视、内容是否压到字幕带（top≤880）。
   - **视觉品味自检**（`references/visual-taste.md` 末尾 7 项，纯代码级即可查）：无 AI 默认值/强调色锁 `C.accent`/字号按 `S` 档位/圆角统一/构图非又一个居中/动画动机说得清/屏幕额外文字无破折号无 AI 腔。
   - ⚠️ **不要在这里渲 still**：此刻 manifest 还没装配（Step 4 才装）、`timing.json` 也可能还没生成（beat 会回退到近似值），并行子代理也不能各自改主合成。**视觉级 still 审查统一放 Step 4 做**。
4. **返回**：该段用了什么可视化、beat 数、代码级自检结果（tsc 过没过、逐句 beat 映射对没对）。

> 隔离的好处：每段上下文只有自己这一片，不被前面 N 段的代码稀释 → 知识组织更紧、基元选得更准、布局更稳，且可并行更快、每段等质量。

## Step 3：开篇场景 = 分层学习架构图（固定形式 · 跨整套课程复用）

学习类视频（系列课）每一节的第一段都是**分层学习架构图开篇**（脊柱里 `is_opening:true`）。
这张图谱**一次定义、贯穿整个系列**：换一节课只改一个 `activeId`，不重画、不复制场景。

```tsx
<RoadmapFromCurriculum
  activeId="<active_node_id>" // 今天这节课在 curriculum 里的节点 id
  revealStartSec={0.6}
  zoomSec={beatsOf("intro", NARRATION).at(-1).start} // 最后一拍：放大今天这站进正片
/>
```

**数据唯一源**：`video-agent-pipeline/input/学习/curriculum.json`（权威课表，勿改 remotion 里的副本）。
渲染前由 `video-agent-pipeline/tools/sync_curriculum.sh` 同步到 `remotion-rlhf-poc/src/curriculum.json`。
结构：`layers[]`（分层，按 `order` 自底向上）+ `nodes[]`（每个 = 一个知识点，含 `layer/day/deps/unlocks/summary`）。
当前 7 层：① 数学与编程基础 → ② 核心架构 Transformer → ③ 预训练 → ④ 微调与对齐 → ⑤ 智能体 → ⑥ 部署·评测·上线 → ⑦ 项目实战。

**组件自动做的事**（`primitives/LearningRoadmap.tsx`，无需手写坐标）：

- 自底向上画分层泳道 + 彩色层标签（色取 `theme.ts` 的 `C.layerHues`，按 `layer.order`）；行内节点统一列距、对称居中（含单节点层落正中），上下行列位对齐不参差。
- 高亮 `activeId`（暖橙脉冲）；**只画本节相关连线**：蓝实线=前置依赖（`deps`）、橙虚线=解锁下游（`unlocks`）。
- `zoomSec` 时把今天这站从原位**平移到画面正中并放大**，过渡进正片。**任意 activeId 通用**。

**怎么用（做某一天的课）**：`active_node_id` 取那天对应的节点 id —— 如 Day1 讲注意力=`attention`、讲 RAG 那天=`rag`、讲微调=`sft`、讲多智能体=`multi-agent`，其余全自动。

**`active_node_id=null`（自由主题 / 开源速递）**：**不用 RoadmapFromCurriculum 开篇**（没有课表节点可定位）。开源速递的开篇 = outline 第一段「切入」直接进正片，第二段「架构总览」用 bespoke 现写一张**项目核心架构图**（模块 + 数据流），这张图是全片视觉主轴、后续亮点段都挂在它上面展开。其余分段生产机制不变。

**怎么扩课表 / 加模块**（不动场景代码）：

1. 编辑 `input/学习/curriculum.json`：加 `node`（设 `layer/deps/unlocks/day/summary`）或加 `layer`（同时在 `theme.ts` 的 `C.layerHues` 补一个色）。
2. 约束：每层建议 ≥3 个节点（单节点仅留给收尾峰顶层）；`day` 保持依赖拓扑序（被依赖的节点 day 不得晚于本节点）。
3. 跑 `bash tools/sync_curriculum.sh` 同步，再渲染。

开篇 narration 按 video-script 的钩子前置——**前 3 秒先抛核心冲突再定位**（别让开篇变成纯念欢迎词）。

## Step 3.5：信息速递（股市）专项——数据驱动 + 强隔离（`script_type=信息速递`）

信息速递类（首个实例=股市每周复盘）与学习视频**共享底座、强隔离类型特定层**。`active_node_id=null`（非课程），不走 RoadmapFromCurriculum。视觉主轴不是架构图，而是**数据**。

### 股市 scene 模板集（一组互不引用的数据卡，按六层骨架落段）

| scene 模板 | 渲染什么 | 对应骨架层 |
| ---------- | -------- | ---------- |
| 指数卡 IndexStat | 名称 + 大数字点位 + 涨跌% + 进度条（涨跌色） | L1 行情面 |
| 个股分化榜 DivBoard | 领跌列 vs 逆势列，逐行股票简称+涨跌%（实锚 data_verified） | L1 结构看点 |
| 排序归因 CauseRank | 主因/次因/放大器三卡，每卡走五步链文字 | L3/L4/L5/L6 溯源 |
| 多空情景 ScenarioCard | 偏谨慎 / 偏乐观双卡，各列 if-then 要点 | 展望 |
| 观察变量 WatchVars | 4 个变量 chip（icon+名+监控点） | 展望·监控 |
| 免责 Disclaimer | 数据来源 + "观点、不构成投资建议" | 免责 |

### 强隔离纪律（**关键·保证学习视频零回归**）

`render_bespoke.py` 的 `GLOBAL_PATHS` 指纹覆盖 `design/`、`primitives/`、`components/`、`scenes/bespoke/_Scene.tsx`、**扁平** `scenes/bespoke/manifest.ts`——改这些会让**所有学习段缓存失效**。所以股市场景必须：

1. **子组件全部 inline 在股市场景 .tsx 内**（IndexStat/StockRow/DivCol/VarChip/CauseCard…）——**绝不**新增到 `src/primitives/`、`src/components/`、`src/design/`。这是与学习视频"现写新基元入库"相反的纪律：信息速递的数据卡是类型专属、不进共享库，避免污染指纹 + 撞车学习视频。
2. **市场涨跌色 inline 为文件内局部常量**（`const UP="#F87171"/*A股红涨*/, DOWN="#34D399"/*绿跌*/`）——**不改 `design/theme.ts`**（红涨绿跌与 study-dark 的 good/bad 语义冲突，混进去会污染学习视频配色）。其余配色仍用 `C/F/S` token。
3. **只写项目级 manifest** `src/projects/股市速递_<期次>/manifest.ts`，**不碰扁平 `src/scenes/bespoke/manifest.ts`**（它在 GLOBAL_PATHS）。
4. 场景文件名带 `Stock` 后缀、audioId 带 `stk_` 前缀（全局唯一），落 `src/scenes/bespoke/`（个别 .tsx 不在指纹内，安全）。

> 结果：新增股市片**不改任何 GLOBAL_PATHS 文件** → 学习段缓存全部有效、效果零回归；唯一对共享代码的改动是 `render_bespoke.py` 追加 `stk_*` 的 `TAIL_PAD`（该文件不在指纹内、且纯加 key，不影响学习 audioId）。

### 音画同步与反空话落地（沿用铁律 + 类型专属）

- **时序仍 beat 锚定**：`beatsOf(audioId, NARRATION)` + `useSeg()`，零硬编码秒——这正是修掉 demo "整段音频+字数比例全局估算"漂移的关键（demo 旧法见 `remotion-logo-demo/StockFullDemo.tsx`，移植时**丢弃** `STARTS`/`AUDIO_SEC` 全局估算，改逐段真实 timing）。
- **每屏标【数据】/【研判】角标**：客观涨跌数=【数据】，方向性研判=【研判】，落实事实/观点分离。
- **数据实锚**：指数/个股数字一律取 `data_verified.json`（交易所接口留痕），不在场景里写死过期数。

## Step 4：装配 manifest + 全量校验（主 Claude）

1. 写**项目级 manifest** `~/code/remotion-rlhf-poc/src/projects/<topic_slug>/manifest.ts`（per-project 作用域：每片自己的 manifest，多片并发隔离）。场景 `.tsx` 仍写在共享的 `src/scenes/bespoke/`，**manifest 用相对路径 `../../scenes/bespoke/` import 本片场景**（只 import 本片 → 打包按需 tree-shake，只含本片，算力不随历史片增长）：

```ts
import { ThreeStepsD2A } from "../../scenes/bespoke/ThreeSteps_<slug>";
// ...
export const BESPOKE_SCENES: { id: string; audioId: string; Comp: React.FC }[] =
  [
    { id: "intro", audioId: "intro", Comp: IntroD2A },
    { id: "hook", audioId: "hook", Comp: HookD2A },
    // ... audioId 全局唯一（带片前缀，如 mg_/ev_），对应 public/audio/<audioId>.mp3
  ];
```

> 入口 `Root.tsx`/`index.ts` 无需手写——首次 `render_bespoke.py --project <topic_slug>` 会自动脚手架（复用 `bespoke_core` 工厂）。`<topic_slug>` 即项目名（与渲染 `--project`、抽帧入口一致）。

2. **全量 tsc**：`cd ~/code/remotion-rlhf-poc && npx tsc --noEmit` 必须零错。
2.5. **check_layout 静态 gate（强制·渲前拦偏下，别只靠肉眼 still）**：`python3 tools/check_layout.py --all`，**有"高危(必偏下)"项必须先改掉再往下**（退出码非 0 即拦）。它揪两类 AbsoluteFill 偏下写法：①有 top+居中缺 bottom ②有 top+bottom 但无 `height:'auto'`（默认 height:100% 盖掉 bottom）——这俩 still 肉眼常被当"还行"放过，静态拦更稳。本片相关段 0 高危才进渲染。
3. **生成 timing.json（关键·让 beat 对准真实音频）**：`cd ~/code/remotion-rlhf-poc && python3 tools/render_bespoke.py --project <topic_slug> --tts-only`——它从本片各 .tsx 的 `NARRATION` 合成配音、写 `src/timing.json`（各段真实 `audioSec`，audioId 全局唯一故各片共存不冲突），不渲染整片。**必须在 still 审查前做**，否则 `beatsOf` 回退到近似值、自检失真。（⚠️ 别用旧的 `gen_tts.sh`，它的旁白是写死的 Day1 内容、会覆盖成错的 timing。）改了某段 `NARRATION`/`pad` 后想确认 timing 是否还对齐，跑 `python3 tools/render_bespoke.py --check-timing`（只读自检，过期 exit 3 会列出哪些段需重配）。
4. **帧号算法**：读 `src/timing.json` 拿各段 `sceneSec`，累加得每段起始秒 `from`；某段第 i 句的帧 = `(from + beatsOf(audioId,NARRATION)[i].start) * 30`。中点帧 = `(from + sceneSec/2) * 30`。
5. **全段冒烟渲帧（强制·防渲染期崩溃，先于视觉审查）**：对**每一段**先渲 frame0 + 中点帧**+ 该段最短 beat 窗口的边界帧**三类，确认没有运行期崩溃。子代理 tsc 过 ≠ 运行期不崩——单 beat 场景 `seg(0,0)`、退化 beat 窗口（短句给出 <1.2s 的窗）、`zoomSec=0`、`holdEnd` 边界这类**正是崩溃高发区**，且只在那个最短窗口的帧上触发，frame0/中点抽不到。所以**额外抽每段最短 beat 的 start 帧**。整片 full render 全或无、崩在某一帧废掉一整轮 ~10min 渲染；冒烟一遍 ~5min 远比崩了便宜。任一段渲帧报错 → 修该段再继续。
6. **统一 still 视觉审查（覆盖全 27 段，不挑高风险子集）**：对**每一段**渲句子边界帧 + 中点帧（**别只取中点**——重叠/位置问题是相位局部的，中点会漏），多模态逐帧看：画面对得上旁白、无组件重叠、**内容不贴字幕带(≤880)、不偏心、不局促**、运算过程算出来了、相位淡净、**多项浮现的场景每一项都充分可见（禁"按句分批导致中间项永不显示"）**。
   `npx remotion still src/projects/<topic_slug>/index.ts MainBespoke out/check_<id>_s<i>.png --frame=<N>`（项目入口；旧扁平用 `src/index.ts`）
   这一步在 manifest 装配 + timing.json 生成之后，所以 MainBespoke 含本片全部场景、beat 也准——是音画/重叠的第一道把关（成片后 video-eval 再帧级复审）。
7. 哪段 still 有问题 → 回去让对应子代理（或主 Claude）改那一段，重渲该段帧复查。
8. **改了共享基元（primitives/）后，回归它所有使用处**：增强一个基元别只验新场景——把它在所有场景的渲染都过一遍（如给 LayerStack 加固定标签宽，修好了有模块场景却会弄坏无模块场景的层名换行）。
9. **TTS↔timing 耦合**：改了任何 NARRATION 或 pad 后，timing.json 会重写、所有帧号位移——必须重读 timing.json 重算帧号，绝不缓存旧帧号。

## Step 5：自检清单（输出前）

- [ ] 每段 narration 非空、就是该段配音；视觉就是讲的内容（画面对得上旁白）
- [ ] **时序全用 beatsOf/useSeg，无任何手填绝对秒数**；**最后一相收到 `sceneSecOf`（非 audioSecOf）**，主视觉保持到镜头结束、不留 pad 尾空台
- [ ] **主可视都包在 MainStage/Stage 容器里**（无裸 `AbsoluteFill+top/bottom` 定位主可视）；`python3 tools/check_layout.py --all` 本片相关段 0 高危
- [ ] **布局守三分区**：标题带/主舞台/字幕带不互侵；同一时刻主舞台单主可视；底部 ≥160px 留白
- [ ] **无组件重叠**：相位时间互斥（除 0.6s 交叉淡变），still 上没有元素叠在一起
- [ ] **内容脊柱图贯穿全片**：选了一张贯穿骨架主视觉（按主题类型，源自 `learning_mainline`）？三处锚定到位——开篇亮全图、每个模块段开场高亮该模块、回顾段复用作思维导图？样张已卡点确认？
- [ ] **establishing 镜头不一闪而过**：逐 beat 算相位窗时长，信息密集主视觉（架构图/公式/代码/矩阵）的窗 <2s 的标红，用 `holdEnd()` 从相邻长 beat 借时间补到 ≥2.6s（纯代码推演就能抓，见 PRIMITIVES.md 时序铁律第 5 条）
- [ ] **开场不拖沓**：开场段没在短首句上堆动画把它拖长；establishing 在主体而非开场
- [ ] **时间体验改动渲多帧复验**：凡改了 reveal 速度/停留时长/相位窗，渲「入场后 0.4s / 中段 / 退场前」时间序多帧确认——tsc 过 ≠ 看得清（一闪而过 tsc 完全正常）
- [ ] 流程类都把**运算过程算出来**了（ComputeViz），不是只摆步骤名
- [ ] 旁白里每个问句/自检/悬念都用 `QuestionCard` 显式上屏
- [ ] 公式都用 `Formula`(KaTeX)；概念首次出现两段式（继承 video-script）
- [ ] **组件多样**：没有一个基元被滥用到全片单调
- [ ] **视觉品味（anti-slop）**：过 `references/visual-taste.md` 末尾 7 项——无 AI 默认值（紫/彩虹渐变文字/发光/装饰线/角标编号）；强调色锁 `C.accent`、同语义同色、无纯黑投影；层级靠字重+色不靠堆大字号、字号只用 `S` 档位；圆角统一；构图反居中惯性、同构图家族未连用 >2 段；每个动画动机能一句话说清、缓动非线性；屏幕额外文字无破折号、无 AI 腔填充词、无编造精度数字
- [ ] outline 强制元素全保留：钩子＝点题在开篇、系列衔接（主题承接·不报 Day 号）、今天意义、5 行代码、3 场景、中段钩子、金句、互动引导、下集预告（主题名）；原理段紧跟 everyday_example
- [ ] **开头不出现 Day 号/集序数字**（旁白和屏幕文字都不念"Day 几/第 N 集"）；开场 ≤3 段、占比 ≤10%、~30s 进第一个主题模块
- [ ] 全量 `npx tsc --noEmit` 无类型错误
- [ ] 只用设计系统 token，零写死 hex

## Step 6：报告 + 交棒

报告：场景数、每段用了什么可视化形式、组件多样性、自检结果（tsc/still/重叠/错位）。**不要自己渲整片**——交给 video-render（`render_bespoke.py` 一键 TTS+渲染）。

## 反馈回灌支持（video-eval 报告回来时）

输入含 `current_eval`（帧级审查报告，标了哪段音画错位/组件重叠）时：

1. 解析报告的 per-scene issues（按 severity）
2. **只重生产被点名的那几段**（派对应子代理定向修），不动其余段
3. 错位类 → 检查该段是否仍用了硬编码秒、是否该把 startSec/seg 改成 beat 锚定；重叠类 → 检查分区、相位时间是否互斥、主舞台是否塞了多件
4. 修完重跑该段 still 自检 + 全量 tsc，再交回 video-eval 复审

## 缺合适形式时（开放生长）

某段没有贴切的现成基元 → **在 Step 1 脊柱阶段定下来，由主 Claude 现写新基元**到 `src/primitives/`（主题感知、数据驱动、测过能渲染），并**补一条进 PRIMITIVES.md**。子代理只组合不新建，避免并行冲突。库越用越厚。

## 注意

- 不调 LLM API，你（Claude）+ 子代理直接思考 + 写 TSX
- 不要调用 video-render
- 子代理之间写**不同的场景文件**互不冲突；新基元/manifest 由主 Claude 串行写
- 子 skill 间只通过磁盘文件 + 项目代码通信，不共享对话上下文
- 旧的"8 固定 scene_type 模板"方案已废弃（`references/catalog.md` 仅历史参考），一律走 bespoke
- **基元/时序铁律（`primitives/`、`beats.ts`、`PRIMITIVES.md`）只改「真源」`~/code/remotion-rlhf-poc`，再同步到隔离副本**（被并行生产占用时会 rsync 出 `remotion-tf` 之类隔离副本——见 [[video-render-isolated-copy]]）。**绝不只改隔离副本**——那是临时的，下次同步会被真源覆盖、改动丢失。改完 `cp` 真源的基元/beats/PRIMITIVES 到当前隔离副本保持一致。

## P1《数据工程》自进化补丁（2026-07-06 · append-only）

- **冷开场禁"数据量/指标对比柱图·双柱比大小"当钩子**（即使带真实数字）——要"看得见的行为差异/具体场景"（如同题双答：脏数据模型逐字背无关原文 vs 精选模型分步答对）。**柱状图/条形一律从基线向上长、禁从顶部基准线"向下挂"**（反直觉像下跌，P1 初版两柱顶端对齐 MMLU 线往下延伸被用户打回"开头又是模型数据对比、留人差""柱状图怎么是向下的"）。招牌数字须与屏上可视化自洽（柱高读 8× 就标 8×）。详见 memory `video-viz-cold-open`。
- **final render 前必查 `_Stage.tsx` 的 `DEBUG_BANDS = false`**：修复子代理常临时开 DEBUG_BANDS 渲验证帧、理应还原，但它是共享文件，若以 `true` 出片则**每一段都带红/青调试参考线**。渲整片前 `grep 'export const DEBUG_BANDS' src/scenes/bespoke/_Stage.tsx` 确认 false。
- **check_layout 必加 `--all`**：`tools/check_layout.py` 默认只扫 `_MG` 文件，`grep <文件名>` 无 `--all` = 漏扫假通过（P1 多个子代理踩）。子代理自检 prompt 里写死 `--all`。
