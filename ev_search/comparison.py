"""Hash-bound issue #99 paired comparison jobs; one job per invocation."""

import copy
import hashlib
import json
import math
from pathlib import Path

from ev_models.checkpoint import digest
from ev_models.data import InputRun
from ev_runner.continuous_run import code_identity as continuous_code_identity
from ev_runner.continuous_run import execute as execute_continuous
from ev_runner.run import execute as execute_discrete
from ev_runner.run import runtime_code as discrete_code_identity
from ev_search.ledger import canonical

TARGETS = ("1405", "2152", "1153", "1693")
SEEDS = (42, 43, 44)
METHODS = ("lambda0", "fixed", "discrete", "continuous", "frozen_lambda")


def plan_jobs(
    inputs: InputRun,
    protocol_path: Path,
    lock_path: Path,
    sources: dict,
) -> list[dict]:
    """Pin all 60 method-target-seed identities without opening outcome labels."""
    protocol_sha = digest(protocol_path)
    lock_sha = digest(lock_path)
    protocol = json.loads(protocol_path.read_text())
    lock = json.loads(lock_path.read_text())
    if (
        protocol.get("status") != "locked_owner_approved"
        or not protocol.get("owner_authorization")
        or lock.get("schema") != "issue99-comparison-lock-v1"
        or lock.get("status") != "locked_owner_approved"
        or lock.get("protocol_sha256") != protocol_sha
    ):
        raise ValueError("Comparison requires matching owner-locked protocol and selection")
    if inputs.target_role != "development" or inputs.config["history_days"] != 14:
        raise ValueError("Comparison is Development 14d only; Final is excluded")
    if (
        inputs.sha256 != protocol["input_manifest_sha256"]
        or inputs.source_hash != protocol["source_population_sha256"]
    ):
        raise ValueError("Comparison input/source population differs from protocol")
    if set(sources) != {str(seed) for seed in SEEDS}:
        raise ValueError("Comparison needs Source10 seeds 42/43/44")
    fixed = lock["selected_fixed_lambda"]
    initial = lock["controller_initial_lambda"]
    study = lock["study_template"]
    discrete = lock["discrete_config"]
    if study.get("phase") != "evaluation" or study.get("replay_days") != 90:
        raise ValueError("Comparison study template must be 90-day evaluation")
    if discrete.get("replay_days") != 90 or discrete.get("method", {}).get("name") != "adaptive":
        raise ValueError("Historical discrete recipe must be explicit adaptive method")
    if any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value < 0
        for value in (fixed, initial)
    ):
        raise ValueError("Invalid selected Fixed/controller lambda")
    code = {
        "continuous": continuous_code_identity()["files"],
        "discrete": discrete_code_identity()["files"],
    }
    jobs = []
    first_by_key = {}
    for method in METHODS:
        for target in TARGETS:
            for seed in SEEDS:
                source = sources[str(seed)]
                if method == "discrete":
                    family = "discrete"
                    config = copy.deepcopy(discrete)
                    for name in ("initial_training", "online_training"):
                        config[name]["seed"] = seed
                    config["controller"]["seed"] = seed
                    config["development_entities"] = list(TARGETS)
                    new_profile = study
                    for name in ("initial_training", "online_training"):
                        expected = copy.deepcopy(new_profile[name])
                        expected["seed"] = seed
                        if config[name] != expected:
                            raise ValueError(
                                "Discrete training profile differs from matched methods"
                            )
                else:
                    family = "continuous"
                    config = copy.deepcopy(study)
                    config["phase"] = "evaluation"
                    config["protocol_sha256"] = protocol_sha
                    config["objective_origins"] = protocol["evaluation_origins"][target]
                    config["frozen_lambda"] = method != "continuous"
                    config["initial_lambda"] = (
                        0.0 if method == "lambda0" else fixed if method == "fixed" else initial
                    )
                    for name in ("initial_training", "online_training"):
                        config[name]["seed"] = seed
                identity = {
                    "family": family,
                    "target": target,
                    "seed": seed,
                    "config": config,
                    "input_manifest_sha256": inputs.sha256,
                    "source_population_sha256": inputs.source_hash,
                    "source_checkpoint_sha256": source["sha256"],
                    "protocol_sha256": protocol_sha,
                    "code_files": code[family],
                }
                execution_key = hashlib.sha256(canonical(identity)).hexdigest()
                job_id = f"{method}-{target}-seed{seed}"
                reuse_job_id = first_by_key.get(execution_key)
                if reuse_job_id is None:
                    first_by_key[execution_key] = job_id
                jobs.append(
                    {
                        "schema": "issue99-comparison-job-v1",
                        "job_id": job_id,
                        "method": method,
                        "target": target,
                        "seed": seed,
                        "family": family,
                        "source_path": source["path"],
                        "source_sha256": source["sha256"],
                        "config": config,
                        "evaluation_origins": protocol["evaluation_origins"][target],
                        "protocol_sha256": protocol_sha,
                        "lock_sha256": lock_sha,
                        "execution_key": execution_key,
                        "reuse_job_id": reuse_job_id,
                    }
                )
    if len(jobs) != 60 or len({job["job_id"] for job in jobs}) != 60:
        raise ValueError("Comparison matrix identity incomplete")
    return jobs


