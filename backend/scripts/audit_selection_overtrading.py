"""Audit selection and overtrading from debug_counts artifact."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description="Selection/overtrading audit")
    p.add_argument("--debug", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    payload = json.loads(Path(args.debug).read_text(encoding="utf-8"))
    c = payload.get("counts", payload)

    matches_total = int(c.get("matches_total", 0) or 0)
    setups_total = int(c.get("setups_created_total", 0) or 0)
    after_risk_total = int(c.get("setups_after_risk_filter_total", 0) or 0)
    opened_total = int(c.get("trades_opened_total", 0) or 0)

    def ratio(a: int, b: int) -> float:
        return (a / b) if b else 0.0

    top_traded = sorted(
        (c.get("trades_opened_by_playbook") or {}).items(),
        key=lambda kv: kv[1],
        reverse=True,
    )
    top_after_risk = sorted(
        (c.get("setups_after_risk_filter_by_playbook") or {}).items(),
        key=lambda kv: kv[1],
        reverse=True,
    )
    top_rejected_mode = sorted(
        (c.get("setups_rejected_by_mode_by_playbook") or {}).items(),
        key=lambda kv: kv[1],
        reverse=True,
    )

    out = {
        "run_id": payload.get("run_id"),
        "counts": {
            "playbooks_registered_count": c.get("playbooks_registered_count"),
            "matches_total": matches_total,
            "setups_created_total": setups_total,
            "setups_after_risk_filter_total": after_risk_total,
            "trades_opened_total": opened_total,
        },
        "funnel_ratios": {
            "match_to_setup": ratio(setups_total, matches_total),
            "setup_to_after_risk": ratio(after_risk_total, setups_total),
            "after_risk_to_trade": ratio(opened_total, after_risk_total),
            "match_to_trade": ratio(opened_total, matches_total),
        },
        "risk_snapshot": c.get("risk_allowlist_snapshot"),
        "blocked_by_per_minute_cap": c.get("blocked_by_per_minute_cap"),
        "top_traded_playbooks": top_traded[:10],
        "top_after_risk_playbooks": top_after_risk[:10],
        "top_rejected_by_mode_playbooks": top_rejected_mode[:10],
        "news_fade_selection": {
            "final_pool_count": c.get("news_fade_post_risk_final_pool_count"),
            "multi_setup_count": c.get("news_fade_post_risk_final_pool_multi_setup_count"),
            "won_count": c.get("news_fade_post_risk_won_final_selection_count"),
            "lost_count": c.get("news_fade_post_risk_lost_final_selection_count"),
            "lost_by_winner": c.get("news_fade_post_risk_lost_final_selection_by_winner"),
        },
    }

    outp = Path(args.output)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {outp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
