"""Monte-Carlo-Projektion: Form, Ordnung der Perzentile, Reproduzierbarkeit."""

from kontocast import synth
from kontocast.forecast import simulate


def _txs():
    return synth.to_transactions(synth.generate_ledger(months=12, seed=5))


def test_shapes_and_percentile_order():
    fc = simulate(_txs(), horizon_months=6, n_sims=500, start_balance=1000.0, seed=1)
    assert len(fc.months) == len(fc.p10) == len(fc.p50) == len(fc.p90) == 6
    for lo, mid, hi in zip(fc.p10, fc.p50, fc.p90):
        assert lo <= mid <= hi


def test_reproducible_with_same_seed():
    a = simulate(_txs(), horizon_months=6, n_sims=500, start_balance=1000.0, seed=1)
    b = simulate(_txs(), horizon_months=6, n_sims=500, start_balance=1000.0, seed=1)
    assert a.p10 == b.p10 and a.p50 == b.p50 and a.p90 == b.p90


def test_positive_household_drifts_upward():
    """Der Synth-Haushalt spart jeden Monat — der Median muss steigen."""
    fc = simulate(_txs(), horizon_months=12, n_sims=500, start_balance=0.0, seed=2)
    assert fc.p50[-1] > fc.p50[0]
