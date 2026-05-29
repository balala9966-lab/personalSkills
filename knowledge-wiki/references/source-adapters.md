# Source Adapters

源适配器负责从不同平台获取内容并转换为 Markdown。每个适配器实现统一接口，核心逻辑不绑定特定平台。

## 适配器接口

```
detect(source_spec) -> boolean          # 能否处理此源
fetch(source_spec) -> raw_content       # 获取原始内容
list(source_spec) -> [source_items]     # 列出所有项（批量源）
detect_changes(spec, last_state) -> []  # 检测变更
to_markdown(raw_content) -> markdown    # 转换为 Markdown
```

---

## 内置适配器

### Web Article Adapter

**检测规则**：URL 以 `http://` 或 `https://` 开头，且不属于已知笔记平台域名。

**处理流程**：
1. 验证 URL 可访问性
2. 使用 `fetch_content` 或 `WebFetch` 抓取内容
3. 清洗：去除导航、广告、侧栏、页脚，保留标题、正文、列表、表格、代码块
4. 提取元数据：title、author、date、url
5. 下载图片到 `raw/business/assets/{slug}/`，重写路径
6. 保存为 `raw/business/web/{slug}.md`

**存储**：`raw/business/web/{slug}.md`

**错误处理**：
- 404/不可达：报告错误，跳过
- 付费墙/需登录：警告用户，保存已获取的部分内容
- 重 JS 渲染：建议用户使用浏览器剪藏工具预处理

---

### Yuque Adapter

**检测规则**：URL 包含 `yuque.com` 或 `yuque.antfin.com`。

**单篇文章**（3+ 路径段）：
1. `skylark_resolve_url(url)` → doc_id
2. `skylark_doc_detail(doc_id)` → 内容
3. 转换 Lake 格式为 Markdown
4. 提取元数据：title、author、updated_at、url
5. 保存为 `raw/business/yuque/{slug}.md`

**整个知识库**（2 路径段）：
1. `skylark_resolve_url(url)` → book_id
2. `skylark_doc_list(book_id)` → 文档列表
3. 展示清单，用户确认范围
4. 逐篇获取（1-2 秒间隔），进度追踪到 `.kb-state.json`
5. 中断后可从断点恢复

**变更检测**：`skylark_doc_detail` 返回的 `content_updated_at` 与 `.kb-state.json` 中记录的时间戳对比。

**依赖 MCP**：`skylark_*` 系列工具

---

### Feishu / Lark Adapter

**检测规则**：URL 包含 `feishu.cn`、`larksuite.com`、`open.feishu.cn`。

**单篇文档**：
1. 解析 URL 提取 `app_token` 和 `obj_type`（docx/wiki/bitable）
2. 调用飞书 API 获取文档内容：
   - 文档：`GET /open-apis/docx/v1/documents/{app_token}/raw_content`
   - Wiki：先 `GET /open-apis/wiki/v2/spaces/get_node` 获取 obj_token，再获取内容
3. 转换飞书 Block 格式为 Markdown
4. 提取元数据
5. 保存为 `raw/business/feishu/{slug}.md`

**整个知识空间**：
1. `GET /open-apis/wiki/v2/spaces` → 空间列表
2. `GET /open-apis/wiki/v2/spaces/{space_id}/nodes` → 节点树
3. 遍历节点，逐篇获取

**变更检测**：`last_modified_time` 与 `.kb-state.json` 对比。

**依赖**：飞书 MCP 工具或 `FEISHU_APP_ID` / `FEISHU_APP_SECRET` 环境变量。

---

### Local Markdown Adapter

**检测规则**：本地文件路径以 `.md` 结尾。

**处理流程**：
1. 验证文件存在且可读
2. 复制到 `raw/business/local/{filename}.md`
3. 扫描图片引用，复制到 `raw/business/assets/`，重写路径
4. 保留已有 YAML frontmatter

---

