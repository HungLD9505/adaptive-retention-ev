"""Compare energy-only and energy-plus-duration completeness without changing outputs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import subprocess
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TextIO

from tools.sources import ROOT
from tools.urbanev import fingerprint, write_json
from tools.urbanev_hourly import RAW_FIELDS, HourlyConfig


def classify(text: str) -> tuple[float | None, str]:
    """Classify source tokens independently of the processing predicate."""
    if not text.strip():
        return None, "blank"
    try:
        value = float(text)
    except ValueError:
        return None, "malformed"
    if not math.isfinite(value):
        return None, "nonfinite"
    if value < 0:
        return None, "negative"
    return value, "valid"


def compare_station(
    stream: TextIO, config: HourlyConfig, slots: dict[str, int], entity: str
) -> dict:
    """Evaluate both rules on exactly the same source clock and structural conditions."""
    reader = csv.reader(stream)
    if tuple(next(reader, ())) != RAW_FIELDS:
        raise ValueError(f"{entity}: unexpected header")
    a, b = [0] * config.hours, [0] * config.hours
    sums_a, sums_b = [0.0] * config.hours, [0.0] * config.hours
    structural = set()
    disagreement_hours = set()
    seen = set()
    pairs = Counter()
    kinds = Counter()
    mismatch_months = Counter()
    examples: dict[str, list] = {}
    previous = -1
    out_of_order = 0
    for line, row in enumerate(reader, 2):
        if len(row) != len(RAW_FIELDS):
            raise ValueError(f"{entity}:{line}: malformed row")
        slot = slots.get(row[0])
        if slot is None:
            stamp = datetime.fromisoformat(row[0])
            if stamp.tzinfo:
                raise ValueError("Unexpected timezone-aware source")
            effective = stamp - timedelta(minutes=5 if config.interval_label == "end" else 0)
            if config.start <= effective < config.end:
                structural.add(int((effective - config.start).total_seconds() // 3600))
            continue
        hour = slot // 12
        if slot in seen:
            structural.add(hour)
            continue
        seen.add(slot)
        out_of_order += slot < previous
        previous = slot
        volume, vk = classify(row[10])
        duration, dk = classify(row[9])
        kinds[f"volume_{vk}"] += 1
        kinds[f"duration_{dk}"] += 1
        av = vk == "valid"
        bv = av and dk == "valid"
        pairs[
            f"volume_{'valid' if av else 'invalid'}_duration_"
            f"{'valid' if dk == 'valid' else 'invalid'}"
        ] += 1
        if av:
            a[hour] += 1
            sums_a[hour] += volume
        if bv:
            b[hour] += 1
            sums_b[hour] += volume
        category = None
        if av and dk != "valid":
            category = "valid_volume_invalid_duration"
        elif not av and dk == "valid":
            category = "invalid_volume_valid_duration"
        elif bv and volume == 0 and duration > 0:
            category = "zero_volume_positive_duration"
        elif bv and volume > 0 and duration == 0:
            category = "positive_volume_zero_duration"
        if category:
            pairs[category] += 1
            if bv:
                disagreement_hours.add(hour)
                mismatch_months[row[0][:7]] += 1
            if len(examples.setdefault(category, [])) < 3:
                examples[category].append(
                    {
                        "entity_id": entity,
                        "timestamp": row[0],
                        "volume": row[10],
                        "duration": row[9],
                    }
                )
    hourly = Counter()
    distributions_a, distributions_b = Counter(a), Counter(b)
    only_duration_examples = []
    for hour in range(config.hours):
        valid_a = a[hour] == 12 and hour not in structural and math.isfinite(sums_a[hour])
        valid_b = b[hour] == 12 and hour not in structural and math.isfinite(sums_b[hour])
        hourly["rule_a_retained"] += valid_a
        hourly["rule_b_retained"] += valid_b
        hourly["rejected_only_by_duration"] += valid_a and not valid_b
        hourly["retained_only_by_b"] += valid_b and not valid_a
        hourly["rule_b_retained_with_zero_disagreement"] += valid_b and hour in disagreement_hours
        if valid_a and not valid_b and len(only_duration_examples) < 3:
            only_duration_examples.append(
                {"hour_index": hour, "volume_samples": a[hour], "paired_samples": b[hour]}
            )
    return {
        "entity_id": entity,
        "hours": config.hours,
        "hourly": dict(hourly),
        "sample_pairs": dict(pairs),
        "token_kinds": dict(kinds),
        "valid_volume_samples_per_hour": dict(sorted(distributions_a.items())),
        "valid_pair_samples_per_hour": dict(sorted(distributions_b.items())),
        "zero_disagreement_months": dict(mismatch_months),
        "examples": examples,
        "duration_only_hour_examples": only_duration_examples,
        "out_of_order_rows": out_of_order,
        "structurally_invalid_hours": len(structural),
        "unique_grid_samples": len(seen),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-run", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    reference = args.reference_run.resolve()
    if Path(args.run_id).name != args.run_id or args.run_id in {".", ".."}:
        parser.error("Unsafe run ID")
    output = (args.output_root / args.run_id).resolve()
    manifest = json.loads((reference / "manifest.json").read_text())
    source = Path(manifest["source_root"]).resolve()
    if (
        output.is_relative_to(source.parent)
        or output.is_relative_to(reference)
        or source.is_relative_to(output)
        or output.is_relative_to(Path(manifest["archive"]["path"]).parent.resolve())
        or output.is_relative_to((ROOT / "data/raw").resolve())
    ):
        parser.error("Analysis output must be separate from source/reference artifacts")
    output.mkdir(parents=True, exist_ok=False)
    began = time.perf_counter()
    result = {
        "run_id": args.run_id,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "reference_run_id": manifest["run_id"],
        "reference_manifest_sha256": fingerprint(reference / "manifest.json")["sha256"],
        "reference_archive_sha256": manifest["archive"]["sha256"],
        "config": manifest["config"],
        "python": platform.python_version(),
        "code_commit": subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip(),
        "analysis_source_sha256": fingerprint(Path(__file__))["sha256"],
        "rules": {
            "A": "12 unique finite nonnegative volume values",
            "B": "12 unique finite nonnegative volume/duration pairs; existing pipeline",
        },
        "pipeline_outputs_modified": False,
    }
    try:
        if manifest["status"] != "technical_qc_pass":
            raise ValueError("Reference must be a completed technical-QC run")
        c = manifest["config"]
        config = HourlyConfig(
            datetime.fromisoformat(c["start_local"]),
            datetime.fromisoformat(c["end_local_exclusive"]),
            c["timezone"],
            c["source_interval_label"],
        )
        slots = config.slots()
        reference_qc = json.loads((reference / "station_qc.json").read_text())
        records = []
        for index, original in enumerate(reference_qc, 1):
            path = source / original["input"]["path"]
            if not path.resolve().is_relative_to(source):
                raise ValueError("Unsafe source member")
            identity = fingerprint(path)
            if identity["sha256"] != original["input"]["sha256"]:
                raise ValueError(f"Input changed since reference: {path.name}")
            with path.open(newline="", encoding="utf-8-sig") as stream:
                station = compare_station(stream, config, slots, original["entity_id"])
            if station["hourly"]["rule_b_retained"] != original["diagnostics"].get(
                "valid_hours", 0
            ):
                raise ValueError(f"Independent Rule B differs from reference: {path.name}")
            records.append(station)
            if index % 100 == 0 or index == len(reference_qc):
                print(f"Compared {index}/{len(reference_qc)} stations", flush=True)
        result["stations"] = len(records)
        result["hours"] = config.hours * len(records)
        for key in [
            "hourly",
            "sample_pairs",
            "token_kinds",
            "zero_disagreement_months",
            "valid_volume_samples_per_hour",
            "valid_pair_samples_per_hour",
        ]:
            total = Counter()
            for r in records:
                total.update(r[key])
            result[key] = dict(sorted(total.items()))
        result["stations_with_duration_only_losses"] = sum(
            r["hourly"]["rejected_only_by_duration"] > 0 for r in records
        )
        result["zero_disagreement_station_count"] = sum(
            r["sample_pairs"].get("zero_volume_positive_duration", 0)
            + r["sample_pairs"].get("positive_volume_zero_duration", 0)
            > 0
            for r in records
        )
        result["top_zero_disagreement_stations"] = sorted(
            [
                {
                    "entity_id": r["entity_id"],
                    "zero_volume_positive_duration": r["sample_pairs"].get(
                        "zero_volume_positive_duration", 0
                    ),
                    "positive_volume_zero_duration": r["sample_pairs"].get(
                        "positive_volume_zero_duration", 0
                    ),
                }
                for r in records
            ],
            key=lambda r: r["zero_volume_positive_duration"] + r["positive_volume_zero_duration"],
            reverse=True,
        )[:10]
        result["examples"] = {}
        for r in records:
            for key, values in r["examples"].items():
                result["examples"].setdefault(key, []).extend(values)
        result["examples"] = {k: v[:5] for k, v in result["examples"].items()}
        write_json(output / "station_comparison.json", records)
        result["station_comparison_sha256"] = fingerprint(output / "station_comparison.json")[
            "sha256"
        ]
        result["status"] = "passed"
    except (OSError, ValueError, KeyError, csv.Error) as error:
        result["status"] = "failed"
        result["error"] = str(error)
        raise
    finally:
        result["elapsed_seconds"] = time.perf_counter() - began
        write_json(output / "comparison.json", result)
    print(
        json.dumps(
            {k: result[k] for k in ["stations", "hours", "hourly", "sample_pairs"]}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
