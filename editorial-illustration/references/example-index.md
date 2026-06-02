# Example Index

This skill ships with no bundled example images. You build your own reference library over time. Calibration from your own real outputs is more honest than calibration from someone else's portfolio — your taste, your topics, your handwriting.

## How To Use Examples

When you start collecting examples:

- Place final illustrations you are proud of under `assets/examples/` with a descriptive filename, e.g. `01-llm-context-window.png`.
- Add an entry to this file recording: the topic, the structure type used (see `composition-patterns.md`), and what specifically is worth calibrating from it (line density, whitespace ratio, label restraint, color discipline, character action).
- Treat each entry as a *what to imitate at the texture level*, not *what to copy at the composition level*.

## Entry Template

Copy this block when adding a new example:

```markdown
- `assets/examples/<NN>-<slug>.png`
  - Topic: <one-sentence description of the article idea>
  - Structure: <Threshold / Split path / Loop / Compression / Translation / Balance / Excavation / Relay / Repair / Mismatch>
  - Useful for: <line density / whitespace / annotation restraint / mascot-as-actor / sparse arrows / before-after contrast / etc.>
```

## Calibration Rules

- Match the feel, not the composition.
- Keep the character active in the mechanism, never decorative.
- Keep the canvas mostly white.
- Keep annotations short and handwritten.
- Use orange for movement, red for problems / outcomes, and blue for secondary system or mental-state notes.
- Do not turn these references into reusable templates. If you find yourself repeating a metaphor across multiple articles, retire it (see the anti-repetition list in `composition-patterns.md`).

## When To Skip Examples Entirely

For the first generation on a new article, often the best move is to skip the example library and let the prompt template + style DNA + composition patterns drive the image. Reach for examples when:

- A specific texture (line wobble, whitespace ratio) is drifting and you need to recalibrate.
- The article topic closely resembles one you have already illustrated and a consistency cue would help.
- You are introducing a new collaborator or model and need a quick visual brief.
