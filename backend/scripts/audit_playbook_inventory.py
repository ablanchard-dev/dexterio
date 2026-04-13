"""Audit playbooks: intention vs runtime across debug_counts artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
import yaml


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _counts(payload: dict[str, Any]) -> dict[str, Any]:
    c = payload.get("counts")
    return c if isinstance(c, dict) else payload


def _load_source_playbooks(base: Path) -> dict[str, list[str]]:
    kb = base / "knowledge"
    playbooks_yml = yaml.safe_load((kb / "playbooks.yml").read_text(encoding="utf-8")) or []
    aplus = yaml.safe_load((kb / "aplus_setups.yml").read_text(encoding="utf-8")) or {}

    core_names = [x.get("playbook_name") for x in playbooks_yml if isinstance(x, dict) and x.get("playbook_name")]
    day_ap = [x.get("name") for x in (aplus.get("day_setups") or []) if isinstance(x, dict) and x.get("name")]
    scalp_ap = [x.get("name") for x in (aplus.get("scalp_setups") or []) if isinstance(x, dict) and x.get("name")]

    return {
        "core": core_names,
        "aplus": day_ap + scalp_ap,
        "all": core_names + day_ap + scalp_ap,
    }


def _to_set(d: dict[str, Any], key: str) -> set[str]:
    v = d.get(key, {})
    if isinstance(v, dict):
        return set(v.keys())
    if isinstance(v, list):
        return set(x for x in v if isinstance(x, str))
    return set()


def main() -> int:
    p = argparse.ArgumentParser(description="Audit intention vs runtime playbooks")
    p.add_argument("--backend-dir", default=".")
    p.add_argument("--runtime-debug", required=True)
    p.add_argument("--reference-debug", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    backend = Path(args.backend_dir).resolve()
    runtime = _counts(_load_json(Path(args.runtime_debug)))
    ref = _counts(_load_json(Path(args.reference_debug)))
    src = _load_source_playbooks(backend)

    runtime_registered = set(runtime.get("playbooks_registered_names") or [])
    ref_registered = set(ref.get("playbooks_registered_names") or [])
    source_registered = set(src["all"])

    runtime_match = _to_set(runtime, "matches_by_playbook")
    runtime_setup = _to_set(runtime, "setups_created_by_playbook")
    runtime_after_risk = _to_set(runtime, "setups_after_risk_filter_by_playbook")
    runtime_traded = _to_set(runtime, "trades_opened_by_playbook")

    missing_vs_reference = sorted(ref_registered - runtime_registered)
    missing_vs_source = sorted(source_registered - runtime_registered)
    orphan_runtime = sorted(runtime_registered - source_registered)

    out = {
        "runtime_file": str(Path(args.runtime_debug)),
        "reference_file": str(Path(args.reference_debug)),
        "source_counts": {
            "core": len(src["core"]),
            "aplus": len(src["aplus"]),
            "total": len(src["all"]),
        },
        "runtime_counts": {
            "playbooks_registered_count": runtime.get("playbooks_registered_count"),
            "matches_total": runtime.get("matches_total"),
            "setups_created_total": runtime.get("setups_created_total"),
            "setups_after_risk_filter_total": runtime.get("setups_after_risk_filter_total"),
            "trades_opened_total": runtime.get("trades_opened_total"),
        },
        "reference_counts": {
            "playbooks_registered_count": ref.get("playbooks_registered_count"),
            "matches_total": ref.get("matches_total"),
            "setups_created_total": ref.get("setups_created_total"),
            "setups_after_risk_filter_total": ref.get("setups_after_risk_filter_total"),
            "trades_opened_total": ref.get("trades_opened_total"),
        },
        "missing_vs_reference": missing_vs_reference,
        "missing_vs_source": missing_vs_source,
        "orphan_runtime_not_in_source": orphan_runtime,
        "funnel_sets": {
            "registered": sorted(runtime_registered),
            "matched": sorted(runtime_match),
            "setup_created": sorted(runtime_setup),
            "after_risk": sorted(runtime_after_risk),
            "traded": sorted(runtime_traded),
        },
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
