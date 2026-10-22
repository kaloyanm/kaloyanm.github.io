# Frame selection

## How candidates are found

`frames` combines four signals:

1. A uniform sample every 8 seconds, so no stretch of the video is invisible.
2. Scene-change detection, which catches cuts and slide transitions.
3. Chapter starts, where a talk usually introduces a new visual.
4. Transcript cue lines: "as you can see", "this diagram", "look here", "notice how", "the chart", and similar. These are the moments a speaker points at something.

Candidate stills are 720 px wide for inspection. Contact sheets are 360 px tiles, labelled `cand-HH-MM-SS-mmm`. `frames/index.json` lists every candidate and which sheet it landed on.

## Review workflow

1. Open every `sheets/sheet-*.jpg` with the image-reading tool. Do not choose from filenames alone. If you cannot view images, stop.
2. For each H2 in the planned essay, write a one-line **visual brief**: what the reader must see to believe or understand that section.
3. Shortlist 8-12 candidates that answer those briefs. A pretty frame that does not answer a brief is noise.
4. For each shortlisted timestamp, extract the full frame to `/tmp` and inspect it before committing.
5. Reject talking heads, transitions, watermarks, black frames, duplicates, unreadable text, and frames that need a paragraph of caption.
6. Keep 3-6. Re-extract at the exact moment the visual settles; a slide mid-animation is a bad still.
7. Write `figures.md` in the scratch directory: `time | shows | section | caption`. If a section has no visual, leave it without one.

## Coverage

A good set covers different jobs, not the same job six times:

- One frame establishes the setup or the problem.
- One frame shows the mechanism or architecture.
- One frame shows the evidence: a number, chart, code output, or demo state.
- One frame shows the failure, cost, or edge case, if the video has one.

If two candidates show the same slide, keep the later, settled one. If a section's brief cannot be answered by any frame, say so in the plan and let the prose carry it.

## What earns a place

- A diagram that shows the causal chain described in the prose.
- A slide with a number, formula, or comparison that would be tedious to describe.
- A code or terminal frame with a concrete failure or output.
- A demo state that proves the claim: before/after, the broken version, the fixed version.
- A chart where the shape matters more than the exact values.
- A physical object or setup that grounds an abstract idea.

## Audio-only and static sources

A podcast, interview, or single-camera talk may have nothing worth showing. Do not manufacture stills or pad the piece with speaker frames. Use 0-2 frames that carry real information (a whiteboard, a guest, a demo) and let the prose do the work. The 3-6 figure target is for visual talks with slides or diagrams. If the source is truly audio-only, say so in the source line and skip figures entirely.

## What to reject

- Talking heads, unless the person is the subject of the essay.
- Frames with burned-in captions that duplicate the prose.
- Watermarks, channel logos, subscribe overlays, progress bars.
- Mid-transition blur, slide animations, cursor artifacts, notification popups.
- A frame that needs three sentences of caption to make sense.
- Screenshots of text that could be quoted more clearly.
- Anything that reveals private information: email, tokens, customer names, chat.

## Crop and scale

- Crop only dead space, letterboxing, UI chrome, or a distracting panel.
- Keep the information; do not crop a diagram's labels or a code line's context.
- Preserve aspect ratio. Never stretch.
- Final width: 1200-1600 px is enough for the 680 px prose column and retina.
- Save JPEG, quality 85. Avoid PNG unless the frame is line art with text; then PNG may be sharper.
- If the source is vertical, crop to the meaningful area rather than padding it into a wide frame.

Command shape:

```bash
python3 .claude/skills/youtube-deep-dive/scripts/youtube_essay.py still \
  .cache/youtube/<slug> --time 12:34 --out assets/images/think/<slug>/fig-01.jpg \
  --width 1600 --crop 1280:720:320:180
```

`--crop` is `W:H:X:Y` in source pixels. Inspect the result; do not trust the numbers blindly.

## Captions

Pattern: `Fig. N — what to notice. [MM:SS]`

- The caption tells the reader where to look, not what the image is.
- Weak: "Fig. 1 — A diagram of the system."
- Strong: "Fig. 1 — The write reaches the replica before the ack returns, so a crash here loses the write. [14:08]"
- Use the actual timestamp of the still.
- If the frame is a slide the speaker did not discuss, say so or drop it.
- Credit the video in the source line; the caption only needs the timestamp.

## Alt text

Describe the information, not the medium.

- Weak: "Screenshot."
- Weak: "Image of a diagram."
- Strong: "Three boxes in a row: client, queue, worker. An arrow loops from worker back to queue labelled retry."
- Include visible text only when it carries meaning. Do not transcribe an entire slide.
- Keep it one or two sentences.

## Placement

- Put the figure after the paragraph that makes the reader want it.
- Introduce it in the prose: "The frame below shows the moment the second worker stalls."
- Do not stack two figures back to back unless they are a deliberate before/after pair.
- Do not open the essay with a figure; the drop cap and first paragraph do that work.
- If a figure interrupts a causal chain, move it after the chain.

## Audit before publishing

`check_article.py` audits the final figures when ImageMagick is available:

- Identical image signatures fail the check, so the same frame cannot be embedded twice.
- A near-black frame (mean luminance under 0.015) warns, catching bad timestamps.
- A frame under 600 px wide warns; re-extract from a higher-resolution source or accept it only for a small inset.
- An extreme aspect ratio warns.
- Each figure must be introduced by the preceding prose, and captions must say what to notice, not "screenshot".
- A `source_kind = 'video'` essay must have at least 2 figures. Audio-only sources may have zero.
- Run the checker with `--scratch .cache/youtube/<slug>`. It requires `figures.md` and at least as many planned rows as embedded figures, so the visual review cannot be skipped.

Open the rendered page and confirm each figure sits beside the claim it supports. If it does not, move it or drop it.

## File hygiene

- One slug, one image directory: `assets/images/think/<slug>/`.
- Sequential names: `fig-01.jpg`, `fig-02.jpg`.
- Remove unused candidates from the asset directory; keep them in `.cache/`.
- Do not commit `.cache/`. It is ignored.
- Verify each file opens and is not a black frame or a duplicate of the previous one.
- Check the rendered page; Hugo fingerprints the asset URL, so the `src` will not match the filename exactly.
