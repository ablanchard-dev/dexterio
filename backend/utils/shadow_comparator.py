"""
Shadow comparator between TradingPipeline legacy setup selection and SetupEngineV2.

Design constraints:
- Non-blocking: failures must never affect legacy output.
- Repo-driven: write artefacts under backend/results/ (ignored by git by default).
- No migration: legacy remains the executing path; V2 is shadow-only.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from models.market_data import MarketState
from models.setup import Setup, PlaybookMatch, PatternDetection, CandlestickPattern
from utils.path_resolver import results_path, repo_root


_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,120}$")


def _safe_token(name: str, value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    v = value.strip()
    if not v:
        return None
    if not _TOKEN_RE.match(v):
        raise ValueError(f"Invalid {name}: {value!r} (allowed: [A-Za-z0-9][A-Za-z0-9_.-]{{0,120}})")
    return v


def _git_sha_short() -> Optional[str]:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root()),
            capture_output=True,
            text=True,
            timeout=2.0,
        )
        if proc.returncode != 0:
            return None
        s = (proc.stdout or "").strip()
        return s or None
    except Exception:
        return None


def candlestick_patterns_from_legacy_detections(detections: Sequence[PatternDetection]) -> list[CandlestickPattern]:
    """
    Minimal adapter: TradingPipeline legacy candlestick engine returns PatternDetection,
    while SetupEngineV2 expects CandlestickPattern.
    """
    out: list[CandlestickPattern] = []
    for p in detections:
        pt = (p.pattern_type or "").lower()
        if "bullish" in pt:
            direction = "bullish"
        elif "bearish" in pt:
            direction = "bearish"
        else:
            direction = "neutral"

        strength = float(getattr(p, "pattern_score", 0.0) or 0.0)
        out.append(
            CandlestickPattern(
                family=p.pattern_name,
                name=p.pattern_name,
                direction=direction,
                timeframe=p.timeframe,
                timestamp=p.timestamp,
                strength=strength,
                body_size=0.0,
                confirmation=(p.strength == "strong"),
                at_level=bool(getattr(p, "at_support_resistance", False) or getattr(p, "at_htf_level", False)),
                after_sweep=bool(getattr(p, "after_sweep", False)),
            )
        )
    return out


def _summarize_playbook_matches(matches: Sequence[PlaybookMatch]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in matches:
        out.append(
            {
                "playbook_name": getattr(m, "playbook_name", None),
                "confidence": getattr(m, "confidence", None),
                "matched_conditions": list(getattr(m, "matched_conditions", []) or []),
            }
        )
    return out


def _summarize_setup(setup: Setup) -> dict[str, Any]:
    return {
        "id": setup.id,
        "timestamp": setup.timestamp.isoformat() if setup.timestamp else None,
        "symbol": setup.symbol,
        "direction": setup.direction,
        "trade_type": setup.trade_type,
        "quality": setup.quality,
        "final_score": float(setup.final_score),
        "match_score": setup.match_score,
        "match_grade": setup.match_grade,
        "playbook_name": getattr(setup, "playbook_name", "") or "",
        "playbook_matches": _summarize_playbook_matches(list(setup.playbook_matches or [])),
        "entry_price": setup.entry_price,
        "stop_loss": setup.stop_loss,
        "take_profit_1": setup.take_profit_1,
        "take_profit_2": setup.take_profit_2,
        "risk_reward": setup.risk_reward,
        "market_bias": setup.market_bias,
        "session": setup.session,
        "confluences_count": setup.confluences_count,
        "notes": setup.notes,
    }


def _policy_eval_for_setup(*, setup: Setup, is_playbook_allowed) -> dict[str, Any]:
    evaluated: list[dict[str, Any]] = []
    allowed_all = True
    blocked_reason = None

    for m in list(setup.playbook_matches or []):
        name = getattr(m, "playbook_name", None)
        if not name:
            continue
        allowed, reason = is_playbook_allowed(name)
        evaluated.append({"playbook_name": name, "allowed": bool(allowed), "reason": reason})
        if not allowed and allowed_all:
            allowed_all = False
            blocked_reason = {"playbook_name": name, "reason": reason}

    return {
        "allowed": bool(allowed_all),
        "blocked_first": blocked_reason,
        "evaluated": evaluated,
    }


def _best_setup(setups: Sequence[Setup]) -> Optional[Setup]:
    if not setups:
        return None
    return max(setups, key=lambda s: float(getattr(s, "final_score", 0.0) or 0.0))


def build_shadow_comparison_payload(
    *,
    symbol: str,
    analysis_time: datetime,
    trading_mode: str,
    market_state: MarketState,
    current_price: float,
    legacy_raw: Optional[Setup],
    legacy_final: Sequence[Setup],
    v2_raw: Sequence[Setup],
    v2_final: Sequence[Setup],
    v2_error: Optional[str],
    counts: dict[str, Any],
    is_playbook_allowed,
) -> dict[str, Any]:
    legacy_raw_policy = (
        _policy_eval_for_setup(setup=legacy_raw, is_playbook_allowed=is_playbook_allowed) if legacy_raw else None
    )
    legacy_best = _best_setup(list(legacy_final))
    v2_best_raw = _best_setup(list(v2_raw))
    v2_best = _best_setup(list(v2_final))

    legacy_policy = _policy_eval_for_setup(setup=legacy_best, is_playbook_allowed=is_playbook_allowed) if legacy_best else None
    v2_policy_raw = _policy_eval_for_setup(setup=v2_best_raw, is_playbook_allowed=is_playbook_allowed) if v2_best_raw else None
    v2_policy = _policy_eval_for_setup(setup=v2_best, is_playbook_allowed=is_playbook_allowed) if v2_best else None

    divergence_reasons: list[str] = []
    if bool(legacy_best) != bool(v2_best):
        if legacy_best and not v2_best:
            divergence_reasons.append("v2_missing_final_setup")
        elif v2_best and not legacy_best:
            divergence_reasons.append("legacy_missing_final_setup")
        if v2_best_raw and not v2_best:
            divergence_reasons.append("v2_filtered_or_blocked")
    else:
        if legacy_best and v2_best:
            if legacy_best.direction != v2_best.direction:
                divergence_reasons.append("direction_mismatch")
            if legacy_best.quality != v2_best.quality:
                divergence_reasons.append("grade_mismatch")
            legacy_pbs = {m.get("playbook_name") for m in _summarize_playbook_matches(list(legacy_best.playbook_matches or []))}
            v2_pbs = {m.get("playbook_name") for m in _summarize_playbook_matches(list(v2_best.playbook_matches or []))}
            if legacy_pbs != v2_pbs:
                divergence_reasons.append("playbook_matches_mismatch")

    return {
        "schema_version": "ShadowComparatorV0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_time_utc": analysis_time.astimezone(timezone.utc).isoformat(),
        "git_sha": _git_sha_short(),
        "symbol": symbol,
        "trading_mode": trading_mode,
        "current_price": float(current_price),
        "counts": counts,
        "market_state": {
            "bias": market_state.bias,
            "current_session": market_state.current_session,
            "day_type": getattr(market_state, "day_type", "unknown"),
            "daily_structure": getattr(market_state, "daily_structure", "unknown"),
            "h4_structure": getattr(market_state, "h4_structure", "unknown"),
            "h1_structure": getattr(market_state, "h1_structure", "unknown"),
            "volatility": getattr(market_state, "volatility", None),
        },
        "legacy": {
            "raw": _summarize_setup(legacy_raw) if legacy_raw else None,
            "policy_raw": legacy_raw_policy,
            "final_setups": [_summarize_setup(s) for s in list(legacy_final)],
            "best_final": _summarize_setup(legacy_best) if legacy_best else None,
            "policy_best_final": legacy_policy,
        },
        "v2_shadow": {
            "error": v2_error,
            "best_raw": _summarize_setup(v2_best_raw) if v2_best_raw else None,
            "policy_best_raw": v2_policy_raw,
            "raw_setups": [_summarize_setup(s) for s in list(v2_raw)],
            "final_setups": [_summarize_setup(s) for s in list(v2_final)],
            "best_final": _summarize_setup(v2_best) if v2_best else None,
            "policy_best_final": v2_policy,
        },
        "diff": {
            "divergence_reasons": divergence_reasons,
        },
    }


@dataclass(frozen=True)
class ShadowWriteResult:
    path: Path
    payload: dict[str, Any]


def write_shadow_comparison(
    payload: dict[str, Any],
    *,
    symbol: str,
    analysis_time: datetime,
    label: Optional[str] = None,
    base_dir: Optional[Path] = None,
) -> ShadowWriteResult:
    safe_label = _safe_token("shadow_label", label)
    ts = analysis_time.astimezone(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = safe_label or "auto"
    filename = f"shadow_compare_{symbol}_{ts}_{suffix}.json"

    out_dir = base_dir if base_dir is not None else results_path("debug", "shadow_compare")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return ShadowWriteResult(path=path, payload=payload)
