# CLAUDE.md — kontocast

Lokaler Cashflow-Analyzer für deutsche Bank-Exporte. Portfolio-Projekt (öffentliches Repo
`Chinozilla/kontocast`) — Code-Qualität, Tests und README sind Teil des Produkts.

## Befehle

```bash
.venv/Scripts/python -m pytest -q     # Tests (Windows-venv im Projektordner)
.venv/Scripts/python -m ruff check src tests
pip install -e .[dev]                 # Setup (im venv)
kontocast --help                      # CLI-Einstieg
```

## Architektur (Kurzfassung)

Pipeline: Bank-Export → `parsers/` (Format-Erkennung DKB/ING/Sparkasse/CAMT.053, alles →
`models.Transaction`) → `store.py` (SQLite, Dedup über content-hash `tx_id`) →
`categorize/` (Regeln offline, LLM optional, `evaluate.py` misst Accuracy gegen Labels) →
`recurring.py` (Intervall-Muster) → `forecast.py` (Monte-Carlo-Bootstrap, numpy, seeded).

`synth.py` ist die eine Quelle für Demo-Daten, Test-Fixtures UND Eval-Ground-Truth —
deterministisch über seed. Tests bauen darauf auf (Roundtrip aller 4 Formate, identische
tx_ids über Formate hinweg).

## Konventionen (nicht verletzen)

- **Geld ist `Decimal`**, nie float — floats nur an der numpy-Grenze in `forecast.py`.
- **Kern bleibt offline.** Netzwerkzugriff nur in `categorize/llm.py` (optionales Extra).
- **Echte Bankdaten nie ins Repo** — `*.db` und `data/` sind gitignored; `samples/` ist
  ausschließlich synthetisch.
- Gleicher Umsatz aus verschiedenen Formaten MUSS dieselbe `tx_id` ergeben
  (Dedup-Garantie, durch Test abgesichert) — `tx_id`-Inputs nicht ändern, ohne den
  Test + die Migrations-Folgen zu bedenken.
- Neue Parser: in `parsers/` als Modul mit `parse(path) -> list[Transaction]` +
  Erkennung in `detect_format` + Synth-Writer + Roundtrip-Test.
- Kategorien-Liste lebt in `categorize/rules.py` (`CATEGORIES`) — LLM-Prompt und Evals
  hängen daran.

## Roadmap

Phase 2: FastAPI + Next.js-Dashboard (Forecast-Korridor interaktiv). Danach: echte
anonymisierte Bank-Fixtures, What-if-Szenarien, PDF-Import. Siehe README.
