---
name: video-research
description: 把一个主题 + 一组素材种子整理成结构化「知识库 JSON」，供后续脚本生成使用。当用户说"研究 X 主题"、"准备 X 视频的知识库"、"用这些材料生成知识库"，或主 video-pipeline skill 调用本 skill 时触发。输入是主题关键词与种子素材，输出是符合 KnowledgeBase schema 的 JSON 文件。
---

> 📁 **路径约定（输入数据 / 产物落点 / 渲染引擎）以单一真源为准**：`~/code/video-agent-pipeline/README.md`。

# Video Research Skill

把一个视频主题相关的零散素材，整理成下游脚本智能体能直接用的「知识库 JSON」。

## 触发方式

- 用户显式：「/video-research <主题>」、「为 X 主题准备视频知识库」
- 主 skill 调用：`video-pipeline` 第一步

## 输入

调用本 skill 时，必须明确告诉 Claude：

1. `keywords`: 主题关键词（如 "Day1 线性代数在大模型中的应用"）
2. `script_type`: 一个值 `科普` / `故事` / `漫剧` / `学习`（默认 `科普`）
3. `materials_path`: 素材 JSON 路径（**优先**读 `video-retrieval` 产出的 `0_materials.json`）。也接受用户直接提供的 markdown / 笔记
4. `output_path`: 知识库 JSON 写入路径（默认 `<output_root>/1_knowledge_base.json`；output_root 按 类型/课程 组织，由 video-pipeline 传入）

如果上述任意字段未提供，先用 AskUserQuestion 询问。

## 你要做的事

> **职责分界（与 video-retrieval）**：retrieval 负责**取料 + 骨架**（`knowledge_outline` 三层 + `learning_thread` 雏形，且按 `script_type` 取齐下游所需料）。research 负责**深化 + 校验 + 装配**——**复用** retrieval 的骨架作导航（**不重新组织骨架**，避免重复劳动），把素材深化成带 `derivation`/`worked_example`/`everyday_example` 的知识库 + 组装正式 `learning_mainline`。
> **完整性交接（缺 P0 不硬装配）**：装配前先校验 retrieval 产物完整性——若有 `blocking=true`（P0）的子点 `covered:false`（缺它故事断/推导缺环），**别硬着头皮带洞装配**，先把该缺口写进 `retrieval_requests`（`blocking=true`）回灌补检，补到再装配。非阻塞缺口（P1/P2）可记入 `retrieval_requests` 但继续装配。

### Step 1: 读取素材

**优先读 `0_materials.json`**（来自 video-retrieval 的联网搜集产物），它已是结构化素材卡片，含三维评分和 `knowledge_outline`（主题→知识点→子知识点三层 + `learning_thread` 主线雏形）、`reference_videos`、`github_repos`、`knowledge_gaps`。直接拿来用。

**学习/教程：以 `knowledge_outline` 为骨架**。retrieval 已经把主题拆成知识点/子知识点并标了每条素材覆盖哪个点（`covers`）。research 的任务是：照这张骨架把素材组织成有深度的知识库，并把 `learning_thread` 雏形**组装成正式学习主线**（见 Step 1.5）。

**学习/教程类型务必消费 `github_repos`**：高 star repo 里的可跑代码、推导讲解是 depth_layers 的优质原料——把它们喂进对应层的 `derivation`（推导）和 `worked_example`（带真实数字/shape 的技术示例），`source` 注明来自哪个 repo。这是补足"知识点完整性"的关键来源。

如果没有 `0_materials.json`、用户只给了文字素材（markdown / pdf 内容），把它整理成同样的素材卡片结构：

```json
[
  {
    "id": "mat_001",
    "content": "具体事实/数据/类比/案例（一句话），尽量含具体数字",
    "source": "出处（论文/教材/工程经验等）",
    "type": "事实 | 数据 | 类比 | 案例 | 公式 | 工程经验 | 学习方法",
    "scores": {"visual": 1-5, "emotional": 1-5, "specificity": 1-5},
    "suggested_usage": "在脚本中适合放在哪段（钩子/L1/L2/应用）"
  }
]
```

10-15 条素材是合适规模。**若素材明显不足以构建有深度的知识库**（缺原理/缺示例/缺案例），在输出的 `retrieval_requests` 字段里写明缺口，供主 pipeline 回调 video-retrieval 补检——不要硬凑。

