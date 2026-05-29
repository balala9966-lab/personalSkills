# qmd Integration

qmd 是本地 Markdown 搜索引擎，支持关键词搜索、语义向量和混合检索。对于大型知识库（>50 页），强烈推荐安装。

## 安装

```bash
# npm
npm install -g qmd

# 或 bun
bun install -g qmd
```

## Collection 管理

```bash
# 注册 wiki collection
qmd collection add {kb-root}/wiki --name {kb-name}

# 列出所有 collections
qmd collection list

# 查看 collection 信息
qmd collection info {kb-name}
```

## 上下文注解

为搜索增加相关性上下文：

```bash
qmd context add {kb-root}/.schema/CLAUDE.md --collection {kb-name}
qmd context add {kb-root}/wiki/AGENTS.md --collection {kb-name}
```

## 索引与嵌入

```bash
# 增量索引（仅新增/修改的文件）
qmd update --collection {kb-name}

# 强制重新嵌入所有文件
qmd embed --collection {kb-name} --force
```

每次摄入或更新后执行 `qmd embed`。

## 搜索策略

| 命令 | 适用场景 | 示例 |
|------|---------|------|
| `qmd search "{keyword}"` | 精确关键词搜索 | `qmd search "settlement cycle"` |
| `qmd vsearch "{query}"` | 语义相似搜索 | `qmd vsearch "how does refund work"` |
| `qmd query "{question}"` | 混合检索 + 重排序（最强） | `qmd query "compare settlement flows of channel A and B"` |

## MCP Server 集成

在 Claude Code 中配置 qmd MCP server 以获得原生工具支持：

```json
{
  "mcpServers": {
    "qmd": {
      "command": "qmd",
      "args": ["mcp-server"]
    }
  }
}
```

## 与 KB 操作集成

| 操作 | qmd 行为 |
|------|----------|
| kb-init | 注册 collection，添加上下文注解 |
| kb-ingest | 摄入后执行 `qmd embed` |
| kb-query | 根据规模选择搜索策略 |
| kb-update | 更新后执行 `qmd embed` |
| kb-lint | 检查 qmd 索引是否与 wiki/ 同步 |

## 降级策略

qmd 不可用时：
- 所有检索退化为 AGENTS.md 导航 + `grep` 全文搜索
- 跳过 `qmd embed` 步骤
- 在 `log.md` 中标注：`[WARN] qmd not available, using index-only navigation`
- 查询性能下降但仍可用