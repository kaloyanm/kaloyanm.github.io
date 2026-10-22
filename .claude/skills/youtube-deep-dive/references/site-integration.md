# Site integration

Everything here is specific to `kaloyanm.github.io` (Hugo, vendored `portfolio-theme`). Follow it exactly; the design is already decided.

## Paths

| Purpose | Path |
| --- | --- |
| Published essay | `content/think/<slug>.md` |
| Draft essay | same, with `draft = true` |
| Image assets | `assets/images/think/<slug>/fig-01.jpg` |
| Scratch download | `.cache/youtube/<slug>/` |
| Think catalogue | `data/articles.yaml` |
| Theme | `themes/portfolio-theme/` |
| Styles | `themes/portfolio-theme/static/css/main.css` |

Never edit `main.css`, fonts, colors, or layout templates to make an article look better. The article component is already styled. Use the primitives below.

## Front matter

TOML, fenced with `+++`. Match the existing content style (single quotes).

```toml
+++
title = 'A claim, not a topic'
date = 2026-10-22
description = 'One or two sentences: the problem, the payoff, why it matters.'
tags = ['AI engineering', 'Architecture']
source_url = 'https://www.youtube.com/watch?v=...'
source_title = 'Exact video title'
source_channel = 'Channel name'
source_kind = 'video'
+++
```

Optional:

```toml
series = 'Deep dive'   # only when this belongs to a named series
draft = true           # drafts only
```

Rules:

- `title`: 15-95 characters, a claim or sharp question. Do not use the video title.
- `description`: 80-260 characters. This is the dek under the title and the meta description.
- `date`: `YYYY-MM-DD`, today or earlier. Hugo hides future-dated pages by default.
- `tags`: 2-4 concrete topics, matching the vocabulary in `data/articles.yaml`.
- `source_url`, `source_title`, `source_channel`: required for video-derived essays.
- `source_kind`: `video` by default. A video essay must contain at least 2 figures; the checker fails without them. Use `audio` only for a genuinely audio-only source, where 0 figures is allowed.
- The byline, reading time, TOC, progress bar, prev/next, and author card are automatic.

## Images

Save stills as JPEG, max 1600 px on the long edge, quality around 85. Use `fig-01.jpg`, `fig-02.jpg`, and so on. Keep the originals in `.cache/youtube/<slug>/`.

Insert with the site shortcode, not raw HTML and not Markdown image syntax:

```markdown
{{< figure src="fig-01.jpg" alt="The scheduler's queue filling while workers idle." caption="Fig. 1 — Work arrives faster than workers drain it. [04:12]" >}}
```

- A bare `src` resolves to `assets/images/think/<slug>/<src>`.
- A path with a slash resolves from `assets/`.
- The shortcode resizes only when the image is wider than 1400 px (never upscales), fingerprints the URL, and wraps the image in the existing `.figure` frame with `figcaption` styling.
- `alt` is required; `caption` is strongly expected.
- Caption pattern: `Fig. N — what to notice. [MM:SS]`.
- Use 3-6 figures. More than 8 is a slide deck, not an essay.

## Allowed formatting

The prose styles support these. Use them deliberately.

- **H2** for the five to seven movements. These become the sticky TOC.
- **H3** for genuinely separate stages inside a movement.
- **Bold** for a term the first time it is defined. Do not bold whole sentences.
- **Italic** for emphasis and for a speaker's phrase. Use sparingly.
- **Blockquote** for the one sentence the reader should remember, or a short verbatim quote from the speaker with attribution. One or two per essay.
- **Ordered list** for a causal sequence or steps. **Unordered list** for parallel points. Do not make every section a list.
- **Code fence** for code, formulas, or protocol shapes. Inline code for identifiers and literals.
- **`---`** for a scene break. Not between every section.
- **Footnotes** are enabled if a citation needs to stay out of the flow. Prefer a short parenthetical.
- **The drop cap** is automatic on the first paragraph. Do not add a drop cap manually, and do not start the article with a heading or a figure.

## Forbidden

- New CSS classes, inline `style=` attributes, custom colors, or fonts.
- Raw `<div>`, `<span>`, `<table>` layouts. Goldmark strips raw HTML by default.
- Emoji, badges, callout boxes, colored panels, progress meters inside the prose.
- A second H1. The template owns the title.
- Markdown image syntax `![]()` for figures; use the shortcode.
- Tables in prose. The site has no prose table styling. If a comparison is needed, use a short list or a figure.
- Rewriting the Think list template to change the design.

## Published vs in progress

**Published** is the default. A page under `content/think/` with no `draft` flag appears automatically in the **Published** list.

**In progress** comes from `data/articles.yaml` (planned and drafting essays). The Think template hides the In progress block when that list is empty. When publishing an essay that was listed there, remove its catalogue entry. Do not leave a duplicate.

The home **From the desk** panel uses the latest published Think page; if there are no published pages, it falls back to the first catalogue entry. The shared `essay-state.html` partial handles both cases, so an empty queue is safe.

Draft entry shape:

```yaml
- no: "004"
  title: "The claim, not the video title"
  summary: "One sentence, same job as the description."
  date: "October 2026"
  status: "Drafting"
  topic: "Architecture"
  read: "12 min"
  tags:
    - Architecture
    - Caching
```

No `url` while it is a draft. On publish: remove the `draft = true` line and remove the whole entry. The published page list is generated from content, not from YAML.

## Source line

End the essay with a short, plain source block. Do not style it with a heading unless the piece needs one.

```markdown
---

Source: [Video title](https://www.youtube.com/watch?v=...) by Channel, 42 min. Watched 22 October 2026. Figures are stills from the video at the timestamps in their captions.
```

If the video is a talk with slides, name the event. If it is a podcast, name the host. Do not imply endorsement.

## Build and verify

```bash
python3 .claude/skills/youtube-deep-dive/scripts/check_article.py content/think/<slug>.md --scratch .cache/youtube/<slug>
hugo --minify --cleanDestinationDir
```

Then check:

1. `public/think/<slug>/index.html` exists and contains the title.
2. `/think/index.html` lists it under **Published**, not **In progress**.
3. The rendered HTML contains no unresolved `{{<`, `ZgotmplZ`, or empty `src`.
4. Every figure has a rendered `src`, `alt`, and `figcaption`.
5. `hugo server` at desktop and mobile widths; toggle dark mode.
6. The TOC is readable and the first paragraph has the drop cap.

Hugo is pinned to 0.156.0 extended in CI. Use the same major behavior locally.