### Step 1.5: 覆盖校验 + 组装学习主线（针对"知识点完整性不足 + 主线松散"·学习/教程关键）

1. **拿到/补全三层骨架**：直接用 `0_materials.json.knowledge_outline`（主题→知识点→子知识点）。若是用户给的裸素材没有它，先自己穷举补上（参课程权威源 `~/code/video-agent-pipeline/input/学习/curriculum.json` 锚定主题边界、deps 不重讲、unlocks 埋伏笔）。
2. **逐子点核对覆盖**：每个子知识点查素材（含 `github_repos`）是否有支撑，填进 `knowledge_map`。**任何 `covered:false` 的子点必须写进 `retrieval_requests` 触发补检，绝不用内部知识假填**。
3. **组装学习主线 `learning_mainline`（关键）**：把 `learning_thread` 雏形排成一条**讲得顺**的主线——不是知识点罗列，而是一条认知动线：每一步**承接上一步的什么、引出下一步的什么**，遵循"先建立直觉→再讲原理→再落地"的递进 + 概念依赖（前置概念必须先讲）。这条主线决定 depth_layers 的展开顺序，也是 video-script 写"总-分-总"的依据。
   - 例（概率与优化）：交叉熵（损失长什么样、模型错得多离谱）→ 困惑度（把损失翻译成"模型在几个词里纠结"的人话）→ 梯度下降（怎么顺着损失往下走）→ AdamW（工程上实际怎么又快又稳地走）。每步一句话说清"承上启下"。

### Step 1.6: 装配 `series_context`（系列定位数据·学习/教程必做）

video-script 写**系列衔接 / 今天意义段 / 下篇预告**时需要准确的已学前置、解锁后续——这些只有课程表有，**不能让脚本瞎编**。在 KB 里产出 `series_context`，把这些事实喂给下游：

1. 拿 `knowledge_outline.curriculum_ref.node`（retrieval 锚的节点 id），读 `~/code/video-agent-pipeline/input/学习/curriculum.json` 找到该节点。优先用 `episodes[]` 定位本集（一集可含多个 node），取同集 `nodes` 的主题、上一集/下一集的 `title` 作衔接。
2. 取它的 `label`、`deps`（→ 转成"已学前置，只回扣"，**用主题名**）、`unlocks`（→ 转成"学完解锁的后续"，挑 1-2 个最相关的做下篇预告，**用主题名**）。
3. 写一句话**系列衔接** `position_line`——**用主题承接，严禁出现 "Day 几/第 N 集" 等编号**（如「接着上一集的注意力，这一集把整个 Transformer 拼起来」）。
4. `day` 字段可保留供内部排序/路线图组件用，但**明确不进旁白**；旁白衔接只认 `position_line` 的主题措辞。
5. 没匹配到节点（非系列/自由主题）→ `series_context: null`，脚本则不写系列衔接句。

### Step 2: 按 schema 生成知识库

输出符合下面 schema 的 JSON：

