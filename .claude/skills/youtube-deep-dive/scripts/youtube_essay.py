#!/usr/bin/env python3
"""Fetch a YouTube talk, clean its captions, and extract reviewable stills.

Stdlib only. Requires yt-dlp and ffmpeg on PATH.

Commands
  fetch URL --out DIR [--lang en] [--whisper]
  frames DIR [--every 8] [--scene 0.35] [--max 200]
  still DIR --time 12:34 --out assets/images/think/slug/fig-01.jpg
  probe DIR
"""

from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import math
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

YTDLP = shutil.which("yt-dlp") or "yt-dlp"
FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = shutil.which("ffprobe") or "ffprobe"


# ---------------------------------------------------------------- utilities


def die(message: str, code: int = 1) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def run(cmd: list[str], *, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    if not capture:
        print("$ " + " ".join(shlex.quote(str(c)) for c in cmd), file=sys.stderr)
    try:
        return subprocess.run(
            [str(c) for c in cmd],
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
            text=True,
            check=check,
        )
    except FileNotFoundError:
        die(f"{cmd[0]} is not installed. Try: brew install yt-dlp ffmpeg")
    except subprocess.CalledProcessError as exc:
        if capture and exc.stderr:
            print(exc.stderr.strip()[-2000:], file=sys.stderr)
        die(f"command failed: {cmd[0]}")


def parse_time(value: str | float | int) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    value = str(value).strip()
    if not value:
        die("empty time")
    parts = value.split(":")
    try:
        numbers = [float(p) for p in parts]
    except ValueError:
        die(f"bad time: {value!r} (use 12:34 or 1:02:03)")
    if len(numbers) == 1:
        return numbers[0]
    if len(numbers) == 2:
        return numbers[0] * 60 + numbers[1]
    if len(numbers) == 3:
        return numbers[0] * 3600 + numbers[1] * 60 + numbers[2]
    die(f"bad time: {value!r}")


def fmt_time(seconds: float) -> str:
    seconds = max(0, int(round(seconds)))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def stamp(seconds: float) -> str:
    """Filename-safe HH-MM-SS-mmm."""
    ms = int(round((seconds - math.floor(seconds)) * 1000))
    total = int(math.floor(seconds))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}-{m:02d}-{s:02d}-{ms:03d}"


def probe_duration(path: Path) -> float:
    res = run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture=True,
    )
    data = json.loads(res.stdout or "{}")
    return float(data.get("format", {}).get("duration") or 0)


def probe_size(path: Path) -> tuple[int, int]:
    res = run(
        [
            FFPROBE,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(path),
        ],
        capture=True,
    )
    data = json.loads(res.stdout or "{}")
    streams = data.get("streams") or [{}]
    return int(streams[0].get("width") or 0), int(streams[0].get("height") or 0)


def read_source(out: Path) -> dict:
    path = out / "source.json"
    if not path.exists():
        die(f"{path} not found; run fetch first")
    return json.loads(path.read_text(encoding="utf-8"))


VIDEO_SUFFIXES = {".mp4", ".mkv", ".webm", ".mov", ".m4v"}


def existing_video(out: Path) -> Path | None:
    source_path = out / "source.json"
    if source_path.exists():
        try:
            name = json.loads(source_path.read_text(encoding="utf-8")).get("video") or ""
        except json.JSONDecodeError:
            name = ""
        if name and (out / name).is_file():
            return out / name
    candidates = [p for p in out.glob("video.*") if p.suffix.lower() in VIDEO_SUFFIXES]
    return sorted(candidates)[0] if candidates else None


def find_video(out: Path) -> Path:
    video = existing_video(out)
    if video is None:
        die(f"no video file in {out}")
    return video


