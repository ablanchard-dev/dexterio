"""Sprint perf: triage playbooks (quarantine vs shortlist) depuis leaderboard."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List
import yaml

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.path_resolver import results_path  # noqa: E402


def main() -> None:
    lb_file = results_path("playbooks_leaderboard_24m.json")
    if not lb_file.exists():
        raise FileNotFoundError(f"Leaderboard introuvable: {lb_file}")
    payload = json.loads(lb_file.read_text(encoding="utf-8"))
    rows: List[Dict[str, Any]] = payload.get("rows", [])

    quarantine = []
    shortlist = []
    watchlist = []
    for r in rows:
        trades = int(r.get("trades", 0) or 0)
        total_r = float(r.get("total_r_net", 0.0) or 0.0)
        wr = float(r.get("winrate", 0.0) or 0.0)
        pb = str(r.get("playbook", ""))
        if trades >= 25 and total_r <= -5.0:
            quarantine.append({"playbook": pb, "reason": "high_loss_r", "trades": trades, "total_r_net": total_r})
        elif trades >= 25 and total_r > -1.0 and wr >= 30.0:
            shortlist.append({"playbook": pb, "trades": trades, "total_r_net": total_r, "winrate": wr})
        else:
            watchlist.append({"playbook": pb, "trades": trades, "total_r_net": total_r, "winrate": wr})

    out = {
        "source": str(lb_file),
        "quarantine_count": len(quarantine),
        "shortlist_count": len(shortlist),
        "quarantine": quarantine,
        "shortlist": shortlist,
        "watchlist": watchlist[:20],
    }
    out_file = results_path("playbook_triage_recommendations.json")
    out_file.write_text(json.dumps(out, indent=2), encoding="utf-8")
    quarantine_file = backend_dir / "knowledge" / "playbook_quarantine.yaml"
    quarantine_payload = {
        "generated_from": str(lb_file),
        "quarantine": quarantine,
        "shortlist": shortlist,
    }
    quarantine_file.write_text(yaml.safe_dump(quarantine_payload, sort_keys=False), encoding="utf-8")
    print(f"[perf] playbook triage: {out_file}")
    print(f"[perf] quarantine file: {quarantine_file}")


if __name__ == "__main__":
    main()

