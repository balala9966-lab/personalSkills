# Editorial Illustration

A Claude Code skill for generating strange, clean, hand-drawn editorial body illustrations for articles, blogs, Notion docs, and workflow docs. Converts the article's structural arguments into 16:9 horizontal hand-drawn explanation images — not slides, not infographics, not cute cartoons.

Ships with a minimal placeholder character (**The Tinkerer**) as the default IP. You can swap in any IP you provide.

## What It Does

- Reads an article, link, markdown, or brief.
- Picks cognitive anchors (main claims, turning points, contrasts, loops) instead of illustrating everything evenly.
- Produces a **shot list** when you ask for planning, or **generates images directly** when you ask for output.
- Uses a strict visual style: pure white background, thin black hand-drawn line art, sparse red / orange / blue annotation accents, generous whitespace.
- Forces the character to drive the central action, never decorate.

## Install

This skill lives in a personal repo. Install by symlinking it into your Claude Code skills directory:

```bash
ln -s "$(pwd)/editorial-illustration" ~/.claude/skills/editorial-illustration
```

Or use the project's existing `skill-debug-sync` helper if you have it.

## How To Trigger

Say things like:

- "Help me plan illustrations for this blog post."
- "Generate a body illustration for this section."
- "Make me a shot list for my Notion doc."
- "Draw a hand-drawn diagram for this idea."

The skill auto-triggers on requests mentioning article illustrations, body images, visual metaphors, shot lists, image prompts, or illustration revisions.

## Customising The IP

The default IP is The Tinkerer — a deliberately minimal, brandless figure (round head, two upright tufts, plain white coverall, black line work only). It exists so the rule *"the character must drive the action"* has a stable anchor across an article.

To use your own IP:

1. Tell the skill to use your character at the start of the conversation.
2. Provide a brief description of its silhouette and any brand color constraints.
3. The skill will keep the same editorial illustration grammar but make your IP the active subject.

See `references/ip-character.md` for the full Tinkerer spec and replacement rules.

## Layout

```
editorial-illustration/
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── style-dna.md
│   ├── ip-character.md
│   ├── composition-patterns.md
│   ├── prompt-template.md
│   ├── qa-checklist.md
│   └── example-index.md
└── assets/
    ├── examples/             # add your own as you build a library
    └── character-references/  # add IP reference images if you swap in another character
```

## Credits

This skill is a brand-free reimagining of a longer-running editorial illustration workflow. The methodology — strict color discipline, single-structure-per-image, character-as-operator, anti-repetition list, structure pattern dictionary — is preserved. The default IP is a generic placeholder designed from scratch and carries no brand affiliation.
