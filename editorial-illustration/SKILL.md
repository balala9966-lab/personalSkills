---
name: editorial-illustration
description: Generate strange, clean, hand-drawn editorial illustrations for articles, posts, blogs, Notion docs, workflow docs, methods, processes, structures, states, metaphors, and viewpoints. Use when the user asks for article illustrations, body images, visual metaphors, weird hand-drawn diagrams, shot lists, image prompts, title removal, image revision, or illustration generation. Default to English output unless the user specifies another language; support any requested output language.
---

# Editorial Illustration

## Purpose

Design and generate 16:9 horizontal editorial body illustrations. The goal is not commercial illustration, slide infographics, cute cartoons, or literal diagrams. Convert the article's key judgment, process, structure, state, or metaphor into a clean, strange, readable hand-drawn explanation image.

Default visual IP: use **The Tinkerer**, a minimal placeholder character defined in `references/ip-character.md`. If the user supplies a different IP, follow the user's IP for that task and keep the same editorial style. The character must drive the core action in the image; never place it as decoration.

## References

Load only what the task needs:

- `references/style-dna.md`: visual style, color, typography, and strict avoid rules.
- `references/ip-character.md`: default Tinkerer character, behavior, action library, and replacement rules.
- `references/composition-patterns.md`: structure types, metaphor invention, and anti-repetition rules.
- `references/prompt-template.md`: single-image generation prompt template.
- `references/qa-checklist.md`: post-generation checks and iteration rules.
- `references/example-index.md`: how to build and maintain your own reference library.
- `assets/examples/`: optional low-frequency calibration only. Do not copy example compositions, props, or labels.

## Workflow

### 1. Digest the Source

Read the article, link, markdown, Notion content, screenshot, or user brief. Extract:

- Core argument.
- Cognitive turning points.
- Sections that benefit from a visual explanation.
- Sections that should remain text-only.

Do not illustrate evenly. Prefer cognitive anchors: the main claim, two breakpoints, input-output loops, branching, before-after contrast, one-source-many-uses patterns, handoff paths, common traps, or role/state changes.

### 2. Produce a Shot List First

If the user asks to analyze where illustrations should go, plan images, or suggest visuals, provide a shot list instead of generating images.

For each image, include:

- Placement after a specific paragraph or section.
- Theme.
- Core meaning.
- Structure type.
- What the character is doing.
- Suggested visual elements.
- Suggested handwritten labels.

Default to 4-8 images. Use 1-3 for short pieces. Avoid more than 9 unless the article genuinely needs it.

### 3. Compose The Prompt And Generate

This skill is responsible for *producing the prompt*, not for owning a specific image-generation backend. Always output the final, copy-pasteable prompt text to the user, even when an image-generation tool is available. The prompt is the deliverable; the rendered image is an optional follow-on.

For each image:

1. **Compose the prompt** using `references/prompt-template.md`. Fill in every bracketed slot. Do not leave placeholders in the final text.
2. **Print the prompt to the user** inside a fenced code block, labeled with the image number and its purpose. The user must be able to copy this verbatim into any external image tool (Nano Banana / Midjourney / Stable Diffusion / OpenAI Images API / Gemini Imagen / etc.).
3. **If the user explicitly asks to generate, create, output, make images, or revise an image**, also call an available image-generation tool — one image at a time, no combined canvases. Pick the best available option in this order:
   - A sibling skill the user has installed for this purpose (e.g. `generate-image-public`). Trigger it by emitting the appropriate skill invocation with the prompt you just composed.
   - If no image-generation skill is available, say so plainly and stop after printing the prompt — do not silently skip the user's request.
4. **Do not assume image generation succeeded.** If the tool returns an error or no file path, surface it and keep the prompt in the chat so the user can retry elsewhere.

Each image must express one core structure. Each prompt must include:

- 16:9 horizontal editorial body illustration.
- Pure white background.
- Black hand-drawn line art.
- Sparse handwritten annotations in the output language, default English.
- Small accents in red, orange, and blue.
- Generous whitespace.
- The Tinkerer (or the user-supplied IP) as the core action subject.
- No PPT style, commercial illustration, childish cuteness, complex architecture diagrams, or top-left diagram titles.

Use the user-requested language for labels. If no language is specified, use English. The skill instructions are in English, but the output can be in any language the user asks for.

### 4. Check and Iterate

After generation, use `references/qa-checklist.md`. Regenerate or edit if:

- The character is decorative instead of active.
- The image is too full.
- It looks like a PPT flowchart or business infographic.
- Text is excessive, misspelled, or in the wrong language.
- A top-left title such as "Workflow", "Common Pitfalls", or "Architecture" appears.
- The style is too cute, childish, rigid, or polished.
- The background is not clean white.

### 5. Save Deliverables

When working in a workspace, copy final images to:

```text
assets/<article-slug>-illustrations/
```

Name files in order:

```text
01-topic-name.png
02-topic-name.png
```

Preserve original generated files. Do not overwrite existing assets unless the user explicitly asks.

## Response Style

For strategy, be brief and precise. For each generated image, include:

- Image number and purpose.
- The full prompt in a fenced code block (always — even if rendering succeeded).
- Save path if an image file was produced.
- Which images are strongest and which are optional.

Do not explain the style theory at length. Let the images and the prompts carry the work.