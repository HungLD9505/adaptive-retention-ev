"""Recover bounded Development switch traces from repo-local saved manifests."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from tools.hung_development_audit import ROOT, require, sha256


def pinned(path: Path, digest: str) -> bytes:
    resolved = path.resolve()
    require(resolved.is_relative_to(ROOT), "Input outside repository")
    raw = resolved.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == digest, f"Input SHA differs: {path.name}")
    return raw


def decision_counts(manifest: dict, job_id: str) -> tuple[int | None, int | None]:
    evidence = manifest.get("event_evidence")
    require(isinstance(evidence, dict), f"Event evidence absent: {job_id}")
    decisions = evidence.get("decisions")
    if decisions is None:
        require(
            isinstance(evidence.get("issued_count"), int),
            f"Decision list and issued count absent: {job_id}",
        )
        return None, None
    require(isinstance(decisions, list), f"Invalid decision list: {job_id}")
    switches = 0
    for decision in decisions:
        require(isinstance(decision, dict), f"Invalid decision entry: {job_id}")
        current = decision.get("current_level")
        selected = decision.get("selected_level")
        require(
            isinstance(current, (int, float))
            and not isinstance(current, bool)
            and isinstance(selected, (int, float))
            and not isinstance(selected, bool),
            f"Decision level absent: {job_id}",
        )
        switches += selected != current
    return len(decisions), switches


def local_trace(row: dict, run: dict) -> dict:
    job_id = row["job_id"]
    require(
        int(row["budget_days"]) == run["budget"]
        and row["entity_id"] == run["entity_id"]
        and int(row["seed"]) == run["seed"],
        f"Ledger cell differs: {job_id}",
    )
    archive = (ROOT / row["archive_path"]).resolve()
    require(archive.is_relative_to(ROOT / ".cache"), f"Archive outside cache: {job_id}")
    manifest_member = f"jobs/{job_id}/replay-90/run_manifest.json"
    with zipfile.ZipFile(archive) as bundle:
        receipt_raw = bundle.read(row["job_receipt_path"])
        manifest_raw = bundle.read(manifest_member)
    receipt_sha = hashlib.sha256(receipt_raw).hexdigest()
    manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
    require(receipt_sha == row["job_receipt_sha256"], f"Receipt SHA differs: {job_id}")
    receipt = json.loads(receipt_raw)
    require(receipt.get("job_id") == job_id, f"Receipt ID differs: {job_id}")
    stages = dict(part.split(":", 1) for part in row["stage_manifest_sha256"].split(";"))
    require(stages.get("replay-90") == manifest_sha, f"Ledger manifest SHA differs: {job_id}")
    require(run["manifest"]["sha256"] == manifest_sha, f"Merged manifest SHA differs: {job_id}")
    manifest = json.loads(manifest_raw)
    require(manifest.get("run_id") == "replay-90", f"Stage ID differs: {job_id}")
    decisions, switches = decision_counts(manifest, job_id)
    return {
        "job_id": job_id,
        "source_kind": "local_ledger_archive",
        "method": run["method"],
        "budget_days": run["budget"],
        "entity_id": run["entity_id"],
        "seed": run["seed"],
        "archive_sha256": row["archive_sha256"],
        "job_receipt_sha256": receipt_sha,
        "manifest_sha256": manifest_sha,
        "decisions": decisions,
        "switches": switches,
        "evidence_level": "ARCHIVE_RECEIPT_MANIFEST"
        if decisions is not None
        else "ISSUED_COUNT_ONLY",
    }


def main_trace(
    run: dict, pair: dict, capsule: zipfile.ZipFile, capsule_row: dict, capsule_sha: str
) -> dict:
    job_id = run["job_id"]
    require(
        int(pair["budget_days"]) == run["budget"] and int(pair["seed"]) == run["seed"],
        f"Historical pair cell differs: {job_id}",
    )
    path = ROOT / ".cache" / "block7-review-v1" / "manifests" / f"{job_id}.json"
    raw = capsule.read(f"historical/{job_id}/run_manifest.json")
    digest = hashlib.sha256(raw).hexdigest()
    require(
        hashlib.sha256(path.read_bytes()).hexdigest() == digest, f"Direct copy differs: {job_id}"
    )
    require(digest == pair["main_manifest_sha256"], f"Pair manifest SHA differs: {job_id}")
    require(digest == run["manifest"]["sha256"], f"Merged manifest SHA differs: {job_id}")
    require(
        capsule_row["run_manifest"]["sha256"] == digest
        and capsule_row["status"] == "VERIFIED_REUSE",
        f"Capsule ledger binding differs: {job_id}",
    )
    manifest = json.loads(raw)
    require(manifest.get("run_id") == "replay-90", f"Stage ID differs: {job_id}")
    decisions, switches = decision_counts(manifest, job_id)
    return {
        "job_id": job_id,
        "source_kind": "historical_main_manifest",
        "method": run["method"],
        "budget_days": run["budget"],
        "entity_id": run["entity_id"],
        "seed": run["seed"],
        "archive_sha256": capsule_sha,
        "job_receipt_sha256": None,
        "manifest_sha256": digest,
        "decisions": decisions,
        "switches": switches,
        "evidence_level": "CAPSULE_LEDGER_MANIFEST_NO_JOB_RECEIPT"
        if decisions is not None
        else "ISSUED_COUNT_ONLY",
    }


def audit(
    merged: dict,
    ledger: list[dict],
    pairs: list[dict],
    kaggle: list[dict],
    capsule_path: Path,
    capsule_sha: str,
) -> tuple[list[dict], dict]:
    runs = {row["job_id"]: row for row in merged["runs"]}
    require(len(runs) == len(merged["runs"]) == 851, "Merged run ID count differs")
    ledger_by_id = {row["job_id"]: row for row in ledger}
    require(len(ledger_by_id) == len(ledger) == 782, "Ledger job ID count differs")
    local = {key: row for key, row in ledger_by_id.items() if row["provider_route"] != "kaggle"}
    kaggle_ids = set(ledger_by_id) - set(local)
    pair_by_id = {row["main_run_id"]: row for row in pairs}
    require(len(local) == 222 and len(kaggle_ids) == 560, "Provider split differs")
    require(len(pair_by_id) == len(pairs) == 69, "Historical Main pair count differs")
    require(set(runs) == set(ledger_by_id) | set(pair_by_id), "851-run exact job set differs")
    require(not (set(ledger_by_id) & set(pair_by_id)), "Main ID overlaps new job")
    archive_pins: dict[str, tuple[int, str]] = {}
    for row in local.values():
        key = row["archive_path"]
        pin = (int(row["archive_bytes"]), row["archive_sha256"])
        require(key not in archive_pins or archive_pins[key] == pin, "Conflicting archive pins")
        archive_pins[key] = pin
    for name, (size, digest) in archive_pins.items():
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT / ".cache"), "Archive outside cache")
        require(
            path.stat().st_size == size and sha256(path) == digest, f"Archive pin differs: {name}"
        )

    results = [local_trace(local[job_id], runs[job_id]) for job_id in sorted(local)]
    with zipfile.ZipFile(capsule_path) as capsule:
        capsule_ledger = json.loads(capsule.read("metadata/ledger.json"))
        capsule_main = {
            row["job_id"]: row
            for row in capsule_ledger["jobs"]
            if row["job_id"].startswith("main_")
        }
        require(set(capsule_main) == set(pair_by_id), "Capsule Main set differs")
        results.extend(
            main_trace(runs[job_id], pair_by_id[job_id], capsule, capsule_main[job_id], capsule_sha)
            for job_id in sorted(pair_by_id)
        )
    seen_kaggle = set()
    for row in kaggle:
        job_id = row["job_id"]
        require(job_id in kaggle_ids and job_id not in seen_kaggle, f"Kaggle ID differs: {job_id}")
        seen_kaggle.add(job_id)
        ledger_row = ledger_by_id[job_id]
        require(
            row["archive_sha256"] == ledger_row["archive_sha256"]
            and row["job_receipt_sha256"] == ledger_row["job_receipt_sha256"]
            and row["final_manifest_sha256"] == runs[job_id]["manifest"]["sha256"]
            and int(row["budget_days"]) == runs[job_id]["budget"]
            and row["entity_id"] == runs[job_id]["entity_id"]
            and int(row["seed"]) == runs[job_id]["seed"],
            f"Kaggle pins differ: {job_id}",
        )
        results.append(
            {
                "job_id": job_id,
                "source_kind": "kaggle_v2_verified",
                "method": runs[job_id]["method"],
                "budget_days": runs[job_id]["budget"],
                "entity_id": runs[job_id]["entity_id"],
                "seed": runs[job_id]["seed"],
                "archive_sha256": row["archive_sha256"],
                "job_receipt_sha256": row["job_receipt_sha256"],
                "manifest_sha256": row["final_manifest_sha256"],
                "decisions": int(row["decisions"]) if row["decisions"] else None,
                "switches": int(row["switches"]) if row["switches"] else None,
                "evidence_level": "ARCHIVE_RECEIPT_MANIFEST"
                if row["decisions"]
                else "ISSUED_COUNT_ONLY",
            }
        )
    require(seen_kaggle == kaggle_ids, "Kaggle exact job set differs")
    require(len(results) == len({row["job_id"] for row in results}) == 851, "Output ID set differs")
    results.sort(key=lambda row: row["job_id"])
    groups: dict[tuple[str, str, int], list[dict]] = defaultdict(list)
    for row in results:
        groups[(row["source_kind"], row["method"], int(row["budget_days"]))].append(row)
    summary = {
        "scope": "development_only",
        "runs": len(results),
        "source_kind_counts": dict(sorted(Counter(row["source_kind"] for row in results).items())),
        "decision_trace_runs": sum(row["decisions"] is not None for row in results),
        "issued_count_only_runs": sum(row["decisions"] is None for row in results),
        "decisions": sum(row["decisions"] or 0 for row in results),
        "switches": sum(row["switches"] or 0 for row in results),
        "groups": [
            {
                "source_kind": source,
                "method": method,
                "budget_days": budget,
                "runs": len(rows),
                "decision_trace_runs": sum(row["decisions"] is not None for row in rows),
                "decisions": sum(row["decisions"] or 0 for row in rows),
                "switches": sum(row["switches"] or 0 for row in rows),
            }
            for (source, method, budget), rows in sorted(groups.items())
        ],
        "limits": [
            "Historical Main manifests match the saved review capsule, its internal ledger, the tracked pair table and merged-result SHA; there is no per-job Main receipt in the capsule.",
            "Issued-count-only fixed policies have null decision/switch counts, not zero.",
            "Kaggle per-job trace rows inherit the pinned v2 audit; their archive bytes are not rehashed by this recovery pass.",
            "This audit reports observed Development decisions; it does not establish causal benefit or Final performance.",
        ],
    }
    return results, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--merged", required=True, type=Path)
    parser.add_argument("--merged-sha256", required=True)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--ledger-sha256", required=True)
    parser.add_argument("--pairs", required=True, type=Path)
    parser.add_argument("--pairs-sha256", required=True)
    parser.add_argument("--kaggle-switches", required=True, type=Path)
    parser.add_argument("--kaggle-sha256", required=True)
    parser.add_argument("--main-capsule", required=True, type=Path)
    parser.add_argument("--main-capsule-sha256", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    merged = json.loads(pinned(args.merged, args.merged_sha256))
    ledger = list(csv.DictReader(pinned(args.ledger, args.ledger_sha256).decode().splitlines()))
    pairs = list(csv.DictReader(pinned(args.pairs, args.pairs_sha256).decode().splitlines()))
    kaggle = list(
        csv.DictReader(pinned(args.kaggle_switches, args.kaggle_sha256).decode().splitlines())
    )
    capsule_path = args.main_capsule.resolve()
    require(capsule_path.is_relative_to(ROOT / ".cache"), "Capsule outside repository cache")
    require(sha256(capsule_path) == args.main_capsule_sha256, "Capsule SHA differs")
    receipt_path = capsule_path.parent / "receipt.json"
    receipt = json.loads(receipt_path.read_bytes())
    require(
        capsule_path.stat().st_size == receipt["bytes"]
        and args.main_capsule_sha256 == receipt["sha256"]
        and receipt["main_runs"] == 69
        and receipt["scope"] == "development_only",
        "Capsule receipt differs",
    )
    results, summary = audit(merged, ledger, pairs, kaggle, capsule_path, args.main_capsule_sha256)
    summary["source_sha256"] = {
        "merged": args.merged_sha256,
        "ledger": args.ledger_sha256,
        "pairs": args.pairs_sha256,
        "kaggle_switches": args.kaggle_sha256,
        "main_capsule": args.main_capsule_sha256,
        "main_capsule_receipt": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
    }
    out = args.output_dir.resolve()
    require(out.is_relative_to(ROOT), "Output outside repository")
    out.mkdir(parents=True, exist_ok=False)
    with (out / "switch_audit_full.csv").open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    with (out / "summary.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(summary, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({key: summary[key] for key in ("runs", "decision_trace_runs", "switches")}))


if __name__ == "__main__":
    main()
