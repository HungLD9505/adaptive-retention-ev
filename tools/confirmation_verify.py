"""Independent saved-vector, delayed-label, hash-chain and interval confirmation audit."""

import argparse
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import torch

from ev_runner.state import state_digest


def fingerprint(path: Path) -> str:
    """Hash bytes without trusting recorded digests."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def equal(actual: object, expected: object) -> None:
    """Reject numerical mismatches, including missing or nonfinite values."""
    np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-10)


def independent_arms(cell: dict, recipe: dict) -> dict:
    """Reconstruct exponential expert updates directly, without controller helpers."""
    stable, fast, labels = (np.asarray(cell[k]) for k in ("stable", "fast", "labels"))
    clocks = [datetime.fromisoformat(v) for v in cell["origins"]]
    arrivals = [datetime.fromisoformat(v) for v in cell["available_at"]]
    losses = np.stack([abs(stable - labels).mean(1), abs(fast - labels).mean(1)], axis=1)
    losses /= cell["scale"]
    probabilities = np.array([recipe["initial_weight"], 1 - recipe["initial_weight"]])
    consumed, weights, predictions = set(), [], []
    for index, clock in enumerate(clocks):
        for earlier in sorted(range(index), key=lambda j: (arrivals[j], clocks[j])):
            if earlier in consumed or arrivals[earlier] > clock:
                continue
            likelihood = np.exp(-recipe["eta"] * (losses[earlier] - losses[earlier].min()))
            posterior = probabilities * likelihood
            posterior /= posterior.sum()
            probabilities = (1 - recipe["share"]) * posterior + recipe["share"] * posterior[::-1]
            consumed.add(earlier)
        weights.append(probabilities[0])
        predictions.append(probabilities[0] * stable[index] + probabilities[1] * fast[index])
    result = {}
    for name, vector in {
        "fixed": stable,
        "fast_only": fast,
        "static": recipe["initial_weight"] * stable + (1 - recipe["initial_weight"]) * fast,
        "adaptive": np.asarray(predictions),
    }.items():
        daily = abs(vector - labels).mean(1)
        result[name] = {"predictions_kwh": vector, "daily_mae": daily, "mae": daily.mean()}
    result["adaptive"]["weights"] = weights
    return result


def independent_intervals(data: dict, profile: dict) -> dict:
    """Recompute identical draws using calendar multiplicities and matrix products."""
    rng = np.random.default_rng(profile["seed"])
    samples = {name: np.zeros(profile["resamples"]) for name in ("fixed", "static")}
    valid = {name: np.ones(profile["resamples"], bool) for name in samples}
    length = profile["segment_days"]
    for namespace in sorted(data):
        arrays = data[namespace]
        count, days = arrays["adaptive"].shape
        for offset in range(0, profile["resamples"], 128):
            size = min(128, profile["resamples"] - offset)
            selected = rng.integers(count, size=(size, count))
            starts = rng.integers(days, size=(size, int(np.ceil(days / length))))
            dates = ((starts[..., None] + np.arange(length)) % days).reshape(size, -1)[:, :days]
            multiplicity = np.array([np.bincount(row, minlength=days) for row in dates])
            finite_counts = np.isfinite(arrays["adaptive"]).astype(float) @ multiplicity.T
            scores = {}
            for name, values in arrays.items():
                numerator = np.nan_to_num(values) @ multiplicity.T
                scores[name] = (numerator / np.maximum(finite_counts, 1))[
                    selected, np.arange(size)[:, None]
                ].mean(1)
            good = (finite_counts[selected, np.arange(size)[:, None]] > 0).all(1)
            for name in samples:
                okay = good & (scores[name] > 0)
                valid[name][offset : offset + size] &= okay
                contribution = np.zeros(size)
                contribution[okay] = (
                    100 * (scores[name][okay] - scores["adaptive"][okay]) / scores[name][okay]
                )
                samples[name][offset : offset + size] += contribution / len(data)
    alpha = profile["alpha_per_comparison"]
    return {
        name: {
            "invalid_replicates": int((~valid[name]).sum()),
            "interval_percent": None
            if not valid[name].all()
            else np.quantile(values, [alpha / 2, 1 - alpha / 2]).tolist(),
        }
        for name, values in samples.items()
    }


def verify(
    protocol_path: Path, run: Path, analysis: Path, input_parent: Path, base: Path, output: Path
) -> dict:
    """Authenticate saved artifacts against selected original inputs and separate arithmetic."""
    protocol = json.loads(protocol_path.read_text())
    results = json.loads((analysis / "results.json").read_text())
    completion = json.loads((run / "completion.json").read_text())
    assert completion["complete"] and not completion["failures"]
    assert fingerprint(protocol_path) == results["protocol_sha256"]
    counters = dict(cells=0, expert_runs=0, committed_ticks=0, expert_scored_days=0, checkpoints=0)
    data, groups, evidence = {}, {}, []
    for group in protocol["groups"]:
        namespace = group["namespace"]
        source_states = {}
        for seed, source in group["sources"].items():
            assert fingerprint(base / source["path"]) == source["sha256"]
            checkpoint = torch.load(base / source["path"], weights_only=True, map_location="cpu")
            assert checkpoint["completed_epochs"] == 10
            assert (
                checkpoint["metadata"]["source_population_sha256"]
                == group["source_population_sha256"]
            )
            assert checkpoint["metadata"]["training_config"]["seed"] == int(seed)
            source_states[int(seed)] = state_digest(checkpoint["model"])
        folder = input_parent / (namespace + "-14d")
        assert fingerprint(folder / "manifest.json") == group["input_manifest_sha256"]
        manifest = json.loads((folder / "manifest.json").read_text())
        for name, entry in manifest["files"].items():
            assert fingerprint(folder / name) == entry["sha256"]
        entities = [
            json.loads(line) for line in (folder / "entities.jsonl").read_text().splitlines()
        ]
        selected = {
            tuple(row["identity"]): row
            for row in entities
            if row["identity"][2] in group["selected_ids"]
        }
        assert len(selected) == len(group["selected_ids"])
        prefixes = {
            ('{"identity": ' + json.dumps(list(identity)) + ', "origin": "').encode(): identity
            for identity in selected
        }
        labels = {}
        with (folder / "labels.jsonl").open("rb") as stream:
            for line in stream:
                for prefix, identity in prefixes.items():
                    if line.startswith(prefix):
                        row = json.loads(line)
                        labels[identity[2], row["origin"]] = row
                        break
        manifest_path = run / namespace / "manifest.json"
        expected = next(g for g in completion["complete_groups"] if g["namespace"] == namespace)
        assert fingerprint(manifest_path) == expected["manifest_sha256"]
        entries = json.loads(manifest_path.read_text())
        assert len(entries) == len(group["selected_ids"]) * len(protocol["seeds"])
        assert {(e["target"], e["seed"]) for e in entries} == {
            (t, s) for t in group["selected_ids"] for s in protocol["seeds"]
        }
        days_by_target = {}
        means = {name: [] for name in ("fixed", "static", "adaptive", "fast_only")}
        for entry in entries:
            path = Path(entry["path"])
            assert fingerprint(path) == entry["sha256"]
            saved = json.loads(path.read_text())
            cell = saved["cell"]
            assert cell is not None
            target, seed = entry["target"], entry["seed"]
            assert (saved["target"], saved["seed"], saved["namespace"]) == (target, seed, namespace)
            assert saved["protocol_sha256"] == fingerprint(protocol_path)
            identity = next(i for i in selected if i[2] == target)
            equal(cell["scale"], selected[identity]["scale"]["energy_scale"])
            for origin, available, vector in zip(
                cell["origins"], cell["available_at"], cell["labels"], strict=True
            ):
                row = labels[target, origin]
                assert all(row["file_valid"]) and all(row["available_at"])
                equal(row["energy_kwh"], vector)
                clock = datetime.fromisoformat(available)
                assert clock >= datetime.fromisoformat(origin) + timedelta(days=1)
                assert max(map(datetime.fromisoformat, row["available_at"])) <= clock
            for name, key, coefficient in (("stable", "stable", 1.0), ("fast", "fast", 0.0)):
                expert = run / namespace / f"{name}-{target}-{seed}"
                ticks, previous, forecasts, scores = sorted(expert.glob("tick-*")), "0" * 64, {}, {}
                for index, tick in enumerate(ticks):
                    commit = json.loads((tick / "commit.json").read_text())
                    assert commit["index"] == index and commit["previous"] == previous
                    for file, checksum in commit["files"].items():
                        assert file in {"state.pt", "events.jsonl", "forecasts.json"}
                        if file == "state.pt" and index < len(ticks) - 1:
                            continue
                        assert fingerprint(tick / file) == checksum
                    previous = fingerprint(tick / "commit.json")
                    forecast = json.loads((tick / "forecasts.json").read_text())
                    if forecast:
                        assert forecast["origin"] not in forecasts
                        assert forecast["lambda"] == coefficient
                        forecasts[forecast["origin"]] = (
                            forecast["prediction"],
                            fingerprint(tick / "forecasts.json"),
                        )
                    for event in map(json.loads, (tick / "events.jsonl").read_text().splitlines()):
                        if event["event"] == "score":
                            assert event["origin"] not in scores
                            scores[event["origin"]] = event
                assert set(scores) == set(cell["origins"])
                for i, origin in enumerate(cell["origins"]):
                    vector, checksum = forecasts[origin]
                    equal(np.asarray(vector) * cell["scale"], cell[key][i])
                    assert scores[origin]["prediction_sha256"] == checksum
                    assert scores[origin]["as_of"] == cell["available_at"][i]
                    equal(
                        scores[origin]["mae_kwh"],
                        abs(np.asarray(cell[key][i]) - cell["labels"][i]).mean(),
                    )
                state = torch.load(ticks[-1] / "state.pt", weights_only=True, map_location="cpu")
                metadata = json.loads((expert / "run.json").read_text())
                binding = metadata["binding"]
                assert binding == json.loads((expert / "binding.json").read_text())
                assert binding["protocol_sha256"] == fingerprint(protocol_path)
                assert (
                    binding["input"]["source_checkpoint_sha256"]
                    == group["sources"][str(seed)]["sha256"]
                )
                assert binding["input"]["input_manifest_sha256"] == group["input_manifest_sha256"]
                assert binding["input"]["entity_id"] == target
                assert (
                    state["source_state_sha256"]
                    == source_states[seed]
                    == metadata["source_frozen_sha256"]
                )
                assert state_digest(state["branch"]) == metadata["final_state_sha256"]
                assert state["virtual_steps"] == 0 and state["current_lambda"] == coefficient
                assert all(
                    torch.isfinite(tensor).all() for tensor in state["branch"]["model"].values()
                )
                counters["expert_runs"] += 1
                counters["committed_ticks"] += len(ticks)
                counters["expert_scored_days"] += len(scores)
                counters["checkpoints"] += 1
            reconstructed = independent_arms(cell, protocol["recipe"])
            for name, arm in reconstructed.items():
                for field, value in arm.items():
                    equal(value, saved["arms"][name][field])
                means[name].append((target, arm["mae"]))
            start = datetime.fromisoformat(group["deployment"]).date()
            indices = [(datetime.fromisoformat(o).date() - start).days for o in cell["origins"]]
            arrays = days_by_target.setdefault(
                target, {name: [] for name in ("fixed", "static", "adaptive")}
            )
            for name in arrays:
                row = np.full(90, np.nan)
                row[indices] = reconstructed[name]["daily_mae"]
                arrays[name].append(row)
            counters["cells"] += 1
            evidence.append({"path": str(path), "sha256": fingerprint(path)})
        groups[namespace] = {
            name: float(
                np.mean(
                    [
                        np.mean([v for t, v in pairs if t == target])
                        for target in group["selected_ids"]
                    ]
                )
            )
            for name, pairs in means.items()
        }
        expected_group = next(g for g in results["group_results"] if g["namespace"] == namespace)
        for name, value in groups[namespace].items():
            equal(value, expected_group[name])
        data[namespace] = {
            name: np.array(
                [np.mean(days_by_target[t][name], axis=0) for t in group["selected_ids"]]
            )
            for name in ("fixed", "static", "adaptive")
        }
        print(f"Verified {namespace}: {len(group['selected_ids'])} entities", flush=True)
    for name in ("fixed", "static"):
        point = np.mean([100 * (g[name] - g["adaptive"]) / g[name] for g in groups.values()])
        equal(point, results["primary"]["comparisons"][name]["equal_namespace_reduction_percent"])
    for length, profile in results["sensitivity"].items():
        oracle = independent_intervals(data, profile)
        for name, value in oracle.items():
            expected = profile["comparisons"][name]
            assert value["invalid_replicates"] == expected["invalid_replicates"]
            if value["interval_percent"] is None:
                assert expected["interval_percent"] is None
            else:
                equal(value["interval_percent"], expected["interval_percent"])
        print(f"Verified block-{length} intervals", flush=True)
    receipt = {
        "status": "passed",
        "counts": counters,
        "verifier_sha256": fingerprint(Path(__file__)),
        "protocol_sha256": fingerprint(protocol_path),
        "results_sha256": fingerprint(analysis / "results.json"),
        "authenticated_cells": evidence,
        "scope": "Original selected labels and arrival clocks; all saved expert prediction/score hashes and tick chains; latest full checkpoints; independent exponential mixing and calendar-count bootstrap arithmetic.",
        "limits": "Software replay, not physical deployment. Historical state bytes pruned by declared latest policy cannot be rehashed; their commitments remain. Previously prepared inputs, not fresh raw archive validation. No independent external dataset or physical-site alias guarantee.",
    }
    with output.open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    for name in ("protocol", "run", "analysis", "input-parent", "base", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    verify(args.protocol, args.run, args.analysis, args.input_parent, args.base, args.output)


if __name__ == "__main__":
    main()
