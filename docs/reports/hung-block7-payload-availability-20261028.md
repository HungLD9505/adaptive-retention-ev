# Block7 historical checkpoint availability audit — 28 October 2026

**Scope:** read-only search for exact historical Source and Target checkpoint **file bytes** within the current repository, including its ignored cache and ZIP members. This does not compare deserialized model/optimizer/RNG payloads, establish fairness, choose a method, or access Final/test data. All 69 historical Block7 IDs remain `PENDING_PEER`.

The [69-cell pair table](hung-block7-manifest-pairs-20261028.csv) was the expected-hash source (SHA-256 `e260de421d6c53ef3dffe5901f9e3478708b9e578791d3f370588a0a508699de`). It lists 9 unique historical Source and 69 historical Target file hashes, plus 9 Main Source and 69 Main Target hashes. Paths in the copied coverage JSON that resolve to other worktrees were **not** followed.

| Repository-local search | Files/members hashed | Historical Source | Historical Target | Main Source | Main Target |
| --- | ---: | ---: | ---: | ---: | ---: |
| Direct `.pt` files | 508 | 0/9 | 0/69 | 9/9 | 69/69 |
| `.pt` members in 44 ZIPs | 22,711 | 0/9 | 0/69 | not checked | not checked |

No `.pt` or ZIP files were found under the repository's `.cache/agent-worktrees/`, so excluding that duplicate-worktree subtree did not omit a checkpoint candidate. Every direct `.pt` file and ZIP `.pt` member was streamed through SHA-256; ZIPs were opened without extraction. The direct-file scan took about seven seconds and the ZIP scan about one minute on this host. The exact expected historical **file SHA** is absent from these repository-local inventories. This does **not** disprove the earlier [PR #70](https://github.com/HungLD9505/adaptive-retention-ev/pull/70) claim that unequal checkpoint files had equal model/optimizer/latent-scale/RNG payloads after deserialization. It means that claim cannot be freshly reproduced here from the exact historical file bytes. The PR #70 body reports 9/9 and 69/69 payload equality; its tracked patch does not contain a pairwise payload-proof artifact.

The [manifest-pair audit](hung-block7-manifest-pairs-20261028.md) and [origin-event audit](hung-block7-origin-eligibility-20261028.md) remain valid at their narrower scopes. A reviewer still needs the historical checkpoint files or an accessible byte-pinned pairwise comparison proof, plus numeric/per-origin eligibility and tolerance evidence, before accepting a mapping. If the reviewer explicitly rejects equivalence, the [fairness packet](hung-block7-fairness-20261027-v1.md) describes 69 new replay IDs. This availability audit does **not** authorize those replays.

## Reproduction of this bounded search

From the repository root, use the 69-cell CSV to construct expected SHA sets, then hash direct `.pt` files and ZIP members without writing output:

```python
from pathlib import Path
from zipfile import ZipFile
import csv
import hashlib

table = Path('docs/reports/hung-block7-manifest-pairs-20261028.csv')
with table.open(newline='', encoding='utf-8') as source:
    rows = list(csv.DictReader(source))
columns = ('historical_source_sha256', 'historical_target_sha256',
           'main_source_sha256', 'main_target_sha256')
expected = {key: {row[key] for row in rows} for key in columns}
found = {key: set() for key in columns}
for path in Path('.').rglob('*.pt'):
    if 'agent-worktrees' in path.parts:
        continue
    with path.open('rb') as source:
        digest = hashlib.file_digest(source, 'sha256').hexdigest()
    for key in columns:
        if digest in expected[key]:
            found[key].add(digest)
for path in Path('.cache').rglob('*.zip'):
    if 'agent-worktrees' in path.parts:
        continue
    with ZipFile(path) as archive:
        for member in archive.infolist():
            if not member.filename.endswith('.pt'):
                continue
            with archive.open(member) as source:
                digest = hashlib.file_digest(source, 'sha256').hexdigest()
            for key in columns[:2]:
                if digest in expected[key]:
                    found[key].add(digest)
```

**Checks:** `Get-FileHash` confirmed the CSV pin; direct `.pt` scan found 508 files; ZIP inventory found 44 ZIPs and 22,711 `.pt` members. The two scans returned the counts above with exit 0. No file was changed, extracted, trained or submitted during the scan. This report is an additional evidence-bound availability finding, not a reviewer decision.
