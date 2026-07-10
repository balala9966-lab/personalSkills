---
name: video-retrieval
description: 多路召回一个视频主题的全面素材，整理成结构化「素材卡片 JSON」，供后续知识库/脚本/分镜使用。委派子代理并行从四路取料——roadmap 课程文本 + curriculum 课程表 + Web 检索 + GitHub 高 star——再去重整合。当用户说"搜集 X 主题素材"、"研究 X 的资料"、下游 skill 发现信息缺口需要定向补检，或主 video-pipeline 调用时触发。输入主题关键词，输出 0_materials.json。
---

> 📁 **路径约定（输入数据 / 产物落点 / 渲染引擎）以单一真源为准**：`~/code/video-agent-pipeline/README.md`。

# Video Retrieval Skill

视频生产链路的**第一步**：联网把一个主题的零散信息搜全，整理成下游能直接消费的「素材卡片」。也承担**定向补检**——当下游 skill 发现某块信息不够时回头补搜。

## 触发方式

- 用户显式：「/video-retrieval <主题>」、「搜集 X 主题的素材」、「为 X 视频找资料」
- 主 skill 调用：`video-pipeline` 第一步（STEP 0.5）
- 补检调用：当 `retrieval_requests.json` 非空时，做定向补搜

## 输入

1. `keywords`: 主题关键词（如 "Day1 线性代数在大模型中的应用"）
2. `script_type`: `科普` / `故事` / `漫剧` / `学习` / `教程` / `开源速递` / `信息速递`（默认 `科普`）
3. `materials_seed`: 可选，用户已提供的种子素材（markdown / 笔记 / 已有 JSON）
4. `output_path`: 素材 JSON 写入路径（默认 `<output_root>/0_materials.json`；output_root 按 类型/课程 组织，如 `output/学习/大模型学习/Day8_MiniGPT实战/`，由 video-pipeline 传入）
5. `requests_path`: 补检请求文件路径（默认 `<同目录>/retrieval_requests.json`）

## 数据源分流（按 script_type·关键）

不同视频类型的"取数"路径**真实隔离、互不影响**：

- **学习 / 科普 / 开源速递** → 走本 skill 的**多路召回**（roadmap + curriculum + Web + GitHub），产出 `0_materials.json`。
- **信息速递（股市等数据驱动类）** → **不走多路召回**，走**接口取数**：`~/code/video-agent-pipeline/tools/fetch_market_week.py`（交易所级接口，绕代理直连）→ 产出 `data_verified.json`（**数据契约**，含每项的 base/last 收盘价 + 本周涨跌幅 + 数据源留痕），直接喂给 video-script。本 skill 仅在信息速递**需要定性背景补充**（如估值分位来源、政策面、资金面口径）时，以**模式 B 定向补检**介入，把搜到的背景标来源后追加；接口能复跑的核心数字一律以 `data_verified.json` 为准、不用搜索值覆盖。

## 两种运行模式

### 模式 A：首轮全面搜集（`retrieval_requests.json` 不存在或为空）

目标——**为后续提供充足的知识、示例、实践、优化各方面信息，尽可能全面**。下游做知识库/脚本/分镜时不该因为"信息不够"卡壳。

### 模式 B：定向补检（`retrieval_requests.json` 非空）

读 `retrieval_requests.json`（结构见下），**只针对其中每条 `query`/`purpose` 做定向召回**，把新素材**追加**进 `0_materials.json`，完成后**清空** `retrieval_requests.json`（写 `[]`）。

> 补检也走多路、主次同样不反：**先看缺口能不能在 roadmap 课程文本/课程表里补到**（系列课的缺口常常本来就在 INDEX 指到的那一节里），补不到再 Web/GitHub 定向搜。

`retrieval_requests.json` 契约（下游 skill 写、本 skill 读后清空）：

```json
[
  {
    "stage": "script|scene_design",
    "query": "具体搜索词",
    "purpose": "为什么需要这块信息（缺口说明）",
    "needed_for": "哪段/哪个概念需要它（如 seq5 的 KV-cache 推导），便于回灌后只重做受影响段",
    "blocking": true,
    "priority": "high|medium|low"
  }
]
```

> `blocking=true`（等价 P0：缺它故事就断/推导缺环）→ 必须补到才放行；`false`（P1/P2 锦上添花）→ 补不到可记 gap 不阻塞。`needed_for` 让下游回灌后**只重做受影响段**（配合增量渲染）。

