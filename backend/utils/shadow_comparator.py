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
import hashlib
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Sequence

from models.market_data import MarketState
from models.setup import Setup, PlaybookMatch, PatternDetection, CandlestickPattern, ICTPattern
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


def _jsonable(obj: Any) -> Any:
    """
    Best-effort conversion to JSON-serializable Python objects.
    Keeps this module dependency-light (no custom encoders).
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, datetime):
        return obj.astimezone(timezone.utc).isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            # Fall back to a plain dict view if possible.
            try:
                return dict(obj)
            except Exception:
                return str(obj)
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_jsonable(v) for v in obj]
    return str(obj)


def _strip_ids(obj: Any) -> Any:
    """
    Remove volatile ids from nested dicts/lists to build stable fingerprints.
    """
    if isinstance(obj, list):
        return [_strip_ids(v) for v in obj]
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if k == "id":
                continue
            out[str(k)] = _strip_ids(v)
        return out
    return obj


def _sha256_canonical_json(obj: Any) -> str:
    dumped = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


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


def _dump_playbook_matches_raw(matches: Sequence[Any]) -> list[dict[str, Any]]:
    """
    Snapshot-friendly dumping for legacy PlaybookEngine matches.

    Note: `models.setup.PlaybookMatch` currently only stores a small subset of fields
    (playbook_name/confidence/matched_conditions). We dump the model as-is to stay
    consistent with what `TradingPipeline` actually sees today.
    """
    out: list[dict[str, Any]] = []
    for m in list(matches or []):
        if hasattr(m, "model_dump"):
            out.append(m.model_dump(mode="json"))
        elif isinstance(m, dict):
            out.append(_jsonable(m))
        else:
            out.append({"playbook_name": getattr(m, "playbook_name", None)})
    return out


def _dump_patterns_raw(patterns: Sequence[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in list(patterns or []):
        if hasattr(p, "model_dump"):
            out.append(p.model_dump(mode="json"))
        elif isinstance(p, dict):
            out.append(_jsonable(p))
        else:
            out.append({"pattern_type": getattr(p, "pattern_type", None), "timeframe": getattr(p, "timeframe", None)})
    return out


def _dump_liquidity_levels_raw(levels: Sequence[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for lvl in list(levels or []):
        if hasattr(lvl, "model_dump"):
            row = lvl.model_dump(mode="json")
            # sweep_details may include non-JSONable types; sanitize defensively.
            if isinstance(row, dict) and row.get("sweep_details") is not None:
                row["sweep_details"] = _jsonable(row.get("sweep_details"))
            out.append(row)
        elif isinstance(lvl, dict):
            out.append(_jsonable(lvl))
        else:
            out.append({"price": getattr(lvl, "price", None), "level_type": getattr(lvl, "level_type", None)})
    return out


def build_shadow_input_snapshot_payload(
    *,
    symbol: str,
    analysis_time: datetime,
    trading_mode: str,
    risk_engine_mode: str,
    current_price: float,
    market_state: MarketState,
    ict_patterns: Sequence[ICTPattern],
    candlestick_patterns: Sequence[PatternDetection],
    liquidity_levels: Sequence[Any],
    swept_levels: Sequence[Any],
    playbook_matches: Sequence[Any],
    policy_context: dict[str, Any],
) -> dict[str, Any]:
    core = {
        "symbol": symbol,
        "analysis_time_utc": analysis_time.astimezone(timezone.utc).isoformat(),
        "trading_mode": trading_mode,
        "risk_engine_mode": risk_engine_mode,
        "current_price": float(current_price),
        "market_state": market_state.model_dump(mode="json"),
        "ict_patterns": _dump_patterns_raw(ict_patterns),
        "candlestick_patterns": _dump_patterns_raw(candlestick_patterns),
        "liquidity_levels": _dump_liquidity_levels_raw(liquidity_levels),
        "swept_levels": _dump_liquidity_levels_raw(swept_levels),
        "playbook_matches": _dump_playbook_matches_raw(playbook_matches),
        "policy_context": _jsonable(policy_context),
    }
    fingerprint = _sha256_canonical_json(_strip_ids(core))
    return {
        "schema_version": "ShadowInputSnapshotV0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": _git_sha_short(),
        "input_fingerprint_sha256": fingerprint,
        "input": core,
    }


@dataclass(frozen=True)
class ShadowSnapshotWriteResult:
    path: Path
    payload: dict[str, Any]


def write_shadow_input_snapshot(
    payload: dict[str, Any],
    *,
    symbol: str,
    analysis_time: datetime,
    label: Optional[str] = None,
    base_dir: Optional[Path] = None,
) -> ShadowSnapshotWriteResult:
    safe_label = _safe_token("shadow_label", label)
    ts = analysis_time.astimezone(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = safe_label or "auto"
    filename = f"shadow_input_snapshot_{symbol}_{ts}_{suffix}.json"

    out_dir = base_dir if base_dir is not None else results_path("debug", "shadow_compare")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / filename
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return ShadowSnapshotWriteResult(path=path, payload=payload)


def _is_playbook_allowed_from_policy_context(
    *,
    playbook_name: str,
    policy_context: dict[str, Any],
    risk_engine_mode: str,
) -> tuple[bool, str]:
    if not playbook_name:
        return True, "OK"
    if bool(policy_context.get("eval_allow_all_playbooks")):
        return True, "RISK_EVAL_ALLOW_ALL_PLAYBOOKS=true"

    denylist = set(policy_context.get("denylist") or [])
    if playbook_name in denylist:
        return False, f"Playbook '{playbook_name}' is in DENYLIST (destructeur)"

    paper_flag = bool(policy_context.get("paper_use_wave1_playbooks"))
    paper_allow = list(policy_context.get("paper_wave1_allowlist") or [])
    if paper_flag and paper_allow and playbook_name not in set(paper_allow):
        return False, f"Playbook '{playbook_name}' not in PAPER Wave1 allowlist"

    if str(risk_engine_mode).upper() == "SAFE":
        allow = set(policy_context.get("safe_allowlist") or [])
        if playbook_name not in allow:
            return False, f"Playbook '{playbook_name}' not in SAFE allowlist"
    else:
        allow = set(policy_context.get("aggressive_allowlist") or [])
        if playbook_name not in allow:
            return False, f"Playbook '{playbook_name}' not in AGGRESSIVE allowlist"

    return True, "OK"


def replay_shadow_comparison_from_snapshot(
    snapshot_payload: dict[str, Any],
    *,
    legacy_score_setup: Optional[Callable[..., Optional[Setup]]] = None,
    v2_generate_setups: Optional[Callable[..., Sequence[Setup]]] = None,
    snapshot_path: Optional[Path] = None,
    label: Optional[str] = None,
    base_dir: Optional[Path] = None,
) -> ShadowWriteResult:
    """
    Recompute legacy vs V2 shadow comparison from a serialized input snapshot.

    This function must never fetch live data; it only uses the snapshot contents.
    """
    if snapshot_payload.get("schema_version") != "ShadowInputSnapshotV0":
        raise ValueError(f"Unsupported snapshot schema_version: {snapshot_payload.get('schema_version')!r}")

    raw = snapshot_payload.get("input") or {}
    symbol = raw["symbol"]
    analysis_time = datetime.fromisoformat(raw["analysis_time_utc"].replace("Z", "+00:00"))
    trading_mode = str(raw.get("trading_mode") or "")
    risk_engine_mode = str(raw.get("risk_engine_mode") or trading_mode)
    current_price = float(raw["current_price"])

    policy_context = dict(raw.get("policy_context") or {})
    is_playbook_allowed = lambda name: _is_playbook_allowed_from_policy_context(  # noqa: E731
        playbook_name=name, policy_context=policy_context, risk_engine_mode=risk_engine_mode
    )

    # Rehydrate models (only what the engines consume).
    market_state = MarketState.model_validate(raw["market_state"])
    ict_patterns = [ICTPattern.model_validate(p) for p in list(raw.get("ict_patterns") or [])]
    candlestick_patterns = [PatternDetection.model_validate(p) for p in list(raw.get("candlestick_patterns") or [])]
    liquidity_levels = []
    from models.market_data import LiquidityLevel  # local import to keep top-level minimal
    for lvl in list(raw.get("liquidity_levels") or []):
        liquidity_levels.append(LiquidityLevel.model_validate(lvl))
    swept_levels = []
    for lvl in list(raw.get("swept_levels") or []):
        swept_levels.append(LiquidityLevel.model_validate(lvl))
    playbook_matches = [PlaybookMatch.model_validate(m) for m in list(raw.get("playbook_matches") or [])]

    # Engines: allow injection for tests; default to real engines for the script usage.
    if legacy_score_setup is None:
        from engines.setup_engine import SetupEngine  # local import (no pipeline dependency)
        legacy_engine = SetupEngine()
        legacy_score_setup = legacy_engine.score_setup

    if v2_generate_setups is None:
        from engines.setup_engine_v2 import SetupEngineV2  # local import (no pipeline dependency)
        v2_engine = SetupEngineV2()
        v2_generate_setups = v2_engine.generate_setups

    legacy_raw = legacy_score_setup(
        symbol,
        market_state,
        ict_patterns,
        candlestick_patterns,
        playbook_matches,
        swept_levels,
        current_price,
    )

    # Apply the same legacy filtering contract as TradingPipeline.
    legacy_final: list[Setup] = []
    if legacy_raw is not None:
        if trading_mode.upper() == "SAFE":
            from engines.setup_engine import filter_setups_safe_mode
            legacy_final = filter_setups_safe_mode([legacy_raw])
        else:
            from engines.setup_engine import filter_setups_aggressive_mode
            legacy_final = filter_setups_aggressive_mode([legacy_raw])

        accepted: list[Setup] = []
        for s in legacy_final:
            rejected = False
            for m in list(s.playbook_matches or []):
                allowed, _reason = is_playbook_allowed(getattr(m, "playbook_name", "") or "")
                if not allowed:
                    rejected = True
                    break
            if not rejected:
                accepted.append(s)
        legacy_final = accepted

    # V2 shadow (same adapter as pipeline).
    v2_raw = list(
        v2_generate_setups(
            symbol=symbol,
            market_state=market_state,
            ict_patterns=ict_patterns,
            candle_patterns=candlestick_patterns_from_legacy_detections(candlestick_patterns),
            liquidity_levels=liquidity_levels,
            current_time=analysis_time,
            trading_mode=trading_mode,
            last_price=current_price,
        )
        or []
    )
    v2_candle_patterns = candlestick_patterns_from_legacy_detections(candlestick_patterns)

    if trading_mode.upper() == "SAFE":
        from engines.setup_engine import filter_setups_safe_mode
        v2_final = filter_setups_safe_mode(list(v2_raw))
    else:
        from engines.setup_engine import filter_setups_aggressive_mode
        v2_final = filter_setups_aggressive_mode(list(v2_raw))

    accepted_v2: list[Setup] = []
    for s in list(v2_final):
        rejected = False
        for m in list(s.playbook_matches or []):
            allowed, _reason = is_playbook_allowed(getattr(m, "playbook_name", "") or "")
            if not allowed:
                rejected = True
                break
        if not rejected:
            accepted_v2.append(s)
    v2_final = accepted_v2

    payload = build_shadow_comparison_payload(
        symbol=symbol,
        analysis_time=analysis_time,
        trading_mode=trading_mode,
        market_state=market_state,
        current_price=current_price,
        legacy_raw=legacy_raw,
        legacy_final=list(legacy_final),
        v2_raw=list(v2_raw),
        v2_final=list(v2_final),
        v2_error=None,
        counts={
            "candlestick_patterns_legacy": len(candlestick_patterns),
            "candlestick_patterns_v2": len(v2_candle_patterns),
            "ict_patterns": len(ict_patterns),
            "liquidity_levels": len(liquidity_levels),
            "legacy_playbook_matches": len(playbook_matches),
            "v2_raw_setups": len(v2_raw),
            "v2_final_setups": len(v2_final),
            "legacy_final_setups": len(legacy_final),
        },
        is_playbook_allowed=is_playbook_allowed,
    )
    payload["input_snapshot"] = {
        "path": str(snapshot_path) if snapshot_path else None,
        "fingerprint_sha256": snapshot_payload.get("input_fingerprint_sha256"),
    }
    wr = write_shadow_comparison(payload, symbol=symbol, analysis_time=analysis_time, label=label, base_dir=base_dir)
    return wr


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
