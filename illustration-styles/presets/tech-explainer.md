---
id: tech-explainer
type: infographic
style: blueprint
---

# Tech Explainer

The default preset for technical deep-dives, API anatomy, system metrics. Combines `infographic` Type with `blueprint` Style — structure-first, precise, engineering-flavored.

## Why This Combo

`infographic` provides the grid + labeled-zones layout that data-dense technical content needs. `blueprint` adds the engineering register that signals "this is rigorous, not marketing." The combination reads as a spec-page from an internal doc rather than a SaaS landing page.

## Best For

- API documentation feature pieces ("how the `/v1/messages` endpoint actually works")
- System metric breakdowns
- Architecture-anatomy articles
- Recommended density: `balanced` to `per-section`

## Tuning Tips

- **Grid alignment**: prompt should explicitly mention grid layout — image models drift toward freeform without it
- **Label discipline**: use technical terms from the article verbatim, not generic placeholders
- **Color**: blue + white default; introduce red only for the most critical callout per image
- **Avoid**: scene elements, characters, narrative composition — they pull the result toward "warm explainer" which fights the spec aesthetic

## Example Prompt Skeleton

```text
A 16:9 technical infographic in blueprint style.

Subject: <one-sentence concept from the article>

Composition: grid layout with 3-4 clearly bounded zones. Each zone has a small heading and 2-3 labels using the article's actual terminology: <list 5-8 specific terms/numbers from the article>.

Style: technical blueprint aesthetic, precise thin black lines on white, blue accent grid underlay, monospace labels, one critical detail highlighted in red.

Avoid: scene elements, characters, soft warm colors, hand-drawn wobble, marketing infographic style.
```
