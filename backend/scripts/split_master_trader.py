"""Split MASTER_FINAL.txt into 71 individual trader transcripts.

Standalone housekeeping script (Q0.2). Not imported by the bot runtime.

Separator format:
    ==============================
    VIDEO NNN — <title>
    ==============================
    <body>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "videos" / "trader" / "MASTER_FINAL.txt"
OUT_DIR = REPO_ROOT / "videos" / "trader"

HEADER_RE = re.compile(
    r"^=+\nVIDEO\s+(\d+)\s+—\s+(.+?)\n=+\n",
    re.MULTILINE,
)


def slugify(title: str) -> str:
    s = re.sub(r"[^\w\-]", "_", title.strip())
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:120] or "unknown"


def main() -> int:
    if not SOURCE.exists():
        print(f"ERROR: {SOURCE} not found", file=sys.stderr)
        return 1

    text = SOURCE.read_text(encoding="utf-8")

    matches = list(HEADER_RE.finditer(text))
    if not matches:
        print("ERROR: no VIDEO headers matched. Separator format may have changed.", file=sys.stderr)
        return 1

    print(f"Detected {len(matches)} video headers.")

    written = 0
    for i, m in enumerate(matches):
        num = int(m.group(1))
        title = m.group(2).strip()
        body_start = m.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()

        slug = slugify(title)
        filename = f"{num:03d}_{slug}.txt"
        out_path = OUT_DIR / filename

        header = f"VIDEO {num:03d} — {title}\n\n"
        out_path.write_text(header + body + "\n", encoding="utf-8")
        written += 1

    print(f"Wrote {written} transcripts to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