def choose_language(info: dict, override: str | None) -> tuple[str | None, bool]:
    manual = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}

    if override:
        if override in manual:
            return override, False
        if override in auto:
            return override, True

    def pick(table: dict) -> str | None:
        if not table:
            return None
        for code in ("en", "en-US", "en-GB", "en-orig", "en-en"):
            if code in table:
                return code
        for code in table:
            if code.lower().startswith("en"):
                return code
        return next(iter(table), None)

    manual_lang = pick(manual)
    if manual_lang:
        return manual_lang, False
    auto_lang = pick(auto)
    if auto_lang:
        return auto_lang, True
    return None, False


def pick_vtt(out: Path, lang: str | None) -> Path | None:
    vtts = sorted(out.glob("video*.vtt"))
    if not vtts:
        return None
    if lang:
        exact = [p for p in vtts if f".{lang}." in p.name or p.name.endswith(f".{lang}.vtt")]
        if exact:
            return exact[0]
    english = [p for p in vtts if ".en" in p.name]
    if english:
        return english[0]
    return vtts[0]


# ---------------------------------------------------------------- captions


def vtt_seconds(value: str) -> float:
    value = value.strip().replace(",", ".")
    parts = value.split(":")
    try:
        numbers = [float(p) for p in parts]
    except ValueError:
        return 0.0
    if len(numbers) == 3:
        return numbers[0] * 3600 + numbers[1] * 60 + numbers[2]
    if len(numbers) == 2:
        return numbers[0] * 60 + numbers[1]
    return numbers[0] if numbers else 0.0


def parse_vtt(path: Path) -> list[tuple[float, str]]:
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    cues: list[tuple[float, str]] = []
    for block in re.split(r"\n\s*\n", raw):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines or lines[0].upper().startswith("WEBVTT"):
            continue
        timing = next((line for line in lines if "-->" in line), None)
        if not timing:
            continue
        start_raw = timing.split("-->", 1)[0].strip().split()[0]
        payload = lines[lines.index(timing) + 1 :]
        text = " ".join(payload)
        text = re.sub(r"<[^>]+>", "", text)
        text = html.unescape(text)
        text = text.replace("\u200b", "").replace("\ufeff", "")
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\[(?:music|applause|laughter|silence)\]", "", text, flags=re.I)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            cues.append((vtt_seconds(start_raw), text))
    return cues


def norm_word(word: str) -> str:
    return re.sub(r"[^\w']", "", word.lower())


def overlap_length(acc: list[str], new: list[str], cap: int = 24) -> int:
    limit = min(len(acc), len(new), cap)
    for size in range(limit, 0, -1):
        if acc[-size:] == new[:size]:
            return size
    return 0


def clean_transcript(cues: list[tuple[float, str]]) -> list[dict]:
    """Remove rolling-caption repeats and group into timestamped blocks."""
    blocks: list[dict] = []
    acc_words: list[str] = []
    acc_norm: list[str] = []
    context_norm: list[str] = []
    block_start: float | None = None

    def flush() -> None:
        nonlocal acc_words, acc_norm, context_norm, block_start
        text = " ".join(acc_words).strip()
        text = re.sub(r"\s+([,.;:!?])", r"\1", text)
        text = re.sub(r"\s{2,}", " ", text)
        if text:
            blocks.append(
                {
                    "seconds": round(block_start or 0, 2),
                    "time": fmt_time(block_start or 0),
                    "text": text,
                }
            )
            context_norm = acc_norm[-24:]
        acc_words = []
        acc_norm = []
        block_start = None

    previous_seconds: float | None = None
    for seconds, text in cues:
        new_words = text.split()
        new_norm = [norm_word(w) for w in new_words]
        new_norm = [w for w in new_norm if w]
        if not new_norm:
            continue

        if (
            acc_norm
            and previous_seconds is not None
            and seconds - previous_seconds > 3.0
            and overlap_length(acc_norm, new_norm) < 2
        ):
            flush()

        if acc_norm:
            overlap = overlap_length(acc_norm, new_norm)
            new_words = new_words[overlap:]
            new_norm = new_norm[overlap:]
        elif context_norm:
            overlap = overlap_length(context_norm, new_norm)
            if overlap >= 2:
                new_words = new_words[overlap:]
                new_norm = new_norm[overlap:]
        if not new_norm:
            previous_seconds = seconds
            continue
        if block_start is None:
            block_start = seconds
        acc_words.extend(new_words)
        acc_norm.extend(new_norm)

        if len(" ".join(acc_words)) > 700:
            flush()
        previous_seconds = seconds

    flush()
    return blocks


