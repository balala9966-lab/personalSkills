# Scene Catalog · 8 固定 scene_type 详细 schema

每个 scene 的 props 完整字段。SceneDesigner 必须按此 schema 填充。

---

## 1. hook

**用途**：开场反差钩子。两个对比对象 + 一个倍数爆点。

```json
{
  "scene_type": "hook",
  "props": {
    "narration": "string  钩子段旁白，3 句以内，前 15 秒不许铺垫",
    "big": { "label": "大对象名", "params": "大数值", "emoji": "可选 emoji" },
    "small": { "label": "小对象名", "params": "小数值", "emoji": "可选 emoji" },
    "multiplier": "倍数文本，如 '100×' 或 '5 LINES'",
    "title": "可选 主标题",
    "topChipText": "可选 顶部小标签，学习视频用 'WEEK X · DAY Y'"
  }
}
```

⚠️ `big.params` 和 `small.params` 必须是**同一量纲**才能做 multiplier，否则 multiplier 用"LINES" "STEPS" 等定性词。

---

## 2. anchor

**用途**：问题锚定 + 引出核心关键词。4 卡片矩阵 + 字符 stagger 关键词。

```json
{
  "scene_type": "anchor",
  "props": {
    "narration": "string 必须满足 concept_grounding：新术语先专业后通俗",
    "products": [{ "name": "产品名", "color": "品牌色 #hex" }],
    "keyword": "核心关键词大写英文",
    "subtitle": "关键词副标题（英文全称或中文释义）",
    "topChipText": "可选 顶部小标签"
  }
}
```

products 通常 4 个。

---

## 3. three-steps

**用途**：三步流程展示。3 卡片依次入场 + 流光连接。

```json
{
  "scene_type": "three-steps",
  "props": {
    "narration": "按 concept_grounding 规范",
    "steps": [
      {
        "idx": 1,
        "code": "步骤短代号",
        "fullName": "中文全名",
        "analogy": "通俗类比或公式简写",
        "detail": "1-2 句机制说明",
        "icon": "可选 emoji"
      }
    ],
    "title": "可选 主标题",
    "topChipText": "可选 顶部小标签"
  }
}
```

steps 数组必须恰好 3 项。

---

## 4. deep-dive

**用途**：深度原理段，三个子面板依次切换。最重的段。

```json
{
  "scene_type": "deep-dive",
  "props": {
    "narration": "总旁白覆盖三个子主题",
    "panels": [
      {
        "_template": "models-grid",
        "enterSec": 0,
        "title": "英文小标题",
        "subtitle": "中文主标",
        "models": ["元素1", "元素2", "元素3", "元素4"],
        "stat": "底部强调数据"
      },
      {
        "_template": "keyword-with-svg",
        "enterSec": 23,
        "title": "英文小标题",
        "subtitle": "中文主标",
        "keyword": "大字关键词（英文）",
        "keywordCn": "中文释义",
        "definition": "一句话专业定义",
        "analogy": "一句话通俗类比"
      },
      {
        "_template": "before-after-stat",
        "enterSec": 47,
        "title": "英文小标题",
        "subtitle": "中文主标",
        "before": "改变前数值/形态",
        "after": "改变后数值/形态",
        "stat": "改进百分比，如 '-70%'",
        "caption": "底部说明"
      }
    ]
  }
}
```

panels 数组必须恰好 3 项，每项的 `_template` 字段告知用哪个面板模板（实际渲染时按数组下标 0/1/2 自动匹配 models-grid / keyword-with-svg / before-after-stat 模板）。

---

## 5. apps-spotlight

**用途**：应用图景 + 单一方法 spotlight。

```json
{
  "scene_type": "apps-spotlight",
  "props": {
    "narration": "...",
    "topChip": "顶部小标签",
    "title": "主标题",
    "products": [{ "name": "...", "color": "..." }],
    "quote": { "text": "引述文本", "author": "人物 · 年份" },
    "spotlight": {
      "keyword": "核心方法关键词（大字英文）",
      "fullName": "英文全称",
      "cnName": "中文名",
      "impact": "影响力一句话"
    }
  }
}
```

---

## 6. mapping-table

**用途**：跨领域映射表。N 行左右对照。

```json
{
  "scene_type": "mapping-table",
  "props": {
    "narration": "...",
    "topChip": "顶部小标签",
    "title": "主标题",
    "mappings": [
      {
        "brain": "左侧领域 A 概念（中文）",
        "brainEn": "左侧英文（可选）",
        "ai": "右侧领域 B 概念（英文）",
        "aiCn": "右侧中文（可选）",
        "color": "强调色 #hex"
      }
    ]
  }
}
```

mappings 通常 3 项。

---

## 7. terminal

**用途**：黑色终端 + 打字机文字 + 模型自言自语 / 代码展示。

