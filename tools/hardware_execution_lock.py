"""Create a hardware child lock without changing frozen scientific identities.

This metadata tool does not authorize dispatch or independently verify GPU evidence.
The Root coordinator must verify the pinned evidence, tracked execution checkout,
exclusive unstarted lease, and child-aware independent verifier before dispatch.
"""

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

PARENT_SHA256 = "9c65169cced1506a450fdd7b8a57a69d5a720cac7acaa0dcd1c8ccfd1723ce42"
SCIENTIFIC_COMMIT = "61c32328d9829a69037dca629f727b4863015122"
CHECKS = ("shape", "gradient", "freeze", "checkpoint_resume", "numeric_comparison")
ARRAYS = ("predictions", "loss", "trainable_gradients", "resumed_predictions")
CHILD_FIELDS = {"runtime_profile", "hardware_extension"}


def sha256(raw: bytes) -> str:
    """Return a byte identity, never a semantic substitute for a file hash."""
    return hashlib.sha256(raw).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def build_child(
    parent_raw: bytes,
    profile_raw: bytes,
    authorization_raw: bytes,
    policy_raw: bytes,
    evidence_raw: bytes,
    indices: list[int],
    *,
    expected_parent_sha256: str = PARENT_SHA256,
) -> dict:
    """Validate linked metadata and preserve every nonhardware parent field.

    expected_parent_sha256 is injectable for independent offline fixtures. The CLI
    always uses the production constant. Evidence PASS values are attestations;
    accepting their underlying raw artifacts remains an independent Root action.
    """
    parent_sha = sha256(parent_raw)
    require(parent_sha == expected_parent_sha256, "Parent byte identity differs")
    parent, profile, auth, policy, evidence = (
        json.loads(raw)
        for raw in (parent_raw, profile_raw, authorization_raw, policy_raw, evidence_raw)
    )
    require(parent.get("schema") == "ev-final-execution-lock-v1", "Unsupported parent")
    require("hardware_extension" not in parent, "Nested hardware extensions are unsupported")
    require(
        parent.get("whole_units") == 810
        and parent.get("method_seed_cells") == 11340
        and len(parent.get("files", {})) == 140
        and len(parent.get("unit_order", [])) == 810,
        "Parent scientific scope differs",
    )
    require(
        isinstance(indices, list)
        and bool(indices)
        and all(type(i) is int and 0 <= i < 810 for i in indices)
        and indices == sorted(set(indices)),
        "Lease indices must be sorted unique exact integers in frozen order",
    )
    require(
        auth.get("schema") == "ev-final-hardware-authorization-v1"
        and auth.get("parent_lock_sha256") == parent_sha
        and auth.get("hardware_extension_authorized") is True
        and auth.get("independent_peer_approval") is False
        and isinstance(auth.get("human_instruction"), str)
        and bool(auth["human_instruction"].strip())
        and isinstance(auth.get("evidence_reference"), str)
        and bool(auth["evidence_reference"].strip()),
        "Explicit human hardware authorization is absent",
    )
    original = parent["runtime_profile"]
    require(set(profile) == set(original), "Runtime profile keys differ")
    require(
        all(profile[k] == v for k, v in original.items() if k != "device_name")
        and profile["device_name"]
        in ("NVIDIA L4", "NVIDIA A100-SXM4-40GB", "NVIDIA A100-SXM4-80GB")
        and profile["device"] == "cuda"
        and profile["deterministic_algorithms"] is True,
        "Only explicitly supported GPU hardware may differ",
    )
    require(
        policy.get("schema") == "ev-final-hardware-numeric-policy-v1"
        and policy.get("dtype") == "float32"
        and policy.get("final_outcomes_used") is False
        and policy.get("bitwise_equality_claimed") is False,
        "Missing predeclared FP32 numeric policy",
    )
    require(policy.get("required_arrays") == list(ARRAYS), "Numeric array coverage differs")
    for key in ("atol", "rtol"):
        value = policy.get(key)
        require(
            type(value) in (int, float) and math.isfinite(value) and 0 < value <= 0.001,
            "Numeric tolerance must be finite, positive and <=0.001",
        )
    require(
        evidence.get("schema") == "ev-final-hardware-compatibility-v1"
        and evidence.get("parent_lock_sha256") == parent_sha
        and evidence.get("scientific_commit") == SCIENTIFIC_COMMIT
        and evidence.get("scientific_files") == parent["files"]
        and evidence.get("runtime_profile") == profile
        and evidence.get("runtime_packages_sha256")
        == parent["files"].get(parent["runtime_packages_path"])
        and evidence.get("numeric_policy_sha256") == sha256(policy_raw)
        and evidence.get("authorization_sha256") == sha256(authorization_raw)
        and evidence.get("synthetic_only") is True
        and evidence.get("final_values_read") is False
        and evidence.get("source_refits") == 0
        and type(evidence.get("source_refits")) is int
        and evidence.get("checks") == dict.fromkeys(CHECKS, "PASS"),
        "Missing, failed or mismatched compatibility evidence",
    )
    require(
        type(policy.get("declared_epoch")) in (int, float)
        and type(evidence.get("started_epoch")) in (int, float)
        and math.isfinite(policy["declared_epoch"])
        and math.isfinite(evidence["started_epoch"])
        and 0 < policy["declared_epoch"] < evidence["started_epoch"],
        "Numeric policy must predate the compatibility trial",
    )
    comparisons = evidence.get("numeric_comparisons", {})
    require(set(comparisons) == set(ARRAYS), "Numeric comparison arrays absent")
    for comparison in comparisons.values():
        ratio = comparison.get("max_tolerance_ratio")
        require(
            comparison.get("shapes_equal") is True
            and comparison.get("finite_masks_equal") is True
            and type(comparison.get("finite_elements")) is int
            and comparison["finite_elements"] > 0
            and type(ratio) in (int, float)
            and math.isfinite(ratio)
            and 0 <= ratio <= 1,
            "Numeric comparison failed declared elementwise tolerance",
        )
    artifacts = evidence.get("artifacts")
    require(isinstance(artifacts, list) and bool(artifacts), "Raw evidence artifacts absent")
    for artifact in artifacts:
        require(
            isinstance(artifact, dict)
            and isinstance(artifact.get("sha256"), str)
            and len(artifact["sha256"]) == 64
            and all(c in "0123456789abcdef" for c in artifact["sha256"])
            and type(artifact.get("bytes")) is int
            and artifact["bytes"] > 0
            and isinstance(artifact.get("reference"), str)
            and bool(artifact["reference"]),
            "Raw evidence artifact identity is invalid",
        )
    child = copy.deepcopy(parent)
    child["runtime_profile"] = profile
    child["hardware_extension"] = {
        "schema": "ev-final-hardware-child-v1",
        "parent_lock_sha256": parent_sha,
        "scientific_commit": SCIENTIFIC_COMMIT,
        "authorization_sha256": sha256(authorization_raw),
        "compatibility_evidence_sha256": sha256(evidence_raw),
        "numeric_policy_sha256": sha256(policy_raw),
        "runtime_profile_sha256": sha256(profile_raw),
        "eligible_unit_indices": indices,
        "independent_peer_approval": False,
        "dispatch_authorized_by_this_tool": False,
        "requires": [
            "tracked clean execution checkout with unchanged 140 scientific pins",
            "Root verified external evidence raw bytes and independent content",
            "exclusive unstarted lease checked against current canonical and inflight",
            "truthful child-aware independent content/identity/daily/latest verifier",
            "fresh actual quota, reserve30 and one completed inflight per worker",
        ],
    }
    require(
        {k: v for k, v in child.items() if k not in CHILD_FIELDS}
        == {k: v for k, v in parent.items() if k not in CHILD_FIELDS},
        "Nonhardware parent fields changed",
    )
    return child


def main() -> None:
    """Write a new child file exclusively; never overwrite historical locks."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("parent", "profile", "authorization", "policy", "evidence", "indices", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    child = build_child(
        args.parent.read_bytes(),
        args.profile.read_bytes(),
        args.authorization.read_bytes(),
        args.policy.read_bytes(),
        args.evidence.read_bytes(),
        json.loads(args.indices.read_text()),
    )
    raw = (json.dumps(child, indent=2) + "\n").encode()
    with args.output.open("xb") as output:
        output.write(raw)
    print(
        json.dumps({"path": str(args.output), "sha256": sha256(raw), "dispatch_authorized": False})
    )


if __name__ == "__main__":
    main()
