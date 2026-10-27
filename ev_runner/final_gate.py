"""Fail-closed Final access after live independent review and lead acceptance."""

import copy
import hashlib
import json
import subprocess
from pathlib import Path

from ev_models.checkpoint import digest
from ev_models.data import InputRun

REPOSITORY = "HungLD9505/adaptive-retention-ev"
LEAD = "HungLD9505"
MARKERS = ("DEVELOPMENT_ACCEPTED", "FINAL_CAPACITY_ACCEPTED", "FINAL_EXECUTION_APPROVED")


def github_pages(endpoint: str) -> list[dict]:
    """Read authenticated GitHub evidence; unavailable evidence fails closed."""
    raw = subprocess.check_output(
        ["gh", "api", "--paginate", "--slurp", f"repos/{REPOSITORY}/{endpoint}"], text=True
    )
    return [item for page in json.loads(raw) for item in page]


class FinalAccess:
    """Authorization bound to one tracked lock and independently approved revision.

    Use authorize() in production. This research workflow gate is not a sandbox
    against someone editing Python; tests substitute live evidence with fixtures.
    """

    def __init__(self, root: Path, lock_path: Path, commit: str, review: dict) -> None:
        self.root, self.lock_path, self.commit = root, lock_path, commit
        self.sha256 = digest(lock_path)
        self.lock = json.loads(lock_path.read_text())
        self.review = review
        self._pins = None

    def check(self) -> None:
        """Recheck lock and pinned files before opening target values."""
        if digest(self.lock_path) != self.sha256:
            raise ValueError("Final lock changed after approval")
        pins = {}
        for name, sha in self.lock["files"].items():
            path = Path(name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"Final lock file changed or unsafe path: {name}")
            value = (self.root / path).stat()
            pins[name] = (
                value.st_dev,
                value.st_ino,
                value.st_size,
                value.st_mtime_ns,
                value.st_ctime_ns,
            )
            if self._pins is None and digest(self.root / path) != sha:
                raise ValueError(f"Final lock file changed: {name}")
        if self._pins is not None and pins != self._pins:
            raise ValueError("Immutable Final dependency changed during execution")
        self._pins = pins

    def input_group(self, inputs: InputRun, entity: str) -> dict:
        self.check()
        matches = [
            g
            for g in self.lock["groups"]
            if tuple(g["namespace"]) == inputs.namespace
            and g["history_days"] == inputs.config["history_days"]
        ]
        if len(matches) != 1:
            raise ValueError("Final input group absent from lock")
        group = matches[0]
        if (
            entity not in group["selected_ids"]
            or inputs.sha256 != group["input_manifest_sha256"]
            or inputs.source_hash != group["source_population_sha256"]
            or inputs.entities.get((*inputs.namespace, entity), {}).get("role") != "final"
        ):
            raise ValueError("Final target/input/Source population differs from lock")
        return group

    def check_run(self, inputs: InputRun, entity: str, config: dict, source_sha: str) -> None:
        group = self.input_group(inputs, entity)
        seed = config["initial_training"]["seed"]
        templates = self.lock["method_configs"].get(str(seed), {})
        expected = []
        for template in templates.values():
            candidate = copy.deepcopy(template)
            candidate["development_entities"] = [entity]
            expected.append(candidate)
        if config not in expected or source_sha != group["sources"][str(seed)]["sha256"]:
            raise ValueError("Final config or reused Source differs from immutable lock")

    def provenance(self) -> dict:
        if self.review.get("mode") == "explicit_lead_exception":
            return {
                "lock_sha256": self.sha256,
                "execution_code_identity_sha256": hashlib.sha256(
                    json.dumps(
                        {n: s for n, s in self.lock["files"].items() if n.endswith(".py")},
                        sort_keys=True,
                    ).encode()
                ).hexdigest(),
                "authorization": self.review,
                "independent_peer_approval": False,
            }
        return {"lock_sha256": self.sha256, "reviewed_commit": self.commit, "review": self.review}


def explicit_exception(root: Path, lock: dict) -> dict | None:
    """Validate the tracked, scope-specific human exception; never invent a peer review."""
    policy = lock.get("authorization_policy", {"mode": "independent_peer_review"})
    if policy.get("mode") == "independent_peer_review":
        return None
    if policy.get("mode") != "explicit_lead_exception":
        raise ValueError("Unknown Final authorization policy")
    name = policy["record_path"]
    path = Path(name)
    if path.is_absolute() or ".." in path.parts or lock["files"].get(name) != digest(root / path):
        raise ValueError("Missing or changed explicit lead exception record")
    record = json.loads((root / path).read_text())
    if (
        record.get("schema") != "ev-explicit-lead-final-exception-v1"
        or record.get("independent_peer_approval") is not False
        or record.get("originating_coordination_chat") != "01a13446-0da0-7fd1-b984-e655242b5497"
        or record.get("method_seed_cells") != 11340
        or record.get("whole_units") != 810
        or record.get("entity_budget_pairs") != 270
        or record.get("namespace_entity_ids") != 90
        or record.get("seeds") != [42, 43, 44]
        or record.get("history_days") != [7, 14, 28]
        or record.get("replay_days") != 90
        or hashlib.sha256(record["issue_section"].encode()).hexdigest()
        != record["issue_section_sha256"]
        or "one-time override" not in record["issue_section"]
        or record["cohort_path"] != lock["cohort_path"]
        or record["cohort_sha256"] != lock["files"].get(record["cohort_path"])
    ):
        raise ValueError("Lead exception scope/provenance differs from frozen bounded lock")
    return {
        "mode": "explicit_lead_exception",
        "record_path": name,
        "record_sha256": digest(root / path),
        "source_issue": record["issue_url"],
        "independent_peer_approval": False,
    }


