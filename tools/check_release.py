"""Validate the supervisor-report release offline; never train or access providers."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath

FROZEN_COMMIT = "61c32328d9829a69037dca629f727b4863015122"
FROZEN_TAG = "evidence/primary-final-20261027-v2"
FROZEN_LOCK = "configs/issue23/final-execution-lock-20261027-v2.json"
LOCK_SHA256 = "9c65169cced1506a450fdd7b8a57a69d5a720cac7acaa0dcd1c8ccfd1723ce42"
REQUIRED = (
    "README.md",
    "RELEASE_SCOPE.md",
    "report/README.md",
    "report/retention-manuscript-v8.tex",
    "report/retention-supplement-v8.tex",
    "docs/ARCHIVE_INDEX.md",
    "docs/reports/main-readiness-20261102.md",
    "ev_inputs/__init__.py",
    "ev_models/__init__.py",
    "ev_control/__init__.py",
    "ev_runner/__init__.py",
    "ev_baselines/__init__.py",
    "ev_evaluation/__init__.py",
)
EXCLUDED_PREFIXES = (
    "data/raw/",
    "data/processed/",
    "data/inputs/",
    "runs/",
    ".cache/",
    ".venv/",
    "output/",
    "tmp/",
)


def git(root: Path, *args: str) -> bytes:
    """Read local repository metadata; no shell, network or writes."""
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)


def verify_report(root: Path) -> int:
    """Check the exact copied report package, rejecting links, duplicates and escapes."""
    report = root / "report"
    manifest = json.loads((report / "manifest.json").read_text())
    seen = set()
    for record in manifest["files"]:
        name = record["path"]
        parts = PurePosixPath(name).parts
        if (
            not name
            or "\\" in name
            or PurePosixPath(name).is_absolute()
            or any(p in {".", ".."} or ":" in p for p in parts)
        ):
            raise ValueError("Unsafe report asset path")
        if name in seen:
            raise ValueError("Duplicate report asset")
        seen.add(name)
        path = report / name
        if path.is_symlink() or not path.resolve().is_relative_to(report.resolve()):
            raise ValueError("Linked or escaping report asset")
        raw = path.read_bytes()
        if len(raw) != record["bytes"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
            raise ValueError(f"Report asset differs: {name}")
    if not seen:
        raise ValueError("Empty report package")
    return len(seen)


def verify_frozen_source(root: Path) -> int:
    """Authenticate original code, not a claim that today's checkout is the old runtime."""
    if git(root, "rev-parse", FROZEN_TAG).decode().strip() != FROZEN_COMMIT:
        raise ValueError("Frozen scientific tag moved")
    raw = (root / FROZEN_LOCK).read_bytes()
    if hashlib.sha256(raw).hexdigest() != LOCK_SHA256:
        raise ValueError("Frozen lock changed")
    checked = 0
    for name, expected in json.loads(raw)["files"].items():
        if name.startswith("runs/"):
            continue  # External data/checkpoints are deliberately not authenticated here.
        original = git(root, "show", f"{FROZEN_COMMIT}:{name}")
        if hashlib.sha256(original).hexdigest() != expected:
            raise ValueError(f"Frozen source differs: {name}")
        checked += 1
    return checked


def verify_attribution(root: Path) -> list[str]:
    """Check real source-head reachability; GitHub UI attribution is a separate check."""
    record = json.loads((root / "docs/reports/dev-integration-final-20261102-v1.json").read_text())
    authors = record["attribution"]
    if set(authors) != {"Qyroven", "HungLD9505", "huuduc32", "hung00cyber"}:
        raise ValueError("Four-member attribution inventory differs")
    for author, commit in authors.items():
        result = subprocess.run(
            ["git", "-C", str(root), "merge-base", "--is-ancestor", commit, "HEAD"],
            capture_output=True,
        )
        if result.returncode:
            raise ValueError(f"Member source head is not preserved: {author}")
    return sorted(authors)


def check(root: Path) -> dict:
    """Validate the release contract without external artifacts or GPU dependencies."""
    for name in REQUIRED:
        if not (root / name).is_file():
            raise ValueError(f"Required release entry point missing: {name}")
    tracked = git(root, "ls-files", "-z").decode().strip("\0").split("\0")
    forbidden = [name for name in tracked if name.startswith(EXCLUDED_PREFIXES)]
    if forbidden:
        raise ValueError(f"Generated/data directories tracked: {forbidden}")
    report_count = verify_report(root)
    report_names = {
        r["path"] for r in json.loads((root / "report/manifest.json").read_text())["files"]
    }
    required_assets = {
        "sn-jnl.cls",
        "sn-mathphys-num.bst",
        "retention-references-v6.bib",
        "full-results.csv",
        "switch-audits.csv",
    }
    for document in ("retention-manuscript-v8.tex", "retention-supplement-v8.tex"):
        required_assets.add(document)
        text = (root / "report" / document).read_text()
        for asset in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text):
            candidates = {asset, asset + ".pdf", asset + ".png"}
            if not candidates & report_names:
                raise ValueError(f"Referenced report figure missing from inventory: {asset}")
    if not required_assets.issubset(report_names):
        raise ValueError("Required report source or result tables missing from inventory")
    return {
        "schema": "ev-report-release-check-v1",
        "status": "passed",
        "code_commit": git(root, "rev-parse", "HEAD").decode().strip(),
        "report_files_verified": report_count,
        "historical_source_pins_verified": verify_frozen_source(root),
        "member_source_heads_preserved": verify_attribution(root),
        "external_artifacts_verified": False,
        "fresh_pdf_compile": False,
        "github_contributors_ui_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(check(args.root.resolve()), indent=2))


if __name__ == "__main__":
    main()
