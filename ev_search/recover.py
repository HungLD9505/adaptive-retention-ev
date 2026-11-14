"""Explicitly close one interrupted Fixed trial without changing its artifacts."""

import argparse
import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path

from ev_models.checkpoint import digest
from ev_runner.continuous_run import code_identity
from ev_search.fixed import FixedSearchConfig
from ev_search.ledger import FixedLedger, canonical
from ev_search.protocol import canonical_sha256, require_scored_bindings

ROOT = Path(__file__).resolve().parents[1]


def _trial_evidence(trial_root: Path) -> dict:
    if not trial_root.is_dir() or trial_root.is_symlink():
        raise ValueError("Interrupted trial directory is missing or unsafe")
    result = hashlib.sha256()
    count = 0
    size = 0
    for path in sorted(trial_root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Interrupted trial contains a symlink")
        if not path.is_file():
            continue
        relative = path.relative_to(trial_root).as_posix()
        file_sha = digest(path)
        file_size = path.stat().st_size
        result.update(canonical({"path": relative, "size_bytes": file_size, "sha256": file_sha}))
        count += 1
        size += file_size
    return {"files": count, "size_bytes": size, "tree_sha256": result.hexdigest()}


def recover_interrupted_trial(
    ledger_root: Path,
    protocol_path: Path,
    search_config_path: Path,
    study_template_path: Path,
) -> dict:
    """Authenticate ledger and bindings, then append a failed/null trial_end."""
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    study = json.loads(study_template_path.read_text(encoding="utf-8"))
    search = FixedSearchConfig(**json.loads(search_config_path.read_text(encoding="utf-8")))
    search_sha = digest(search_config_path)
    protocol_sha = digest(protocol_path)
    require_scored_bindings(
        protocol, study, fixed_search_config_sha256=search_sha, phase="calibration"
    )
    metadata = json.loads((ledger_root / "config.json").read_text(encoding="utf-8"))
    binding = metadata["binding"]
    expected = {
        "schema": "issue99-fixed-calibration-binding-v1",
        "input_manifest_sha256": protocol["input_manifest_sha256"],
        "source_population_sha256": protocol["source_population_sha256"],
        "protocol_sha256": protocol_sha,
        "calibration_study_template_sha256": canonical_sha256(study),
        "fixed_search_config_sha256": search_sha,
        "code_commit": protocol["code_commit"],
        "sources": protocol["source_checkpoint_sha256"],
        "code_files": {
            str(path.relative_to(ROOT)): digest(path)
            for path in sorted((ROOT / "ev_search").glob("*.py"))
        },
        "runner_code_files": code_identity()["files"],
    }
    if binding != expected:
        raise ValueError("Interrupted trial binding differs from locked code/protocol/inputs")
    identity = hashlib.sha256(canonical({"config": asdict(search), "binding": binding})).hexdigest()
    if (
        metadata.get("schema") != "issue99-fixed-ledger-v1"
        or metadata.get("config") != json.loads(json.dumps(asdict(search)))
        or metadata.get("sha256") != identity
    ):
        raise ValueError("Interrupted trial metadata/config identity differs")
    events_path = ledger_root / "events.jsonl"
    ledger_before = digest(events_path)
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    chain = "0" * 64
    pending = None
    completed = 0
    for event in events:
        body = {key: value for key, value in event.items() if key != "sha256"}
        checksum = hashlib.sha256(canonical(body)).hexdigest()
        if event.get("previous") != chain or event.get("sha256") != checksum:
            raise ValueError("Interrupted trial ledger chain differs")
        chain = checksum
        if event.get("event") == "trial_start":
            if pending is not None or event.get("trial") != completed:
                raise ValueError("Duplicate or out-of-order trial_start")
            pending = event
        elif event.get("event") == "trial_end":
            if pending is None or any(
                event.get(key) != pending.get(key) for key in ("trial", "lambda", "role")
            ):
                raise ValueError("Mismatched trial_end")
            pending = None
            completed += 1
        elif event.get("event") == "domain_expansion":
            if pending is not None or event.get("after_trial") != completed - 1:
                raise ValueError("Misordered domain expansion")
        else:
            raise ValueError("Unknown ledger event")
    if pending is None or not events or events[-1]["event"] != "trial_start":
        raise ValueError("No single trailing interrupted trial_start")
    trial_root = ledger_root / f"trial-{pending['trial']:04d}"
    evidence = _trial_evidence(trial_root)
    result = {
        "event": "trial_end",
        "trial": pending["trial"],
        "lambda": pending["lambda"],
        "role": pending["role"],
        "status": "failed",
        "outcome": {
            "objective_mae_kwh": None,
            "error": "Interrupted trial explicitly closed; partial artifacts retained",
            "recovery_evidence": {**evidence, "ledger_before_sha256": ledger_before},
        },
        "previous": chain,
    }
    result["sha256"] = hashlib.sha256(canonical(result)).hexdigest()
    if digest(events_path) != ledger_before:
        raise ValueError("Ledger changed while inspecting interrupted trial")
    with events_path.open("ab") as stream:
        stream.write(canonical(result))
        stream.flush()
        os.fsync(stream.fileno())
    FixedLedger(ledger_root, search, binding=binding, resume=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--search-config", type=Path, required=True)
    parser.add_argument("--study-template", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            recover_interrupted_trial(
                args.ledger, args.protocol, args.search_config, args.study_template
            ),
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