def authorize(lock_path: Path, root: Path) -> FinalAccess:
    """Require current-head non-author approval and three exact lead markers."""
    root, lock_path = root.resolve(), lock_path.resolve()
    relative = lock_path.relative_to(root).as_posix()
    commit = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"], text=True):
        raise ValueError("Final requires a clean reviewed checkout")
    tracked = subprocess.check_output(["git", "-C", str(root), "show", f"HEAD:{relative}"])
    if tracked != lock_path.read_bytes():
        raise ValueError("Final lock must be tracked at reviewed HEAD")
    lock = json.loads(tracked)
    if lock.get("schema") != "ev-final-execution-lock-v1" or lock.get("method_seed_cells") != 11340:
        raise ValueError("Unsupported Final execution lock")
    exception = explicit_exception(root, lock)
    if exception is not None:
        record_name = exception["record_path"]
        if (
            subprocess.check_output(["git", "-C", str(root), "show", f"HEAD:{record_name}"])
            != (root / record_name).read_bytes()
        ):
            raise ValueError("Lead exception must be tracked at execution HEAD")
        if (
            not isinstance(lock.get("runtime_profile"), dict)
            or lock["runtime_profile"].get("device") != "cuda"
        ):
            raise ValueError("Measured CUDA runtime profile is not locked")
        access = FinalAccess(root, lock_path, commit, exception)
        access.check()
        return access
    pr = json.loads(
        subprocess.check_output(["gh", "api", f"repos/{REPOSITORY}/pulls/52"], text=True)
    )
    if pr["state"] != "open" or pr["head"]["sha"] != commit or pr["base"]["ref"] != "dev":
        raise ValueError("Final review is not on this open PR52 head into dev")
    latest = {}
    for review in github_pages("pulls/52/reviews"):
        if review["state"] != "COMMENTED":
            latest[review["user"]["login"]] = review
    approvals = [
        r
        for login, r in latest.items()
        if login != pr["user"]["login"] and r["state"] == "APPROVED" and r["commit_id"] == commit
    ]
    if not approvals:
        raise ValueError("Independent latest-head Final lock review approval is missing")
    required = {f"{marker} {digest(lock_path)}" for marker in MARKERS}
    found = set()
    for comment in github_pages("issues/23/comments"):
        if comment["user"]["login"] == LEAD:
            found.update(required.intersection(comment["body"].splitlines()))
    if found != required:
        raise ValueError("Lead Development/capacity/Final execution acceptance markers missing")
    if (
        not isinstance(lock.get("runtime_profile"), dict)
        or lock["runtime_profile"].get("device") != "cuda"
    ):
        raise ValueError("Measured CUDA runtime profile is not locked")
    access = FinalAccess(
        root, lock_path, commit, {"id": approvals[-1]["id"], "url": approvals[-1]["html_url"]}
    )
    access.check()
    return access


class FinalInputRun(InputRun):
    """Accepted validation with an explicitly approved Final target boundary."""

    target_role = "final"

    def __init__(self, root: Path, sha256: str, access: FinalAccess) -> None:
        access.check()
        self.final_access = access
        self._verified_files = {}
        super().__init__(root, sha256)

    def verify(self, name: str) -> None:
        """Authenticate once, then reject ordinary file changes within this unit."""
        if name not in {
            "training.jsonl",
            "entities.jsonl",
            "forecasts.jsonl",
            "labels.jsonl",
            "schedule.jsonl",
        }:
            super().verify(name)
        path = self.root / name
        value = path.stat()
        pin = (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        if name in self._verified_files:
            if self._verified_files[name] != pin:
                raise ValueError("Immutable Final input file changed during execution")
            return
        super().verify(name)
        self._verified_files[name] = pin

    def check_target(self, entity_id: str) -> None:
        self.final_access.input_group(self, entity_id)
        super().check_target(entity_id)

    def training(self, role: str, entity_id: str | None = None) -> list[dict]:
        if role != "final" or entity_id is None:
            raise ValueError("Final execution reuses Sources; no new Source training")
        self.check_target(entity_id)
        return super().training(role, entity_id)
