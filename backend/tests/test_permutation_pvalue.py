"""p-value de permutation : (k+1)/(n+1), jamais k/n.

Revue 17/09 : scripts/bar_permutation_test.py divisait par `iterations` sans compter la
valeur observee comme un tirage. La p-value pouvait valoir exactement 0 et restait
systematiquement trop basse, ce qui facilitait le passage de la porte p < 0.05.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from bar_permutation_test import permutation_test  # noqa: E402


def test_p_value_never_zero_even_when_observed_is_extreme():
    r = np.array([5.0] * 30)            # toutes les permutations de signe sont <= observe
    res = permutation_test(r, iterations=200, seed=1)
    assert res["p_one_sided_ge"] >= 1.0 / 201


def test_p_value_uses_plus_one_correction():
    r = np.array([1.0, -1.0, 2.0, -0.5, 0.3, -0.2, 1.5, -1.1])
    iters = 500
    res = permutation_test(r, iterations=iters, seed=7)
    rng = np.random.default_rng(7)
    obs = r.mean()
    k = sum(1 for _ in range(iters)
            if (np.abs(r) * rng.choice([-1.0, 1.0], size=len(r))).mean() >= obs)
    assert abs(res["p_one_sided_ge"] - (k + 1) / (iters + 1)) < 1e-12