## 你要做的事（模式 A · 多路召回 + 子代理整合）

知识获取走**多路并行召回**：roadmap 课程文本、课程表知识图谱、Web、GitHub 各成一路，**委派子代理并行去取**，主 Claude 最后整合去重。每路专注、互不稀释、可并行更快、覆盖更全。

### Step 1: 规划（主 Claude 先做，给子代理定靶）

先内联快速锚定，产出"召回靶清单"，再 fan-out（scout-then-fanout）：

1. **锚定节点**：读 `~/code/video-agent-pipeline/input/学习/curriculum.json`，按 `active_node_id`/主题名找到本节点，记 `summary` / `deps`（前置不重讲）/ `unlocks`（后续埋点）/ `day`。
2. **定 roadmap 出处**：读 `~/code/video-agent-pipeline/input/学习/roadmap/INDEX.md`，查到本节点对应的 `weekN-*.md` 学习日（或记下"roadmap 暂无专节"，该路跳过）。
3. **拟 `knowledge_outline` 骨架**：主题 → 知识点（3-6）→ 子知识点（每个 2-4）。**这张三层表就是各路子代理的覆盖靶**。**完整性约束**：骨架必须覆盖 `learning_thread` 的全部必经节点（不漏前置依赖），且**前瞻下游**——按 `script_type` 把下游制作需要的料类型（学习/教程的五桶、13 项清单所需）纳入子知识点，避免到 script/scene-design 才发现取料缺类。
4. **拟 `learning_thread` 雏形**：知识点按认知递进 + 依赖排序。

> **职责分界（与 video-research）**：retrieval 拥有"取料 + 骨架"——骨架（knowledge_outline/learning_thread）在此一次定稿，下游 research **复用不重组**。research 只做深化（derivation/worked_example）+ 校验 + 装配。

> 非系列（科普/故事/漫剧）可简化：靶清单 = 主题的几个叙事角度，主要走路 3，跳过 roadmap/课程表路。
>
> **开源速递专属**：主题是一个具体的 GitHub repo（来自 `tools/trending_repos.py` 选出的候选）。`active_node_id=null`，**只走路 3 Web + 路 4 GitHub（GitHub 为主料源）**，跳过路 1 roadmap / 路 2 课程表。`knowledge_outline` 退化为：项目 → 3-6 个核心模块/亮点 → 每个的子点。把学习类的「五桶」换成**四桶**（每桶 ≥2-3 条）：①解决什么问题/背景痛点（这项目出现前怎么办、痛在哪）②核心架构/工作原理（主要模块、数据流、关键机制）③关键技术亮点与创新点（做对了什么、比同类强在哪）④典型用法/效果/对比（真实用法、性能/体验数据、对标）。主料源 = repo 的 README/docs/架构图 + 作者博客/HN 讨论/关键 issue/release notes。

### Step 2: 多路并行召回（委派子代理，见 superpowers:dispatching-parallel-agents）

按下面四路**同时派子代理**（学习/教程四路全开；科普等以路 3 为主）。给每个子代理传：主题 + `knowledge_outline` 骨架（要覆盖的子知识点清单）+ 该路职责 + 统一返回格式（**素材卡片数组**，每条含 `content`/`source`/`type`/`covers`/三维 `scores`/`suggested_usage`）。各子代理**只取本路、只返回结构化卡片，不写文件**。

- **路 1 · roadmap 课程文本**（首要）：读 INDEX 指到的 `weekN-*.md` 那一节，把 📖知识点表 / 💻可跑代码 / ⚡优化 / 🎯面试题 抽成素材卡片，`source` 标 `roadmap/weekN`。这是**已验证的课程主干**，优先级最高。
- **路 2 · 课程表知识图谱**（辅助锚定）：读 curriculum.json 本节点 + 相邻节点（deps/unlocks）的 `summary`，提炼本期知识点骨架与边界——哪些是前置只回扣、哪些是本期主体、引向哪个后续——`source` 标 `curriculum`。它定"讲到哪为止"，防越界/重复。
- **路 3 · Web 深度检索**（补充）：用 WebSearch/WebFetch 三轮递进（基础认知→叙事深挖→视觉/对标），对 `knowledge_outline` 里**路 1/2 还没覆盖的子知识点**逐个打，并搜齐**五桶**（见下）。
- **路 4 · GitHub 高 star**（补充）：`site:github.com <主题> awesome/tutorial/from scratch/minimal pytorch`，WebFetch 高 star repo 的 README/notebook。优先官方/名家/万级 star（karpathy、huggingface、papers-with-code…），采集 `github_repos`（repo/stars/url/what_to_use/quality_signal）+ 可跑代码卡片。搜不到 → 记缺口。

