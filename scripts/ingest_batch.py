"""Ingest batch helper — pulls transcripts + metadata for a list of video IDs.

Writes raw_transcript.txt + metadata.json under
backend/knowledge/master_expansion_batch_01/videos/<video_id>/.

Usage:
    .venv/bin/python scripts/ingest_batch.py VID1 VID2 ...
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from youtube_transcript_api import YouTubeTranscriptApi

ROOT = Path("/home/dexter/dexterio1-main/backend/knowledge/master_expansion_batch_01/videos")


def ingest(video_id: str) -> dict:
    out_dir = ROOT / video_id
    out_dir.mkdir(parents=True, exist_ok=True)
    url = f"https://www.youtube.com/watch?v={video_id}"
    result = {"video_id": video_id, "url": url, "status": "pending"}

    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=["en", "fr"])
        snippets = fetched.snippets
        lines = [f"[{s.start:.2f}] {s.text}" for s in snippets]
        (out_dir / "raw_transcript.txt").write_text("\n".join(lines))

        duration = snippets[-1].start + snippets[-1].duration if snippets else 0
        metadata = {
            "video_id": video_id,
            "url": url,
            "language": str(fetched.language) if hasattr(fetched, "language") else "unknown",
            "language_code": str(fetched.language_code) if hasattr(fetched, "language_code") else "unknown",
            "is_generated": bool(fetched.is_generated) if hasattr(fetched, "is_generated") else None,
            "snippet_count": len(snippets),
            "duration_seconds": round(duration, 2),
            "duration_minutes": round(duration / 60.0, 2),
            "ingest_method": "youtube-transcript-api",
        }
        (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        result.update(metadata)
        result["status"] = "ok"
        return result
    except Exception as exc:
        result["api_error"] = f"{type(exc).__name__}: {exc}"

    # Fallback: yt-dlp subs
    try:
        cmd = [
            "yt-dlp", "--skip-download", "--write-auto-subs", "--write-subs",
            "--sub-langs", "en,fr", "--sub-format", "vtt/srt/best",
            "-o", str(out_dir / "%(id)s.%(ext)s"), url,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        vtt_files = list(out_dir.glob(f"{video_id}*.vtt")) + list(out_dir.glob(f"{video_id}*.srt"))
        if vtt_files:
            raw = vtt_files[0].read_text()
            (out_dir / "raw_transcript.txt").write_text(raw)
            metadata = {
                "video_id": video_id,
                "url": url,
                "ingest_method": "yt-dlp-fallback",
                "source_file": vtt_files[0].name,
                "bytes": len(raw),
            }
            (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
            result.update(metadata)
            result["status"] = "ok_fallback"
        else:
            result["status"] = "fail"
            result["ytdlp_stderr"] = proc.stderr[-500:]
    except Exception as exc2:
        result["status"] = "fail"
        result["ytdlp_error"] = f"{type(exc2).__name__}: {exc2}"

    return result


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: ingest_batch.py VID1 VID2 ...", file=sys.stderr)
        return 2
    results = [ingest(v) for v in sys.argv[1:]]
    print(json.dumps(results, indent=2))
    return 0 if all(r["status"].startswith("ok") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
