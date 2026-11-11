"""Immutable prepared-input caching for the bounded issue99 study."""

import copy
import os
from pathlib import Path
from typing import Iterator

from ev_models.data import InputRun

_TRUST_FILE_STAT = os.name != "nt"


class PreparedInputs(InputRun):
    """Authenticate bytes; cache POSIX stats, rehash every Windows access.

    Cache only explicitly requested Development predictor/prefix rows. Replay
    label energy stays in the original delayed provider and is never cached here.
    """

    def __init__(self, root: Path, sha256: str) -> None:
        self._verified: dict[str, tuple[int, int, int, int]] = {}
        self._rows: dict[tuple, list[dict]] = {}
        super().__init__(root, sha256)
        for name in self.manifest["files"]:
            self.verify(name)

    def verify(self, name: str) -> None:
        info = (self.root / name).stat()
        stamp = (info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_ino)
        if name in self._verified:
            if self._verified[name] != stamp:
                raise ValueError(f"Immutable prepared input changed: {name}")
            if not _TRUST_FILE_STAT:
                # Windows can retain the same stat tuple across rapid same-size
                # writes. A cached tuple is not sufficient authentication there.
                try:
                    super().verify(name)
                except ValueError as error:
                    raise ValueError(f"Immutable prepared input changed: {name}") from error
        else:
            super().verify(name)
            after = (self.root / name).stat()
            if (after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_ino) != stamp:
                raise ValueError("Input changed during authentication")
            self._verified[name] = stamp

    def _selected_rows(self, name: str, role: str, entity_id: str | None) -> Iterator[dict]:
        if role != "development" or entity_id not in {"1405", "2152", "1153", "1693"}:
            raise ValueError("Prepared study cache is restricted to four Development targets")
        self.verify(name)
        key = (name, role, entity_id)
        if key not in self._rows:
            self._rows[key] = list(super()._selected_rows(name, role, entity_id))
        yield from copy.deepcopy(self._rows[key])

    def reauthenticate(self) -> None:
        """Rehash the immutable source artifacts after the final job."""
        for name in self.manifest["files"]:
            self.verify(name)
            InputRun.verify(self, name)
