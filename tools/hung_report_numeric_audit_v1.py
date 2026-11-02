"""Check the published bounded-Final numeric claims against tracked result tables."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

VARIANTS = {
    "Target-only": "target_only",
    "Main confidence controller": "main",
    "Seasonal Naive": "seasonal_naive",
    "Frozen Source": "frozen_source",
    "Full fine-tuning": "full_finetuning",
    "Fixed retention": "fixed_retention",
    "Online best-λ / without confidence": "online_best_lambda",
    "Source-error controller": "source_error",
    "Uncertainty controller": "uncertainty",
    "Drift controller": "drift",
    "Parameter retention": "parameter_retention",
    "Changed block to 7 days": "block7",
    "Changed block to 28 days": "block28",
    "No Source initialization": "no_source",
}
ABLATIONS = {
    "Without confidence / online best-λ": "online_best_lambda",
    "Fixed λ / fixed retention": "fixed_retention",
    "Parameter retention": "parameter_retention",
    "Block size 7 instead of 14": "block7",
    "Block size 28 instead of 14": "block28",
    "Without Source initialization / no_source": "no_source",
}
BUDGETS = (7, 14, 28)


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _table(report: str, heading: str, width: int) -> list[list[str]]:
    marker = f"| {heading} |"
    if report.count(marker) != 1:
        raise ValueError(f"Expected one report table: {heading}")
    lines = report.split(marker, 1)[1].split("\n\n", 1)[0].splitlines()
    result = []
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != width:
            raise ValueError(f"Malformed {heading} row: {line}")
        result.append(cells)
    return result


def _match(shown: str, source: str | float, digits: int, label: str) -> None:
    tolerance = 0.5 * 10 ** (-digits) + 1e-10
    if abs(float(shown.replace("−", "-")) - float(source)) > tolerance:
        raise ValueError(f"{label}: report {shown} differs from source {source}")


def audit(report_path: Path, station_path: Path, wape_path: Path) -> dict:
    """Validate 90 displayed numeric cells, without modifying any input."""
    report = report_path.read_text(encoding="utf-8")
    with station_path.open(newline="", encoding="utf-8") as stream:
        stations = list(csv.DictReader(stream))
    station_rows = {
        (row["variant"], int(row["budget_days"]), row["reference"]): row for row in stations
    }
    if len(station_rows) != len(stations):
        raise ValueError("Duplicate station-first variant/budget/reference row")
    wape = json.loads(wape_path.read_text(encoding="utf-8"))
    wape_rows = {
        (row["variant"], row["budget_days"]): row["equal_station_wape"]
        for row in wape["station_first"]
    }
    if len(wape_rows) != len(wape["station_first"]):
        raise ValueError("Duplicate WAPE variant/budget row")

    checked = 0
    panel = _table(report, "Executed variant", 4)
    if len(panel) != len(VARIANTS) or {row[0] for row in panel} != set(VARIANTS):
        raise ValueError("Final MAE panel is not the exact 14-variant set")
    for name, *values in panel:
        variant = VARIANTS[name]
        for budget, shown in zip(BUDGETS, values, strict=True):
            reference = "main" if variant == "target_only" else "target_only"
            source = station_rows[(variant, budget, reference)]["method_mae_kwh"]
            _match(shown, source, 3, f"panel {variant}/{budget}")
            checked += 1

    ablations = _table(report, "Required ablation / executed identity", 5)
    if len(ablations) != len(ABLATIONS) or {row[0] for row in ablations} != set(ABLATIONS):
        raise ValueError("Ablation table is not the exact six-row executed set")
    for name, *values in ablations:
        variant = ABLATIONS[name]
        for budget, shown in zip(BUDGETS, values[:3], strict=True):
            source = -float(station_rows[(variant, budget, "main")]["mae_gain_kwh"])
            _match(shown, source, 3, f"ablation {variant}/{budget}")
            checked += 1

    main_rows = _table(report, "Budget (days)", 6)
    if len(main_rows) != 3 or {row[0] for row in main_rows} != {"7", "14", "28"}:
        raise ValueError("Main-versus-Target-only table lacks a locked budget")
    for cells in main_rows:
        budget = int(cells[0])
        source = station_rows[("main", budget, "target_only")]
        shown_main = cells[1].split(" / ")
        shown_target = cells[2].split(" / ")
        interval = re.fullmatch(r"([0-9.]+) \[([0-9.]+), ([0-9.]+)\]", cells[3])
        if len(shown_main) != 2 or len(shown_target) != 2 or interval is None:
            raise ValueError(f"Malformed Main-versus-Target-only row: {budget}")
        values = [
            (shown_main[0], "method_mae_kwh"),
            (shown_main[1], "method_rmse_kwh"),
            (shown_target[0], "reference_mae_kwh"),
            (shown_target[1], "reference_rmse_kwh"),
            (interval.group(1), "mae_gain_kwh"),
            (interval.group(2), "mae_ci95_low_kwh"),
            (interval.group(3), "mae_ci95_high_kwh"),
            (cells[4], "transfer_gain"),
        ]
        for shown, field in values:
            _match(shown, source[field], 3, f"Main/{budget}/{field}")
            checked += 1
        expected_ntr = (
            f"{source['negative_transfer_stations']}/{source['negative_transfer_denominator']}"
        )
        if cells[5] != expected_ntr:
            raise ValueError(f"Main/{budget}/NTR: {cells[5]} differs from {expected_ntr}")

    wape_lines = [
        line
        for line in report.splitlines()
        if line.startswith("The separate [checkpoint WAPE audit]")
    ]
    if len(wape_lines) != 1:
        raise ValueError("Expected one Final WAPE claim paragraph")
    for variant, pattern in (
        ("main", r"WAPE for Main is ([0-9.]+/[0-9.]+/[0-9.]+)"),
        ("target_only", r"Target-only ([0-9.]+/[0-9.]+/[0-9.]+)"),
    ):
        match = re.search(pattern, wape_lines[0])
        if match is None:
            raise ValueError(f"Missing WAPE claim: {variant}")
        for budget, shown in zip(BUDGETS, match.group(1).rstrip(".").split("/"), strict=True):
            _match(shown, wape_rows[(variant, budget)], 6, f"WAPE {variant}/{budget}")
            checked += 1

    if checked != 90:
        raise ValueError(f"Unexpected numeric-cell coverage: {checked}")
    return {
        "schema": "hung-report-numeric-audit-v1",
        "checked_numeric_cells": checked,
        "report_sha256": _sha256(report_path),
        "station_first_sha256": _sha256(station_path),
        "wape_summary_sha256": _sha256(wape_path),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--station-first", type=Path, required=True)
    parser.add_argument("--wape-summary", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(audit(args.report, args.station_first, args.wape_summary), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
