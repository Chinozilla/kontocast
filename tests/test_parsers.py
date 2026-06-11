"""Parser-Roundtrip: synthetische Exporte aller vier Formate müssen identisch einlesen."""

import pytest

from kontocast import synth
from kontocast.parsers import detect_format, parse_file

FILES = ["dkb.csv", "ing.csv", "sparkasse.csv", "camt053.xml"]


@pytest.fixture(scope="module")
def sample_dir(tmp_path_factory):
    out = tmp_path_factory.mktemp("samples")
    ledger = synth.write_all(out, months=6, seed=7)
    return out, ledger


@pytest.mark.parametrize(
    "fname,expected",
    [("dkb.csv", "dkb"), ("ing.csv", "ing"), ("sparkasse.csv", "sparkasse"), ("camt053.xml", "camt053")],
)
def test_detect_format(sample_dir, fname, expected):
    out, _ = sample_dir
    assert detect_format(out / fname) == expected


@pytest.mark.parametrize("fname", FILES)
def test_roundtrip_counts_and_sums(sample_dir, fname):
    out, ledger = sample_dir
    txs = parse_file(out / fname)
    assert len(txs) == len(ledger)
    assert sum(t.amount for t in txs) == sum(t.amount for t in ledger)
    assert {t.booking_date for t in txs} == {t.booking_date for t in ledger}
    assert {t.counterparty for t in txs} == {t.counterparty for t in ledger}


def test_all_formats_produce_identical_tx_ids(sample_dir):
    """Derselbe Umsatz muss aus jedem Format dieselbe tx_id ergeben (Dedup-Garantie)."""
    out, ledger = sample_dir
    id_sets = [{t.tx_id for t in parse_file(out / f)} for f in FILES]
    assert id_sets[0] == id_sets[1] == id_sets[2] == id_sets[3]
    assert len(id_sets[0]) == len(ledger)
