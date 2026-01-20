"""Funnel Metrics Collector
This module fournit une classe utilitaire pour collecter des statistiques
sur le parcours des setups dans le funnel de décision DexterioBOT.
Les compteurs sont enregistrés par playbook :
 - matched_count : nombre de fois où le playbook a été sélectionné par
   l'évaluateur de playbooks.
 - pass_grade_count : nombre de fois où le setup a obtenu un grade
   suffisant pour passer le filtrage de pré‑grade.
 - pass_timefilter_count : nombre de fois où le setup a passé les
   filtres de session/horaires.
 - pass_risk_count : nombre de fois où le RiskEngine a autorisé le setup
   (allowlist/denylist et kill‑switch).
 - executed_trades_count : nombre de trades effectivement exécutés pour
   ce playbook.
 - reject_reasons : dictionnaire des raisons de rejet et de leur fréquence.

Cette implémentation est volontairement simple ; elle peut être
améliorée en instrumentant chaque étape du pipeline pour collecter
davantage d'informations et d'exemples.  Un appel à `save_json()`
permet d'écrire les métriques sous forme JSON.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any


class FunnelMetrics:
    """Collecteur de métriques de funnel par playbook, symbole et jour.

    Les compteurs sont stockés avec une granularité plus fine :
      * playbook_name
      * symbol
      * date (YYYY‑MM‑DD)

    Chaque combinaison possède ses propres compteurs.  Si `symbol` ou
    `timestamp` ne sont pas fournis, la valeur 'UNKNOWN' est utilisée.
    """

    def __init__(self) -> None:
        # Structure : playbook -> symbol -> date -> metrics
        self._data: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(
                    lambda: {
                        'matched_count': 0,
                        'pass_grade_count': 0,
                        'pass_timefilter_count': 0,
                        'pass_risk_count': 0,
                        'executed_trades_count': 0,
                        'reject_reasons': defaultdict(int),
                    }
                )
            )
        )

    def _key(self, symbol: str | None, timestamp: Any | None) -> (str, str):
        """Retourne (symbol, date) à partir des arguments.

        Args:
            symbol: Symbole de l'actif (ex: SPY).  None → 'UNKNOWN'.
            timestamp: datetime ou chaîne iso.  None → 'UNKNOWN'.
        Returns:
            Tuple (symbol_str, date_str)
        """
        sym = symbol or 'UNKNOWN'
        if timestamp is None:
            date_str = 'UNKNOWN'
        else:
            try:
                # Accepte datetime ou ISO string
                from datetime import datetime as _dt
                if hasattr(timestamp, 'date'):
                    date_str = timestamp.date().isoformat()
                else:
                    dt_obj = _dt.fromisoformat(str(timestamp))
                    date_str = dt_obj.date().isoformat()
            except Exception:
                date_str = 'UNKNOWN'
        return sym, date_str

    def record_matched(self, playbook_name: str, symbol: str | None = None, timestamp: Any | None = None) -> None:
        sym, date_str = self._key(symbol, timestamp)
        self._data[playbook_name][sym][date_str]['matched_count'] += 1

    def record_pass_grade(self, playbook_name: str, symbol: str | None = None, timestamp: Any | None = None) -> None:
        sym, date_str = self._key(symbol, timestamp)
        self._data[playbook_name][sym][date_str]['pass_grade_count'] += 1

    def record_pass_timefilter(self, playbook_name: str, symbol: str | None = None, timestamp: Any | None = None) -> None:
        sym, date_str = self._key(symbol, timestamp)
        self._data[playbook_name][sym][date_str]['pass_timefilter_count'] += 1

    def record_pass_risk(self, playbook_name: str, symbol: str | None = None, timestamp: Any | None = None) -> None:
        sym, date_str = self._key(symbol, timestamp)
        self._data[playbook_name][sym][date_str]['pass_risk_count'] += 1

    def record_executed(self, playbook_name: str, symbol: str | None = None, timestamp: Any | None = None) -> None:
        sym, date_str = self._key(symbol, timestamp)
        self._data[playbook_name][sym][date_str]['executed_trades_count'] += 1

    def record_reject(self, playbook_name: str, reason: str, symbol: str | None = None, timestamp: Any | None = None) -> None:
        sym, date_str = self._key(symbol, timestamp)
        self._data[playbook_name][sym][date_str]['reject_reasons'][reason] += 1

    def export(self) -> Dict[str, Any]:
        """Retourne une structure prête pour l'export JSON avec top 5 raisons.

        La structure exportée est :

        {
          playbook_name: {
            symbol: {
              date: {
                matched_count: int,
                pass_grade_count: int,
                pass_timefilter_count: int,
                pass_risk_count: int,
                executed_trades_count: int,
                top_reject_reasons: [ {reason, count}, ... ],
              },
              ...
            },
            ...
          },
          ...
        }
        """
        export_data: Dict[str, Any] = {}
        for pb_name, by_symbol in self._data.items():
            export_data[pb_name] = {}
            for sym, by_date in by_symbol.items():
                export_data[pb_name][sym] = {}
                for date_str, metrics in by_date.items():
                    data = {k: v for k, v in metrics.items() if k != 'reject_reasons'}
                    reasons = metrics['reject_reasons']
                    top_reasons = sorted(
                        reasons.items(), key=lambda kv: kv[1], reverse=True
                    )[:5]
                    data['top_reject_reasons'] = [
                        {'reason': r, 'count': c} for r, c in top_reasons
                    ]
                    export_data[pb_name][sym][date_str] = data
        return export_data

    def save_json(self, path: str | Path) -> None:
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(self.export(), f, indent=2)