def write_transcript(out: Path, info: dict, blocks: list[dict], lang: str, auto: bool) -> None:
    title = info.get("title") or "Untitled"
    channel = info.get("uploader") or info.get("channel") or ""
    duration = info.get("duration") or 0
    kind = "auto" if auto else "manual"

    header = [
        f"# {title}",
        "",
        f"- Source: {info.get('webpage_url') or info.get('original_url') or info.get('url') or ''}",
        f"- Channel: {channel}",
        f"- Duration: {fmt_time(duration)}",
        f"- Captions: {kind} {lang}",
        "",
        "Transcript blocks are timestamped for locating frames. Verify names and numbers.",
        "",
        "---",
        "",
    ]
    body_lines: list[str] = []
    for block in blocks:
        body_lines.append(f"[{block['time']}]")
        body_lines.append(block["text"])
        body_lines.append("")

    (out / "transcript.md").write_text("\n".join(header + body_lines).rstrip() + "\n", encoding="utf-8")
    (out / "transcript.txt").write_text("\n\n".join(b["text"] for b in blocks) + "\n", encoding="utf-8")
    (out / "transcript.json").write_text(
        json.dumps(blocks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def description_chapters(description: str) -> list[dict]:
    if not description:
        return []
    chapters: list[dict] = []
    for line in description.splitlines():
        match = re.match(r"^\s*[\[(]?(\d{1,2}:\d{2}(?::\d{2})?)[\])]?\s*[-–—:]?\s*(.+?)\s*$", line)
        if match:
            chapters.append({"start_time": parse_time(match.group(1)), "title": match.group(2)})
    return chapters


def write_outline(out: Path, info: dict, lang: str, auto: bool) -> None:
    chapters = info.get("chapters") or description_chapters(info.get("description") or "")
    lines = [
        f"# {info.get('title') or 'Untitled'}",
        "",
        f"- URL: {info.get('webpage_url') or info.get('original_url') or info.get('url') or ''}",
        f"- Channel: {info.get('uploader') or info.get('channel') or ''}",
        f"- Duration: {fmt_time(info.get('duration') or 0)}",
        f"- Uploaded: {info.get('upload_date') or 'unknown'}",
        f"- Captions: {'auto' if auto else 'manual'} {lang}",
        "",
        "## Chapters",
        "",
    ]
    if chapters:
        for chapter in chapters:
            start = chapter.get("start_time") or 0
            lines.append(f"- [{fmt_time(start)}] {chapter.get('title') or 'Untitled'}")
    else:
        lines.append("_No chapter markers in the source. Read transcript.md for the structure._")
    lines.append("")
    (out / "outline.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------- fetch


def try_whisper(video: Path, out: Path, lang: str | None, model: str) -> Path | None:
    whisper = shutil.which("whisper")
    if whisper:
        cmd = [whisper, str(video), "--model", model, "--output_format", "vtt", "--output_dir", str(out)]
    else:
        uvx = shutil.which("uvx")
        if not uvx:
            return None
        cmd = [
            uvx,
            "--from",
            "openai-whisper",
            "whisper",
            str(video),
            "--model",
            model,
            "--output_format",
            "vtt",
            "--output_dir",
            str(out),
        ]
    if lang:
        cmd.extend(["--language", lang])
    print("No captions found; running Whisper. This can take a while.", file=sys.stderr)
    run(cmd)
    return pick_vtt(out, lang)


def cmd_fetch(args: argparse.Namespace) -> None:
    for binary in (YTDLP, FFMPEG):
        if not shutil.which(binary) and not Path(binary).exists():
            die(f"{binary} is not installed. Try: brew install yt-dlp ffmpeg")

    url = args.url
    print("Reading video metadata ...", file=sys.stderr)
    info_res = run(
        [
            YTDLP,
            "--dump-single-json",
            "--no-warnings",
            "--skip-download",
            "--no-playlist",
            url,
        ],
        capture=True,
    )
    try:
        info = json.loads(info_res.stdout)
    except json.JSONDecodeError:
        die("yt-dlp did not return JSON; is the URL valid and public?")

    video_id = info.get("id") or "video"
    out = Path(args.out) if args.out else Path(".cache/youtube") / video_id
    out.mkdir(parents=True, exist_ok=True)

    lang, auto = choose_language(info, args.lang)
    if args.lang and lang and lang != args.lang:
        print(f"warning: {args.lang!r} captions are not available; using {lang!r}", file=sys.stderr)
    if args.lang and lang is None:
        die(f"no captions in language {args.lang!r} and no fallback captions")

    video = existing_video(out)
    if args.force or video is None:
        fmt = args.format or (
            "bv*[height<=1080][vcodec^=avc1]+ba[acodec^=mp4a]/"
            "bv*[height<=1080]+ba/b[height<=1080]/b"
        )
        cmd = [
            YTDLP,
            "--no-playlist",
            "--no-warnings",
            "--newline",
            "--retries",
            "3",
            "--fragment-retries",
            "3",
            "--concurrent-fragments",
            "4",
            "-f",
            fmt,
            "--merge-output-format",
            "mp4",
            "-o",
            str(out / "video.%(ext)s"),
            "--write-info-json",
            "--convert-subs",
            "vtt",
        ]
        if lang:
            if auto:
                cmd += ["--write-auto-subs", "--sub-langs", lang]
            else:
                cmd += ["--write-subs", "--sub-langs", lang]
        cmd.append(url)
        run(cmd)
    else:
        print(f"Reusing {video}", file=sys.stderr)

    video = find_video(out)
    vtt = pick_vtt(out, lang)
    if vtt is None and args.whisper:
        vtt = try_whisper(video, out, args.lang, args.whisper_model)
        if vtt is not None:
            lang = lang or "en"
            auto = True

    if vtt is not None:
        canonical = out / "subtitles.vtt"
        if vtt != canonical:
            shutil.copyfile(vtt, canonical)
        vtt = canonical

    source = {
        "id": video_id,
        "url": info.get("webpage_url") or url,
        "title": info.get("title") or "Untitled",
        "channel": info.get("uploader") or info.get("channel") or "",
        "duration": info.get("duration") or probe_duration(video),
        "upload_date": info.get("upload_date") or "",
        "description": info.get("description") or "",
        "chapters": info.get("chapters") or description_chapters(info.get("description") or ""),
        "video": video.name,
        "subtitles": vtt.name if vtt else "",
        "language": lang or "",
        "auto_captions": auto,
        "thumbnail": info.get("thumbnail") or "",
    }
    (out / "source.json").write_text(
        json.dumps(source, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    if vtt is None:
        print("", file=sys.stderr)
        print("No captions were downloaded. The video cannot be turned into an essay yet.", file=sys.stderr)
        print("Options:", file=sys.stderr)
        print("  1. Re-run with --whisper (local OpenAI Whisper; slow, downloads a model).", file=sys.stderr)
        print("  2. Re-run with --whisper-model small to trade accuracy for speed.", file=sys.stderr)
        print("  3. Check whether the video has captions enabled on YouTube.", file=sys.stderr)
        raise SystemExit(3)

    blocks = clean_transcript(parse_vtt(vtt))
    write_transcript(out, source, blocks, lang or "unknown", auto)
    write_outline(out, source, lang or "unknown", auto)

    print("", file=sys.stderr)
    print(f"scratch:    {out.resolve()}", file=sys.stderr)
    print(f"video:      {video.name} ({fmt_time(source['duration'])})", file=sys.stderr)
    print(f"captions:   {vtt.name} ({'auto' if auto else 'manual'} {lang})", file=sys.stderr)
    print(f"transcript: {len(blocks)} blocks, {sum(len(b['text'].split()) for b in blocks)} words", file=sys.stderr)
    print(f"outline:    {out / 'outline.md'}", file=sys.stderr)
    print(f"next:       python3 {Path(__file__).name} frames {out} --every 8", file=sys.stderr)


# ---------------------------------------------------------------- frames


def scene_times(video: Path, threshold: float, start: float, end: float) -> list[float]:
    print(f"Detecting scene changes (threshold {threshold}) ...", file=sys.stderr)
    cmd = [
        FFMPEG,
        "-hide_banner",
        "-nostats",
        "-i",
        str(video),
        "-an",
        "-vf",
        f"scale=320:-2,select='gt(scene,{threshold})',showinfo",
        "-f",
        "null",
        "-",
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    times = [float(m) for m in re.findall(r"pts_time:([0-9.]+)", res.stderr or "")]
    times = [t for t in times if start <= t <= end]
    print(f"  {len(times)} scene changes", file=sys.stderr)
    return times


VISUAL_CUES = (
    "as you can see",
    "you can see",
    "look at",
    "look here",
    "over here",
    "right here",
    "this diagram",
    "this chart",
    "this graph",
    "this plot",
    "this table",
    "this code",
    "this slide",
    "on the slide",
    "on screen",
    "what you're seeing",
    "what you are seeing",
    "let me show",
    "i'll show",
    "notice that",
    "notice how",
    "picture this",
    "imagine this",
    "this is what",
    "here's what",
    "here is what",
    "the picture",
    "the figure",
    "the visualization",
    "the animation",
)


def cue_times(out: Path, start: float, end: float) -> tuple[list[float], int]:
    """Timestamps where the speaker points at something or a chapter opens."""
    times: list[float] = []
    hits = 0
    transcript = out / "transcript.json"
    if transcript.exists():
        blocks = json.loads(transcript.read_text(encoding="utf-8"))
        for block in blocks:
            text = (block.get("text") or "").lower()
            if any(cue in text for cue in VISUAL_CUES):
                base = float(block.get("seconds") or 0)
                for offset in (1.0, 3.0):
                    t = base + offset
                    if start <= t <= end:
                        times.append(t)
                hits += 1
    source = read_source(out)
    for chapter in source.get("chapters") or []:
        t = float(chapter.get("start_time") or 0) + 1.5
        if start <= t <= end:
            times.append(t)
    return times, hits


def cap_times(times: list[float], maximum: int) -> list[float]:
    if len(times) <= maximum:
        return times
    if maximum == 1:
        return [times[0]]
    indexes = {round(i * (len(times) - 1) / (maximum - 1)) for i in range(maximum)}
    return [times[i] for i in sorted(indexes)]


def montage_sheet(files: list[Path], sheet: Path) -> bool:
    montage = shutil.which("montage")
    if not montage:
        return False
    columns = min(4, len(files))
    rows = max(1, math.ceil(len(files) / 4))
    cmd = [
        montage,
        "-background",
        "#f6f4ee",
        "-fill",
        "#17191d",
        "-pointsize",
        "14",
        "-label",
        "%t",
    ]
    font = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
    if font.exists():
        cmd += ["-font", str(font)]
    cmd += [str(p) for p in files]
    cmd += ["-tile", f"{columns}x{rows}", "-geometry", "360x203+6+6", "-quality", "88", str(sheet)]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(res.stderr.strip()[-800:], file=sys.stderr)
        return False
    return True


def cmd_frames(args: argparse.Namespace) -> None:
    out = Path(args.dir)
    video = find_video(out)
    duration = probe_duration(video)
    start = max(0.5, args.start or 0.5)
    end = min(duration - 0.5, args.end or duration - 0.5)
    if end <= start:
        die("empty time range")

    times: list[float] = []
    if args.every > 0:
        t = start
        while t < end:
            times.append(t)
            t += args.every
    if args.scene > 0:
        times.extend(scene_times(video, args.scene, start, end))
    if not args.no_cues:
        cues, hits = cue_times(out, start, end)
        times.extend(cues)
        print(f"  {hits} visual-cue lines, {len(cues)} candidate moments", file=sys.stderr)

    times = sorted(t for t in times if start <= t <= end)
    deduped: list[float] = []
    for t in times:
        if not deduped or t - deduped[-1] >= args.min_gap:
            deduped.append(t)
    times = cap_times(deduped, args.max)
    if not times:
        die("no candidate frames; try a larger --every or a lower --scene threshold")

    frames_dir = out / "frames"
    sheets_dir = out / "sheets"
    if frames_dir.exists():
        for old in frames_dir.glob("cand-*.jpg"):
            old.unlink()
    frames_dir.mkdir(parents=True, exist_ok=True)
    sheets_dir.mkdir(parents=True, exist_ok=True)
    for old in sheets_dir.glob("sheet-*"):
        old.unlink()

    def extract(t: float) -> tuple[float, Path]:
        path = frames_dir / f"cand-{stamp(t)}.jpg"
        cmd = [
            FFMPEG,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{t:.3f}",
            "-i",
            str(video),
            "-frames:v",
            "1",
            "-vf",
            "scale=720:-2",
            "-q:v",
            "4",
            str(path),
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        return t, path

    print(f"Extracting {len(times)} candidate frames ...", file=sys.stderr)
    extracted: list[tuple[float, Path]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for index, (t, path) in enumerate(pool.map(extract, times), start=1):
            if path.exists():
                extracted.append((t, path))
            if index % 20 == 0 or index == len(times):
                print(f"  {index}/{len(times)}", file=sys.stderr)

    extracted.sort(key=lambda pair: pair[0])
    sheets: list[dict] = []
    chunk_size = 20
    for index in range(0, len(extracted), chunk_size):
        chunk = extracted[index : index + chunk_size]
        sheet = sheets_dir / f"sheet-{len(sheets) + 1:02d}.jpg"
        ok = montage_sheet([p for _, p in chunk], sheet)
        sheets.append(
            {
                "file": sheet.name if ok else "",
                "items": [
                    {"time": fmt_time(t), "seconds": round(t, 2), "file": p.name}
                    for t, p in chunk
                ],
            }
        )
        if ok:
            print(f"  sheet {sheet.name} ({len(chunk)} frames)", file=sys.stderr)

    manifest = {
        "duration": fmt_time(duration),
        "candidates": [
            {"time": fmt_time(t), "seconds": round(t, 2), "file": p.name}
            for t, p in extracted
        ],
        "sheets": sheets,
        "has_contact_sheets": any(s["file"] for s in sheets),
    }
    (out / "frames" / "index.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print("", file=sys.stderr)
    print(f"candidates: {len(extracted)} in {frames_dir}", file=sys.stderr)
    if manifest["has_contact_sheets"]:
        print(f"sheets:     {len(sheets)} in {sheets_dir} (open in order)", file=sys.stderr)
    else:
        print("sheets:     ImageMagick montage not found; review frames individually", file=sys.stderr)
    print(f"next:       python3 {Path(__file__).name} still {out} --time MM:SS --out assets/images/think/<slug>/fig-01.jpg", file=sys.stderr)


# ---------------------------------------------------------------- still


def cmd_still(args: argparse.Namespace) -> None:
    out = Path(args.dir)
    video = find_video(out)
    seconds = parse_time(args.time)
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)

    filters: list[str] = []
    if args.crop:
        parts = re.split(r"[:x, ]+", args.crop.strip())
        if len(parts) != 4:
            die("--crop must be W:H:X:Y")
        w, h, x, y = parts
        filters.append(f"crop={w}:{h}:{x}:{y}")
    if args.width:
        filters.append(f"scale='min({args.width},iw)':-2")
    vf = ",".join(filters) if filters else "null"

    cmd = [
        FFMPEG,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{seconds:.3f}",
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-vf",
        vf,
    ]
    if target.suffix.lower() in {".jpg", ".jpeg"}:
        cmd += ["-q:v", str(args.quality)]
    cmd.append(str(target))
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, check=True)

    width, height = probe_size(target)
    result = {
        "path": str(target.resolve()),
        "time": fmt_time(seconds),
        "seconds": round(seconds, 3),
        "width": width,
        "height": height,
        "bytes": target.stat().st_size,
    }
    print(json.dumps(result, indent=2))


def cmd_probe(args: argparse.Namespace) -> None:
    out = Path(args.dir)
    source = read_source(out)
    video = find_video(out)
    width, height = probe_size(video)
    result = dict(source)
    result.update(
        {
            "video_bytes": video.stat().st_size,
            "width": width,
            "height": height,
            "transcript_blocks": len(json.loads((out / "transcript.json").read_text(encoding="utf-8")))
            if (out / "transcript.json").exists()
            else 0,
            "candidates": len(json.loads((out / "frames" / "index.json").read_text(encoding="utf-8")).get("candidates", []))
            if (out / "frames" / "index.json").exists()
            else 0,
        }
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------- cli


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    fetch = sub.add_parser("fetch", help="download video, captions, and clean transcript")
    fetch.add_argument("url")
    fetch.add_argument("--out", default="", help="scratch directory (default .cache/youtube/<id>)")
    fetch.add_argument("--lang", default="", help="caption language code, e.g. en")
    fetch.add_argument("--format", default="", help="yt-dlp format selector override")
    fetch.add_argument("--force", action="store_true", help="re-download even if the video exists")
    fetch.add_argument("--whisper", action="store_true", help="transcribe locally if no captions exist")
    fetch.add_argument("--whisper-model", default="small", help="Whisper model size (default small)")
    fetch.set_defaults(func=cmd_fetch)

    frames = sub.add_parser("frames", help="extract candidate stills and contact sheets")
    frames.add_argument("dir")
    frames.add_argument("--every", type=float, default=8.0, help="seconds between samples (0 disables)")
    frames.add_argument("--scene", type=float, default=0.35, help="scene-change threshold (0 disables)")
    frames.add_argument("--start", type=float, default=0.0)
    frames.add_argument("--end", type=float, default=0.0)
    frames.add_argument("--min-gap", type=float, default=2.0)
    frames.add_argument("--max", type=int, default=200)
    frames.add_argument("--no-cues", action="store_true", help="skip transcript visual-cue sampling")
    frames.add_argument("--jobs", type=int, default=4)
    frames.set_defaults(func=cmd_frames)

    still = sub.add_parser("still", help="extract one full-quality frame")
    still.add_argument("dir")
    still.add_argument("--time", required=True, help="12:34 or 1:02:03")
    still.add_argument("--out", required=True)
    still.add_argument("--width", type=int, default=1600)
    still.add_argument("--crop", default="", help="W:H:X:Y before scaling")
    still.add_argument("--quality", type=int, default=3, help="JPEG quality 2-5 (2 is best)")
    still.set_defaults(func=cmd_still)

    probe = sub.add_parser("probe", help="show source, transcript, and frame counts")
    probe.add_argument("dir")
    probe.set_defaults(func=cmd_probe)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
