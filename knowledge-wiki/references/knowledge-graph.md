# Knowledge Graph Specification

知识图谱是 Knowledge Wiki 的关系可视化层，从 wikilink 提取确定性关系，并通过 LLM 推断隐式关系，形成三层边类型的知识网络。

---

## 图谱数据格式

`graph/graph.json`：

```json
{
  "metadata": {
    "kb_name": "my-kb",
    "generated_at": "2025-01-15T10:30:00Z",
    "total_nodes": 42,
    "total_edges": 78,
    "edge_type_counts": {
      "EXTRACTED": 50,
      "INFERRED": 20,
      "AMBIGUOUS": 8
    }
  },
  "nodes": [
    {
      "id": "payment-channel",
      "label": "支付渠道",
      "type": "entity",
      "domain": "business",
      "file": "wiki/entities/payment-channel.md"
    },
    {
      "id": "settlement-service",
      "label": "SettlementService",
      "type": "module",
      "domain": "code",
      "file": "wiki/code/modules/settlement-service.md"
    }
  ],
  "edges": [
    {
      "source": "payment-channel",
      "target": "settlement",
      "type": "EXTRACTED",
      "confidence": 1.0,
      "label": "depends_on",
      "evidence": "[[payment-channel]] contains [[settlement]]"
    },
    {
      "source": "payment-channel",
      "target": "settlement-service",
      "type": "INFERRED",
      "confidence": 0.85,
      "label": "implemented_by",
      "evidence": "PaymentChannel depends on settlement logic which is implemented in SettlementService"
    },
    {
      "source": "risk-control",
      "target": "payment-channel",
      "type": "AMBIGUOUS",
      "confidence": 0.55,
      "label": "regulates",
      "evidence": "Risk control may apply limits to payment channels"
    }
  ]
}
```

---

## 三层边类型

| 边类型 | 来源 | 置信度 | 说明 | 图谱可视化 |
|--------|------|--------|------|-----------|
| EXTRACTED | wikilink 提取 | 1.0 | 页面中显式的 `[[link]]` 关系 | 实线 |
| INFERRED | LLM 推断 | ≥ 0.7 | 页面内容语义关联但无显式链接 | 虚线 |
| AMBIGUOUS | LLM 推断 | < 0.7 | 弱关联，需人工确认 | 点线 |

---

## 图谱构建流程

### Step 1：提取 EXTRACTED 边

扫描 `wiki/` 下所有 Markdown 文件，提取 `[[wikilinks]]`：

1. 读取每个 `.md` 文件
2. 正则匹配 `[[link-text]]` 和 `[[link-text|display-text]]`
3. 解析链接目标（去除 display-text 部分）
4. 验证目标页面是否存在
5. 生成 EXTRACTED 边（confidence = 1.0）

### Step 2：推断 INFERRED 和 AMBIGUOUS 边

对每组相关页面使用 LLM 推断隐式关系：

1. 按 domain/topic 分组页面（避免全量两两比较）
2. 对每组内页面，让 LLM 分析内容并推断关系
3. LLM 输出格式：
   ```
   source: {page-id}
   target: {page-id}
   label: {relationship-type}
   confidence: {0.0-1.0}
   evidence: {brief explanation}
   ```
4. confidence ≥ 0.7 → INFERRED 边
5. confidence < 0.7 → AMBIGUOUS 边

**关系类型标签**：

| 标签 | 含义 | 方向性 |
|------|------|--------|
| depends_on | A 依赖 B | 有向 |
| implemented_by | 业务概念由代码实现 | 有向（业务→代码） |
| implements | 代码实现业务概念 | 有向（代码→业务） |
| relates_to | 一般关联 | 无向 |
| contradicts | 矛盾关系 | 无向 |
| evolves_from | 演化关系 | 有向 |
| regulates | 约束/规范关系 | 有向 |

### Step 3：生成可视化

输出 `graph/graph.html`，使用 D3.js force-directed 布局：

- **节点颜色**：按 domain 区分（business = 蓝色，code = 绿色）
- **节点大小**：按入边数量（hub 页面更大）
- **边样式**：EXTRACTED 实线、INFERRED 虚线、AMBIGUOUS 点线
- **交互**：悬停显示详情、点击跳转 wiki 页面、拖拽调整布局
- **筛选**：按边类型、domain、confidence 筛选

### Step 4：更新导航

在 `wiki/index.md` 和 `wiki/AGENTS.md` 中添加图谱链接：

```markdown
## Knowledge Graph
- [Interactive Graph](../graph/graph.html) — {total_nodes} nodes, {total_edges} edges
- Last updated: {date}
```

---

## 图谱更新触发

| 事件 | 图谱操作 |
|------|----------|
| 新建/更新 wiki 页面 | 重新提取该页面的 EXTRACTED 边 |
| 删除 wiki 页面 | 移除相关边和孤立节点 |
| `lint` 命令 | 检查 AMBIGUOUS 边是否可以升级或移除 |
| `update graph` | 全量重建 EXTRACTED + INFERRED + AMBIGUOUS |
| `update all` | 包含 `update graph` |

---

## 与 Lint 的集成

lint 命令中的图谱相关检查：

| 检查 | 说明 | 严重级别 |
|------|------|----------|
| 图谱边缺失 | 高度相关但未建立 wikilink 的页面对 | INFO |
| AMBIGUOUS 边过期 | 长期未确认的 AMBIGUOUS 边（>30 天） | INFO |
| 孤立节点 | 无任何边连接的页面（maps/ 除外） | WARNING |
| 跨域边缺失 | 代码页与业务页之间缺少链接 | WARNING |

---

## 性能考虑

- 小型 KB（< 50 页）：全量推断，无需优化
- 中型 KB（50-200 页）：按 domain/topic 分组推断，减少两两比较
- 大型 KB（> 200 页）：仅对同一 topic cluster 内的页面推断，EXTRACTED 边始终全量提取
- AMBIGUOUS 边数量上限：总边数的 20%，超出时按 confidence 升序移除