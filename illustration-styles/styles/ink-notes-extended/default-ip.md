# Default IP Characters

Two built-in IP characters are available. The user can also supply their own.

---

## Option A: The Tinkerer (generic placeholder)

A minimal, brandless placeholder character. Use when no specific IP is needed or the article is purely technical.

### Visual Traits (hand-drawn line art)

- **Head**: clean round, slightly oversized, single thin black line
- **Hair/antennae**: two short upright strokes on top — the silhouette signature
- **Eyes**: two small dots, calm and attentive
- **Mouth**: tiny straight or slightly curved line, usually neutral
- **Body**: small, compact, plain white coverall — no logo, no patch, no text
- **Hands**: simple mitten-like, always doing something
- **Feet**: plain rounded shoes
- **Palette on figure**: black line work only

Androgynous, age-neutral, culture-neutral. No reference image required.

---

## Option B: 贵公子 (default when user has set up the reference image)

A cute ancient-Chinese-style young boy — warm, curious, slightly mischievous. Better suited than The Tinkerer for articles with personality, narrative voice, or Chinese-language content.

**Reference image**: `assets/character-references/贵公子.png`

### Visual Traits

- **Head**: round, slightly oversized relative to body, with short neat dark hair (no hat, no bun)
- **Face**: big expressive eyes, small nose, gentle expressions — can show: happy smile, surprise, shyness, playful wink (see reference sheet)
- **Outfit**: light celadon/mint-green (浅青色) traditional hanfu robe with white inner layer, tied at the waist with a darker teal sash
- **Accessories**: small jade pendant (玉佩) hanging from the waist sash — the silhouette signature
- **Body**: small, compact, toddler-like proportions (big head, short limbs)
- **Hands**: small rounded hands, always actively doing something
- **Feet**: simple cloth shoes matching the robe color
- **Palette on figure**: celadon green robe + white inner + teal sash + warm skin tone — when translated to ink-notes style, keep the green as the ONE allowed accent color on the character; rest of the scene uses the standard ink-notes palette (black + red/orange/blue)

### Four-View Reference

The reference image provides front / 45° left / 45° right / back views — use these for silhouette consistency across an article's illustrations.

### Expression Reference

The reference image provides four expressions: 开心微笑 (happy smile), 惊讶 (surprise), 害羞 (shy), 俏皮眨眼 (playful wink). Match expression to the article's tone at each insertion point.

### Action Poses

The reference image shows two action poses — use these as a starting point for dynamic compositions. The character should always be *doing*, never standing idle.

## Role In The Image

The Tinkerer must participate in the core action:

- Carrying, sorting, dragging, repairing, balancing, mapping, filtering, inspecting, catching, splitting, stitching, measuring, watering, or negotiating the central metaphor.
- Creating the state change the article is describing.
- Revealing the contradiction, bottleneck, or transformation.
- Acting as the operator inside the idea, not as a presenter outside it.

**Do NOT use The Tinkerer as:**

- A passive observer
- A logo in the corner
- A decorative sticker
- A waving figure beside the actual concept
- A smiling narrator pointing at a diagram

## Personality

- Curious, patient, slightly mischievous
- Serious enough to solve the strange task in front of it
- Competent but sometimes overmatched by the metaphor — that gap is where the article's tension shows
- Warm without becoming childish, cute-poster-like, or slapstick

## Common Generation Corrections

Regenerate if:
- The figure has colored body fill (should be black line only)
- The two upright tufts are missing (silhouette signature lost)
- A logo, brand mark, or readable word appears on clothing
- The face has detailed features (pupils, eyelashes, blush, smile lines) — drifted toward cartoon mascot
- The figure stands aside pointing instead of operating the mechanism

## User-Supplied IP Replacement

When the user provides their own character:

1. **Preserve its canonical silhouette and brand constraints** (if any)
2. **Keep the same editorial illustration grammar** — line weight, color discipline, whitespace, single-structure rule
3. **Make the user's IP the active subject** of the central metaphor
4. **Do NOT mix The Tinkerer with the user's IP** unless explicitly asked
5. **If the user's IP has its own canonical color**, allow that one color on the character; the rest of the color discipline still applies to the scene
6. **If the user provides reference images**, use those for silhouette fidelity; apply the same role/personality/correction rules as The Tinkerer

### How To Specify A Custom IP

In the prompt or EXTEND.md, set:

```yaml
custom_ip:
  name: "My Character"
  description: "A round robot with one antenna and treads instead of legs"
  canonical_color: "#3B82F6"  # optional: one color allowed on the character
  ref_images:
    - "path/to/ref1.png"
    - "path/to/ref2.png"
```

The composer will substitute The Tinkerer's trait description in the prompt template with the custom IP's description. All other rules (must drive action, no decoration, no mixed IPs) remain.
