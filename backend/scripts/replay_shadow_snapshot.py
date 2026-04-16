"""
Replay a TradingPipeline shadow input snapshot (legacy vs SetupEngineV2) without live data.

This is a debug/engineering tool: it only consumes a serialized snapshot written under
`backend/results/debug/shadow_compare/` when `use_v2_shadow=true`.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from utils.shadow_comparator import replay_shadow_comparison_from_snapshot


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Remove volatile fields to compare two comparison payloads semantically.
    """
    p = json.loads(json.dumps(payload))  # deep copy via json
    p.pop("created_at_utc", None)
    p.pop("git_sha", None)

    def strip_ids(obj: Any) -> Any:
        if isinstance(obj, list):
            return [strip_ids(v) for v in obj]
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                if k == "id":
                    continue
                out[k] = strip_ids(v)
            return out
        return obj

    return strip_ids(p)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", required=True, help="Path to ShadowInputSnapshotV0 JSON")
    ap.add_argument("--label", default="replay", help="Label suffix for output file (token)")
    ap.add_argument("--out-dir", default=None, help="Optional output dir (default results/debug/shadow_compare)")
    ap.add_argument(
        "--compare-with",
        default=None,
        help="Optional baseline ShadowComparatorV0 JSON to compare (semantic, ignores volatile ids/timestamps).",
    )
    args = ap.parse_args()

    snapshot_path = Path(args.snapshot)
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

    base_dir = Path(args.out_dir) if args.out_dir else None
    wr = replay_shadow_comparison_from_snapshot(
        snapshot,
        snapshot_path=snapshot_path,
        label=args.label,
        base_dir=base_dir,
    )
    print(str(wr.path))

    if args.compare_with:
        baseline = json.loads(Path(args.compare_with).read_text(encoding="utf-8"))
        ok = _normalize_payload(baseline) == _normalize_payload(wr.payload)
        print(f"normalized_equal={ok}")
        return 0 if ok else 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
