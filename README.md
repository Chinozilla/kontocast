# kontocast

> Local-first cash-flow analytics & Monte-Carlo forecasting for German bank exports.

[![CI](https://github.com/Chinozilla/kontocast/actions/workflows/ci.yml/badge.svg)](https://github.com/Chinozilla/kontocast/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Banking apps show your **past** as a list. kontocast turns it into a **forecast**:
import your bank statements, let it learn your recurring payments and spending
patterns, and get a probabilistic answer to *"what will my balance look like in
6 months?"* — entirely on your own machine. No account linking, no cloud, no
data leaving your computer.

```
bank exports          normalize              analyze                 project
─────────────         ─────────────          ─────────────           ─────────────
DKB CSV       ─┐                             rule/LLM categorizer    Monte-Carlo
ING CSV        ├──►   one Transaction  ──►   recurring detection ──► balance corridor
Sparkasse CSV  │      model + SQLite         monthly aggregates      p10 / p50 / p90
CAMT.053 XML  ─┘      (deduplicated)         accuracy evals          per future month
```

## Why this is harder than it sounds

- **German bank exports are a mess.** Every bank ships a different CSV dialect:
  different columns, different encodings (UTF-8-BOM vs. CP1252), German decimal
  commas, metadata blocks before the actual table, duplicated header names.
  kontocast auto-detects the format and normalizes everything into one model.
- **CAMT.053** (the ISO-20022 XML standard used by German banks) is parsed
  namespace-agnostically, so versions `.001.02` through `.001.08` all work.
- **Deduplication by content hash**: the same booking imported from a DKB CSV
  and a CAMT file produces the same `tx_id` — importing overlapping exports is
  safe by construction (verified by tests).
- **Categorization is measured, not vibes.** A deterministic rule engine is the
  offline baseline; an optional LLM categorizer (Anthropic API) can take over.
  Both run against a ground-truth-labeled dataset through an eval harness that
  reports accuracy per category — so any change to rules or prompts is
  quantified.
- **Forecasting without fake certainty.** Recurring items (salary, rent,
  subscriptions) are detected from interval patterns and projected
  deterministically; everything else is bootstrapped from your own monthly
  history (resampling, no distribution assumptions). 1000 simulated futures
  become a p10/p50/p90 corridor instead of a single misleading line.

## Quickstart

```bash
pip install -e .[dev]

# 1. Generate a realistic synthetic household (4 bank formats + ground-truth labels)
kontocast synth samples --months 18

# 2. Import — format auto-detected; the 4 files dedupe into one history
kontocast import samples/dkb.csv samples/ing.csv samples/sparkasse.csv samples/camt053.xml

# 3. Categorize (offline rules; add --llm for the Anthropic-powered version)
kontocast categorize

# 4. Analyze
kontocast report        # monthly income/expenses + spend per category
kontocast recurring     # detected subscriptions, rent, salary with monthly cost

# 5. Project the future
kontocast forecast --months 12 --start-balance 2500

# 6. Measure categorization accuracy against ground truth
kontocast eval samples/labels.csv
```

With your real data: export CSV (DKB, ING, Sparkasse) or CAMT.053 from your
online banking and run `kontocast import <file>`. Real data stays local —
`*.db` and `data/` are gitignored by design.

## Forecast methodology

1. `detect_recurring` groups transactions by counterparty and direction, then
   checks booking-date gaps against period windows (weekly / monthly /
   quarterly / yearly). Amount stability is enforced (median absolute deviation
   ≤ 35 % of the median) so grocery runs don't masquerade as subscriptions.
2. Recurring items contribute a deterministic, month-normalized amount
   (`median × 30.44 / period_days`).
3. All remaining transactions form the *variable* monthly history. Each
   simulated future month draws one of those historical months at random
   (bootstrap with replacement) — fat tails and seasonality survive, no
   normal-distribution assumption is made.
4. 1000 paths × N months → cumulative balance paths → p10/p50/p90 percentiles.
   Seeded RNG makes every forecast reproducible.

## Evaluation-driven categorization

The synthetic generator knows the true category of every transaction it emits
and writes them to `labels.csv`. The eval harness joins labels to parsed
transactions and scores any categorizer:

```
Genauigkeit: 100.0% (412/412)        # rule engine on synthetic data
```

The same harness scores the LLM categorizer (`kontocast eval labels.csv --llm`),
which is the honest way to decide whether an LLM beats your rules — and to
catch prompt regressions.

## Project layout

```
src/kontocast/
  models.py          # Transaction: frozen dataclass, Decimal amounts, content-hash id
  parsers/           # format detection + DKB / ING / Sparkasse / CAMT.053 parsers
  store.py           # SQLite persistence, dedup on insert
  categorize/
    rules.py         # deterministic offline baseline
    llm.py           # optional Anthropic-powered categorizer (kontocast[llm])
    evaluate.py      # accuracy harness against labeled data
  recurring.py       # interval-pattern detection of recurring payments
  forecast.py        # Monte-Carlo balance projection (numpy)
  synth.py           # synthetic household generator — demo data & test fixture
  cli.py             # typer CLI
tests/               # pytest: parser roundtrips, dedup guarantee, detection, simulation
```

Design decisions worth noting:

- **`Decimal` everywhere money flows** — floats only enter at the
  numpy/simulation boundary where rounding noise is irrelevant.
- **The core is offline.** The LLM categorizer is an optional extra
  (`pip install kontocast[llm]`); nothing else touches the network.
- **Synthetic data is a feature, not a stub.** One generator produces demo
  data, parser fixtures, recurring-detection test cases and eval ground truth —
  all deterministic via seed.

## Roadmap

- [ ] FastAPI backend + Next.js dashboard (interactive forecast corridor)
- [ ] Real-world export fixtures per bank (anonymized) hardening the parsers
- [ ] What-if scenarios ("cancel subscription X", "rent +100 €")
- [ ] PDF statement import (OCR) for banks without CSV export

## License

MIT
