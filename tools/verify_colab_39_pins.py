"""Check that the #39 Colab notebook pins a local, readable code bundle.

This is an offline preflight. It never uploads or executes the notebook.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(notebook_path: Path, bundle_path: Path, checkout_path: Path) -> dict[str, object]:
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    if len(code) != 2:
        raise ValueError("Expected two code cells")
    for index, cell in enumerate(code, start=1):
        compile("".join(cell["source"]), f"cell-{index}", "exec")
        if cell["execution_count"] is not None or cell["outputs"]:
            raise ValueError("Notebook must remain unexecuted for this preflight")
    source = "".join(code[0]["source"])
    commit = subprocess.check_output(
        ["git", "-C", str(checkout_path), "rev-parse", "HEAD"], text=True
    ).strip()
    subprocess.run(
        ["git", "-C", str(checkout_path), "bundle", "verify", str(bundle_path.resolve())],
        check=True,
        capture_output=True,
        text=True,
    )
    pins = {
        "EXPECTED_BUNDLE_SHA256": sha256_file(bundle_path),
        "EXPECTED_CODE_SHA": commit,
        "EXPECTED_SELECTION_SHA256": sha256_file(
            checkout_path / "docs/reports/hung-development-selection-20261025-v2.json"
        ),
        "EXPECTED_CONFIG_SHA256": sha256_file(
            checkout_path / "experiments/hung_sprint2/development_config_v1.json"
        ),
    }
    for name, value in pins.items():
        if f'{name} = "{value}"' not in source:
            raise ValueError(f"Notebook {name} does not match local artifact")
    if "tensor = torch.ones(8, device={DEVICE!r})" not in source:
        raise ValueError("Live device tensor probe is missing")
    return {
        "status": "PASS",
        "code_cells_compiled": len(code),
        "pins": pins,
        "notebook_sha256": sha256_file(notebook_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--notebook", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--checkout", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.notebook, args.bundle, args.checkout), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
