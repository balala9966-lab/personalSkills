---
name: video-content-eval
description: 对视频生产链路中任一阶段的文本产物（知识库/大纲/场景）做内容质量评估。多维度打分 + grounded 问题定位 + 可操作改进建议，输出质检报告 markdown。只诊断不改——评估结果供用户在卡点决定是否让上游 skill 重写。当用户说"评估这份大纲/知识库质量"、"这个 outline 合格吗"，或主 video-pipeline 在每个卡点调用时触发。注意：这是文本内容评估，与 video-eval（渲染帧视觉评估）不同。
---

> 📁 **路径约定（输入数据 / 产物落点 / 渲染引擎）以单一真源为准**：`~/code/video-agent-pipeline/README.md`。

# Video Content Eval Skill

视频生产链路的**内容质检员**。评估 knowledge_base / outline / scene_spine 三类文本产物的内容质量，给多维度分数 + 具体问题 + 改进建议。

**核心定位：只诊断、不改。** 你产出质检报告，由用户（或 video-pipeline 卡点）决定是否让上游 skill 按报告重写。你绝不直接修改被评估的产物。

> 与 `video-eval` 区分：video-eval 评的是"渲染出来的画面长什么样"（多模态看帧），本 skill 评的是"文字内容写得好不好"（读 JSON）。

## 触发方式

- 用户显式：「/video-content-eval <产物.json>」、「评估这份大纲质量」、「这个知识库合格吗」
- 主 skill 调用：`video-pipeline` 每个阶段产物出来后的卡点

## 输入

1. `target_path`: 被评估产物的 JSON 路径（1_knowledge_base.json / 2_outline.json / scene_spine.json）
2. `target_type`: `knowledge_base` | `outline` | `scene_spine`（可从文件名推断）
3. `script_type`: `科普` / `学习` / `教程` / `故事` / `漫剧`
4. `context_path`: 可选，上游产物路径（评 outline 带 KB、评 scene_spine 带 outline，做跨阶段一致性检查）
5. `output_path`: 报告写入路径（默认 `<同目录>/eval/<target_type>_report.md`）
6. `framework_path`: 可选，用户提供的**权威框架文档**（分层框架/大纲/术语表）。给了就作为 `external_framework_fidelity` 维度的外部标尺，逐子项核对，别拿 KB 自评

## 评估原则

0. **独立评审优先**：本 skill 由独立 fresh-context 子代理执行最佳——写产物的人不评自己的产物（同上下文自评=橡皮图章，审不出框架级结构问题）。
1. **严格但建设性**：每个问题必须附带"怎么改"的具体建议——模糊评价等于没评价
2. **事实导向**：评分基于具体标准，不凭感觉
3. **必须 grounded**：每条 issue 必须 quote 原文中被评论的具体片段（≤30 字，原文逐字摘录），否则视为无效反馈。空泛的"某段过于笼统"不予采纳

## 评分维度（每维度 1-10 分）

> **元标准对齐（防漂移）**：评分标尺(1-10) / severity 分级 / grounded 要求 / pass·conditional_pass·fail 判定格式 / 质检纪律，统一见 `~/code/video-agent-pipeline/docs/quality_rubric.md`（§一 元标准 + §二 内容维度目录）。下列维度分档与 fail 红线为本 skill 操作细则，二者并用、不冲突。

### 通用维度（所有阶段都评）

- **concept_grounding**（**高权重维度**）：每个新引入的术语/缩写/专业名词，首次出现时是否做到"先专业定义、后通俗类比"两段式？**逐段扫描，列出所有"用了但没解释"或"解释只有一句敷衍"的概念。任何引入后不管的术语都是 critical 级问题，必须列入 issues 并显式 quote 出原文。**
- **completeness**：完整度，是否覆盖主题关键方面 / 有无明显叙事缺口
- **explanatory_clarity**（**高权重·学习/教程**）：讲明白没。每个核心论断/反常识数据，是否紧跟把**因果机制**讲到新手秒懂，而不是只陈述事实？"反直觉/很重要/最关键"等空标签是否兑现了解释（反在哪、为什么重要）？**只陈述不解释因果 = critical**，列入 issues 并 quote。诊断"没讲明白"的主维度。
- **external_framework_fidelity**（**有 `framework_path` 时高权重**）：当用户提供权威框架文档（如分层框架/大纲/术语表）时，**以该文档为外部标尺**逐节点/子项核对——框架里每一层/每个子能力，narration 讲到没、（评 scene_spine 时）框架总览主视觉画全没？**不许拿 KB 自生成的 knowledge_map 自评蒙混**。框架子项缺失/只取子集 = high 及以上，明确指出漏了哪个子项。无 framework_path 时跳过。

