# Prompt Templates

Each Type has a recommended skeleton. The composer fills the slots from the outline block and the chosen Style/Palette, then writes the assembled prompt to `prompts/NN-{type}-{slug}.md`.

Inside the prompt file the body is the literal text sent to the image backend. There is no template DSL — the body is plain text.

## Shared header (every prompt)

```text
Create a {ASPECT} {SIZE_DESCRIPTOR} illustration.

Style: {STYLE_PHRASES from illustration-styles/styles/<style>.md "Generation Prompt Hints"}
Palette: {PALETTE_PHRASES from illustration-styles/palettes/<palette>.md "Generation Prompt Hints"}
```

`SIZE_DESCRIPTOR`: `editorial body` for body illustrations, `cover hero` for covers.

## infographic skeleton

```text
[Shared header]

Subject: {CORE_IDEA_FROM_OUTLINE_PURPOSE}

Layout: {grid|radial|hierarchy|left-right|top-bottom} layout with {N} clearly bounded zones.

Zones:
{For each visual element in outline:}
- {Element name}: {description}, label "{actual label text from the article}"

Color discipline:
- {primary color #HEX}: {semantic role e.g. main lines}
- {accent color #HEX}: {semantic role e.g. key callouts}
- {secondary color #HEX}: {semantic role}

Labels: use these exact terms from the article: {comma-separated list of 5-8 actual terms/numbers}.
Language: {ARTICLE_LANGUAGE}.

Avoid: {STYLE_AVOID_PHRASES from illustration-styles}, any company logos, any readable brand wordmarks.
```

## scene skeleton

```text
[Shared header]

Scene: {CONCRETE_SCENE_DESCRIPTION — what is happening in the image}

Character: {who/what is the focal subject, doing what action}.
Composition: {placement, lighting, environmental detail that grounds the scene}.

Mood: {mood word from style or article tone}.

Avoid: {STYLE_AVOID_PHRASES}, posed-portrait composition, lifeless tableau, specific recognizable faces.
```

## flowchart skeleton

```text
[Shared header]

Process: {WHAT_FLOW_IS_BEING_DESCRIBED}.

Steps: {N} steps arranged {left-to-right|top-to-bottom}.

Each step:
{For each step:}
- Step {idx}: {label}, {brief content}

Connectors: arrows between consecutive steps; {special connectors if any: loop-back, branch}.
Color discipline: {as in infographic}.

Avoid: {STYLE_AVOID_PHRASES}, dense paragraphs of explanatory text inside steps, flowchart-box clip-art aesthetic.
```

## comparison skeleton

```text
[Shared header]

Comparison: {OPTION_A} vs {OPTION_B} on the dimension of {DIMENSION}.

Layout: split composition, {OPTION_A} on the left, {OPTION_B} on the right, vertical divider in the middle.

Left side:
- Visual representation of {OPTION_A}
- Labels: {key labels for A}
- Verdict line: "{one-line verdict for A}"

Right side:
- Visual representation of {OPTION_B}
- Labels: {key labels for B}
- Verdict line: "{one-line verdict for B}"

Color discipline: one accent color per side ({hex for A}, {hex for B}); shared neutral for axes/dividers.

Avoid: {STYLE_AVOID_PHRASES}, unbalanced visual weight between sides.
```

## framework skeleton

```text
[Shared header]

System: {WHAT_FRAMEWORK_IS_BEING_DESCRIBED}.

Components: {N} components arranged {hierarchically|in a cycle|as a matrix|as a network}.

Components and their roles:
{For each component:}
- {Component name}: {role / responsibility}

Relationships: {how components connect — arrows, lines, containment, nesting}.

Color discipline: {primary node color}; {accent for highlighted component or critical edge}.

Avoid: {STYLE_AVOID_PHRASES}, abstract decorative shapes that don't map to a labeled component.
```

## timeline skeleton

```text
[Shared header]

Timeline: {WHAT_PERIOD_IS_BEING_SHOWN — duration, scope}.

Axis: horizontal line, {LEFT_LABEL} on the left, {RIGHT_LABEL} on the right.

Milestones:
{For each milestone:}
- {Year/date}: {event}, brief detail "{label}"

Composition: milestones evenly spaced; key milestones visually emphasized (larger marker, accent color).

Color discipline: neutral axis line; {accent color} for emphasized milestones.

Avoid: {STYLE_AVOID_PHRASES}, uniformly emphasized milestones (defeats the visual hierarchy purpose).
```

## cover skeleton

```text
Create a {ASPECT} cover image.

Title (visible in image): "{ARTICLE_TITLE}"
{Subtitle (visible in image): "{SUBTITLE}"} — only if text_level >= title-subtitle

Style: {STYLE_PHRASES from selected cover style}
Palette: {PALETTE_PHRASES from selected cover palette}
Rendering: {flat-vector|hand-drawn|painterly|digital|screen-print|chalk|pixel}

Subject: {CORE_VISUAL — what the cover depicts}

Composition: {hero|conceptual|metaphor|scene|minimal|typography} composition.
- {composition detail 1}
- {composition detail 2}

Mood: {subtle|balanced|bold}.

Text treatment: title typography {description — serif/sans, weight, placement}. Do not invent any text not provided here.

Avoid: {STYLE_AVOID_PHRASES}, real recognizable faces, any company logos, any readable brand wordmarks not explicitly in the title.
```

## Universal "avoid" tail

Always append, regardless of type:

```text
- any company logo
- any brand wordmark
- any readable text on character clothing not explicitly part of the labels above
- watermarks (unless watermark.enabled in EXTEND.md)
- photorealistic faces of identifiable real people
```