**路 3 必搜的五桶**（学习/教程·硬要求，每桶 ≥2-3 条）：①原理推导（为什么除以 √d_k、不除会怎样，去论文/教材/优质博客）②可运行示例（能跑的最小代码+真实数值/shape/输出）③真实场景（工程侧"怎么用/不用会怎样" + **日常案例侧**：观众平时真会遇到的场景印证原理，标对应哪条原理供 `everyday_example` 配对）④对标讲解（高质量讲解视频/博客怎么把它讲透、怎么可视化，记 `reference_videos`）。⑤GitHub 桶由路 4 负责。

### Step 3: 整合（主 Claude·去重合并多路结果）

把各路子代理返回的卡片整合成统一素材集：

1. **去重合并**：同一事实多路命中 → 合成一条，`source` 记多个出处（roadmap 优先署名）。
2. **统一编号 `mat_xxx`**，每条补齐三维 `scores`：**visual**（可视化潜力 1-5）/ **emotional**（情感锚点 1-5）/ **specificity**（具体程度 1-5）。
3. **回填覆盖**：`knowledge_outline.points[].covered` 把每个子知识点映射到支撑它的 `mat_id`（多路都没覆盖 → null）。
4. **缺口**：`covered:null` 的子点 + 五桶缺的桶 + 缺 GitHub 优质源 → 全写进 `knowledge_gaps`，**绝不用脑内存货假填**。
5. **定稿 `learning_thread`**。
6. **标优先级 `priority`**（防"信息缺失/故事不完整"，回答"召回有优先级吗"）：每条素材按对故事的重要性分级——
   - **P0**＝覆盖 `learning_thread` 必经节点 / 是后续概念的前置依赖（缺它故事就断、推导缺环）；
   - **P1**＝主题核心但非必经；
   - **P2**＝锦上添花（增强可视化/情感）。
     赋值依据 `learning_thread` 主线与 `knowledge_outline` 依赖关系，不是凭感觉。

### Step 4: 输出 schema

写 `0_materials.json`：

```json
{
  "keywords": "主题关键词",
  "script_type": "学习",
  "knowledge_outline": {
    "topic": "概率与优化",
    "curriculum_ref": {
      "node": "prob-opt",
      "day": 2,
      "deps": ["linalg"],
      "unlocks": ["pretrain"]
    },
    "points": [
      {
        "point": "交叉熵损失",
        "subpoints": ["信息熵", "KL 散度", "与 softmax 配合", "为何适合分类"],
        "covered": {
          "信息熵": "mat_003",
          "KL 散度": "mat_004",
          "与 softmax 配合": null
        }
      }
    ],
    "learning_thread": ["交叉熵损失", "困惑度", "梯度下降", "AdamW"]
  },
  "materials": [
    {
      "id": "mat_001",
      "content": "素材内容摘要（一句话，尽量含具体数字/事实）",
      "source": "来源说明（论文/URL/教材/工程经验等）",
      "type": "事实 | 数据 | 类比 | 案例 | 公式 | 工程经验 | 学习方法 | 引用",
      "covers": "交叉熵损失 / KL 散度",
      "scores": { "visual": 4, "emotional": 3, "specificity": 5 },
      "priority": "P0 | P1 | P2",
      "suggested_usage": "在脚本中适合放在哪段（钩子/L1/L2/应用/实战代码）"
    }
  ],
  "reference_videos": [
    {
      "title": "对标讲解视频标题",
      "url": "...",
      "what_to_learn": "它怎么呈现这个知识点，值得借鉴什么形式"
    }
  ],
  "github_repos": [
    {
      "repo": "owner/name",
      "stars": "约 N（万级/千级即可）",
      "url": "https://github.com/...",
      "what_to_use": "可跑代码 | 推导讲解 | awesome 清单 | 高质量教程",
      "quality_signal": "官方 | 名家 | 高star"
    }
  ],
  "knowledge_gaps": ["首轮搜完后仍预计缺失的信息类型（供下游判断是否补检）"]
}
```

