"""Build a small, commit-pinned Kaggle notebook for the persistent follow-up.

Run only after the controller, dispatcher, verifier, protocol and tests are
committed. The notebook embeds code bytes; large Source/input ZIPs stay in the
already attached Kaggle dataset. No local model execution is performed.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DATASET = "/kaggle/input/datasets/hungluongduc/issue99-source10-2798384-scored-inputs-v1"
OUTER_MANIFEST_SHA256 = "a09f6a03ae5911717fd5afd070e93b52e0a3a066398278dac7b598bfd89ae088"
PREFLIGHT_SHA256 = "6bede89694d6d0dfb30fd59ed8b0305d7d374eca932e723e4af690d56ab561f6"
INCLUDE_DIRS = ("ev_inputs", "ev_models", "ev_control", "ev_runner", "ev_search")
INCLUDE_FILES = (
    "configs/issue99-persistent-protocol-v1.json",
    "docs/reports/issue99-study-20261110/fixed-station-seed.csv",
    "docs/reports/issue99-study-20261110/controller-selection.json",
)


def committed_bytes(commit: str, name: str) -> bytes:
    if subprocess.run(["git", "diff", "--quiet", commit, "--", name], cwd=ROOT, check=False).returncode:
        raise ValueError(f"Working file differs from pinned commit: {name}")
    data = subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=ROOT)
    return data


def package(commit: str) -> tuple[str, str, dict[str, str]]:
    tracked = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", commit], cwd=ROOT, text=True).splitlines()
    names = sorted(
        name for name in tracked
        if (name.endswith(".py") and name.split("/", 1)[0] in INCLUDE_DIRS)
        or (name.startswith(("tools/issue99", "tests/test_issue99")) and name.endswith(".py"))
        or name in {"tools/__init__.py", "tests/__init__.py", "tools/check_release.py"}
        or name in INCLUDE_FILES
        or (name.startswith("configs/issue99") and name.endswith(".json"))
        or name in {"pyproject.toml", "requirements-model.txt", "requirements-cuda.txt"}
    )
    required = {
        "tools/issue99_persistent_experiment.py",
        "tools/issue99_persistent_verify.py",
        "ev_control/persistent.py",
        "ev_runner/persistent.py",
        "tests/test_issue99_persistent.py",
        *INCLUDE_FILES,
    }
    if not required.issubset(names):
        raise ValueError(f"Pinned commit lacks required files: {sorted(required - set(names))}")
    memory = io.BytesIO()
    hashes = {}
    with ZipFile(memory, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for name in names:
            data = committed_bytes(commit, name)
            archive.writestr(name, data)
            hashes[name] = hashlib.sha256(data).hexdigest()
        archive.writestr(".issue99-code-commit", commit + "\n")
    payload = memory.getvalue()
    return base64.b64encode(payload).decode("ascii"), hashlib.sha256(payload).hexdigest(), hashes


def code_cell(source: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source.splitlines(keepends=True)}


def markdown_cell(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def notebook(commit: str, payload: str, payload_sha: str, files: dict[str, str]) -> dict:
    suffix = commit[:8]
    bootstrap = f'''import base64, hashlib, importlib.util, json, os, pathlib, platform, subprocess, sys, zipfile
from pathlib import Path
DATASET = Path({DATASET!r})
OUTER_SHA = {OUTER_MANIFEST_SHA256!r}
PREFLIGHT_SHA = {PREFLIGHT_SHA256!r}
COMMIT = {commit!r}
ZIP_SHA = {payload_sha!r}
FILE_HASHES = {json.dumps(files, sort_keys=True)}
PAYLOAD = {payload!r}
ROOT = Path('/kaggle/working/issue99-persistent-{suffix}')
BUNDLE = ROOT / 'verified-bundle'
STAGE = ROOT / 'stage'
CODE = ROOT / 'code'
RESULT = ROOT / 'results'
assert DATASET.is_dir(), 'Existing Source/input dataset attachment is missing'
preflight_path = DATASET / 'preflight.py'
assert hashlib.sha256(preflight_path.read_bytes()).hexdigest() == PREFLIGHT_SHA
spec = importlib.util.spec_from_file_location('issue99_existing_preflight', preflight_path)
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)
ROOT.mkdir(exist_ok=False)
runtime = preflight.rehydrate_and_stage(DATASET, BUNDLE, STAGE, expected_manifest_sha256=OUTER_SHA, require_t4=True)
raw = base64.b64decode(PAYLOAD, validate=True)
assert hashlib.sha256(raw).hexdigest() == ZIP_SHA
CODE.mkdir(exist_ok=False)
archive_path = ROOT / 'new-code-package.zip'
archive_path.write_bytes(raw)
with zipfile.ZipFile(archive_path) as archive:
    assert archive.testzip() is None
    for member in archive.namelist():
        relative = pathlib.PurePosixPath(member)
        assert not relative.is_absolute() and '..' not in relative.parts
        destination = CODE.joinpath(*relative.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(archive.read(member))
for name, expected in FILE_HASHES.items():
    assert hashlib.sha256((CODE / name).read_bytes()).hexdigest() == expected, name
assert (CODE / '.issue99-code-commit').read_text().strip() == COMMIT
sys.path.insert(0, str(CODE))
os.chdir(CODE)
RESULT.mkdir(exist_ok=False)
(RESULT / 'runtime.json').write_text(json.dumps({{'new_code_commit': COMMIT, 'new_package_sha256': ZIP_SHA, 'outer_manifest_sha256': OUTER_SHA, 'runtime': runtime}}, indent=2) + '\\n')
print(json.dumps({{'stage': 'verified', 'commit': COMMIT, 'package_sha256': ZIP_SHA, 'outer_manifest_sha256': OUTER_SHA, 'runtime': runtime}}, default=str))
'''
    test = '''import importlib.util, json, subprocess, sys
tests = [
    'tests/test_issue99_persistent.py',
    'tests/test_issue99_persistent_verify.py',
    'tests/test_issue99_continuous.py',
    'tests/test_issue99_continuous_runner.py',
    'tests/test_issue99_hypergradient.py',
    'tests/test_issue99_study_config.py',
    'tests/test_issue99_checkpoint_audit.py',
]
checks = []
def record(command, required):
    completed = subprocess.run(command, cwd=CODE, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    entry = {'command': command, 'returncode': completed.returncode, 'required_before_training': required, 'output': completed.stdout}
    checks.append(entry)
    (RESULT / 'checks.json').write_text(json.dumps(checks, indent=2) + '\\n')
    print('KAGGLE_CHECK', ' '.join(command), 'EXIT', completed.returncode, '\\n', completed.stdout[-4000:], flush=True)
    if required and completed.returncode:
        raise RuntimeError('Required technical test failed before training')
record([sys.executable, '-m', 'pytest', '-q', *tests], True)
if importlib.util.find_spec('ruff') is None:
    record([sys.executable, '-m', 'ruff', 'check', 'ev_control', 'ev_runner', 'tools/issue99_persistent_experiment.py', 'tools/issue99_persistent_verify.py'], False)
    print('README_RUFF_CHECK_UNAVAILABLE: ruff is not installed in Kaggle runtime', flush=True)
else:
    for command in ([sys.executable, '-m', 'ruff', 'check', 'ev_control', 'ev_runner', 'tools/issue99_persistent_experiment.py', 'tools/issue99_persistent_verify.py'], [sys.executable, '-m', 'ruff', 'format', '--check', 'ev_control', 'ev_runner', 'tools/issue99_persistent_experiment.py', 'tools/issue99_persistent_verify.py']):
        record(command, True)
record([sys.executable, '-m', 'tools.check_release'], False)
print('README_CHECK_RELEASE_SCOPE: embedded package has no Git history or frozen report fixtures; see checks.json', flush=True)
'''
    execute = '''import json, subprocess, sys
PROTOCOL = CODE / 'configs/issue99-persistent-protocol-v1.json'
base = [sys.executable, '-m', 'tools.issue99_persistent_experiment', '--stage', str(STAGE), '--protocol', str(PROTOCOL), '--output', str(RESULT), '--device', 'cuda']
def experiment(phase):
    print('EXPERIMENT_PHASE', phase, flush=True)
    subprocess.run([*base, '--phase', phase], cwd=CODE, check=True)
def verify(phase, output_name):
    command = [sys.executable, '-m', 'tools.issue99_persistent_verify', '--root', str(RESULT), '--inputs', str(STAGE / 'inputs'), '--protocol', str(RESULT / 'protocol-lock.json'), '--output', str(RESULT / output_name), '--phase', phase]
    print('INDEPENDENT_VERIFICATION', phase, flush=True)
    subprocess.run(command, cwd=CODE, check=True)
experiment('pilot')
verify('pilot', 'pilot-independent-verification.json')
experiment('calibration_reference')
experiment('reference_guard')
experiment('calibration_remaining')
experiment('gate')
verify('calibration', 'independent-verification.json')
gate = json.loads((RESULT / 'calibration-gate.json').read_text())
verification = json.loads((RESULT / 'independent-verification.json').read_text())
print('REGISTERED_GATE', json.dumps({'go_to_later': gate['go_to_later'], 'checks': gate['checks'], 'independent_status': verification['status'], 'independent_gate_pass': verification['gate_pass']}), flush=True)
if gate['go_to_later'] and verification['status'] == 'PASS' and verification['gate_pass']:
    experiment('evaluation')
    verify('evaluation', 'later-independent-verification.json')
else:
    print('LATER_STOPPED_BY_REGISTERED_GATE', flush=True)
'''
    report = '''import hashlib, json
from pathlib import Path
for name in ('pilot-independent-verification.json', 'reference-comparability.json', 'calibration-gate.json', 'independent-verification.json', 'later-independent-verification.json'):
    path = RESULT / name
    if path.exists():
        value = json.loads(path.read_text())
        keys = ('status', 'screen_pass', 'gate_pass', 'go_to_later', 'macro_mae_kwh', 'target_mean_mae_kwh', 'seed_macro_mae_kwh', 'checks', 'gate_checks', 'failures')
        print('SUMMARY', name, json.dumps({key: value[key] for key in keys if key in value}, allow_nan=False, sort_keys=True), flush=True)
for phase in ('calibration', 'later'):
    directory = RESULT / phase
    if directory.exists():
        for path in sorted(directory.glob('*/run.json')):
            value = json.loads(path.read_text())
            print('CELL', phase, path.parent.name, value['mae_kwh'], value['objective_scored_days'], value['invocation_wall_seconds'], value['final_lambda'], flush=True)
artifacts = []
for path in sorted(RESULT.rglob('*')):
    if path.is_file() and (path.name in ('run.json', 'calibration-gate.json', 'independent-verification.json', 'reference-comparability.json', 'runtime.json') or path.name.endswith('dispatch-summary.json')):
        artifacts.append({'path': str(path.relative_to(RESULT)), 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
print('ARTIFACT_INVENTORY', json.dumps(artifacts, sort_keys=True), flush=True)
'''
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}, "issue99_code_commit": commit, "issue99_code_package_sha256": payload_sha},
        "cells": [
            markdown_cell("# Issue #99 persistent λ follow-up\n\nExploratory Development only. This notebook uses the existing authenticated Source10/14-day dataset attachment. It creates new output paths and runs the preregistered pilot, Calibration, independent verifier and conditional Later matrix.\n"),
            code_cell(bootstrap), code_cell(test), code_cell(execute), code_cell(report),
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", help="Pinned committed code SHA; defaults to HEAD")
    args = parser.parse_args()
    commit = args.commit or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if len(commit) != 40:
        raise ValueError("Expected full git commit SHA")
    payload, payload_sha, files = package(commit)
    value = notebook(commit, payload, payload_sha, files)
    if len(json.dumps(value, ensure_ascii=False).encode("utf-8")) >= 950_000:
        raise ValueError("Embedded notebook exceeds the Kaggle source-size safety limit")
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=1)
        stream.write("\n")
    print(json.dumps({"notebook": str(args.output), "commit": commit, "package_sha256": payload_sha, "files": len(files), "bytes": args.output.stat().st_size}))


if __name__ == "__main__":
    main()