```json
{
  "series_context": {
    "active_node": "prob-opt",
    "day": 2,
    "_day_note": "day 仅供内部排序/路线图，严禁进旁白",
    "label": "概率与优化",
    "position_line": "接着前面的注意力，这次讲训练靠什么把模型练出来——损失与更新规则",
    "deps_learned": ["线性代数", "注意力"],
    "unlocks_next": ["预训练", "PyTorch 训练循环"]
  },
  "core_concept": {
    "one_sentence": "30 字以内,让完全不懂的人也能听懂",
    "analogy": "用一个日常事物类比,必须具体(例:'像 37 万亿士兵的军事基地')",
    "why_care": "50 字以内,说明这个知识跟观众的关联"
  },
  "narrative_clusters": [
    {
      "theme": "这组素材讲什么故事",
      "angle": "从什么角度切入最吸引人",
      "hook": "最能勾住观众的一句话(必须含具体数字或画面)",
      "visual_potential": "高 | 中 | 低",
      "key_facts": [{ "fact": "...", "source": "...", "can_visualize": true }],
      "emotional_beats": ["..."],
      "hands_on": "如果 script_type=学习/教程,标明该聚类对应的动手验证方式"
    }
  ],
  "depth_layers": [
    {
      "level": 1,
      "title": "这一层讲述什么",
      "core_insight": "一句话核心洞察",
      "key_principles": ["数学/物理原理列表"],
      "intuitive_explanation": "用直觉理解而非公式推导的解释",
      "derivation": "原理推导链：这个结论/公式是怎么一步步得出的、为什么成立（学习/教程必填，不能只给结论）",
      "worked_example": "一个具体可验证的技术示例：含真实数字/shape/输入输出，最好能对应可运行代码（学习/教程必填）",
      "everyday_example": "讲完这层原理后紧跟的【日常案例示例】：用一个观众平时使用中真会遇到的具体场景印证这条原理（如讲完'上下文改写词义'→'你输入法打苹果，前面聊科技还是水果，候选词就不一样'）。有真实贴切的就填，纯内部机制（如数值缩放）实在没有可留空",
      "visual_metaphor": "可视觉化的类比画面"
    }
  ],
  "_depth_layers_note": "level 取 1-5（越大越深）。强制覆盖至少 3 个递进维度——从'是什么/怎么用'到'底层数学/物理原理'再到'为什么这么设计'，不能只停在表层平铺。**学习/教程：depth_layers 要按 learning_mainline 的顺序展开（一步接一步、承上启下），不是知识点散装罗列**。每层必须有 derivation（推导）+ worked_example（技术示例）；**凡是能找到日常案例的原理层，都要配 everyday_example（讲完原理紧跟一个观众有体感的例子）**。只给结论不给推导即不合格",
  "reverse_explanations": [
    {
      "familiar_thing": "观众已知、有体感的现象/产品（如'GPT 回答时一个字一个字蹦''推荐流越刷越懂你'）",
      "underlying_principle": "它背后正是本视频讲的哪条原理",
      "the_aha": "一句'原来如此'——把熟悉现象反向连回原理，让观众感到'我天天用的东西原来是这个道理'"
    }
  ],
  "_reverse_explanations_note": "深入浅出的关键：不止正向讲原理，还要反向解释观众已熟悉的现象为什么是那样。学习/教程类型至少 2 条",
  "engineering_context": {
    "historical_evolution": "关键历史节点和设计灵感来源",
    "design_tradeoffs": ["主要工程权衡"],
    "technical_challenges": ["关键挑战和解决方案"]
  },
  "corroborating_knowledge": [
    {
      "field": "关联领域",
      "insight": "1-2 句话关联点",
      "connection": "类比|延伸|反例|同源"
    }
  ],
  "application_landscape": [
    {
      "domain": "应用领域",
      "use_case": "具体场景",
      "why_suitable": "为什么适合",
      "key_requirement": "关键性能指标"
    }
  ],
  "glossary": [
    {
      "term": "专业术语",
      "plain_explanation": "20 字以内通俗解释",
      "visualization_hint": "如何视觉化"
    }
  ],
  "suggested_openings": [
    {
      "style": "悬念式|故事式|数据式|提问式",
      "hook_sentence": "具体开场句",
      "why_it_works": "为什么有效"
    }
  ],
  "suggested_duration": "整数 90-360，根据主题复杂度估算（秒）",
  "knowledge_map": [
    {
      "point": "知识点（来自 knowledge_outline）",
      "subpoints": [
        {
          "name": "子知识点",
          "covered": true,
          "source_ref": "mat_008 / karpathy/nanoGPT"
        }
      ]
    }
  ],
  "learning_mainline": [
    {
      "step": 1,
      "point": "交叉熵损失",
      "teaches": "这一步让观众看见'损失=模型错得多离谱'",
      "builds_on": "（开篇/上一步）",
      "leads_to": "有了损失这个数，下一步才有'怎么读它'"
    }
  ],
  "retrieval_requests": [
    {
      "query": "具体搜索词",
      "purpose": "为什么需要这块信息（缺口说明）",
      "priority": "high|medium|low"
    }
  ]
}
```

`retrieval_requests` **产生规则**：只在"严重影响脚本质量的信息缺口"时才填（如缺关键原理推导、缺真实工程案例、缺可视化数据）。每条结构 `{stage:"research", query, purpose, needed_for, blocking, priority}`——`needed_for` 写哪段/哪概念需要它，`blocking=true` 表示缺它故事断/推导缺环（=P0，必须补到）。一般情况留空数组 `[]`，避免过度补检。主 pipeline 见此字段非空会回调 video-retrieval 定向补搜。

