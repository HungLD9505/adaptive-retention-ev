"""Fail-closed Final access after live independent review and lead acceptance."""

import copy
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

    def check(self) -> None:
        """Recheck lock and pinned files before opening target values."""
        if digest(self.lock_path) != self.sha256:
            raise ValueError("Final lock changed after approval")
        for name, sha in self.lock["files"].items():
            path = Path(name)
            if path.is_absolute() or ".." in path.parts or digest(self.root / path) != sha:
                raise ValueError(f"Final lock file changed or unsafe path: {name}")

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
        return {"lock_sha256": self.sha256, "reviewed_commit": self.commit, "review": self.review}


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
        super().__init__(root, sha256)

    def check_target(self, entity_id: str) -> None:
        self.final_access.input_group(self, entity_id)
        super().check_target(entity_id)

    def training(self, role: str, entity_id: str | None = None) -> list[dict]:
        if role != "final" or entity_id is None:
            raise ValueError("Final execution reuses Sources; no new Source training")
        self.check_target(entity_id)
        return super().training(role, entity_id)
