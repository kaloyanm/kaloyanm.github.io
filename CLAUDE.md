# CLAUDE.md

This file provides guidance when working in this repository.

## What this is

A personal site for Kaloyan Mirchev — backend engineer and AI engineering consultant. Built with Hugo and deployed to GitHub Pages at `kaloyanm.github.io`. The design direction is "Paper Terminal": late-90s personal-web structure (numbered indexes, ledgers, counters, colophon badges) carried by modern layout, typography, and accessibility.

## Commands

- `hugo server` — run the site locally with live reload (`http://localhost:1313`).
- `hugo server -D` — include draft content.
- `hugo --minify --cleanDestinationDir` — production build into `public/`.
- No package manager, linter, or test suite.

## Architecture

- **Theme** is vendored at `themes/portfolio-theme` (not a submodule). Site-level overrides in top-level `layouts/` follow Hugo's override-by-path convention; currently everything lives in the theme.
- **Design tokens and all styling** are in `themes/portfolio-theme/static/css/main.css`. Typography: Source Serif 4 (headings and prose), Inter (UI), JetBrains Mono (metadata). Light/dark themes are CSS variables on `[data-theme]`; `main.js` handles the toggle and stores the choice.
- **Shared chrome**: `layouts/partials/ticker.html` (status bar), `header.html` (sticky masthead + nav), `index-menu.html` (`<dialog>` sitemap, opened by the Index button or ⌘/Ctrl+K), `footer.html` (sitemap, colophon, badges).
- **Pages**
  - Home: `content/_index.md` → `layouts/index.html`, composed from `hero.html`, `doors.html` (Think / Design / Architect), `work-ledger.html`, `desk.html`, `career.html`.
  - Think (essays): `content/think/_index.md` → `layouts/think/list.html`; individual essays → `layouts/think/single.html` (reading progress, TOC, copy-link, end matter).
  - Work: `content/work.md` (`type = 'work'`) → `layouts/work/single.html`; projects grouped by `track` with anchors `#design` and `#architect`.
  - About: `content/about.md` (`type = 'about'`) → `layouts/about/single.html`; bio, career, skills, contact.
- **Data** in `data/`
  - `articles.yaml` — the Think catalogue. Entries are upcoming essays (`no`, `title`, `summary`, `date`, `status`, `topic`, `read`, `tags`). Adding `url` turns the title into a link; published essays can also live as real pages under `content/think/`.
  - `projects.yaml` — `slug` (used for anchors), `year`, `period`, `track` (`design` | `architect`), `role`, `outcome`, `short`, `description`, `tags`.
  - `experience.yaml`, `skills.yaml` — career and skills on home/about.
- **Site params** in `hugo.toml` (`name`, `role`, `summary`, `email`, `location`, `availability`, `since`, `now_*`) feed the ticker, ID card, Now panel, and About page. Edit there rather than hardcoding copy in templates.
- **Syntax highlighting** is class-based (`[markup.highlight] noClasses = false`) and themed in `main.css` to match the paper palette. Do not reintroduce inline dark code blocks.
- **Deployment**: `.github/workflows/hugo.yml` builds and deploys to GitHub Pages on every push to `main` (or manual dispatch), pinned to Hugo 0.156.0 extended.

## Publishing an essay

1. Create `content/think/<slug>.md` with `title`, `date` (past), `description`, optional `series`, and `tags`.
2. Remove the matching entry from `data/articles.yaml`; the Published list is generated from `content/think/`. (If you keep a published catalogue entry, add `url = "/think/<slug>/"`; the In progress table ignores entries that have a URL.)
3. Put figures in `assets/images/think/<slug>/` and insert them with `{{< figure src="fig-01.jpg" alt="..." caption="..." >}}`; the shortcode applies the existing figure frame and does not upscale.
4. `hugo --minify --cleanDestinationDir` and verify `/think/` lists it under "Published".

## Notes

- `design/1999-wireframes.html` is the original wireframe artifact for this direction. It is outside Hugo's content/static dirs and is not published; open it directly in a browser.
- **Video essays**: `.claude/skills/youtube-deep-dive/` turns a YouTube URL into a Think piece (yt-dlp captions, ffmpeg stills, first-principles drafting). It writes to `content/think/<slug>.md` and `assets/images/think/<slug>/`, and uses the `figure` shortcode rather than raw HTML.
- **Think queue**: `data/articles.yaml` is the "In progress" list. The Think page hides that block when the list is empty; the home "From the desk" panel falls back to the latest published essay. Published pages do not need a catalogue entry.
- There are no trackers, analytics scripts, newsletter forms, or comment systems. Keep it that way unless asked.