### Step 3: 类型差异化（script_type 决定）

- **科普**: 重点突出反常识事实和可视化数据。每个 narrative_cluster 应能转化为一个"恍然大悟"时刻
- **学习/教程**: 重点突出可实操的代码片段、可验证的实验、学习目标。每个 cluster 必须配一个具体的代码/实验/数值，narrative_cluster 多加 `hands_on` 字段
- **故事**: 重点突出人物关系和情感节点。每个 cluster 包含一个可展开的叙事弧
- **漫剧**: 重点突出视觉冲突和对话素材

### Step 4: 自检清单

输出前逐条确认：

1. 每条 key_fact 标了 source 吗？
2. 每个术语都有 plain_explanation 吗？
3. suggested_openings 是具体的句子，不是方向性建议？
4. depth_layers 的 intuitive_explanation 是否真正解释了"为什么"（而非"是什么"）？
5. application_landscape 覆盖了 3 个以上不同领域吗？
6. corroborating_knowledge 至少 2 条有意义的关联吗？
7. 是否有"众所周知""不言而喻""随着科技发展"等废话？（必须删除）
8. 如果是学习类型，narrative_clusters 是否都有 hands_on 字段？
9. depth_layers 是否覆盖至少 3 个递进维度（表层→原理→设计动机），而非平铺？
10. 信息缺口是否如实写进 retrieval_requests（而不是硬凑/留空蒙混）？
11. **学习/教程：knowledge_map 是否按 knowledge_outline 的"知识点→子知识点"两层列全，每个子点标了 covered + source_ref？所有 covered:false 是否都进了 retrieval_requests？**
12. **学习/教程：是否产出 learning_mainline——把知识点排成一条承上启下的学习主线（每步标 teaches/builds_on/leads_to），且 depth_layers 按这条主线顺序展开（不是知识点散装罗列）？**
13. **学习/教程：是否从 curriculum.json 装配了 `series_context`（active_node/day/position_line/deps_learned/unlocks_next）？`position_line` 用主题承接、不含 Day 号/编号（day 仅内部用）？非系列主题置 null？**
14. **学习/教程：是否消费了 github_repos——把高 star repo 的可跑代码/推导喂进 depth_layers 的 derivation/worked_example？**
15. **学习/教程：每个 depth_layer 是否都有 derivation（推导链）+ worked_example（带真实数字的示例）？只给结论不给推导 = 不合格，打回去补**
16. **职责边界：是否复用了 retrieval 的 `knowledge_outline` 骨架（没另起炉灶重组）？装配前是否校验过——无 `blocking=true` 的 P0 子点 `covered:false`（有就先回灌补检、不带洞硬装配）？**
17. **学习/教程：reverse_explanations 是否 ≥2 条，把观众熟悉的现象反向连回原理？**
18. **能配日常案例的原理层是否都填了 everyday_example（讲完原理紧跟一个观众有体感的例子）？纯内部机制可豁免**
19. 知识库整体过一遍：一个完全不懂的人看完，能不能"理解原理 + 看懂技术示例 + 看到日常案例 + 联系到自己熟悉的东西"？做不到就是还太浅

### Step 5: 写入文件

用 Write 工具把 JSON 写到 `output_path`。写完后简短报告：

- 知识库主路径
- 主题核心 (core_concept.one_sentence)
- narrative_clusters 数量
- depth_layers 数量
- knowledge_map 覆盖率（covered / 总子知识点）+ 缺口数（进 retrieval_requests）
- learning_mainline 步数（学习主线：知识点 1→2→3→…）
- suggested_duration

## 输出契约

返回给调用者（用户或主 skill）：

```
✓ knowledge_base written to <path>
  core: <one_sentence>
  clusters: N | depth: N | 覆盖: M/K 知识点 | duration: Ns
```

## 注意

- 这个 skill **不调用 LLM API**（DeepSeek 等），由你（Claude）直接思考输出
- **不要**调用 video-script 或其他下游 skill——你只负责知识库阶段，下游由 video-pipeline 主 skill 编排
- 如果用户给的素材不足以构建完整知识库，用 AskUserQuestion 反问需要补什么
