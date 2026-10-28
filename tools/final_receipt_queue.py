"""Bounded receipt backpressure; immutable14method driver and Root credit remain separate."""

import argparse
import dataclasses
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

if __package__:
    from .final_receipt_policy import (
        ReceiptPolicy,
        claim_undispatched,
        dispatch_budget,
        verified_receipt,
        wait_expired,
    )
else:
    from final_receipt_policy import (
        ReceiptPolicy,
        claim_undispatched,
        dispatch_budget,
        verified_receipt,
        wait_expired,
    )


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def new_json(path: Path, record: dict) -> None:
    with path.open("x") as stream:
        json.dump(record, stream, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def actual_quota(folder: Path, policy: ReceiptPolicy) -> tuple[dict, dict]:
    observations = sorted(folder.glob("quota-actual-*.json"))
    if not observations:
        raise ValueError("No actual quota observation; no dispatch")
    observation = read(observations[-1])
    budget = dispatch_budget(observation, time.time(), policy)
    budget["actual_observation_file"] = str(observations[-1])
    budget["actual_observation_sha256"] = sha(observations[-1])
    return observation, budget


def run_queue(config: dict) -> None:
    policy = ReceiptPolicy(**config["receipt_policy"])
    started_queue = time.monotonic()
    repo, ops = Path(config["repo"]), Path(config["ops"])
    lock = repo / "configs/issue23/final-execution-lock-20261027-v2.json"
    assert sha(lock) == config["lock_sha256"]
    frozen = read(lock)
    assert (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        == config["commit"]
    )
    assert not subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=repo, text=True
    ).strip()
    for name, pin in config["ops_pins"].items():
        assert sha(ops / name) == pin
    assert (
        type(config["queue_wall_seconds"]) is int and 2100 <= config["queue_wall_seconds"] <= 10800
    )
    assert len(config["indices"]) == len(set(config["indices"])) <= 44
    assert config["indices"] == sorted(config["indices"])
    for index in config["indices"]:
        assert index % 2 == config["lane"]
        assert sha(lock) == config["lock_sha256"]
        assert (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
            == config["commit"]
        )
        assert not subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=repo, text=True
        ).strip()
        for name, pin in config["ops_pins"].items():
            assert sha(ops / name) == pin
        route = next(row for row in config["reservations"] if index in row["indices"])
        reservation_path = Path(route["path"])
        assert sha(reservation_path) == route["sha256"]
        reservation = read(reservation_path)
        assert (
            next(row["unit"] for row in reservation["units"] if row["index"] == index)
            == frozen["unit_order"][index]
        )
        remote = Path(reservation["storage"]["mounted_parent"])
        lane = "A" if config["lane"] == 0 else "C"
        first = reservation["ownership"][lane][0]
        previous_parent = (
            Path(
                reservation["storage"].get(
                    "previous_mounted_parent", reservation["storage"]["main_mounted_parent"]
                )
            )
            if index == first
            else remote
        )
        receipt = previous_parent / f"root-acceptance-unit-{index - 2:04d}.json"
        waited = time.monotonic()
        while not receipt.exists():
            if wait_expired(waited, time.monotonic(), policy):
                raise TimeoutError(
                    "Finite600second receipt deadline; preserve completed output; no retry"
                )
            time.sleep(3)
        previous_sha = verified_receipt(receipt, config["lock_sha256"], index - 2, config["lane"])
        if index == config["indices"][0]:
            assert previous_sha == config["initial_previous_receipt_sha256"]
        # Never restart a completed/partial/uncertain unit after a controller crash.
        output = Path(config["scratch"]) / f"final-unit-{index:04d}-v2"
        log = Path(config["scratch"]) / f"final-unit-{index:04d}-v2.operator.log"
        process_file = remote / f"unit-{index:04d}-process.json"
        forbidden = (
            output,
            log,
            process_file,
            remote / f"unit-{index:04d}",
            remote / f"root-acceptance-unit-{index:04d}.json",
            remote / f"final-unit-{index:04d}-publication.zip",
        )
        if (
            time.monotonic()
            - started_queue
            + policy.unit_seconds
            + policy.receipt_seconds
            + policy.release_seconds
            > config["queue_wall_seconds"]
        ):
            print("BOUNDED_QUEUE_START_HORIZON_REACHED", index, flush=True)
            return
        observation, budget = actual_quota(Path(config["quota_folder"]), policy)
        previous_process = read(previous_parent / f"unit-{index - 2:04d}-process.json")
        assert type(previous_process["pid"]) is int and previous_process["pid"] > 0
        intent_folder = remote / config["intent_folder_name"]
        intent_folder.mkdir(exist_ok=True)
        claim_undispatched(
            intent_folder / f"unit-{index:04d}.json",
            forbidden,
            {
                "index": index,
                "lane": config["lane"],
                "queue_pid": os.getpid(),
                "queue_sha256": sha(Path(__file__)),
                "previous_receipt_sha256": previous_sha,
                "policy": dataclasses.asdict(policy),
                "quota_budget": budget,
            },
        )
        command = [
            sys.executable,
            "-u",
            str(ops / "prototype_final_unit.py"),
            "--lock",
            str(lock),
            "--inputs-root",
            reservation["input_roots"][lane],
            "--unit-index",
            str(index),
            "--lane",
            str(config["lane"]),
            "--output",
            str(output),
            "--backup-root",
            str(remote / f"unit-{index:04d}"),
            "--drive-mount",
            config["drive_mount"],
            "--previous-receipt",
            str(receipt),
            "--previous-sha256",
            previous_sha,
        ]
        start = last_progress = time.monotonic()
        epoch, completed, reason = time.time(), 0, None
        with log.open("x") as stream:
            child = subprocess.Popen(
                command,
                cwd=repo,
                env={**os.environ, "PYTHONPATH": str(repo) + os.pathsep + str(ops)},
                stdout=stream,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            process = {
                "pid": child.pid,
                "command": command,
                "unit_index": index,
                "lane": config["lane"],
                "queue_parent_pid": os.getpid(),
                "previous_queue_parent_pid": config["previous_queue_parent_pid"],
                "previous_unit_process_pid": previous_process["pid"],
                "previous_receipt_sha256": previous_sha,
                "previous_receipt_path": str(receipt),
                "previous_process_parent": str(previous_parent),
                "publication_parent": str(remote),
                "reservation_sha256": route["sha256"],
                "operator_sha256": {
                    name: config["ops_pins"][name]
                    for name in ["prototype_final_unit.py", "async_export.py"]
                },
                "lock_sha256": config["lock_sha256"],
                "start_utc": epoch,
                "queue_sha256": sha(Path(__file__)),
                "receipt_policy": dataclasses.asdict(policy),
                "quota_observation": observation,
                "quota_budget": budget,
                "operational_envelope_sha256": config["operational_envelope_sha256"],
            }
            new_json(process_file, process)
            print(
                "FROZEN_MISSING_UNIT_DISPATCHED",
                json.dumps(
                    {
                        "index": index,
                        "pid": child.pid,
                        "parent_pid": os.getpid(),
                        "publication_parent": str(remote),
                    }
                ),
                flush=True,
            )
            while child.poll() is None:
                count = len(list(output.glob("progress-*.json"))) if output.exists() else 0
                if count > completed:
                    completed, last_progress = count, time.monotonic()
                if (
                    time.monotonic() - start > policy.unit_seconds
                    or time.monotonic() - last_progress > 120
                ):
                    reason = "wall_or_no_completed_run_deadman"
                    os.killpg(child.pid, signal.SIGTERM)
                    break
                time.sleep(3)
            try:
                returncode = child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                returncode = child.wait()
        completed = len(list(output.glob("progress-*.json"))) if output.exists() else 0
        exit_record = {
            "returncode": returncode,
            "completed_method_cells": completed,
            "seconds": time.monotonic() - start,
            "stop_reason": reason,
            "unit_index": index,
            "lane": config["lane"],
            "start_utc": epoch,
            "completed_utc": time.time(),
            "queue_parent_pid": os.getpid(),
            "reservation_sha256": route["sha256"],
            "previous_receipt_sha256": previous_sha,
            "operator_sha256": process["operator_sha256"],
            "publication_parent": str(remote),
            "receipt_policy": dataclasses.asdict(policy),
            "scope": "One immutable14method unit; per-run mounted/local proofs preserved; Root acceptance remains full fresh external verification",
        }
        new_json(remote / f"unit-{index:04d}-exit.json", exit_record)
        with (remote / f"unit-{index:04d}-operator.log").open("xb") as stream:
            stream.write(log.read_bytes())
        if returncode != 0 or completed != 14 or reason is not None:
            raise RuntimeError(f"Unit{index} failed; preserve all artifacts; no retry")
        assert (remote / f"final-unit-{index:04d}-publication.zip").is_file()
        assert len(list((remote / f"unit-{index:04d}").glob("*.receipt.json"))) == 14
        print(
            "COMPLETE_AWAITING_INDEPENDENT_ROOT",
            index,
            "max_completed_inflight",
            policy.completed_inflight,
            flush=True,
        )
    print("BOUNDED_RECEIPT_QUEUE_COMPLETE", config["lane"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    config = read(parser.parse_args().config)
    status = {
        "queue_pid": os.getpid(),
        "lane": config["lane"],
        "started_utc": time.time(),
        "queue_sha256": sha(Path(__file__)),
    }
    try:
        run_queue(config)
        status.update(returncode=0, reason="finite_queue_finished_or_start_horizon")
    except Exception as error:
        status.update(returncode=1, reason=type(error).__name__ + ": " + str(error))
        raise
    finally:
        status["finished_utc"] = time.time()
        for reservation in config["reservations"]:
            remote = Path(read(Path(reservation["path"]))["storage"]["mounted_parent"])
            new_json(remote / config["queue_exit_name"], status)
        print("FINITE_QUEUE_EXIT", json.dumps(status), flush=True)