### knowledge_base 阶段

- **factual_accuracy**：事实准确性，是否与检索材料一致
- **narrative_value**：叙事价值，素材筛选是否有叙事潜力
- **depth_richness**（学习/教程类型**高权重**，分档见下）：知识深度，depth_layers 是否真正从表层深入到数学/物理原理？是否有推导链和真实示例，而非只给结论？
- **breadth_coverage**：知识广度，是否覆盖工程背景、应用场景、关联知识
- **knowledge_coverage**（学习/教程类型**高权重**）：知识点完整性。`knowledge_map` 是否按"知识点→子知识点"两层系统列全（不是只挑好讲的）？子点覆盖率如何（covered / 总子点）？所有 `covered:false` 是否如实进了 `retrieval_requests`，而非假填蒙混？这是诊断"知识点完整性不足"的主维度
- **learning_mainline**（学习/教程类型**高权重**）：学习主线是否成立。`learning_mainline` 是否把知识点排成一条承上启下的动线（每步 teaches/builds_on/leads_to 说得通、前置概念在前）？depth_layers 是否按这条主线顺序展开，而不是知识点散装罗列？这是诊断"内容组装松散、讲不顺"的主维度
- **reverse_grounding**（学习/教程类型）：是否有"反向解释"——把原理连回观众已熟悉的现象/产品，做到深入浅出？

#### depth_richness 评分分档（学习/教程，硬标准）

- **1-4（fail）**：只有"是什么/现象描述"，没有 derivation 推导链，没有 worked_example 真实示例。**这就是"内容太简单"的典型，必须 fail 打回**
- **5-6（conditional）**：有原理方向但推导不完整，或示例是伪代码/无真实数字
- **7-8**：每层有完整推导 + 可验证示例（真实数字/shape/输出）
- **9-10**：推导透彻 + 示例可运行 + 有 reverse_explanations 把原理连回熟悉现象

**fail 规则**：学习/教程类型知识库若 depth_richness ≤ 4，overall 直接判 fail，issue 标 critical，并具体指出"哪一层缺推导/缺示例"。

**knowledge_coverage fail 规则**：学习/教程类型若 `knowledge_map` 缺失/敷衍（没按知识点→子知识点列全），或有重要子知识点 `covered:false` 却没进 `retrieval_requests`（假填蒙混），overall 判 fail，issue 标 critical，明确指出"漏了哪个该讲的子知识点 / 哪个缺口没补检"。

**learning_mainline fail 规则**：学习/教程类型若 `learning_mainline` 缺失，或只是知识点罗列而无承上启下（depth_layers 顺序混乱、前置概念后置），overall 判 fail，issue 标 critical，指出"主线在哪断了 / 哪两步顺序该调"。

### outline 阶段

