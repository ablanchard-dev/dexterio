"""Fetch + transcribe YouTube quant videos into ~/Documents/videos/quant/.

Standalone script, not imported by the bot runtime. Idempotent: skips videos
that already have a transcript on disk.

Default path: YouTube auto-captions via youtube-transcript-api (fast, no audio
download, no Whisper). If a video has no captions, it is flagged in the manifest
with status='no_captions'; we do NOT fall back to Whisper automatically — that
would silently add heavy dependencies. Run `--whisper` to opt in.

Usage:
    python3 backend/scripts/fetch_quant_videos.py
    python3 backend/scripts/fetch_quant_videos.py --sources path/to/list.txt
    python3 backend/scripts/fetch_quant_videos.py --dry-run

Outputs:
    ~/Documents/videos/quant/<video_id>.txt         -- transcript (plain text, paragraphs)
    ~/Documents/videos/quant/<video_id>.meta.json   -- per-video metadata (title, url, captions_kind, length)
    ~/Documents/videos/quant/manifest.json          -- aggregated manifest
    ~/Documents/videos/QUANT_FINAL.txt              -- concat of all transcripts with headers
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        NoTranscriptFound,
        TranscriptsDisabled,
        VideoUnavailable,
    )
except ImportError:
    print("ERROR: youtube-transcript-api not installed. Run:", file=sys.stderr)
    print("  pip install youtube-transcript-api", file=sys.stderr)
    sys.exit(1)


DEFAULT_SOURCES = Path(__file__).resolve().parent.parent / "knowledge" / "quant_video_sources.txt"
DEFAULT_OUT = Path.home() / "Documents" / "videos"

_VIDEO_ID_RE = re.compile(r"(?:youtu\.be/|v=|/shorts/)([A-Za-z0-9_-]{11})")


def parse_sources(path: Path) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = _VIDEO_ID_RE.search(line)
        if not m:
            print(f"WARN: cannot parse video id from line: {line!r}", file=sys.stderr)
            continue
        vid = m.group(1)
        if vid in seen:
            continue
        seen.add(vid)
        ids.append(vid)
    return ids


def fetch_metadata(video_id: str) -> dict:
    """Use YouTube oEmbed to get title/author without API key."""
    url = f"https://www.youtube.com/oembed?url=https://youtu.be/{video_id}&format=json"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        return {
            "title": data.get("title", ""),
            "author": data.get("author_name", ""),
            "thumbnail_url": data.get("thumbnail_url", ""),
        }
    except Exception as exc:
        return {"title": "", "author": "", "error": str(exc)}


def fetch_transcript(video_id: str) -> tuple[Optional[str], dict]:
    """Return (text, info). text is None on failure; info always populated."""
    api = YouTubeTranscriptApi()
    try:
        tl = api.list(video_id)
    except TranscriptsDisabled:
        return None, {"status": "no_captions", "error": "TranscriptsDisabled"}
    except VideoUnavailable:
        return None, {"status": "unavailable", "error": "VideoUnavailable"}
    except Exception as exc:
        return None, {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

    # Prefer manual en, then auto en, then any translatable to en.
    candidates = list(tl)
    chosen = None
    for t in candidates:
        if t.language_code.startswith("en") and not t.is_generated:
            chosen = t
            break
    if chosen is None:
        for t in candidates:
            if t.language_code.startswith("en"):
                chosen = t
                break
    if chosen is None:
        for t in candidates:
            if t.is_translatable:
                try:
                    chosen = t.translate("en")
                    break
                except Exception:
                    continue
    if chosen is None:
        return None, {"status": "no_captions", "error": "no usable transcript"}

    try:
        fetched = chosen.fetch()
    except NoTranscriptFound as exc:
        return None, {"status": "no_captions", "error": f"NoTranscriptFound: {exc}"}
    except Exception as exc:
        return None, {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

    # FetchedTranscript is iterable of FetchedTranscriptSnippet.
    entries = list(fetched)
    lines = [e.text.strip() for e in entries if e.text.strip()]
    text = "\n".join(lines)
    duration = sum(e.duration for e in entries) if entries else 0
    info = {
        "status": "ok",
        "language_code": chosen.language_code,
        "is_generated": chosen.is_generated,
        "entries": len(entries),
        "duration_s": round(duration, 1),
    }
    return text, info


def build_final_concat(quant_dir: Path, manifest: dict) -> Path:
    out = quant_dir.parent / "QUANT_FINAL.txt"
    with out.open("w") as f:
        f.write(f"# QUANT_FINAL — concat of quant video transcripts\n")
        f.write(f"# Generated: {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"# Videos: {sum(1 for v in manifest['videos'] if v['status']=='ok')} ok / {len(manifest['videos'])} total\n\n")
        for v in manifest["videos"]:
            if v["status"] != "ok":
                continue
            txt_path = quant_dir / f"{v['id']}.txt"
            if not txt_path.exists():
                continue
            f.write(f"\n\n===== {v['id']} — {v.get('title','')} =====\n")
            f.write(f"URL: {v['url']}\n")
            f.write(f"Author: {v.get('author','')}\n")
            f.write(f"Duration: {v.get('duration_s', 0)}s · Captions: {v.get('language_code','')}{' (auto)' if v.get('is_generated') else ''}\n\n")
            f.write(txt_path.read_text())
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="re-transcribe even if cached")
    args = ap.parse_args()

    if not args.sources.exists():
        print(f"ERROR: sources file missing: {args.sources}", file=sys.stderr)
        return 2

    ids = parse_sources(args.sources)
    print(f"[fetch_quant] {len(ids)} unique video ids from {args.sources}")

    quant_dir = args.out / "quant"
    quant_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        for vid in ids:
            cached = (quant_dir / f"{vid}.txt").exists()
            print(f"  {vid}  {'CACHED' if cached else 'WOULD FETCH'}")
        return 0

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources_file": str(args.sources),
        "videos": [],
    }

    for i, vid in enumerate(ids, 1):
        txt_path = quant_dir / f"{vid}.txt"
        meta_path = quant_dir / f"{vid}.meta.json"
        url = f"https://youtu.be/{vid}"

        if txt_path.exists() and meta_path.exists() and not args.force:
            print(f"[{i}/{len(ids)}] {vid} CACHED")
            meta = json.loads(meta_path.read_text())
            manifest["videos"].append(meta)
            continue

        print(f"[{i}/{len(ids)}] {vid} fetching...")
        oembed = fetch_metadata(vid)
        text, info = fetch_transcript(vid)

        entry = {
            "id": vid,
            "url": url,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            **oembed,
            **info,
        }

        if text is not None:
            txt_path.write_text(text)
            print(f"    ok — {info['entries']} snippets, {info['duration_s']}s, {len(text)} chars")
        else:
            print(f"    FAIL — {info.get('error','unknown')}")

        meta_path.write_text(json.dumps(entry, indent=2))
        manifest["videos"].append(entry)

    manifest_path = quant_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"[fetch_quant] manifest: {manifest_path}")

    concat_path = build_final_concat(quant_dir, manifest)
    print(f"[fetch_quant] concat:   {concat_path}")

    ok = sum(1 for v in manifest["videos"] if v.get("status") == "ok")
    print(f"[fetch_quant] DONE: {ok}/{len(ids)} transcripts produced")
    return 0 if ok == len(ids) else 1


if __name__ == "__main__":
    sys.exit(main())
