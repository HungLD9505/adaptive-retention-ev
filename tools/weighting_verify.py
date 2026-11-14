"""High-precision independent reference for the one bounded weighting attempt."""

import argparse
import json
import math
import sys
from datetime import datetime
from decimal import Decimal, localcontext
from pathlib import Path

import numpy as np

from ev_models.checkpoint import digest


def decimal_weights(total: list[Decimal], eta: Decimal | None) -> list[Decimal]:
    """Uniform leader ties, otherwise directly normalized Decimal exponentials."""
    low = min(total)
    masses = (
        [Decimal(value == low) for value in total]
        if eta is None
        else [(-(value - low) * eta).exp() for value in total]
    )
    return [v / sum(masses) for v in masses]


def reference_weights(cell: dict, method: str, initial: float) -> list[float]:
    """Independent Figure-1 mix-loss differences, using 50-digit arithmetic."""
    with localcontext() as context:
        context.prec = 50
        total, gap = [Decimal(0), Decimal(0)], Decimal(0)
        weight = Decimal("0.5") if method in ("adahedge", "ftl") else Decimal(str(initial))
        origins = [datetime.fromisoformat(x) for x in cell["origins"]]
        arrivals = [datetime.fromisoformat(x) for x in cell["available_at"]]
        stable, fast, labels = (np.asarray(cell[k]) for k in ["stable", "fast", "labels"])
        losses = (
            np.stack([abs(stable - labels).mean(1), abs(fast - labels).mean(1)], axis=1)
            / cell["scale"]
        )
        consumed, output, count = set(), [], 0
        log2 = Decimal(2).ln()
        for index, clock in enumerate(origins):
            for j in sorted(range(index), key=lambda k: (arrivals[k], origins[k])):
                if j in consumed or arrivals[j] > clock:
                    continue
                loss = [Decimal(str(x)) for x in losses[j]]
                if method == "adahedge":
                    eta = log2 / gap if gap else None
                    probabilities = decimal_weights(total, eta)
                    before = min(total)
                    if eta is not None:
                        masses = [(-(v - before) * eta).exp() for v in total]
                        before -= (sum(masses) / 2).ln() / eta
                    next_total = [x + y for x, y in zip(total, loss, strict=True)]
                    after = min(next_total)
                    if eta is not None:
                        masses = [(-(v - after) * eta).exp() for v in next_total]
                        after -= (sum(masses) / 2).ln() / eta
                    increment = sum(
                        weight * value for weight, value in zip(probabilities, loss, strict=True)
                    ) - (after - before)
                    if increment < Decimal("-1e-40"):
                        raise ValueError("Reference negative gap")
                    gap += max(Decimal(0), increment)
                    total = next_total
                    weight = decimal_weights(total, log2 / gap if gap else None)[0]
                elif method == "ftl":
                    total = [x + y for x, y in zip(total, loss, strict=True)]
                    weight = decimal_weights(total, None)[0]
                else:
                    a = weight * (-Decimal("0.1") * (loss[0] - min(loss))).exp()
                    b = (1 - weight) * (-Decimal("0.1") * (loss[1] - min(loss))).exp()
                    posterior = a / (a + b)
                    share = (
                        Decimal(1) / Decimal(count + 2)
                        if method == "decreasing_share"
                        else Decimal(0)
                    )
                    weight = share + (1 - 2 * share) * posterior
                consumed.add(j)
                count += 1
            output.append(float(weight))
        return output


