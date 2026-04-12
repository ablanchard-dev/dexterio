#!/usr/bin/env python3
"""
Post-mortem quantitatif à partir des parquets trades mini-lab / WF (sans moteur).

Lit un ou plusieurs `trades_*_AGGRESSIVE_*.parquet` et agrège :
playbook, split (nom de dossier parent si --campaign-dir), symbole, mois,
exit_reason, fréquence, concentration des pertes.

Usage (depuis backend/) :
  .venv/bin/python scripts/postmortem_campaign_trades.py \\
    --campaign-dir results/labs/mini_week/wf_core3_oos_jun_nov2025 \\
    --out results/campaigns/wf_core3_oos_jun_nov2025/POSTMORTEM_QUANT.json

  .venv/bin/python scripts/postmortem_campaign_trades.py \\
    --parquet path/a.parquet --split-label run_a --parquet path/b.parquet --split-label run_b
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

BACKEND = Path(__file__).resolve().parent.parent


def _agg(g: pd.DataFrame) -> dict[str, Any]:
    return {
        "n": int(len(g)),
        "sum_r": float(g["r_multiple"].sum()),
        "mean_r": float(g["r_multiple"].mean()),
        "sum_pnl_usd": float(g["pnl_dollars"].sum()),
        "win_rate": float((g["r_multiple"] > 0).mean()),
    }


def _load_frames(
    parquet_paths: list[Path],
    split_labels: list[str | None],
) -> pd.DataFrame:
    if split_labels and len(split_labels) != len(parquet_paths):
        print("ERROR: --split-label count must match --parquet count", file=sys.stderr)
        raise SystemExit(2)
    frames: list[pd.DataFrame] = []
    for i, p in enumerate(parquet_paths):
        if not p.is_file():
            print(f"ERROR: missing {p}", file=sys.stderr)
            raise SystemExit(2)
        d = pd.read_parquet(p)
        label = split_labels[i] if split_labels else p.parent.name
        d["_split"] = label
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def _discover_parquets(campaign_dir: Path) -> tuple[list[Path], list[str]]:
    """Sous-dossiers type wf_s0_test / wf_s1_test avec trades_*.parquet."""
    paths: list[Path] = []
    labels: list[str] = []
    for sub in sorted(campaign_dir.iterdir()):
        if not sub.is_dir():
            continue
        cands = list(sub.glob("trades_*AGGRESSIVE*.parquet"))
        if not cands:
            continue
        paths.append(cands[0])
        labels.append(sub.name)
    if not paths:
        print(f"ERROR: no trades parquet under {campaign_dir}", file=sys.stderr)
        raise SystemExit(2)
    return paths, labels


def build_report(df: pd.DataFrame) -> dict[str, Any]:
    need = {"r_multiple", "pnl_dollars", "playbook", "symbol", "timestamp_entry", "exit_reason"}
    missing = need - set(df.columns)
    if missing:
        raise ValueError(f"colonnes manquantes: {sorted(missing)}")

    out: dict[str, Any] = {}
    out["global"] = {
        "n_trades": int(len(df)),
        "sum_r": float(df["r_multiple"].sum()),
        "mean_r": float(df["r_multiple"].mean()),
        "sum_pnl_usd": float(df["pnl_dollars"].sum()),
        "win_rate": float((df["r_multiple"] > 0).mean()),
    }

    rows_pb = []
    for pb, g in df.groupby("playbook"):
        rows_pb.append({"playbook": pb, **_agg(g)})
    rows_pb.sort(key=lambda x: x["sum_r"])
    out["by_playbook"] = rows_pb

    out["by_split"] = [{"split": sp, **_agg(g)} for sp, g in df.groupby("_split")]

    out["by_symbol"] = [{"symbol": sym, **_agg(g)} for sym, g in df.groupby("symbol")]

    df = df.copy()
    df["ym"] = pd.to_datetime(df["timestamp_entry"], utc=True).dt.strftime("%Y-%m")
    by_m = [{"month": ym, **_agg(g)} for ym, g in df.groupby("ym")]
    out["by_month"] = sorted(by_m, key=lambda x: x["month"])

    by_er = [{"exit_reason": er, **_agg(g)} for er, g in df.groupby("exit_reason")]
    out["by_exit_reason"] = sorted(by_er, key=lambda x: x["sum_r"])

    def freq(name: str, sub: pd.DataFrame) -> dict[str, Any]:
        days = int(pd.to_datetime(sub["timestamp_entry"], utc=True).dt.normalize().nunique())
        n = int(len(sub))
        return {
            "split": name,
            "unique_days": days,
            "trades": n,
            "trades_per_day": float(n / max(days, 1)),
        }

    out["trade_frequency"] = [freq(sp, g) for sp, g in df.groupby("_split")]
    all_days = int(pd.to_datetime(df["timestamp_entry"], utc=True).dt.normalize().nunique())
    out["trade_frequency"].append(
        {
            "split": "combined",
            "unique_days": all_days,
            "trades": int(len(df)),
            "trades_per_day": float(len(df) / max(all_days, 1)),
        }
    )

    neg = df[df["r_multiple"] < 0]
    total_neg_r = float(neg["r_multiple"].sum())
    by_pb_neg = neg.groupby("playbook")["r_multiple"].sum().sort_values()
    out["loss_concentration_r"] = {
        "total_negative_r_sum": total_neg_r,
        "by_playbook_share_of_negative_r": [
            {
                "playbook": pb,
                "neg_r_sum": float(v),
                "share_of_total_neg_r": float(v / total_neg_r if total_neg_r != 0 else 0),
            }
            for pb, v in by_pb_neg.items()
        ],
    }

    neg_pnl = df[df["pnl_dollars"] < 0]
    total_neg_pnl = float(neg_pnl["pnl_dollars"].sum())
    by_pb_neg_pnl = neg_pnl.groupby("playbook")["pnl_dollars"].sum().sort_values()
    out["loss_concentration_pnl"] = {
        "total_negative_pnl_usd": total_neg_pnl,
        "by_playbook_share_of_negative_pnl": [
            {
                "playbook": pb,
                "neg_pnl_usd": float(v),
                "share": float(v / total_neg_pnl if total_neg_pnl != 0 else 0),
            }
            for pb, v in by_pb_neg_pnl.items()
        ],
    }

    out["by_split_playbook"] = []
    for (sp, pb), g in df.groupby(["_split", "playbook"]):
        out["by_split_playbook"].append({"split": sp, "playbook": pb, **_agg(g)})

    out["note_costs"] = (
        "Les parquets trades mini-lab n'exposent pas de colonnes commission/slippage décomposées ; "
        "pnl_dollars / r_multiple reflètent le PnL tel que sorti par le moteur (coûts déjà intégrés si le run les applique)."
    )

    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Post-mortem quant trades campagne (parquet)")
    p.add_argument(
        "--campaign-dir",
        type=str,
        default=None,
        help="Dossier type mini_week/<output_parent>/ avec sous-dossiers par run",
    )
    p.add_argument(
        "--parquet",
        action="append",
        default=[],
        help="Chemin parquet trades (répétable)",
    )
    p.add_argument(
        "--split-label",
        action="append",
        default=[],
        help="Label split pour chaque --parquet (même ordre)",
    )
    p.add_argument("--out", type=str, default=None, help="Écrire JSON (sinon stdout)")
    args = p.parse_args()

    if args.campaign_dir:
        cdir = Path(args.campaign_dir).expanduser()
        if not cdir.is_absolute():
            cdir = (BACKEND / cdir).resolve()
        paths, labels = _discover_parquets(cdir)
        df = _load_frames(paths, labels)
    elif args.parquet:
        paths = [Path(x).expanduser() for x in args.parquet]
        for i, path in enumerate(paths):
            if not path.is_absolute():
                paths[i] = (BACKEND / path).resolve()
        df = _load_frames(paths, args.split_label or None)
    else:
        print("ERROR: fournir --campaign-dir ou au moins un --parquet", file=sys.stderr)
        return 2

    rep = build_report(df)
    text = json.dumps(rep, indent=2, ensure_ascii=False)
    if args.out:
        outp = Path(args.out).expanduser()
        if not outp.is_absolute():
            outp = (BACKEND / outp).resolve()
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(text, encoding="utf-8")
        print(f"wrote {outp}", flush=True)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
