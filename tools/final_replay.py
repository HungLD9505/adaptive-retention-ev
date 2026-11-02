"""Execute or independently verify one locked Final cell after live approval gates."""

import argparse
import copy
import json
from pathlib import Path

from ev_runner.final_gate import FinalInputRun, authorize
from ev_runner.run import ROOT, execute
from tools.verify_comparison import verify_run
from tools.verify_latest_states import verify_state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--city", required=True)
    parser.add_argument("--budget", type=int, required=True)
    parser.add_argument("--entity", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume-from", type=Path)
    parser.add_argument("--stop-after-ticks", type=int)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    # No InputRun/Replay/training/label construction before live human gates.
    access = authorize(args.lock, ROOT)
    groups = [
        g
        for g in access.lock["groups"]
        if g["namespace"] == [args.dataset, args.city] and g["history_days"] == args.budget
    ]
    if len(groups) != 1 or args.entity not in groups[0]["selected_ids"]:
        raise ValueError("Cell outside declared bounded Final cohort")
    group = groups[0]
    config = copy.deepcopy(access.lock["method_configs"][str(args.seed)][args.variant])
    # Historical config field retained internally for method-core compatibility.
    config["development_entities"] = [args.entity]
    inputs = FinalInputRun(args.inputs, group["input_manifest_sha256"], access)
    if args.verify:
        saved = json.loads((args.output / "run.json").read_text())
        binding = saved["binding"]
        if (
            binding["input"]["entity_id"] != args.entity
            or binding["config"] != config
            or binding["environment"] != access.lock["runtime_profile"]
        ):
            raise ValueError("Requested Final verification cell/config/runtime differs")
        result = {
            "daily": verify_run(args.output, args.inputs, final_access=access),
            "latest_state": verify_state(args.output, saved),
        }
    else:
        source = group["sources"][str(args.seed)]
        result = execute(
            inputs,
            args.entity,
            ROOT / source["path"],
            source["sha256"],
            config,
            args.output,
            device="cuda",
            resume_from=args.resume_from,
            stop_after_ticks=args.stop_after_ticks,
            ensemble_sources=tuple(
                (ROOT / s["path"], s["sha256"]) for s in group["sources"].values()
            )
            if args.variant == "uncertainty"
            else (),
        )
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