`knowledge_outline`、`reference_videos`、`github_repos` 仅学习/教程类型必填（`github_repos` ≥2-3 条高 star）；其他类型可省。素材卡片若来自 GitHub，`source` 注明 repo + star。`knowledge_outline.points[].covered` 把每个子知识点映射到支撑它的素材 id（没有就 null = 缺口）。

### Step 5: 自检清单

输出前逐条确认：

1. 学习/教程：**四路是否都召回了**——路 1 roadmap（有专节就必取）、路 2 课程表、路 3 Web、路 4 GitHub？Web/GitHub 的 query 命中了真实页面（不是脑内存货编的）？
2. 学习/教程：**先出 `knowledge_outline`（主题→知识点→子知识点）做靶再 fan-out 了吗**？整合后每个子知识点是否都有素材覆盖（`covered` 非 null）？没覆盖的进 `knowledge_gaps`？`learning_thread` 是否把知识点排成了递进主线？
3. 多路结果**去重合并**了吗？素材规模够吗（首轮建议 12-20 条，覆盖知识/示例/实践/优化）？每条标了 `covers`（属哪个知识点）吗？
4. 每条素材标了 `source` 吗（roadmap/curriculum/URL/repo）？三维 `scores` 都填了吗？
5. 学习/教程类型：**五桶是否搜齐**——①原理推导 ②可运行示例 ③真实场景 ④对标讲解 ⑤GitHub 优质源，每桶 ≥2-3 条？`github_repos` 是否填了 ≥2-3 条高 star repo（含 star 数与质量信号）？缺的桶是否如实写进 `knowledge_gaps`？
6. `knowledge_gaps` 是具体的信息类型，不是空话？
7. 有没有"众所周知/随着科技发展"等废话素材？（删除）
8. **每条素材标了 `priority`（P0/P1/P2）吗？`learning_thread` 每个必经节点的前置依赖都有 P0 素材覆盖吗（无 P0 缺口 = 故事不会断）？P0 缺口是否已写成 `blocking=true` 的 `retrieval_requests`？**

### Step 6: 写入文件 + 召回审查 + 报告

1. 用 Write 写 `0_materials.json`。
2. **召回审查（轻量·只查覆盖与故事完整性，不评写作质量）**：写 `<同目录>/0_materials_review.md`，只列事实账目——
   - **覆盖完整性**：`knowledge_outline` 子点 covered/uncovered 清单（M/K）；学习/教程五桶逐桶有无、`github_repos` 条数。
   - **优先级分布**：P0/P1/P2 各几条。
   - **故事完整性**：`learning_thread` 链条逐节点过一遍——每个必经节点的前置依赖是否都有 P0 素材覆盖；**列出会导致故事断的 P0 缺口**。
   - **结论**：`P0 缺口数`。P0 缺口 = 0 → `gate: pass`；有 P0 缺口 → `gate: blocked`，并把每个 P0 缺口写成一条 `retrieval_requests`（`blocking=true`，模式 B 优先自己先补一轮，补不到再交主 pipeline/用户）。
   - 这是覆盖账目，不是内容质量评估（写作质量留给 KB 阶段的 `video-content-eval`）。
3. 报告：

```
✓ materials written to <path>
  mode: 首轮全面 | 定向补检
  知识点覆盖: M/K 子点（学习型）| materials: N 条（P0/P1/P2 = a/b/c）| 对标视频: N 个 | GitHub repos: N 个
  召回审查: gate=pass|blocked · P0 缺口 N 项 → 0_materials_review.md
```

## 注意

- **多路召回是硬要求**：学习/教程主题，roadmap + 课程表 + Web + GitHub 四路尽量全开，子代理并行取、主 Claude 整合。**roadmap/课程表是主干、Web/GitHub 是补充，主次别反**；绝不允许全靠模型脑内存货——那正是旧方案"内容太简单"的病根
- **委派子代理**：用 Agent 工具并行派各路（见 superpowers:dispatching-parallel-agents）；子代理只返回卡片，主 Claude 负责去重整合 + 写文件
- **不调外部搜索 API**（旧方案的 Tavily/Brave 已弃用），Web 路统一用 Claude 原生 WebSearch / WebFetch，走系统代理
- **不要**调用 video-research 或其他下游 skill——你只负责素材召回阶段
- 模式 B 补检完**务必清空** `retrieval_requests.json`，否则主 pipeline 会误判"还有缺口"反复补检
- 子 skill 间只通过磁盘 JSON 通信，不共享对话上下文
