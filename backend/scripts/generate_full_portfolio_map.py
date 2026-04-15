#!/usr/bin/env python3
"""
Generate a repo-driven, executable FULL portfolio map for Dexterio.

Outputs:
  - backend/results/full_portfolio_map/full_portfolio_map.json  (source of truth)
  - backend/docs/FULL_PORTFOLIO_MAP.md                          (human-readable view)

Data sources (repo truth):
  - knowledge/playbooks.yml
  - knowledge/aplus_setups.yml
  - knowledge/playbooks_Aplus_from_transcripts.yaml
  - knowledge/campaigns/*.yml
  - engines/risk_engine.py (AGGRESSIVE_ALLOWLIST / AGGRESSIVE_DENYLIST)
  - knowledge/playbook_quarantine.yaml
  - results/**/run_manifest.json (+ playbooks_yaml linkage)
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml


SCHEMA_VERSION = "FullPortfolioMapV0"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _git_sha(repo_root: Path) -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo_root))
        return out.decode("utf-8").strip()
    except Exception:
        return "UNKNOWN"


def _read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _is_playbook_dict(x: Any) -> bool:
    return isinstance(x, dict) and isinstance(x.get("playbook_name"), str)


def _extract_playbook_names_from_playbooks_yaml(payload: Any) -> List[str]:
    if not isinstance(payload, list):
        return []
    out: List[str] = []
    for x in payload:
        if isinstance(x, dict) and x.get("playbook_name"):
            out.append(str(x["playbook_name"]))
    return out


def _extract_campaign_playbooks(campaign_path: Path) -> List[str]:
    try:
        payload = _read_yaml(campaign_path)
    except Exception:
        return []
    return _extract_playbook_names_from_playbooks_yaml(payload)


def _parse_string_list_assignment(py_path: Path, var_name: str) -> List[str]:
    """
    Parse a python file and extract an assignment like:
      VAR = ['a', 'b', ...]
    Only supports literal list/tuple of strings.
    """
    src = py_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(py_path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == var_name:
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        vals: List[str] = []
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                vals.append(elt.value)
                        return vals
    return []


def _infer_family(name: str, source: str) -> str:
    n = name.lower()
    if source in {"APLUS_BRANCHED", "APLUS_TRANSCRIPTS"}:
        # Keep A+ families explicit, users want both groups.
        return "A+"
    if "ifvg" in n or "fvg" in n:
        return "FVG / IFVG"
    if "ny" in n and ("reversal" in n or "trap" in n or "london" in n):
        return "NY / reversals"
    if "session" in n or "opening" in n or "open_" in n or "open" in n:
        return "Session / opening range"
    if "news" in n:
        return "News Fade"
    if "sweep" in n or "liquidity" in n:
        return "sweeps / liquidity"
    return "Other / uncategorized"


def _timeframe_compression_suspicion_for_core(pb: Dict[str, Any]) -> Tuple[str, str]:
    """
    Heuristic suspicion level for 5m/15m concept compressed into 1m logic.
    This is intentionally conservative: it provides a 'reason' string.
    """
    reasons: List[str] = []
    entry_tf = str(((pb.get("entry_logic") or {}).get("confirmation_tf")) or "").strip().lower()
    if entry_tf in {"5m", "15m"}:
        reasons.append(f"entry confirmation_tf={entry_tf}")
    ctx = pb.get("context_requirements") or {}
    if ctx.get("london_sweep_required"):
        reasons.append("requires London sweep (often HTF/session-structure driven)")
    if (pb.get("ict_confluences") or {}).get("require_sweep"):
        reasons.append("requires sweep (often 5m/15m structure)")
    if (pb.get("ict_confluences") or {}).get("require_bos"):
        reasons.append("requires BOS (structure mapping risk)")
    # If many context fields are set, it tends to be more HTF-conceptual.
    htf_bias_allowed = (ctx.get("htf_bias_allowed") or [])
    if isinstance(htf_bias_allowed, list) and htf_bias_allowed:
        reasons.append("uses HTF bias gates")

    if any("confirmation_tf=15m" in r for r in reasons) or any("requires London sweep" in r for r in reasons):
        return "high", "; ".join(reasons)
    if reasons:
        return "medium", "; ".join(reasons)
    return "low", "no obvious HTF/setup timeframe coupling detected in YAML"


def _timeframe_compression_suspicion_for_campaign_only(pb: Dict[str, Any]) -> Tuple[str, str]:
    req = pb.get("required_signals") or []
    req_s = ",".join(req) if isinstance(req, list) else str(req)
    if "15m" in req_s.lower():
        return "medium", f"required_signals={req_s}"
    if "5m" in req_s.lower():
        return "low", f"required_signals={req_s} (setup explicitly on 5m)"
    entry_tf = str(((pb.get("entry_logic") or {}).get("confirmation_tf")) or "").strip().lower()
    if entry_tf in {"5m", "15m"}:
        return "low", f"entry confirmation_tf={entry_tf} (setup explicitly not 1m-only)"
    return "medium", "campaign-only playbook with unclear conceptual timeframe beyond 1m execution"


def _timeframe_compression_suspicion_for_aplus_transcripts(playbook_id: str, payload: Dict[str, Any]) -> Tuple[str, str]:
    tfs = (((payload.get("timeframes") or {}) or {}).get("setup")) or []
    entry = (((payload.get("timeframes") or {}) or {}).get("entry")) or []
    if isinstance(tfs, list) and any(str(x).lower() in {"15m", "5m"} for x in tfs):
        return "high", f"transcript setup timeframes={tfs}, entry={entry}"
    return "medium", f"transcript timeframes={payload.get('timeframes')}"


@dataclass
class EvidenceRun:
    path: str
    output_parent: str
    label: str
    runner: str
    start_date: str
    end_date: str
    git_sha: str
    kind: str  # e.g. mini_lab_week / walk_forward_parent


def _scan_results_for_evidence(backend_dir: Path, campaign_playbooks_by_file: Dict[str, List[str]]) -> Dict[str, List[EvidenceRun]]:
    """
    Evidence is derived from run_manifest.json files which point to playbooks_yaml.
    For each run with playbooks_yaml, attribute that run as evidence for each playbook in that YAML.
    """
    out: Dict[str, List[EvidenceRun]] = {}
    results_dir = backend_dir / "results"
    if not results_dir.exists():
        return out

    manifests = list(results_dir.rglob("run_manifest.json"))
    for mpath in manifests:
        try:
            manifest = _read_json(mpath)
        except Exception:
            continue
        playbooks_yaml = manifest.get("playbooks_yaml")
        if not playbooks_yaml:
            continue
        try:
            # Normalize to a short-ish repo-relative display when possible
            pb_path = Path(str(playbooks_yaml))
            if pb_path.is_absolute():
                try:
                    playbooks_yaml_rel = str(pb_path.relative_to(backend_dir))
                except Exception:
                    playbooks_yaml_rel = str(pb_path)
            else:
                playbooks_yaml_rel = str(pb_path)
        except Exception:
            playbooks_yaml_rel = str(playbooks_yaml)

        playbooks = campaign_playbooks_by_file.get(playbooks_yaml_rel)
        if not playbooks:
            # If YAML file is outside the known campaign set, try loading it anyway.
            pb_path2 = (backend_dir / playbooks_yaml_rel) if not Path(playbooks_yaml_rel).is_absolute() else Path(playbooks_yaml_rel)
            if pb_path2.exists():
                playbooks = _extract_campaign_playbooks(pb_path2)
            else:
                playbooks = []

        # Deduce output_parent + label from path when nested mini_week layout:
        # results/labs/mini_week/<output_parent>/<label>/run_manifest.json
        parts = mpath.parts
        output_parent = ""
        label = ""
        try:
            # find "mini_week" segment
            if "mini_week" in parts:
                i = parts.index("mini_week")
                # Nested: .../mini_week/<output_parent>/<label>/run_manifest.json
                if len(parts) > i + 3 and parts[i + 3] == "run_manifest.json":
                    output_parent = parts[i + 1]
                    label = parts[i + 2]
                # Flat: .../mini_week/<label>/run_manifest.json
                elif len(parts) > i + 2 and parts[i + 2] == "run_manifest.json":
                    output_parent = parts[i + 1]
                    label = parts[i + 1]
        except Exception:
            output_parent = manifest.get("output_parent") or ""
            label = manifest.get("label") or ""

        ev = EvidenceRun(
            path=str(mpath.parent),
            output_parent=str(output_parent),
            label=str(label),
            runner=str(manifest.get("runner") or ""),
            start_date=str(manifest.get("start_date") or ""),
            end_date=str(manifest.get("end_date") or ""),
            git_sha=str(manifest.get("git_sha") or ""),
            kind="mini_lab_run",
        )

        for pb_name in playbooks:
            out.setdefault(pb_name, []).append(ev)

    # Add parent-level walk_forward info where available
    mini_week = results_dir / "labs" / "mini_week"
    if mini_week.exists():
        for wf_path in mini_week.glob("*/walk_forward_campaign.json"):
            try:
                output_parent = wf_path.parent.name
            except Exception:
                continue
            # We attach this as evidence to all playbooks present in any run under that output_parent.
            # This keeps the map simple and avoids parsing internal WF json schema variants.
            child_manifests = list((wf_path.parent).rglob("run_manifest.json"))
            playbooks_seen: set[str] = set()
            for mpath in child_manifests:
                try:
                    manifest = _read_json(mpath)
                except Exception:
                    continue
                pb_yaml = manifest.get("playbooks_yaml")
                if not pb_yaml:
                    continue
                pb_path = Path(str(pb_yaml))
                if pb_path.is_absolute():
                    try:
                        pb_yaml_rel = str(pb_path.relative_to(backend_dir))
                    except Exception:
                        pb_yaml_rel = str(pb_path)
                else:
                    pb_yaml_rel = str(pb_path)
                for pb_name in campaign_playbooks_by_file.get(pb_yaml_rel, []):
                    playbooks_seen.add(pb_name)
            for pb_name in playbooks_seen:
                out.setdefault(pb_name, []).append(
                    EvidenceRun(
                        path=str(wf_path.parent),
                        output_parent=output_parent,
                        label="(parent)",
                        runner="walk_forward_campaign.json",
                        start_date="",
                        end_date="",
                        git_sha="",
                        kind="walk_forward_parent",
                    )
                )

    return out


def _product_status(
    *,
    source: str,
    policy: str,
    loader_loaded: bool,
    in_quarantine: bool,
) -> str:
    if source == "APLUS_TRANSCRIPTS":
        return "research-only"
    if policy == "denylist":
        return "blocked by deny"
    if source == "CAMPAIGN_ONLY":
        return "FULL runnable via --playbooks-yaml"
    if loader_loaded and policy == "allowlist":
        if in_quarantine:
            return "FULL runnable (quarantined / needs revalidation)"
        return "FULL runnable"
    if loader_loaded and policy == "neither":
        return "loaded but not mapped in policy (needs decision)"
    if not loader_loaded:
        return "not loaded (needs wiring)"
    return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate FULL executable portfolio map (JSON + MD)")
    ap.add_argument("--backend-dir", default=".")
    ap.add_argument("--json-out", default="results/full_portfolio_map/full_portfolio_map.json")
    ap.add_argument("--md-out", default="docs/FULL_PORTFOLIO_MAP.md")
    args = ap.parse_args()

    backend_dir = Path(args.backend_dir).resolve()
    repo_root = backend_dir.parent
    git_sha = _git_sha(repo_root)

    # Sources
    playbooks_yml = backend_dir / "knowledge" / "playbooks.yml"
    aplus_yml = backend_dir / "knowledge" / "aplus_setups.yml"
    transcripts_yml = backend_dir / "knowledge" / "playbooks_Aplus_from_transcripts.yaml"
    quarantine_yml = backend_dir / "knowledge" / "playbook_quarantine.yaml"
    campaigns_dir = backend_dir / "knowledge" / "campaigns"
    risk_engine_py = backend_dir / "engines" / "risk_engine.py"

    core_payload = _read_yaml(playbooks_yml) or []
    core_playbooks: Dict[str, Dict[str, Any]] = {
        str(x["playbook_name"]): x for x in core_payload if _is_playbook_dict(x)
    }

    aplus_payload = _read_yaml(aplus_yml) or {}
    aplus_branch_names: List[str] = []
    if isinstance(aplus_payload, dict):
        for k in ("day_setups", "scalp_setups"):
            items = aplus_payload.get(k) or []
            if isinstance(items, list):
                for it in items:
                    if isinstance(it, dict) and it.get("name"):
                        aplus_branch_names.append(str(it["name"]))

    transcripts_payload = _read_yaml(transcripts_yml) or {}
    transcripts_playbooks: Dict[str, Dict[str, Any]] = {}
    if isinstance(transcripts_payload, dict):
        for it in (transcripts_payload.get("playbooks") or []):
            if isinstance(it, dict) and it.get("id"):
                transcripts_playbooks[str(it["id"])] = it

    quarantine_payload = _read_yaml(quarantine_yml) or {}
    quarantine_set: set[str] = set()
    quarantine_reasons: Dict[str, str] = {}
    if isinstance(quarantine_payload, dict):
        for it in quarantine_payload.get("quarantine") or []:
            if isinstance(it, dict) and it.get("playbook"):
                name = str(it["playbook"])
                quarantine_set.add(name)
                quarantine_reasons[name] = str(it.get("reason") or "")

    aggressive_allow = _parse_string_list_assignment(risk_engine_py, "AGGRESSIVE_ALLOWLIST")
    aggressive_deny = _parse_string_list_assignment(risk_engine_py, "AGGRESSIVE_DENYLIST")
    allow_set = set(aggressive_allow)
    deny_set = set(aggressive_deny)

    # Campaigns
    campaigns_by_file: Dict[str, List[str]] = {}
    campaigns_by_playbook: Dict[str, List[str]] = {}
    if campaigns_dir.exists():
        for cpath in sorted(campaigns_dir.glob("*.yml")):
            rel = str(cpath.relative_to(backend_dir))
            names = _extract_campaign_playbooks(cpath)
            campaigns_by_file[rel] = names
            for n in names:
                campaigns_by_playbook.setdefault(n, []).append(rel)

    # Identify campaign-only playbooks (declared in campaigns but not in core or A+ branched)
    campaign_only_names = sorted(
        set(campaigns_by_playbook.keys()) - set(core_playbooks.keys()) - set(aplus_branch_names)
    )

    # Evidence from results/ (runs + output_parents)
    evidence_by_playbook = _scan_results_for_evidence(backend_dir, campaigns_by_file)

    # Build unified list of candidates
    items: List[Dict[str, Any]] = []

    # CORE
    for name, pb in sorted(core_playbooks.items(), key=lambda kv: kv[0]):
        source = "CORE"
        policy = "allowlist" if name in allow_set else "denylist" if name in deny_set else "neither"
        family = _infer_family(name, source)
        loader_loaded = True
        in_quarantine = name in quarantine_set
        suspicion_level, suspicion_reason = _timeframe_compression_suspicion_for_core(pb)
        items.append(
            {
                "name": name,
                "family": family,
                "source": source,
                "source_files": ["knowledge/playbooks.yml"],
                "loader_loaded": loader_loaded,
                "policy_runtime": policy,
                "in_quarantine_yaml": in_quarantine,
                "quarantine_reason": quarantine_reasons.get(name),
                "product_status": _product_status(
                    source=source,
                    policy=policy,
                    loader_loaded=loader_loaded,
                    in_quarantine=in_quarantine,
                ),
                "campaign_yamls": sorted(campaigns_by_playbook.get(name) or []),
                "evidence_runs": [ev.__dict__ for ev in (evidence_by_playbook.get(name) or [])],
                "timeframe_compression_suspicion": {
                    "level": suspicion_level,
                    "reason": suspicion_reason,
                },
            }
        )

    # A+ branched
    for name in sorted(set(aplus_branch_names)):
        source = "APLUS_BRANCHED"
        policy = "allowlist" if name in allow_set else "denylist" if name in deny_set else "neither"
        family = "A+ branchés"
        loader_loaded = True
        in_quarantine = name in quarantine_set
        # Most A+ setups explicitly reference M5/M15 in their schema -> assume high suspicion.
        suspicion_level = "high"
        suspicion_reason = "A+ setup schema includes HTF/setup timeframes (see aplus_setups.yml); execution likely 1m"
        items.append(
            {
                "name": name,
                "family": family,
                "source": source,
                "source_files": ["knowledge/aplus_setups.yml"],
                "loader_loaded": loader_loaded,
                "policy_runtime": policy,
                "in_quarantine_yaml": in_quarantine,
                "quarantine_reason": quarantine_reasons.get(name),
                "product_status": _product_status(
                    source=source,
                    policy=policy,
                    loader_loaded=loader_loaded,
                    in_quarantine=in_quarantine,
                ),
                "campaign_yamls": sorted(campaigns_by_playbook.get(name) or []),
                "evidence_runs": [ev.__dict__ for ev in (evidence_by_playbook.get(name) or [])],
                "timeframe_compression_suspicion": {
                    "level": suspicion_level,
                    "reason": suspicion_reason,
                },
            }
        )

    # Campaign-only
    for name in campaign_only_names:
        source = "CAMPAIGN_ONLY"
        policy = "allowlist" if name in allow_set else "denylist" if name in deny_set else "neither"
        family = _infer_family(name, source)
        loader_loaded = False
        in_quarantine = name in quarantine_set
        # Find a representative playbook dict from the first campaign that declares it
        rep_pb: Dict[str, Any] = {}
        for cfile in campaigns_by_playbook.get(name) or []:
            cpath = backend_dir / cfile
            payload = _read_yaml(cpath) or []
            if isinstance(payload, list):
                for it in payload:
                    if isinstance(it, dict) and it.get("playbook_name") == name:
                        rep_pb = it
                        break
            if rep_pb:
                break
        suspicion_level, suspicion_reason = _timeframe_compression_suspicion_for_campaign_only(rep_pb or {})
        items.append(
            {
                "name": name,
                "family": family,
                "source": source,
                "source_files": sorted(set(campaigns_by_playbook.get(name) or [])),
                "loader_loaded": loader_loaded,
                "policy_runtime": policy,
                "in_quarantine_yaml": in_quarantine,
                "quarantine_reason": quarantine_reasons.get(name),
                "product_status": _product_status(
                    source=source,
                    policy=policy,
                    loader_loaded=loader_loaded,
                    in_quarantine=in_quarantine,
                ),
                "campaign_yamls": sorted(campaigns_by_playbook.get(name) or []),
                "evidence_runs": [ev.__dict__ for ev in (evidence_by_playbook.get(name) or [])],
                "timeframe_compression_suspicion": {
                    "level": suspicion_level,
                    "reason": suspicion_reason,
                },
            }
        )

    # A+ transcripts (research-only)
    for pid, pb in sorted(transcripts_playbooks.items(), key=lambda kv: kv[0]):
        name = str(pid)
        source = "APLUS_TRANSCRIPTS"
        family = "A+ transcripts research-only"
        loader_loaded = False
        policy = "n/a"
        in_quarantine = False
        suspicion_level, suspicion_reason = _timeframe_compression_suspicion_for_aplus_transcripts(pid, pb)
        items.append(
            {
                "name": name,
                "display_name": str(pb.get("name") or ""),
                "family": family,
                "source": source,
                "source_files": ["knowledge/playbooks_Aplus_from_transcripts.yaml"],
                "loader_loaded": loader_loaded,
                "policy_runtime": policy,
                "in_quarantine_yaml": in_quarantine,
                "quarantine_reason": None,
                "product_status": _product_status(
                    source=source,
                    policy="neither",
                    loader_loaded=loader_loaded,
                    in_quarantine=in_quarantine,
                ),
                "campaign_yamls": [],
                "evidence_runs": [],
                "timeframe_compression_suspicion": {
                    "level": suspicion_level,
                    "reason": suspicion_reason,
                },
                "transcript_timeframes": pb.get("timeframes"),
                "transcript_universe": pb.get("universe"),
            }
        )

    # Families rollup
    families: Dict[str, Dict[str, Any]] = {}
    for it in items:
        fam = str(it.get("family") or "Unknown")
        families.setdefault(
            fam,
            {
                "family": fam,
                "counts": {"total": 0},
                "by_status": {},
                "playbooks": [],
            },
        )
        families[fam]["counts"]["total"] += 1
        st = str(it.get("product_status") or "unknown")
        families[fam]["by_status"][st] = families[fam]["by_status"].get(st, 0) + 1
        families[fam]["playbooks"].append(it["name"])
    # Sort family playbook lists
    for fam in families.values():
        fam["playbooks"] = sorted(set(fam["playbooks"]))

    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": _utc_now_iso(),
        "git_sha": git_sha,
        "sources": {
            "knowledge_playbooks_yml": "knowledge/playbooks.yml",
            "knowledge_aplus_setups_yml": "knowledge/aplus_setups.yml",
            "knowledge_transcripts_yml": "knowledge/playbooks_Aplus_from_transcripts.yaml",
            "knowledge_campaigns_dir": "knowledge/campaigns/",
            "risk_engine_py": "engines/risk_engine.py",
            "knowledge_quarantine_yml": "knowledge/playbook_quarantine.yaml",
            "results_dir": "results/",
        },
        "policy_runtime": {
            "aggressive_allowlist": aggressive_allow,
            "aggressive_denylist": aggressive_deny,
        },
        "families": dict(sorted(families.items(), key=lambda kv: kv[0])),
        "playbooks": items,
        "notes": [
            "policy_runtime is derived from engines/risk_engine.py list literals (no code execution).",
            "evidence_runs is derived from results/**/run_manifest.json playbooks_yaml linkage; runs without playbooks_yaml are ignored.",
            "APLUS_TRANSCRIPTS entries are keyed by transcript 'id' (not a runtime playbook_name).",
        ],
    }

    json_out = backend_dir / args.json_out
    md_out = backend_dir / args.md_out
    _ensure_dir(json_out.parent)
    _ensure_dir(md_out.parent)
    json_out.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")

    # Markdown view (compact, diffable)
    def _md_escape(s: str) -> str:
        return s.replace("|", "\\|")

    lines: List[str] = []
    lines.append("# FULL Portfolio Map (Repo-Driven)")
    lines.append("")
    lines.append(f"- Schema: `{SCHEMA_VERSION}`")
    lines.append(f"- Generated at (UTC): `{payload['generated_at_utc']}`")
    lines.append(f"- Git SHA: `{git_sha}`")
    lines.append("")
    lines.append("## Regenerate")
    lines.append("```bash")
    lines.append("cd /home/dexter/dexterio1-main/backend")
    lines.append(".venv/bin/python scripts/generate_full_portfolio_map.py")
    lines.append("```")
    lines.append("")
    lines.append("## Policy Runtime (AGGRESSIVE)")
    lines.append("")
    lines.append(f"- Allowlist: {', '.join(aggressive_allow)}")
    lines.append(f"- Denylist: {', '.join(aggressive_deny)}")
    lines.append("")
    lines.append("## Families (Rollup)")
    lines.append("")
    lines.append("| Family | Total | Status Breakdown |")
    lines.append("|---|---:|---|")
    for fam_name, fam in payload["families"].items():
        bd = ", ".join([f"{k}={v}" for k, v in sorted(fam.get("by_status", {}).items())])
        lines.append(f"| {_md_escape(fam_name)} | {fam['counts']['total']} | {_md_escape(bd)} |")
    lines.append("")
    lines.append("## Playbooks / Candidates (Detail)")
    lines.append("")
    lines.append("| Name | Family | Source | Loader | Policy | Quarantine | Status | Campaign YAMLs | Evidence (results/) | TF Suspicion |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for it in sorted(payload["playbooks"], key=lambda x: (x.get("family") or "", x.get("name") or "")):
        name = str(it.get("name") or "")
        fam = str(it.get("family") or "")
        src = str(it.get("source") or "")
        loader = "yes" if it.get("loader_loaded") else "no"
        pol = str(it.get("policy_runtime") or "")
        q = "yes" if it.get("in_quarantine_yaml") else "no"
        status = str(it.get("product_status") or "")
        camps = ", ".join(it.get("campaign_yamls") or [])
        # Evidence: show output_parents + labels only (keep diff-friendly)
        evs = it.get("evidence_runs") or []
        ev_short = []
        for ev in evs:
            if ev.get("kind") == "mini_lab_run":
                ev_short.append(
                    f"{ev.get('output_parent')}/{ev.get('label')}@{(ev.get('git_sha') or '')[:7]}"
                )
            elif ev.get("kind") == "walk_forward_parent":
                ev_short.append(f"{ev.get('output_parent')}/(WF)")
        ev_s = ", ".join(sorted(set(ev_short)))
        tf = it.get("timeframe_compression_suspicion") or {}
        tf_s = f"{tf.get('level')}" if tf else ""
        lines.append(
            "| "
            + " | ".join(
                [
                    _md_escape(name),
                    _md_escape(fam),
                    _md_escape(src),
                    loader,
                    _md_escape(pol),
                    q,
                    _md_escape(status),
                    _md_escape(camps),
                    _md_escape(ev_s),
                    _md_escape(tf_s),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("## Notes")
    for n in payload["notes"]:
        lines.append(f"- {_md_escape(str(n))}")
    lines.append("")

    md_out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {json_out}")
    print(f"wrote {md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
