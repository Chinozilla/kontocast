"""kontocast-CLI: synth -> import -> categorize -> report/recurring/forecast/eval."""

from __future__ import annotations

from pathlib import Path
from typing import List

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    help="Lokaler Cashflow-Analyzer für deutsche Bank-Exporte (CSV/CAMT.053).",
    no_args_is_help=True,
)
console = Console()

DB_OPTION = typer.Option(Path("kontocast.db"), "--db", help="Pfad zur lokalen SQLite-Datei.")


def _load(db: Path):
    from kontocast import store

    con = store.connect(db)
    txs = store.load_transactions(con)
    if not txs:
        console.print("[red]Keine Transaktionen in der DB — erst `kontocast import` ausführen.[/red]")
        raise typer.Exit(1)
    return con, txs


@app.command()
def synth(
    outdir: Path = typer.Argument(Path("samples"), help="Zielordner für die Beispieldateien."),
    months: int = typer.Option(18, help="Anzahl Monate Historie."),
    seed: int = typer.Option(42, help="Zufalls-Seed (deterministisch)."),
):
    """Erzeugt synthetische Kontoauszüge in 4 Bank-Formaten + Ground-Truth-Labels."""
    from kontocast import synth as synthmod

    ledger = synthmod.write_all(outdir, months=months, seed=seed)
    console.print(
        f"[green]{len(ledger)} Transaktionen[/green] geschrieben nach {outdir}: "
        "dkb.csv, ing.csv, sparkasse.csv, camt053.xml, labels.csv"
    )


@app.command("import")
def import_(
    files: List[Path] = typer.Argument(..., help="Bank-Export-Dateien (Format wird erkannt)."),
    db: Path = DB_OPTION,
):
    """Importiert Bank-Exporte in die lokale DB (Duplikate werden erkannt)."""
    from kontocast import store
    from kontocast.parsers import detect_format, parse_file

    con = store.connect(db)
    for f in files:
        fmt = detect_format(f)
        txs = parse_file(f)
        added = store.add_transactions(con, txs)
        console.print(f"{f.name}: Format [bold]{fmt}[/bold], {len(txs)} gelesen, {added} neu")


@app.command()
def categorize(
    db: Path = DB_OPTION,
    llm: bool = typer.Option(False, "--llm", help="LLM statt Regeln nutzen (ANTHROPIC_API_KEY nötig)."),
):
    """Kategorisiert alle bisher unkategorisierten Transaktionen."""
    from kontocast import store
    from kontocast.categorize import rules

    con, txs = _load(db)
    todo = [t for t in txs if not t.category]
    if not todo:
        console.print("Alles bereits kategorisiert.")
        return
    if llm:
        from kontocast.categorize import llm as llm_mod

        mapping = llm_mod.categorize_batch(todo)
    else:
        mapping = {t.tx_id: rules.categorize(t) for t in todo}
    store.set_categories(con, mapping)
    console.print(f"[green]{len(mapping)}[/green] Transaktionen kategorisiert ({'LLM' if llm else 'Regeln'}).")


@app.command()
def report(db: Path = DB_OPTION):
    """Monatsübersicht (Einnahmen/Ausgaben/Saldo) und Top-Ausgabenkategorien."""
    import pandas as pd

    _, txs = _load(db)
    df = pd.DataFrame(
        {
            "monat": t.booking_date.strftime("%Y-%m"),
            "betrag": float(t.amount),
            "kategorie": t.category or "(unkategorisiert)",
        }
        for t in txs
    )

    monthly = Table(title="Monatsübersicht")
    for col in ("Monat", "Einnahmen", "Ausgaben", "Saldo"):
        monthly.add_column(col, justify="right")
    for monat, grp in df.groupby("monat")["betrag"]:
        monthly.add_row(
            str(monat),
            f"{grp[grp > 0].sum():,.2f}",
            f"{grp[grp < 0].sum():,.2f}",
            f"{grp.sum():+,.2f}",
        )
    console.print(monthly)

    spend = df[df["betrag"] < 0].groupby("kategorie")["betrag"].sum().sort_values()
    categories = Table(title="Ausgaben nach Kategorie (gesamt)")
    categories.add_column("Kategorie")
    categories.add_column("Summe", justify="right")
    for kategorie, summe in spend.items():
        categories.add_row(str(kategorie), f"{summe:,.2f}")
    console.print(categories)