- **hook_strength**（学习/教程类型**高权重**）：开场钩子强度。**第一段是否就是钩子**（前 3 秒抛核心冲突/悬念，首句是问题或反常识），还是用"欢迎来到/这是第 N 天"等欢迎词开场（=高跳出，critical）？**钩子＝点题：钩子首句在抓人的同时有没有点出本集主题词？没点到 → high**。开场 `visual_anchor` 是否强视觉冲击（特写/动态特效）而非静态公式？**旁白/屏幕文字若出现"Day 几/第 N 集"等编号 → critical（违反去编号约束）**。
- **opening_efficiency**（学习/教程类型**高权重·降流失**）：开场效率——**进入第一个主题模块有多快**。hook_strength 只评"第一段钩子强不强"，本维度评"开场整体拖不拖"。逐段量化：①开场有几段、各多少秒、各讲哪个维度（钩子&点题/衔接/意义/路线）；②**有没有相邻短段讲的是可合并维度却各自独立**（系列定位、路线路标、意义各占一个 ≤15s 独立段 = 典型冗余，应合并）；③**意义价值是否在开头堆了"为什么核心+学不会后果+解锁什么"三件事**（应只留最狠一句，其余拆散）；④算"钩子首句 → 第一个主题模块首句"的秒数与开场占比。**判定**：开场 >35s 或 >全片 10%、或存在 ≥2 个可合并的独立短段、或意义堆三件事 → high（quote 出该合并/该砍的段 seq）。这是诊断"开场拖沓、迟迟不进主题、流失高"的主维度——hook_strength 满分也救不了开场冗长。
- **structure**：结构合理性，信息递进是否自然、情绪曲线是否合理；**学习/教程：是否"总-分-总"——钩子后有"核心问题（总）"一句话锚定全片，结尾回顾呼应它**
- **retention_hooks**（学习/教程类型）：留人钩子。是否有 ≥1 **中段内容钩子**（提问/悬念，`interaction_prompts` type=中段钩子）拉回注意力，避免中段流失？
- **shareability**（学习/教程类型）：传播价值。是否有 ≥1 **金句**（`key_quotes`，易记口诀/比喻）？结尾是否有**互动话题引导**（`interaction_prompts` type=结尾话题，发起讨论）？
- **visualization**：可视化程度，旁白对应画面是否**具体可拍**（不能是"展示一个概念"这类模糊描述）
- **engagement**：吸引力，整体是否有趣/有悬念/有共鸣
- **explanatory_depth**：解释深度，L2（原理深潜）是否真正解释"为什么这么设计"的物理/数学本质，还是只停留现象描述
- **application_coverage**：应用覆盖，L3（应用图景）是否多样化、佐证是否有机融入

**学习/教程 outline fail 规则**：以下任一 → overall 判 fail、issue 标 critical 并 quote 具体 seq：①第一段不是钩子 / 用欢迎词开场；②**钩子首句没点出本集主题词**（钩子≠点题）；③**开头旁白或屏幕文字出现"Day 几/第 N 集/第 N 天"等编号**；④结尾回顾不呼应开篇核心问题；⑤无中段钩子（`interaction_prompts`）；⑥无金句（`key_quotes`）；⑦结尾无互动话题引导。

**opening_efficiency fail 规则**：学习/教程类型若"钩子首句→第一个主题模块"> 45s 或开场 > 全片 12%，或存在 ≥2 个明显可合并却各自独立的开场短段（如系列定位/路线路标/意义分别独立成段），或**意义价值在开头堆满三件事（未瘦身成一句）**→ overall 判 fail、issue 标 high/critical，**明确点名哪两段该合并/哪段该砍**（给出合并后的目标段结构），供 video-script 回灌时直接照改。

### scene_spine 阶段（评分镜脊柱的文本规划，渲染前把关；画面级留给 video-eval）

> 链路已无 scene_specs.json——分镜走 bespoke：`scene_spine.json`（脊柱规划）+ 现写 .tsx。本阶段评**脊柱规划**是否靠谱，画面好不好由 `video-eval`（渲染帧）评。