```json
{
  "scene_type": "terminal",
  "props": {
    "narration": "...",
    "topChip": "如 '5 LINES · LIVE RUN' 或 '2025 · EXPERIMENT'",
    "rule": "高亮规则/公式文本",
    "emergedText": "中文话语 或 学习视频的多行代码字符串",
    "emergedTextEn": "英文话语",
    "insight": "底部一句话洞察"
  }
}
```

**学习视频专属**: `emergedText` 必须放代码字符串，**恰好 3-5 行核心代码**（不许塞完整 import + 全部初始化，完整代码留 outline 的 demo_code），多行用 `\n` 分隔。例：

```
"scores = Q @ K.transpose(-2,-1) / d_k**0.5\nattn = torch.softmax(scores, dim=-1)\noutput = attn @ V\n\n>>> scores.shape\ntorch.Size([2, 4, 4])"
```

---

## 8. outro

**用途**：收尾，回扣 + 警告 + 开放问题 + 候选答案。

```json
{
  "scene_type": "outro",
  "props": {
    "narration": "...",
    "topChip": "顶部小标签",
    "hookback": "回扣开头的问题文本",
    "hookbackAnswer": "→ 一句话答案",
    "warningChip": "警告标签（学习视频用 '⏭ NEXT: ...'）",
    "warning": "下一篇引入问题（一句话）",
    "question": "大字开放问题（学习视频用 '下一集学什么？〈主题名〉'，不报 Day 号）",
    "candidates": ["候选 1", "候选 2", "候选 3"]
  }
}
```

**学习视频专属**: question 用主题名预告下一集（如「下集：把整个 Transformer 拼起来」），**不出现 Day 号/集序数字**，candidates 列出下一篇能学到的能力。warning 是引入问题（"单头只有一个会场，想多维怎么改？"）。

---

## 通用规则

- 所有 scene 的 `id` 字段建议用 scene_type 同名
- `props.narration` 必填，所有其他字段尽可能填全
- 顺序必须严格按 1→8（hook → anchor → three-steps → deep-dive → apps-spotlight → mapping-table → terminal → outro）

## ⚠️ 组件时长契约（最易踩坑·必读）

**场景时长由旁白 TTS 音频长度决定**（render 自动算 sceneSec = 音频 + pad），而每个 tsx 组件的入场动画时间是**硬编码**的。旁白太短 → 后面的动画/面板被切掉、内容消失；旁白太长 → 动画播完后静止 hold（可接受）。所以**每段旁白必须写到下面的目标时长，确保覆盖该组件所有动画**。

中文 TTS 约 **6 字/秒**，按此估算字数。

| scene_type     | 目标旁白时长 | 字数参考 | 组件关键动画时点（旁白必须盖过）                |
| -------------- | ------------ | -------- | ----------------------------------------------- |
| hook           | ~20s         | ~120 字  | 大字震动 5-7s、卡片退场 7-8.8s、倍数 14-16s     |
| anchor         | ~18s         | ~110 字  | 箭头 4-5.5s、关键词 6s、产品 stagger            |
| three-steps    | ~24s         | ~145 字  | **三步在 3 / 13 / 23s 入场**，旁白须念到第 3 步 |
| deep-dive      | ~60s         | ~350 字  | **3 面板按 `enterSec` 切换**，见下方铁律        |
| apps-spotlight | ~45s         | ~270 字  | products 16s、spotlight 30s、impact 35-37s      |
| mapping-table  | ~25s         | ~150 字  | 映射行在 3 / 7 / 11s 逐行入场                   |
| terminal       | ~30s         | ~180 字  | 代码 14s 开始打字、insight 28s                  |
| outro          | ~25s         | ~150 字  | 答案 4-5.5s、候选 9 / 17s、问题尾段自适应       |

**总时长**：8 模板天生是 **~4–4.5 分钟**的密集视频，别为了凑 10 分钟硬塞旁白（会让节奏拖沓）。内容多就提密度，不是拉时长。

### deep-dive enterSec 铁律

`panels[].enterSec` 是"距本场景开始的秒数"，且 panel i 显示区间是 `[enterSec[i], enterSec[i+1]]`，最后一个到 `durationSec`。**enterSec 必须落在旁白时长内、且与旁白讲到该面板的时点对齐**。60s 旁白的标准三档：`0 / 20 / 40`。

❌ 反例（本项目真实踩坑）：deep-dive 旁白只写一句引子（8s），却把 enterSec 设成 0 / 90 / 175 → 后两个面板（Eiffel 例子、sqrt 推导）永不出现，深度从成片消失。
✅ 正解：把词向量 / 上下文改写 / sqrt 推导三段**完整讲进旁白**（~58s），enterSec 0 / 20 / 40 与之对齐。

### terminal 代码呈现

`emergedText` 放 3-5 行代码字符串，组件在 ~14s 开始打字（charsPerSec≈8 内置）。旁白念"每行在做什么"而不是念代码字符，时长盖过打字结束（~30s）。