@app.command()
def recurring(db: Path = DB_OPTION):
    """Zeigt erkannte wiederkehrende Posten (Gehalt, Miete, Abos ...)."""
    from kontocast.recurring import detect_recurring

    _, txs = _load(db)
    items = detect_recurring(txs)
    if not items:
        console.print("Keine wiederkehrenden Posten erkannt.")
        return
    table = Table(title="Wiederkehrende Posten")
    for col in ("Gegenpartei", "Rhythmus", "Betrag", "pro Monat", "Belege", "zuletzt"):
        table.add_column(col, justify="right")
    table.columns[0].justify = "left"
    for item in items:
        table.add_row(
            item.counterparty,
            item.period_label,
            f"{item.median_amount:,.2f}",
            f"{item.monthly_amount:,.2f}",
            str(item.occurrences),
            item.last_date.isoformat(),
        )
    console.print(table)
    total = sum(i.monthly_amount for i in items)
    console.print(f"Fixer Saldo pro Monat: [bold]{total:,.2f} EUR[/bold]")


@app.command()
def forecast(
    db: Path = DB_OPTION,
    months: int = typer.Option(12, help="Projektions-Horizont in Monaten."),
    sims: int = typer.Option(1000, help="Anzahl Monte-Carlo-Simulationen."),
    start_balance: float = typer.Option(0.0, help="Aktueller Kontostand als Startpunkt."),
    seed: int = typer.Option(42, help="Zufalls-Seed (reproduzierbar)."),
):
    """Monte-Carlo-Projektion des Kontostands (p10/p50/p90-Korridor)."""
    from kontocast.forecast import simulate

    _, txs = _load(db)
    fc = simulate(txs, horizon_months=months, n_sims=sims, start_balance=start_balance, seed=seed)
    table = Table(title=f"Kontostand-Projektion ({fc.n_sims} Simulationen)")
    for col in ("Monat", "p10 (vorsichtig)", "p50 (erwartet)", "p90 (optimistisch)"):
        table.add_column(col, justify="right")
    for month, lo, mid, hi in zip(fc.months, fc.p10, fc.p50, fc.p90):
        table.add_row(month, f"{lo:,.2f}", f"{mid:,.2f}", f"{hi:,.2f}")
    console.print(table)
    console.print(
        f"Start: {fc.start_balance:,.2f} EUR | fixe Posten/Monat: {fc.fixed_monthly:+,.2f} EUR"
    )


@app.command("eval")
def eval_(
    labels: Path = typer.Argument(..., help="labels.csv mit Ground-Truth-Kategorien."),
    db: Path = DB_OPTION,
    llm: bool = typer.Option(False, "--llm", help="LLM statt Regeln evaluieren."),
):
    """Misst die Kategorisierungs-Genauigkeit gegen gelabelte Daten."""
    from kontocast.categorize import evaluate as ev
    from kontocast.categorize import rules

    _, txs = _load(db)
    pairs = ev.load_labeled(labels, txs)
    if not pairs:
        console.print("[red]Keine Labels zu den Transaktionen gefunden.[/red]")
        raise typer.Exit(1)
    if llm:
        from kontocast.categorize import llm as llm_mod

        predictions = llm_mod.categorize_batch([t for t, _ in pairs])
        result = ev.evaluate(pairs, lambda t: predictions.get(t.tx_id, "Sonstiges"))
    else:
        result = ev.evaluate(pairs, rules.categorize)

    table = Table(title=f"Genauigkeit: {result.accuracy:.1%} ({result.correct}/{result.total})")
    for col in ("Kategorie", "richtig", "gesamt", "Trefferquote"):
        table.add_column(col, justify="right")
    table.columns[0].justify = "left"
    for category, (correct, total) in sorted(result.per_category.items()):
        table.add_row(category, str(correct), str(total), f"{correct / total:.1%}")
    console.print(table)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