def verify(protocol_path: Path, output: Path, receipt_path: Path) -> dict:
    """Check original identity, old controls, all candidate predictions and stop rule."""
    protocol = json.loads(protocol_path.read_text())
    source = Path(protocol["development_cells"]["path"])
    if digest(source) != protocol["development_cells"]["sha256"]:
        raise ValueError("Development source fingerprint mismatch")
    prior = Path(protocol["development_cells"]["prior_verification_path"])
    if digest(prior) != protocol["development_cells"]["prior_verification_sha256"]:
        raise ValueError("Prior verification fingerprint mismatch")
    original = {(r["target"], r["seed"]): r for r in json.loads(source.read_text())}
    rows = json.loads((output / "cells.json").read_text())
    result = json.loads((output / "results.json").read_text())
    if result["protocol_sha256"] != digest(protocol_path):
        raise ValueError("Protocol fingerprint mismatch")
    if {(r["target"], r["seed"]) for r in rows} != set(original) or len(rows) != 36:
        raise ValueError("Source-cell matrix mismatch")
    maximum_weight_gap = maximum_prediction_gap = 0.0
    entries = []
    for row in rows:
        old = original[row["target"], row["seed"]]
        if old["cell"] != row["cell"]:
            raise ValueError("Source-cell identity mismatch")
        for name, old_name in [
            ("fixed", "stable_fixed"),
            ("fast", "fast_only"),
            ("static", "static_mix"),
            ("legacy", "fixed_share"),
        ]:
            np.testing.assert_allclose(
                row["arms"][name]["predictions_kwh"],
                old["arms"][old_name]["predictions_kwh"],
                rtol=1e-12,
                atol=1e-10,
            )
        stable, fast, labels = (np.asarray(row["cell"][k]) for k in ["stable", "fast", "labels"])
        for method in protocol["candidates"]:
            weight = np.asarray(reference_weights(row["cell"], method, protocol["initial_weight"]))
            saved = row["arms"][method]
            maximum_weight_gap = max(
                maximum_weight_gap, float(abs(weight - saved["weights"]).max())
            )
            np.testing.assert_allclose(weight, saved["weights"], rtol=1e-9, atol=1e-9)
            predictions = weight[:, None] * stable + (1 - weight[:, None]) * fast
            maximum_prediction_gap = max(
                maximum_prediction_gap, float(abs(predictions - saved["predictions_kwh"]).max())
            )
            np.testing.assert_allclose(predictions, saved["predictions_kwh"], rtol=1e-9, atol=1e-8)
            daily = abs(predictions - labels).mean(1)
            np.testing.assert_allclose(daily, saved["daily_mae"], rtol=1e-9, atol=1e-8)
            if not math.isclose(float(daily.mean()), saved["mae"], rel_tol=1e-9, abs_tol=1e-8):
                raise ValueError("Candidate MAE mismatch")
            entries.append(
                dict(target=row["target"], seed=row["seed"], method=method, mae=saved["mae"])
            )
    for method in protocol["candidates"]:
        mean = np.mean(
            [
                np.mean([r["mae"] for r in entries if r["target"] == t and r["method"] == method])
                for t in protocol["development_ids"]
            ]
        )
        if not math.isclose(mean, result["means"][method], abs_tol=1e-12):
            raise ValueError("Candidate aggregate mismatch")
    selected = min(
        protocol["candidates"], key=lambda m: (result["means"][m], protocol["candidates"].index(m))
    )
    if selected != result["selected"]:
        raise ValueError("Selected method mismatch")
    expected_gate = all(
        result["means"][selected] < result["means"][name] for name in ["fixed", "static", "legacy"]
    )
    if result["proceed_to_new_cohort"] is not expected_gate:
        raise ValueError("Proceed gate mismatch")
    receipt = dict(
        status="passed",
        source_cells=36,
        candidate_cells=144,
        decimal_precision=50,
        max_weight_difference=maximum_weight_gap,
        max_prediction_difference_kwh=maximum_prediction_gap,
        protocol_sha256=digest(protocol_path),
        results_sha256=digest(output / "results.json"),
        saved_candidate_cells_sha256=digest(output / "cells.json"),
        verifier_sha256=digest(Path(__file__)),
        source_verification_sha256=digest(prior),
        stop_rule_reproduced=True,
        python_optimization=sys.flags.optimize,
        limits="Conditional replay on already exposed Development inputs; independent arithmetic is not an effectiveness or delay-free regret guarantee. Fresh source readback is recorded separately.",
    )
    with receipt_path.open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps(receipt, indent=2))
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    for name in ["protocol", "output", "receipt"]:
        parser.add_argument("--" + name, type=Path, required=True)
    a = parser.parse_args()
    verify(a.protocol, a.output, a.receipt)


if __name__ == "__main__":
    main()
