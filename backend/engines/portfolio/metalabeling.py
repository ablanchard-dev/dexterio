"""F2 ML metalabeling — Lopez de Prado-style pattern on portfolio strategy.

Overlay ML classifier trained on strategy outcome per trading day (is
next day's strategy return > threshold?). Features : regime (VIX level),
momentum state (recent portfolio performance), cross-asset correlations,
calendar effects.

Philosophy (plan v4.0 §9.1 debloqué) : amplify a thin signal (F2 momentum
Sharpe 0.73 over 6.5y) by FILTERING bad days — not creating edge ex nihilo.
The base strategy must be positive before metalabel overlay ; metalabel
refines.

v1 pragmatic implementation :
  - Binary classifier : next_day_return > 0 (win) vs ≤ 0 (loss).
  - Features : VIX level + VIX change + SPY 5d return + SPY 20d return
    + day_of_week one-hot.
  - Model : RandomForest (robust, no tuning), or LogisticRegression.
  - Train/test split : 60/40 temporal.
  - Overlay : on test days where classifier predicts p_win < 0.4 → skip
    (go to cash). Retain all days where p_win >= 0.4.

Output : compare filtered vs unfiltered equity curves.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class MetalabelResult:
    """Classifier output + filter impact."""

    train_accuracy: float
    test_accuracy: float
    n_train: int
    n_test: int
    n_skipped_test: int  # trading days filtered out
    sharpe_unfiltered: float
    sharpe_filtered: float
    cagr_unfiltered: float
    cagr_filtered: float
    max_dd_unfiltered: float
    max_dd_filtered: float
    feature_importances: Dict[str, float] = field(default_factory=dict)


def build_features(
    strategy_returns: pd.Series,
    vix: pd.Series,
    spy: pd.Series,
) -> pd.DataFrame:
    """Build daily feature matrix for metalabel classifier.

    Each row : features available at t (based on t-1 data — no lookahead).
    Target : strategy_returns.shift(-1) > threshold (next-day outcome).
    """
    df = pd.DataFrame(index=strategy_returns.index)
    # Prior-day VIX level + change
    df["vix_level"] = vix.reindex(df.index, method="pad").shift(1)
    df["vix_change_1d"] = df["vix_level"] - vix.reindex(df.index, method="pad").shift(2)
    df["vix_change_5d"] = df["vix_level"] - vix.reindex(df.index, method="pad").shift(6)
    # SPY momentum (trailing)
    spy_ret = spy.pct_change()
    df["spy_ret_5d"] = spy_ret.rolling(5).sum().shift(1)
    df["spy_ret_20d"] = spy_ret.rolling(20).sum().shift(1)
    # Day-of-week (0=Mon, 4=Fri)
    df["dow_mon"] = (df.index.dayofweek == 0).astype(float)
    df["dow_fri"] = (df.index.dayofweek == 4).astype(float)
    # Strategy's own recent performance (momentum in its own returns)
    df["strat_ret_5d"] = strategy_returns.rolling(5).sum().shift(1)
    df["strat_ret_20d"] = strategy_returns.rolling(20).sum().shift(1)
    return df.dropna()


def train_metalabel(
    features: pd.DataFrame,
    strategy_returns: pd.Series,
    *,
    train_fraction: float = 0.6,
    threshold: float = 0.0,  # target = return > 0 (win)
    model: str = "random_forest",
) -> tuple[object, MetalabelResult]:
    """Train metalabel classifier with temporal split.

    Returns (fitted_model, MetalabelResult).
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score

    # Align features with next-day strategy return.
    aligned_idx = features.index.intersection(strategy_returns.index)
    X = features.loc[aligned_idx]
    y = (strategy_returns.shift(-1).loc[aligned_idx] > threshold).astype(int)
    X = X.iloc[:-1]
    y = y.iloc[:-1]
    mask = X.notna().all(axis=1) & y.notna()
    X, y = X[mask], y[mask]

    n = len(X)
    split_idx = int(n * train_fraction)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    if model == "random_forest":
        clf = RandomForestClassifier(n_estimators=200, max_depth=5, random_state=42,
                                      class_weight="balanced")
    else:
        clf = LogisticRegression(max_iter=2000, class_weight="balanced",
                                  random_state=42)
    clf.fit(X_train, y_train)

    train_acc = accuracy_score(y_train, clf.predict(X_train))
    test_acc = accuracy_score(y_test, clf.predict(X_test))

    # Feature importances
    if hasattr(clf, "feature_importances_"):
        fi = dict(zip(X.columns, clf.feature_importances_))
    else:
        # LogReg : absolute coef
        coefs = clf.coef_[0] if clf.coef_.ndim == 2 else clf.coef_
        fi = dict(zip(X.columns, np.abs(coefs)))

    # Compute filtered equity on test split
    test_returns = strategy_returns.shift(-1).loc[X_test.index]
    proba = clf.predict_proba(X_test)[:, 1]  # p(win)
    # Filter : keep only days where p_win >= 0.4
    keep_mask = proba >= 0.4
    filtered_returns = test_returns.where(keep_mask, 0.0)  # skip → 0% day return (cash)

    n_skipped = int((~keep_mask).sum())

    def sharpe_ann(r):
        r = r.dropna()
        if r.std() == 0 or len(r) < 5:
            return 0.0
        return float(r.mean() / r.std() * np.sqrt(252))

    def cagr(r):
        r = r.dropna()
        if len(r) < 2:
            return 0.0
        eq = (1 + r).cumprod()
        return float(eq.iloc[-1] ** (252 / len(r)) - 1)

    def max_dd(r):
        r = r.dropna()
        if len(r) < 2:
            return 0.0
        eq = (1 + r).cumprod()
        rm = eq.expanding().max()
        return float((eq / rm - 1).min())

    result = MetalabelResult(
        train_accuracy=float(train_acc),
        test_accuracy=float(test_acc),
        n_train=len(X_train),
        n_test=len(X_test),
        n_skipped_test=n_skipped,
        sharpe_unfiltered=sharpe_ann(test_returns),
        sharpe_filtered=sharpe_ann(filtered_returns),
        cagr_unfiltered=cagr(test_returns),
        cagr_filtered=cagr(filtered_returns),
        max_dd_unfiltered=max_dd(test_returns),
        max_dd_filtered=max_dd(filtered_returns),
        feature_importances=fi,
    )
    return clf, result
