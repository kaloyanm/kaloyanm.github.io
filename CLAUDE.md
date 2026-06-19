# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A personal Hugo static blog ("Септокод 0.1") in Bulgarian, deployed to GitHub Pages at `kaloyanm.github.io`. Content is sparse and editorial in nature — most work here is writing/editing Markdown posts, not application code.

## Commands

- `hugo server` — run the site locally with live reload (default `http://localhost:1313`).
- `hugo server -D` — also serve draft content (posts have `draft = true` by default, see Archetype below).
- `hugo --minify` — production build, outputs to `public/`. CI runs this with an explicit `--baseURL`.
- No package manager, linter, or test suite — there's nothing to install and nothing to test.

## Architecture

- **Theme is vendored, not a submodule.** `themes/diary-theme` is a full copy of the [hugo-theme-diary](https://github.com/AmazingRise/hugo-theme-diary) source, committed directly into this repo (no `.gitmodules`). Site-level overrides live in the top-level `layouts/` and `i18n/` directories and follow Hugo's standard override-by-path convention — a file at `layouts/partials/extended_head.html` shadows the theme's partial of the same name. Currently only `extended_head.html` (adds Google Fonts) is overridden.
- **Language is Bulgarian throughout.** `hugo.toml` sets `languageCode = 'bg-bg'` and `defaultContentLanguage = 'bg'`. `i18n/bg.yaml` overrides theme UI strings (date formats, pagination labels, etc.) — this is a site-level override of the theme's own `i18n/` files, not a separate translation layer.
- **Content structure**: `content/posts/*.md` for blog posts, `content/categories/<name>/_index.md` for category landing pages (category names are Bulgarian, e.g. `книгорафт`). Taxonomies (`tags`, `categories`) and the main nav menu are wired up in `hugo.toml` via `[[menu.main]]` entries pointing at `/posts`, `/categories`, `/tags`.
- **New posts**: use `hugo new posts/<name>.md` to scaffold from `archetypes/default.md` (sets `draft = true` and a title-cased title from the filename — Bulgarian titles need to be set manually after scaffolding since the archetype only title-cases the slug).
- **Deployment**: `.github/workflows/hugo.yml` builds and deploys to GitHub Pages on every push to `main` (or manual dispatch). It pins `hugo-version: '0.156.0'` (extended) — match this locally to avoid version drift in rendering.
