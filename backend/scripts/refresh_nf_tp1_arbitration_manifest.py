#!/usr/bin/env python3
"""Écrit uniquement le manifest de complétude campagne arbitrage NF tp1 (scan disque)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.nf_tp1_arbitration_campaign import build_campaign_manifest

MINI_WEEK = backend_dir / "results" / "labs" / "mini_week"
DEFAULT_OUT = MINI_WEEK / "_nf_tp1_arbitration_campaign_manifest.json"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=str, default=str(DEFAULT_OUT))
    args = p.parse_args()
    out = Path(args.out)
    m = build_campaign_manifest(mini_week=MINI_WEEK)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(m, indent=2), encoding="utf-8")
    print(
        f"[manifest] {m['global_status']} complete={m['complete_pair_count']}/"
        f"{m['expected_pair_count']} -> {out}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
