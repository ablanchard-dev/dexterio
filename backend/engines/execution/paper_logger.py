"""Sprint 4-lite — Paper logger structure.

Logs structurés pour paper runs. Format compatible avec backtest verdict G4
pour reconcile backtest↔paper futur.

3 streams de logs :
  - decision_log : pour chaque tick/bar, signal + raison
  - execution_log : ordre placé/cancelled/filled
  - account_snapshot : equity / cash / positions snapshot périodique
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from engines.execution.broker_interface import AccountSnapshot, Order, Position


class PaperLogger:
    """Append-only structured logger for paper runs.

    Files :
      - <run_dir>/decision_log.jsonl
      - <run_dir>/execution_log.jsonl
      - <run_dir>/account_snapshots.jsonl
      - <run_dir>/manifest.json (frozen at start, no mid-run mutation)
    """

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.decision_path = self.run_dir / "decision_log.jsonl"
        self.execution_path = self.run_dir / "execution_log.jsonl"
        self.snapshot_path = self.run_dir / "account_snapshots.jsonl"
        self.manifest_path = self.run_dir / "manifest.json"

    def write_manifest(self, manifest: dict[str, Any]) -> None:
        """Write manifest at run start. Frozen, no mutation after."""
        manifest = {**manifest, "started_at": datetime.now(timezone.utc).isoformat()}
        self.manifest_path.write_text(json.dumps(manifest, indent=2, default=str))

    def log_decision(self, tick_ts: datetime, symbol: str, signal: str,
                       reason: str, extra: Optional[dict[str, Any]] = None) -> None:
        rec = {
            "ts": tick_ts.isoformat() if hasattr(tick_ts, "isoformat") else str(tick_ts),
            "symbol": symbol,
            "signal": signal,
            "reason": reason,
        }
        if extra:
            rec.update(extra)
        with self.decision_path.open("a") as f:
            f.write(json.dumps(rec, default=str) + "\n")

    def log_execution(self, order: Order, event: str = "placed") -> None:
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,  # placed | cancelled | filled | rejected
            "order_id": order.order_id,
            "symbol": order.symbol,
            "side": str(order.side),
            "quantity": order.quantity,
            "type": str(order.order_type),
            "limit_price": order.limit_price,
            "status": str(order.status),
            "fill_price": order.fill_price,
            "fill_quantity": order.fill_quantity,
            "error": order.error_msg,
        }
        with self.execution_path.open("a") as f:
            f.write(json.dumps(rec, default=str) + "\n")

    def log_snapshot(self, account: AccountSnapshot,
                       positions: list[Position]) -> None:
        rec = {
            "ts": account.timestamp.isoformat(),
            "cash": account.cash,
            "equity": account.equity,
            "buying_power": account.buying_power,
            "realized_pnl": account.realized_pnl,
            "n_positions": len(positions),
            "positions": [
                {
                    "symbol": p.symbol,
                    "quantity": p.quantity,
                    "avg_entry": p.avg_entry_price,
                    "market_price": p.market_price,
                    "unrealized_pnl": p.unrealized_pnl,
                }
                for p in positions
            ],
        }
        with self.snapshot_path.open("a") as f:
            f.write(json.dumps(rec, default=str) + "\n")
