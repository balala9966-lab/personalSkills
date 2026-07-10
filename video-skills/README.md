# 视频生成 Skills 完整包（video-*）

一套 Claude Code Skill，把「主题 → mp4」全流程串起来：**素材召回 · 建库 · 大纲 · 场景 · 渲染 · 质检 · 发布 · 自进化**。

## 打包内容（10 个 skill）

| Skill                | 一句话                                                                   |
| -------------------- | ------------------------------------------------------------------------ |
| `video-pipeline`     | 主编排：从关键词到 mp4 一气呵成，串联下面 8 个子 skill                   |
| `video-retrieval`    | 多路召回（roadmap + curriculum + Web + GitHub），产出 `0_materials.json` |
| `video-research`     | 素材 → 结构化知识库 `1_knowledge_base.json`（含 depth_layers）           |
| `video-script`       | KB → 大纲 `2_outline.json`（含钩子 / 中段钩子 / 金句 / 互动）            |
| `video-scene-design` | 大纲 → bespoke 场景 `.tsx` + manifest（每段隔离子代理并行现写）          |
| `video-render`       | 场景 → mp4（TTS + Remotion 渲染 + ffmpeg 拼接）                          |
| `video-content-eval` | 每个内容阶段的质检报告（诊断不改，用户拍板）                             |
| `video-eval`         | 成片后的帧级审查（按句子时点抽帧、多模态查音画错位/组件重叠）            |
| `video-publish`      | 成片后的发布物料：两张封面 + 抖音/小红书文案 + 发飞书                    |
| `video-self-evolve`  | 视频定稿后的复盘 + 自进化（不动生产层、只加固知识/评估层）               |

## 依赖（不在本包内，需要单独准备）

- **Remotion 渲染项目**（`~/code/remotion-rlhf-poc/`）—— bespoke 场景写在这里、基元库住这里
- **视频生产项目**（`~/code/video-agent-pipeline/`）—— 产物落点、`curriculum.json` 权威课表、`tools/` 里 `sync_curriculum.sh` / `preflight_lint.py` / `render_bespoke.py` 等
- **edge-tts / ffmpeg / node.js** —— 系统级依赖
- **飞书凭证**（`~/.openclaw/openclaw.json` 或项目 `.env`）—— video-publish / feishu-* 用

## 安装

```bash
mkdir -p ~/.claude/skills
unzip video-skills.zip -d ~/.claude/skills/
```

之后在 Claude Code 里 `/video-pipeline <主题>` 即可触发。

## 快速起步

```
/video-pipeline 关键词=Transformer 架构 类型=学习
```

主 skill 会问你：素材、系列节点、是否自动跑等，之后按 6 步：召回 → 建库 → 大纲 → 场景 → 渲染 → 收尾。每步之间是内容质量卡点，出报告，你拍板。

## 版本

- 打包时间：2026-07-06
- 运行环境：macOS + Claude Code