### Local PDF Adapter

**检测规则**：本地文件路径以 `.pdf` 结尾。

**处理流程**：
1. 保留原始 PDF 到 `raw/business/local/{filename}.pdf`
2. 使用 `pdf` skill 提取文本
3. 保存提取结果为 `raw/business/local/{filename}.md`

**局限性**：表格可能丢失结构、扫描件可能 OCR 错误、复杂布局可能错乱。

---

### Local DOCX Adapter

**检测规则**：本地文件路径以 `.docx` 结尾。

**处理流程**：
1. 保留原始 DOCX 到 `raw/business/local/{filename}.docx`
2. 使用 `docx` skill 提取内容
3. 保存提取结果为 `raw/business/local/{filename}.md`

---

### GitHub Repository Adapter

**检测规则**：URL 包含 `github.com/` 或用户指定为「代码仓库」。

**处理流程**：
1. `git clone {url}` 到临时目录（或使用已有本地 clone）
2. 分析仓库结构：README、目录树（深度 3）、配置文件、语言/框架
3. 注册到 `.schema/code-repos.md`
4. 触发代码分析流水线（详见 `code-analysis-pipeline.md`）
5. **不复制代码到 raw/**：代码留在仓库中，仅生成分析产物

**变更检测**：`git log --since="{last_analyzed}"` 检查新 commit。

**存储**：
- 注册信息：`.schema/code-repos.md`
- 分析产物：`wiki/code/`
- 仓库元数据：`raw/code/{repo-name}/repo-meta.json`

---

### Generic Git Adapter

**检测规则**：URL 以 `.git` 结尾（非 GitHub）。

**处理流程**：与 GitHub Adapter 相同，但不依赖 GitHub 特有 API。

---

### YouTube Adapter

**检测规则**：URL 包含 `youtube.com/watch` 或 `youtu.be/`。

**处理流程**：
1. 提取视频 ID
2. 使用 YouTube Data API 或字幕接口获取字幕/文稿（优先中文字幕，回退英文）
3. 提取元数据：title、channel、duration、publish_date、tags
4. 保存文稿为 `raw/business/web/{video-id}.md`
5. 若无字幕可用，提示用户手动提供文稿

**变更检测**：YouTube 视频内容通常不变，仅检查元数据（标题、描述）是否更新。

**依赖**：`YOUTUBE_API_KEY` 环境变量（可选，无 API Key 时使用字幕接口）。

**局限性**：自动生成的字幕质量参差不齐；无字幕视频需人工补充。

---

### arXiv Adapter

**检测规则**：URL 包含 `arxiv.org/abs/` 或 `arxiv.org/pdf/`。

**处理流程**：
1. 提取 arXiv ID（如 `2401.12345`）
2. 通过 arXiv API 获取元数据：title、authors、abstract、categories、published date
3. 下载 PDF 到 `raw/business/assets/{arxiv-id}.pdf`
4. 使用 `pdf` skill 提取正文（优先 abstract + introduction + conclusion）
5. 保存摘要为 `raw/business/web/{arxiv-id}.md`

**变更检测**：arXiv 论文不可变，仅检查是否有新版本（v2, v3...）。

**保留方式**：默认 `local`（PDF 下载保存）。

---

### RSS Adapter

**检测规则**：URL 以 `.xml`、`.rss`、`.atom` 结尾，或内容为 RSS/Atom feed 格式。

**处理流程**：
1. 获取 feed 内容，解析 RSS 2.0 / Atom 格式
2. 列出所有条目（title、link、published date、summary）
3. 展示清单，用户确认摄入范围
4. 逐条获取全文，走 Web Adapter 流程
5. 保存 feed 元信息到 `raw/business/web/{feed-name}-feed.md`

**变更检测**：对比 feed 中最新条目的 published date 与 `.kb-state.json` 记录。

**批量处理**：支持，按 feed 分组并发生成。

---

### Jupyter Notebook Adapter

**检测规则**：本地文件路径以 `.ipynb` 结尾。

**处理流程**：
1. 读取 `.ipynb` JSON 结构
2. 提取 markdown cells（保留格式）和 code cells（保留代码 + 输出摘要）
3. 提取内核信息、依赖包（从 code cells 的 import 语句推断）
4. 保存为 `raw/business/local/{filename}.md`

**保留方式**：默认 `local`。

---

### PPTX Adapter

**检测规则**：本地文件路径以 `.pptx` 结尾。

**处理流程**：
1. 保留原始 PPTX 到 `raw/business/local/{filename}.pptx`
2. 使用 `pptx` skill 或 python-pptx 提取每页幻灯片内容
3. 提取文本、表格、图片引用
4. 按幻灯片顺序组织为 Markdown（`## Slide N`）
5. 保存提取结果为 `raw/business/local/{filename}.md`

**保留方式**：默认 `local`。

**局限性**：复杂动画、嵌入式对象可能丢失。

---

### CSV Adapter

**检测规则**：本地文件路径以 `.csv` 结尾。

**处理流程**：
1. 读取 CSV 文件，检测编码和分隔符
2. 提取列名、数据类型、行数、统计摘要
3. 识别关键列和异常值
4. 保存结构化摘要为 `raw/business/local/{filename}.md`
5. 原始 CSV 复制到 `raw/business/local/{filename}.csv`

**保留方式**：默认 `local`。

---

## 自定义适配器

在 `.schema/source-adapters.md` 中注册自定义适配器：

```markdown
## Confluence

- detect: URL 包含 `confluence.` 或 `atlassian.net/wiki/`
- fetch: 使用 Confluence REST API（需配置 token）
- to_markdown: 将 Confluence storage format 转 Markdown
- detect_changes: 通过 `lastModified` 头或 API 字段
- config:
    base_url: https://confluence.example.com
    token_env: CONFLUENCE_TOKEN
- storage: raw/business/confluence/{slug}.md
```

核心流程在摄入时会读取 `.schema/source-adapters.md`，遇到已注册的适配器配置时，按配置中的规则路由和处理。

---

## 适配器选择优先级

当多个适配器都可能匹配时，按以下优先级选择：

1. **精确匹配**：域名完全匹配（yuque.com → Yuque Adapter）
2. **协议匹配**：http(s) → Web Adapter（兜底）
3. **文件扩展名**：.md → Local Markdown，.pdf → Local PDF
4. **用户指定**：用户显式指定适配器类型时，优先使用用户选择

---

## 元数据提取规范

所有适配器产出的 Markdown 文件必须包含 YAML frontmatter：

```yaml
---
title: "{文档标题}"
source_type: "{web|yuque|feishu|youtube|arxiv|rss|jupyter|pptx|csv|local-markdown|local-pdf|local-docx|github|git}"
source_url: "{原始 URL 或文件路径}"
fetched_at: "{获取时间 ISO 8601}"
adapter: "{适配器名称}"
---
```

适配器负责填充这些字段。如果原始源不提供某些字段（如 author），可以留空。

---

## 源文件保留策略

**重要原则：禁止删除源文件。** raw/ 中的原始材料是知识库不可变基础。

| 保留方式 | 说明 | 适用场景 | 默认适配器 |
|----------|------|----------|-----------|
| `local` | 原始文件完整保存到 `raw/` | 核心业务文档、唯一来源、可能下线的内容 | PDF, DOCX, arXiv, PPTX, CSV, Jupyter |
| `link` | 仅保留元数据和原始链接 | 公开网页、可随时重新获取的内容、大文件 | Web, YouTube, RSS |

用户可在摄入时通过 `--preserve local|link` 覆盖默认值。

在 `.kb-state.json` 的 `source_registry` 中通过 `preservation` 字段记录每个源的保留方式。