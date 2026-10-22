#!/usr/bin/env python3
"""Validate a Think essay before building the site.

Checks front matter, length, structure, figures, source attribution, and the
plain-language rules in references/deep-dive-method.md.

Usage:
  python3 check_article.py content/think/my-essay.md [--strict]
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

REQUIRED = ("title", "date", "description", "tags", "source_url")
BANNED_OPENINGS = (
    "in this video",
    "in today's video",
    "this video",
    "today we",
    "in today's world",
    "let's dive",
    "let's unpack",
    "buckle up",
)
BANNED_PHRASES = (
    "delve",
    "tapestry",
    "testament to",
    "game-changer",
    "game changer",
    "in today's fast-paced",
    "it's not just",
    "more than just",
    "at the end of the day",
    "in conclusion",
    "in summary",
    "buckle up",
    "let's unpack",
    "let's dive",
    "this changes everything",
    "the future of work",
)
PLACEHOLDERS = ("TODO", "TBD", "FIXME", "lorem ipsum", "[timestamp]", "XXX")
COMMON_ACRONYMS = {
    "AI", "API", "CPU", "GPU", "HTTP", "HTTPS", "JSON", "SQL", "URL", "HTML",
    "CSS", "JS", "PDF", "RSS", "USB", "RAM", "SSD", "CLI", "SDK", "LLM", "RAG",
    "KYC", "AML", "SLA", "SLO", "UI", "UX", "ID", "OK", "US", "UK", "EU", "CEO",
    "CTO", "MB", "GB", "TB", "KB", "MS", "TV", "DNA", "CPU", "SIMD", "NUMA",
    "TCP", "UDP", "DNS", "TLS", "SSH", "ORM", "CRUD", "SaaS", "PII", "GDPR",
}


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str]] = []

    def pass_(self, message: str) -> None:
        self.rows.append(("PASS", message))

    def warn(self, message: str) -> None:
        self.rows.append(("WARN", message))

    def fail(self, message: str) -> None:
        self.rows.append(("FAIL", message))

    def count(self, level: str) -> int:
        return sum(1 for kind, _ in self.rows if kind == level)


def find_root(start: Path) -> Path | None:
    for parent in [start.resolve(), *start.resolve().parents]:
        if (parent / "hugo.toml").exists():
            return parent
    return None


def parse_front_matter(text: str) -> tuple[dict, str]:
    match = re.match(r"^\s*\+\+\+\s*\n(.*?)\n\+\+\+\s*\n?(.*)$", text, re.S)
    if not match:
        return {}, text
    raw, body = match.group(1), match.group(2)
    fields: dict[str, object] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        fields[key.strip()] = value.strip()
    tags_match = re.search(r"^tags\s*=\s*\[(.*?)\]", raw, re.S | re.M)
    if tags_match:
        fields["tags"] = re.findall(r"['\"]([^'\"]+)['\"]", tags_match.group(1))
    return fields, body


def as_string(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value or "").strip().strip("'\"")


def as_bool(value: object) -> bool:
    return as_string(value).lower() == "true"


def strip_body(body: str) -> str:
    text = re.sub(r"```.*?```", " ", body, flags=re.S)
    text = re.sub(r"`[^`]+`", " ", text)
    text = re.sub(r"\{\{<.*?>\}\}", " ", text, flags=re.S)
    text = re.sub(r"!\[.*?\]\(.*?\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"[*_~]+", "", text)
    text = text.replace(">", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def first_paragraph(body: str) -> str:
    for block in re.split(r"\n\s*\n", body):
        block = block.strip()
        if not block:
            continue
        if block.startswith(("#", "{{", "---", "!", ">", "|", "<")):
            continue
        return re.sub(r"\s+", " ", block)
    return ""


def figure_calls(body: str) -> list[tuple[dict[str, str], int]]:
    calls: list[tuple[dict[str, str], int]] = []
    for match in re.finditer(r"\{\{<\s*figure\b(.*?)>\}\}", body, re.S):
        attrs = {}
        for key, double, single in re.findall(
            r"(\w+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)')", match.group(1)
        ):
            attrs[key] = double or single
        calls.append((attrs, match.start()))
    return calls


def image_stats(path: Path) -> tuple[int, int, float, str] | None:
    """Return width, height, mean luminance, and signature via ImageMagick."""
    magick = shutil.which("magick")
    identify = shutil.which("identify")
    if magick:
        cmd = [magick, "identify", "-format", "%w %h %[fx:mean] %#", str(path)]
    elif identify:
        cmd = [identify, "-format", "%w %h %[fx:mean] %#", str(path)]
    else:
        return None
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        return None
    parts = (res.stdout or "").strip().split()
    if len(parts) < 4:
        return None
    try:
        return int(parts[0]), int(parts[1]), float(parts[2]), parts[3]
    except ValueError:
        return None


def preceding_paragraph(body: str, position: int) -> str:
    """The last prose paragraph before a shortcode, with markup removed."""
    for block in reversed(re.split(r"\n\s*\n", body[:position].rstrip())):
        block = block.strip()
        if not block or block.startswith(("#", "{{", "---", "!", ">", "|", "<")):
            continue
        return strip_body(block).lower()
    return ""


def resolve_asset(root: Path, slug: str, src: str) -> Path | None:
    if not src or "://" in src or src.startswith("data:"):
        return None
    clean = src.lstrip("/")
    options = [
        root / "assets" / "images" / "think" / slug / clean,
        root / "assets" / clean,
        root / "static" / clean,
    ]
    for option in options:
        if option.is_file():
            return option
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("article")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument(
        "--scratch",
        default="",
        help="video scratch directory; requires figures.md from the visual review",
    )
    args = parser.parse_args()

    article = Path(args.article)
    if not article.is_file():
        print(f"FAIL  article not found: {article}")
        raise SystemExit(1)

    root = find_root(article.parent)
    if root is None:
        print("FAIL  could not find hugo.toml above this article")
        raise SystemExit(1)

    text = article.read_text(encoding="utf-8").lstrip("\ufeff")
    fields, body = parse_front_matter(text)
    slug = article.parent.name if article.name == "index.md" else article.stem
    report = Report()

    if not fields:
        report.fail("missing +++ TOML front matter")
    for key in REQUIRED:
        if key not in fields or not as_string(fields[key]):
            report.fail(f"front matter missing: {key}")

    title = as_string(fields.get("title"))
    description = as_string(fields.get("description"))
    date_value = as_string(fields.get("date"))
    tags = fields.get("tags") if isinstance(fields.get("tags"), list) else []
    source_url = as_string(fields.get("source_url"))
    source_kind = as_string(fields.get("source_kind")) or ("video" if source_url else "")
    draft = as_bool(fields.get("draft"))

    if title:
        if not 15 <= len(title) <= 95:
            report.warn(f"title is {len(title)} characters; aim for 15-95")
        report.pass_(f"title: {title}")
    if description:
        if not 80 <= len(description) <= 260:
            report.warn(f"description is {len(description)} characters; aim for 80-260")
        else:
            report.pass_("description length")
    if tags:
        report.pass_(f"tags: {', '.join(tags)}")
    else:
        report.fail("tags is empty")

    if date_value:
        if not re.match(r"^\d{4}-\d{2}-\d{2}", date_value):
            report.fail("date must start with YYYY-MM-DD")
        else:
            try:
                date = dt.date.fromisoformat(date_value[:10])
                if date > dt.date.today():
                    report.warn(f"date {date} is in the future; Hugo will not publish it by default")
                else:
                    report.pass_(f"date: {date}")
            except ValueError:
                report.fail(f"invalid date: {date_value}")

    if source_url:
        if not re.match(r"^https?://", source_url):
            report.fail("source_url is not an http(s) URL")
        else:
            report.pass_("source_url present")
    if not as_string(fields.get("source_title")):
        report.warn("source_title is missing; the source line will be weaker")
    if source_kind and source_kind not in {"video", "audio"}:
        report.warn("source_kind should be 'video' or 'audio'")
    elif source_kind == "audio":
        report.pass_("audio-only source; figures are optional")
    elif source_kind == "video":
        report.pass_("visual source; figures are required")

    plain = strip_body(body)
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-]*", plain)
    word_count = len(words)
    minutes = max(1, math.ceil(word_count / 220))
    if 1200 <= word_count <= 3500:
        report.pass_(f"{word_count} words, about {minutes} min")
    else:
        report.warn(f"{word_count} words; the target is 1200-3500 (about 6-16 min)")

    h2 = re.findall(r"^##\s+(.+)$", body, re.M)
    h3 = re.findall(r"^###\s+(.+)$", body, re.M)
    if len(h2) >= 3:
        report.pass_(f"{len(h2)} H2 sections, {len(h3)} H3")
    else:
        report.fail(f"only {len(h2)} H2 sections; use at least 3")
    generic = {"introduction", "conclusion", "overview", "background", "summary", "final thoughts"}
    for heading in h2:
        if heading.strip().lower() in generic:
            report.warn(f"generic heading: {heading!r}; make it a claim")
    if not any(re.search(r"break|limit|cost|trade|fail|wrong|miss|edge", h, re.I) for h in h2):
        report.warn("add a section about where the idea breaks, costs, or stops working")

    opener = first_paragraph(body)
    if opener:
        low = opener.lower()
        for phrase in BANNED_OPENINGS:
            if low.startswith(phrase):
                report.fail(f"opening starts with {phrase!r}; begin with a scene, number, or claim")
                break
        first_words = len(opener.split())
        if first_words > 160:
            report.warn(f"opening paragraph is {first_words} words; tighten to 60-120")
        if "video" in " ".join(opener.split()[:25]).lower():
            report.warn("the opening mentions the video early; make the idea the subject")
        report.pass_("opening paragraph present")
    else:
        report.fail("no opening paragraph")

    lowered = plain.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lowered:
            report.warn(f"banned phrase: {phrase!r}")
    for token in PLACEHOLDERS:
        if token.lower() in lowered:
            report.fail(f"unresolved placeholder: {token!r}")

    if body.count("{{<") != body.count(">}}"):
        report.fail("unbalanced shortcode delimiters")

    figures = figure_calls(body)
    if source_kind == "video" and len(figures) < 2:
        report.fail(f"{len(figures)} figures; a video essay needs at least 2 to show its evidence")
    elif not 2 <= len(figures) <= 8:
        report.warn(f"{len(figures)} figures; aim for 2-8")
    else:
        report.pass_(f"{len(figures)} figures")

    timestamped = 0
    seen_src: dict[str, int] = {}
    seen_hash: dict[str, int] = {}
    intro_words = (
        "figure", "frame", "diagram", "chart", "plot",
        "image", "screenshot", "photo", "table", "code",
    )
    generic_captions = {"screenshot", "image", "diagram", "frame", "figure", "a screenshot"}

    for index, (figure, position) in enumerate(figures, start=1):
        src = figure.get("src", "")
        alt = figure.get("alt", "")
        caption = figure.get("caption", "")
        if not src:
            report.fail(f"fig. {index}: missing src")
            continue
        if src in seen_src:
            report.fail(f"fig. {index}: duplicate src of fig. {seen_src[src]}")
        else:
            seen_src[src] = index
        if not alt:
            report.fail(f"fig. {index}: missing alt text")
        elif len(alt) < 8 or alt.lower().strip() in {"screenshot", "image", "frame"}:
            report.warn(f"fig. {index}: alt text is too vague")
        if not caption:
            report.warn(f"fig. {index}: missing caption")
        else:
            if re.search(r"\b\d{1,2}:\d{2}\b", caption):
                timestamped += 1
            if caption.lower().strip() in generic_captions:
                report.warn(f"fig. {index}: caption says what it is, not what to notice")
            if len(caption) > 220:
                report.warn(f"fig. {index}: caption is long; keep it under 220 characters")
        window = preceding_paragraph(body, position)
        if not any(word in window for word in intro_words):
            report.warn(f"fig. {index}: not introduced in the paragraph before it")
        if "://" in src:
            continue
        asset = resolve_asset(root, slug, src)
        if asset is None:
            report.fail(f"fig. {index}: asset not found for src={src!r}")
            continue
        if asset.stat().st_size < 5_000:
            report.warn(f"fig. {index}: {asset.name} is under 5 KB; check the crop")
        stats = image_stats(asset)
        if stats is None:
            continue
        width, height, mean, signature = stats
        if width and width < 600:
            report.warn(f"fig. {index}: only {width}px wide; use a larger source frame")
        if mean < 0.015:
            report.warn(f"fig. {index}: almost black (mean {mean:.3f}); check the timestamp")
        if width and height and (width / height > 3 or height / width > 3):
            report.warn(f"fig. {index}: extreme aspect ratio {width}x{height}")
        if signature in seen_hash:
            report.fail(f"fig. {index}: same image as fig. {seen_hash[signature]}")
        else:
            seen_hash[signature] = index

    if figures and timestamped < max(1, len(figures) // 2):
        report.warn("fewer than half of the captions carry a source timestamp")

    if figures:
        h2_positions = [(m.start(), m.group(1).strip()) for m in re.finditer(r"^##\s+(.+)$", body, re.M)]
        first_h2 = h2_positions[0][0] if h2_positions else None
        sections: list[str] = []
        for index, (_, position) in enumerate(figures, start=1):
            if first_h2 is not None and position < first_h2:
                report.warn(f"fig. {index}: appears before the first H2; check that the opening still leads")
            label = "opening"
            for h2_position, h2_label in h2_positions:
                if h2_position < position:
                    label = h2_label
            sections.append(label)
        if len(figures) >= 3 and len(set(sections)) == 1:
            report.warn("all figures sit in one section; distribute them across the argument")

    if args.scratch and source_kind == "video":
        plan = Path(args.scratch) / "figures.md"
        if not plan.is_file():
            report.fail(f"no visual review plan at {plan}; open the sheets and write figures.md")
        else:
            lines = plan.read_text(encoding="utf-8").splitlines()
            rows = [
                line
                for line in lines
                if re.search(r"\b\d{1,2}:\d{2}\b", line) and line.count("|") >= 2
            ]
            if len(rows) < len(figures):
                report.fail(
                    f"figures.md has {len(rows)} planned frames for {len(figures)} figures; "
                    "review more candidates or drop the extra figures"
                )
            else:
                report.pass_(f"visual review plan: {len(rows)} planned frames")
            for index, (figure, _) in enumerate(figures, start=1):
                stamp = re.search(r"\b\d{1,2}:\d{2}\b", figure.get("caption", ""))
                if stamp and stamp.group(0) not in plan.read_text(encoding="utf-8"):
                    report.warn(f"fig. {index}: timestamp {stamp.group(0)} is not in figures.md")

    if source_url and source_url not in body and "source" not in lowered:
        report.warn("add a source line at the end with the video URL")
    elif source_url:
        report.pass_("source line present")

    acronyms = []
    for match in re.finditer(r"\b[A-Z][A-Z0-9]{1,5}\b", plain):
        token = match.group(0)
        if token in COMMON_ACRONYMS or token in title:
            continue
        if token not in acronyms:
            acronyms.append(token)
    unexpanded = []
    for token in acronyms:
        first = plain.find(token)
        window = plain[first : first + 120]
        if "(" not in window:
            unexpanded.append(token)
    for token in unexpanded[:4]:
        report.warn(f"acronym {token!r} is not expanded on first use")

    sentences = re.split(r"(?<=[.!?])\s+", plain)
    long_sentences = [s for s in sentences if len(s.split()) > 55]
    for sentence in long_sentences[:3]:
        report.warn(f"long sentence ({len(sentence.split())} words): {sentence[:90]}...")

    data_path = root / "data" / "articles.yaml"
    if data_path.exists() and title:
        catalogue = data_path.read_text(encoding="utf-8")
        listed = title in catalogue
        if draft and not listed:
            report.warn("draft is not listed in data/articles.yaml; add a Drafting entry")
        if not draft and listed:
            report.warn("published title still appears in data/articles.yaml; remove the draft entry")

    for level in ("FAIL", "WARN", "PASS"):
        for kind, message in report.rows:
            if kind == level:
                print(f"{kind:<4}  {message}")

    failures = report.count("FAIL")
    warnings = report.count("WARN")
    print("")
    print(f"{failures} failures, {warnings} warnings, {report.count('PASS')} passes")
    if failures or (args.strict and warnings):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
