"""Read-only post-hoc Development artifact verification, independent of model code."""

import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_run(root: Path, input_root: Path) -> dict:
    report = json.loads((root / "run.json").read_text())
    binding = report["binding"]["input"]
    expected = (binding["dataset_id"], binding["city_id"], binding["entity_id"])
    with (input_root / "entities.jsonl").open() as stream:
        entities = [json.loads(line) for line in stream]
    summary = next(row for row in entities if tuple(row["identity"]) == expected)
    if summary["role"] != "development":
        raise ValueError("This verifier only permits Development")
    if sha(input_root / "manifest.json") != binding["input_manifest_sha256"]:
        raise ValueError("Input manifest changed")
    manifest = json.loads((input_root / "manifest.json").read_text())
    for name in ("entities.jsonl", "labels.jsonl"):
        if sha(input_root / name) != manifest["files"][name]["sha256"]:
            raise ValueError("Input entity/label artifact changed")
    prefix = ('{"identity": ' + json.dumps(list(expected)) + ', "origin": "').encode()
    labels = {}
    # Never decode other targets, especially Final labels.
    with (input_root / "labels.jsonl").open("rb") as stream:
        for line in stream:
            if line.startswith(prefix):
                row = json.loads(line)
                labels[row["origin"]] = row
    scale = summary["scale"]["energy_scale"]
    retention = report["binding"].get("config", {}).get("state_retention", "all")
    if retention not in {"all", "latest"}:
        raise ValueError("Unknown state-retention policy")
    previous, predictions, scores, file_count, omitted = "0" * 64, {}, [], 0, 0
    decisions, audits, audit_pairs, closed_audits = [], [], {}, set()
    audit_scores = 0
    ticks = sorted(root.glob("tick-*"))
    for index, tick in enumerate(ticks):
        meta = json.loads((tick / "commit.json").read_text())
        if meta["previous"] != previous or meta["index"] != index:
            raise ValueError("Broken daily commit chain")
        if set(meta["files"]) != {"state.pt", "events.jsonl", "forecasts.json"}:
            raise ValueError("Unexpected daily files")
        for name, checksum in meta["files"].items():
            if (
                name == "state.pt"
                and not (tick / name).exists()
                and retention == "latest"
                and index < len(ticks) - 1
            ):
                omitted += 1
                continue
            if sha(tick / name) != checksum:
                raise ValueError("Committed daily file changed")
            file_count += 1
        previous = sha(tick / "commit.json")
        forecast = json.loads((tick / "forecasts.json").read_text())
        # Process score events before today's forecast, exactly as causal replay.
        with (tick / "events.jsonl").open() as events_stream:
            for line in events_stream:
                event = json.loads(line)
                if event["event"] == "decision":
                    decisions.append(
                        {k: v for k, v in event.items() if k not in ("event", "as_of")}
                    )
                if event["event"] == "audit_summary":
                    key = event["switch"]["start"], event["switch"]["lambda"]
                    pairs = audit_pairs.get(key, [])
                    daily = event["daily"]
                    if (
                        key in closed_audits
                        or event["paired_days"] != len(pairs)
                        or len(daily) != len(pairs)
                    ):
                        raise ValueError("Duplicate audit or changed paired audit population")
                    for saved, actual_pair in zip(daily, pairs, strict=True):
                        if saved["origin"] != actual_pair["origin"] or not math.isclose(
                            saved["new_minus_old"],
                            actual_pair["new_minus_old"],
                            rel_tol=1e-9,
                            abs_tol=1e-10,
                        ):
                            raise ValueError(
                                "Audit gap disagrees with original-unit forecast/label recomputation"
                            )
                    expected_mean = (
                        sum(p["new_minus_old"] for p in pairs) / len(pairs) if pairs else None
                    )
                    saved_mean = event["mean_new_minus_old"]
                    if (
                        (saved_mean is None) != (expected_mean is None)
                        or expected_mean is not None
                        and not math.isclose(saved_mean, expected_mean, rel_tol=1e-9, abs_tol=1e-10)
                    ):
                        raise ValueError("Audit summary mean disagrees with recomputed paired gaps")
                    closed_audits.add(key)
                    audits.append(event)
                if event["event"] != "score":
                    continue
                origin = event["origin"]
                issued, checksum = predictions[origin]
                if event["prediction_sha256"] != checksum:
                    raise ValueError("Score points at a different forecast")
                label = labels[origin]
                now = datetime.fromisoformat(event["as_of"])
                if not all(label["file_valid"]) or any(
                    stamp is None or datetime.fromisoformat(stamp) > now
                    for stamp in label["available_at"]
                ):
                    raise ValueError("Score precedes complete label availability")
                if issued["active"] != event["issued_active"]:
                    raise ValueError("Deployed candidate changed retrospectively")
                actual = label["energy_kwh"]
                if len(actual) != 24 or any(
                    v is None or not math.isfinite(v) or v < 0 for v in actual
                ):
                    raise ValueError("Incomplete/invalid labels")
                active = report["candidate_levels"].index(issued["active"])
                for k, pred in enumerate(issued["predictions"]):
                    if len(pred) != 24 or any(not math.isfinite(v) or v < 0 for v in pred):
                        raise ValueError("Invalid prediction")
                    residuals = [a * scale - b for a, b in zip(pred, actual, strict=True)]
                    mae = sum(abs(v) for v in residuals) / 24
                    mse = sum(v * v for v in residuals) / 24
                    if not math.isclose(
                        mae, event["mae_scaled"][k] * scale, rel_tol=1e-9, abs_tol=1e-10
                    ):
                        raise ValueError("Saved MAE disagrees with original-unit recomputation")
                    if not math.isclose(
                        mse, event["mse_scaled"][k] * scale**2, rel_tol=1e-9, abs_tol=1e-10
                    ):
                        raise ValueError("Saved MSE disagrees with original-unit recomputation")
                    if k == active:
                        scores.append((origin, mae, mse))
                audit = issued.get("audit_origin")
                if audit is not None:
                    old_prediction = issued.get("audit_prediction", [])
                    if (
                        len(old_prediction) != 24
                        or any(not math.isfinite(v) or v < 0 for v in old_prediction)
                        or audit["lambda"] not in report["candidate_levels"]
                        or datetime.fromisoformat(audit["start"]) > datetime.fromisoformat(origin)
                    ):
                        raise ValueError("Invalid old-policy audit forecast or switch identity")
                    old_mae = (
                        sum(abs(a * scale - b) for a, b in zip(old_prediction, actual, strict=True))
                        / 24
                    )
                    key = audit["start"], audit["lambda"]
                    audit_pairs.setdefault(key, []).append(
                        {"origin": origin, "new_minus_old": (scores[-1][1] - old_mae) / scale}
                    )
                    audit_scores += 1
                elif "audit_prediction" in issued:
                    raise ValueError("Audit prediction has no identified old policy")
        if forecast:
            origin = forecast["origin"]
            if origin in predictions or tuple(forecast["record"]["identity"]) != expected:
                raise ValueError("Duplicate/wrong target prediction")
            if any(k.startswith("y_") for k in forecast["record"]):
                raise ValueError("Predictor contains labels")
            predictions[origin] = forecast, sha(tick / "forecasts.json")
    if previous != report["commit_chain"] or len(scores) != report["scored_days"]:
        raise ValueError("Report count/chain differs")
    if decisions != report.get("decisions", []) or audits != report.get("audits", []):
        raise ValueError("Report decisions/audits differ from authenticated daily events")
    if len(predictions) != report["issued_days"] or len({s[0] for s in scores}) != len(scores):
        raise ValueError("Forecast count/unique score population differs")
    mae = sum(s[1] for s in scores) / len(scores) if scores else None
    rmse = math.sqrt(sum(s[2] for s in scores) / len(scores)) if scores else None
    for name, value in (("active_mae_kwh", mae), ("active_rmse_kwh", rmse)):
        if (
            value is None
            and report[name] is not None
            or value is not None
            and not math.isclose(value, report[name], rel_tol=1e-9, abs_tol=1e-10)
        ):
            raise ValueError("Aggregate score differs")
    return {
        "state_retention": retention,
        "historical_states_intentionally_omitted": omitted,
        "run_id": root.name,
        "files_hashed": file_count,
        "issued": len(predictions),
        "scored": len(scores),
        "mae_kwh": mae,
        "rmse_kwh": rmse,
        "commit_chain": previous,
        "decision_events_verified": len(decisions),
        "audit_summaries_verified": len(audits),
        "audit_forecast_scores_verified": audit_scores,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--inputs-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    matrix = json.loads(args.matrix.read_text())
    if matrix["status"] != "technical_success":
        raise ValueError("Completed matrix required")
    results = []
    for run in matrix["runs"]:
        binding = run["binding"]["input"]
        name = run["run_id"]
        if Path(name).name != name:
            raise ValueError("Unsafe run identifier")
        local_report = json.loads((args.matrix.parent / name / "run.json").read_text())
        if any(run.get(key) != value for key, value in local_report.items()):
            raise ValueError("Run report differs from identified matrix entry")
        input_name = f"{binding['dataset_id']}-{binding['city_id']}-{binding['history_days']}d"
        results.append(verify_run(args.matrix.parent / name, args.inputs_root / input_name))
    with args.output.open("x") as stream:
        json.dump(
            {"status": "verified", "matrix_sha256": sha(args.matrix), "runs": results},
            stream,
            indent=2,
        )
    print(
        json.dumps(
            {
                "status": "verified",
                "runs": len(results),
                "files_hashed": sum(r["files_hashed"] for r in results),
            }
        )
    )


if __name__ == "__main__":
    main()
