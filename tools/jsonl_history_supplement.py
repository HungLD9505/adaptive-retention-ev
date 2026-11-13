"""Hash-bound JSONL supplement over the exact refs of a prior recorded-use audit."""

import argparse
import json
import subprocess
from pathlib import Path

from ev_models.checkpoint import digest
from tools.data_use_history import extract


def supplement(repository: Path, prior_audit: Path, protocol: Path, output: Path) -> dict:
    """Audit original reachable blobs, avoiding contamination by subsequent execution."""
    audit = json.loads(prior_audit.read_text())
    lock = json.loads(protocol.read_text())
    revisions = sorted({ref.rsplit(" ", 1)[1] for ref in audit["git_refs"]})
    objects = subprocess.check_output(
        ["git", "rev-list", "--objects", *revisions], cwd=repository, text=True
    ).splitlines()
    records, overlaps = [], []
    selected = {(g["namespace"], t) for g in lock["groups"] for t in g["selected_ids"]}
    for row in objects:
        fields = row.split(" ", 1)
        if len(fields) != 2 or not fields[1].endswith(".jsonl"):
            continue
        oid, name = fields
        data = subprocess.check_output(["git", "cat-file", "blob", oid], cwd=repository)
        import hashlib

        declarations = sorted(extract(data, name))
        # Also inspect numeric identity tokens, not only the structured extractor.
        import re

        numeric = set(re.findall(r"(?<![0-9])[0-9]{1,10}(?![0-9])", data.decode("utf-8")))
        raw_hits = sorted((ns, entity) for ns, entity in selected if entity in numeric)
        structured_hits = sorted(
            (ns, entity)
            for ns, entity in selected
            if (ns, entity) in declarations or ("*", entity) in declarations
        )
        records.append(
            dict(
                oid=oid,
                path=name,
                sha256=hashlib.sha256(data).hexdigest(),
                bytes=len(data),
                declarations=declarations,
                selected_numeric_token_hits=raw_hits,
                selected_structured_hits=structured_hits,
            )
        )
        overlaps.extend(
            dict(path=name, oid=oid, namespace=ns, entity_id=entity)
            for ns, entity in structured_hits
        )
    result = dict(
        schema="recorded-jsonl-supplement-v1",
        prior_audit_sha256=digest(prior_audit),
        protocol_sha256=digest(protocol),
        script_sha256=digest(Path(__file__)),
        extractor_sha256=digest(repository / "tools/data_use_history.py"),
        pinned_revision_count=len(revisions),
        files=records,
        structured_selected_overlaps=overlaps,
        scope="All reachable JSONL blobs under the original audit's exact pinned refs, including fixtures; numeric hits are conservative manual-review flags, not proof of exposure. No post-lock refs enter this supplement.",
    )
    with output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            dict(
                blobs=len(records),
                structured_selected_overlaps=len(overlaps),
                numeric_flags=sum(len(r["selected_numeric_token_hits"]) for r in records),
            )
        )
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(__doc__)
    for name in ("repository", "prior-audit", "protocol", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    a = parser.parse_args()
    supplement(a.repository, a.prior_audit, a.protocol, a.output)


if __name__ == "__main__":
    main()