def verify_run_binding(job: dict, report: dict, inputs: InputRun) -> None:
    """Require exact input/config/source/code lineage before accepting a run."""
    binding = report["binding"]
    expected = inputs.binding("target", job["target"], job["source_sha256"])
    if binding.get("input") != expected or binding.get("config") != job["config"]:
        raise ValueError("Comparison run input/config binding differs")
    if binding.get("source_population_sha256") != inputs.source_hash:
        raise ValueError("Comparison source population differs")
    if job["family"] == "continuous":
        if (
            report.get("phase") != "evaluation"
            or binding["code"]["files"] != continuous_code_identity()["files"]
        ):
            raise ValueError("Continuous comparison phase/code differs")
    elif binding["code_files"] != discrete_code_identity()["files"]:
        raise ValueError("Discrete comparison code differs")


def event_hashes(run_path: Path) -> dict[str, str]:
    """Bind every committed tick artifact, including model state where retained."""
    return {
        str(path.relative_to(run_path)).replace("\\", "/"): digest(path)
        for tick in sorted(run_path.glob("tick-*"))
        for path in (
            tick / "forecasts.json",
            tick / "events.jsonl",
            tick / "commit.json",
            tick / "state.pt",
        )
        if path.exists()
    }


def _resume_chain(job: dict, inputs: InputRun, run_path: Path) -> str:
    """Read-only preflight; Store repeats full validation while copying into a new run."""
    binding = json.loads((run_path / "binding.json").read_text())
    if (
        binding.get("input") != inputs.binding("target", job["target"], job["source_sha256"])
        or binding.get("config") != job["config"]
        or binding.get("source_population_sha256") != inputs.source_hash
    ):
        raise ValueError("Resume input/config/source binding differs")
    files = (
        continuous_code_identity()["files"]
        if job["family"] == "continuous"
        else discrete_code_identity()["files"]
    )
    saved_files = (
        binding["code"]["files"] if job["family"] == "continuous" else binding["code_files"]
    )
    if saved_files != files:
        raise ValueError("Resume code binding differs")
    if list(run_path.glob(".pending-*")):
        raise ValueError("Resume source has uncommitted tick")
    ticks = sorted(run_path.glob("tick-*"))
    if not ticks:
        raise ValueError("Resume source has no committed ticks")
    previous = "0" * 64
    retention = job["config"].get("state_retention", "all")
    for index, tick in enumerate(ticks):
        meta = json.loads((tick / "commit.json").read_text())
        if (
            tick.name != f"tick-{index:04d}"
            or meta["index"] != index
            or meta["previous"] != previous
            or set(meta["files"]) != {"state.pt", "events.jsonl", "forecasts.json"}
        ):
            raise ValueError("Resume commit chain differs")
        for name, expected in meta["files"].items():
            path = tick / name
            if (
                name == "state.pt"
                and retention == "latest"
                and index < len(ticks) - 1
                and not path.exists()
            ):
                continue
            if digest(path) != expected:
                raise ValueError("Resume committed artifact differs")
        previous = digest(tick / "commit.json")
    return previous


def execute_job(
    job: dict,
    inputs: InputRun,
    protocol_path: Path,
    lock_path: Path,
    output_root: Path,
    *,
    device: str,
    resume_from: Path | None = None,
) -> dict:
    """Run one fresh job or reuse an exact semantic twin without overwriting."""
    if digest(protocol_path) != job["protocol_sha256"]:
        raise ValueError("Comparison protocol changed")
    if digest(lock_path) != job["lock_sha256"]:
        raise ValueError("Comparison selection lock changed")
    if digest(Path(job["source_path"])) != job["source_sha256"]:
        raise ValueError("Comparison Source checkpoint changed")
    if resume_from is not None and job["reuse_job_id"] is not None:
        raise ValueError("Exact reuse job cannot resume a separate run")
    resume_chain = _resume_chain(job, inputs, resume_from) if resume_from else None
    output = output_root / job["job_id"]
    output.mkdir(parents=True, exist_ok=False)
    reused = job["reuse_job_id"]
    if reused is not None:
        original = output_root / reused / "run" / "run.json"
        report = json.loads(original.read_text())
        verify_run_binding(job, report, inputs)
        result = {
            "job": job,
            "reused_from": reused,
            "run_path": f"{reused}/run",
            "run_sha256": digest(original),
        }
    else:
        if job["family"] == "continuous":
            report = execute_continuous(
                inputs,
                job["target"],
                Path(job["source_path"]),
                job["source_sha256"],
                job["config"],
                output / "run",
                device=device,
                protocol_path=protocol_path,
                resume_from=resume_from,
            )
        else:
            report = execute_discrete(
                inputs,
                job["target"],
                Path(job["source_path"]),
                job["source_sha256"],
                job["config"],
                output / "run",
                device=device,
                resume_from=resume_from,
            )
        verify_run_binding(job, report, inputs)
        run_path = output / "run" / "run.json"
        result = {
            "job": job,
            "reused_from": None,
            "run_path": f"{job['job_id']}/run",
            "run_sha256": digest(run_path),
        }
        if resume_from is not None:
            result["resume_source_chain_sha256"] = resume_chain
    with (output / "job.json").open("xb") as stream:
        result["event_sha256"] = event_hashes(output_root / result["run_path"])
        stream.write(canonical(result))
    return result
