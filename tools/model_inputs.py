"""Create a new development-only input run from an explicit JSON config."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sqlite3
import sys
from pathlib import Path

from ev_inputs.loader import run_inputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New unique run directory")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        config["producer_manifest"] = str(
            (args.config.resolve().parent / config["producer_manifest"]).resolve()
        )
        result = run_inputs(config, args.output)
        print(f"{result['status']}: {args.output / 'manifest.json'}")
        return 0 if result["status"] == "technical_success" else 1
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        StopIteration,
        csv.Error,
        sqlite3.Error,
    ) as error:
        print(f"Input loader failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
