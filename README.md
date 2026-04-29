# personalSkills

A collection of personal AI agent skills for Claude Code, Cursor, Codex, Windsurf and other AI coding tools.

## Skills Included

| Skill | Description |
|-------|-------------|
| [`skill-store-manager`](./skill-store-manager) | Centralized skill repository with symlink distribution. Supports multiple AI tools, dual scope (global/project), batch management via `skills.txt`, and Windows compatibility. |
| [`skill-debug-sync`](./skill-debug-sync) | One-click sync of a skill under development to all installed AI coding tools via symlinks. |

## Quick Start

Each skill has its own `SKILL.md` and `README.md`. See the per-skill directories for installation and usage.

```bash
# Example: install skill-store-manager and try it
cd skill-store-manager
bash scripts/tests/test_basic.sh
python3 scripts/skillctl.py --help
```

## Repository Layout

```
personalSkills/
├── README.md
├── .gitignore
├── skill-store-manager/    # central skill repo manager
│   ├── SKILL.md
│   ├── README.md
│   ├── scripts/
│   └── docs/
└── skill-debug-sync/       # quick local sync for skill development
    ├── SKILL.md
    └── scripts/
```

## License

MIT