- **component_diversity**：组件多样性，`primary_primitive` 是否丰富贴题，有没有一个基元被滥用到全片单调（>2 段复用同一基元即预警）
- **viz_fit**：可视化贴合，每段 `sentence_beats[].primitive` 是否真把"该让观众看见什么"对上（流程类有没有用 ComputeViz 把过程算出来，而非只摆步骤名）
- **kb_slice_coverage**：深度落地，`kb_slice` 是否把 KB 的 derivation/worked_example/everyday_example 分配进了对应段（深度没在脊柱里丢）
- **beat_mapping**：时序锚点，`sentence_beats` 是否按句给了 beat（句数≈可视 beat 数），为后续 beatsOf 锚定打好基础
- **spine_fidelity**：忠实度，脊柱是否保留 outline 的所有强制元素（钩子＝点题开篇/系列衔接·主题承接不报编号/今天意义/代码段/中段钩子/金句/互动引导/下集预告·主题名）没丢
- **spine_diagram_through_line**（学习/教程**高权重·连贯性**）：是否有**一张贯穿全片的内容脊柱图**（按主题选形态：架构图/管线图/分层栈/推导链/循环图，内容源自 `learning_mainline`），并做了**三处锚定**——①开篇亮全图、②每个模块段开场拍高亮该模块（其余压暗）、③回顾段复用作思维导图？**判定**：完全没有贯穿骨架、各模块段各画各的孤立可视化（观众没有"现在在整体哪个位置"的心智地图）→ high；有骨架但只在开篇/回顾用、各模块段没高亮锚定回去 → medium。这是诊断"内容散、缺主心骨、看完记不住整体结构"的主维度。注意区别于开篇 `RoadmapFromCurriculum`（那是系列定位，宏观层；本维度是本片内容骨架，微观层）。

## overall 判定

- **pass**：所有关键维度 ≥ 7 分，无 high/critical 问题 → 可直接进入下一阶段
- **conditional_pass**：仅有少量 medium 问题，不影响整体质量 → 可先进入下一阶段，建议改善
- **fail**：有 high/critical 问题 → 必须修正后重新评估

## 你要做的事

### Step 1: 读产物 + 上下文

Read `target_path`。如果有 `context_path`，一并读入做跨阶段一致性检查（评 outline 时核对它是否忠实承接 KB；评 scene_spine 时核对它是否保留 outline 全部强制元素）。

### Step 2: 逐维度评分 + 定位问题

按上面对应阶段的维度逐项打分（1-10）。**concept_grounding 必须逐段扫描**，把每个"用了没解释"的术语都列成 issue。

每条 issue 结构：

```json
{
  "severity": "critical|high|medium|low",
  "location": "问题位置（如 '段落2'、'scene: terminal'）",
  "quote": "原文逐字摘录，≤30 字",
  "problem": "为什么这段不够好",
  "suggestion": "具体怎么改、改成什么（可给改后示范文本）"
}
```

`quote` 必须真实存在于原文。无法对应到具体文本的全局判断（如"整体节奏偏慢"）用 `"quote": "[全局]"`，但**这类 issue 不超过总数 20%**——绝大多数必须 grounded。

### Step 3: 写质检报告

写 markdown 到 `output_path`，结构：

```markdown
# 内容质检报告 · <target_type>

## 总判定: pass | conditional_pass | fail

一句话总结。

## 评分

| 维度                  | 分数 |
| --------------------- | ---- |
| concept_grounding     | 8/10 |
| ...（该阶段所有维度） |      |

## 问题列表（按 severity 排序：critical → high → medium → low）

### 1. [critical] @ <location>

- 原文: "<quote>"
- 问题: <problem>
- 建议: <suggestion>

（逐条……）

## 回写给上游的修正要点（供卡点决定是否重写时直接喂给上游 skill）

按 severity 排序取前 8 条，每条格式：

- [severity] @ location / 原文:"quote" / 问题 / 建议

修正要求：

- 必须直接处理 critical/high，medium 尽量改善
- 保留已有合理结构，不要因局部问题推翻全文
- 改完自检：每条问题是否都对应到输出某处具体改动
```

最后那段「修正要点」是关键——video-pipeline 在卡点若决定重写，会把这段直接传给上游 skill（video-research / video-script / video-scene-design）作为重写依据。

### Step 4: 报告给用户

打印：

```
✓ eval report → <path>
  overall: pass | conditional_pass | fail
  关键维度: concept_grounding N/10 ...
  critical: N | high: N | medium: N | low: N
```

如果 overall=fail 或任意维度 < 5，明确提示用户"建议让上游 skill 按报告重写"。

## 注意

- **只诊断不改**：绝不修改 target_path 的产物，只输出报告
- **决定权在用户**：你不自动触发重写。是否回灌由用户在 video-pipeline 卡点拍板（C 方案）
- concept_grounding 是第一约束——学习视频最容易犯"假设观众已经懂术语"的错，逐段抓
- 子 skill 间只通过磁盘文件通信，不共享对话上下文
